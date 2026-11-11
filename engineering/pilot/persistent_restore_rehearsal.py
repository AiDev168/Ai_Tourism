"""Restore an exact archive into an explicitly marked, empty rehearsal DB.

The operator must pre-create the isolated rehearsal database and role. This
tool never creates or drops databases and never targets an existing pilot DB.
It restores without ownership or grants, so role/ACL recovery remains a
separate operator rehearsal. All credentials and markers remain in env.
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Mapping

from persistent_backup import BackupBlocked, _HOST, _MARKER, _private_storage, _run

_RESTORE_DB = re.compile(r"rahgard_restore_[a-f0-9]{12}\Z")
_SHA256 = re.compile(r"[a-fA-F0-9]{64}\Z")
_GUARD_SQL = """SELECT current_database(), current_user, current_setting('server_version_num'),
(SELECT count(*) FROM public.rahgard_restore_rehearsal_marker),
(SELECT min(marker_value) FROM public.rahgard_restore_rehearsal_marker),
rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls,
(SELECT count(*) FROM pg_namespace WHERE nspname NOT LIKE 'pg_%'
 AND nspname NOT IN ('public', 'information_schema')),
(SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f')
 AND c.relname <> 'rahgard_restore_rehearsal_marker'
 AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_class'::regclass
                 AND d.objid=c.oid AND d.deptype='e')),
(SELECT count(*) FROM pg_roles r WHERE pg_has_role(current_user, r.oid, 'MEMBER')
 AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls)),
has_database_privilege(current_user, current_database(), 'CREATE')
FROM pg_roles WHERE rolname=current_user"""
_VERIFY_SQL = """SELECT current_database(), (SELECT count(*) FROM system.schema_migrations),
to_regclass('knowledge.destinations') IS NOT NULL,
to_regclass('travel.trips') IS NOT NULL,
to_regclass('identity.users') IS NOT NULL"""


@contextmanager
def _unlinked_spool(directory: Path):
    descriptor, spool_name = tempfile.mkstemp(prefix="rahgard-restore-", dir=directory)
    try:
        with os.fdopen(descriptor, "w+b") as spool:
            os.unlink(spool_name)
            yield spool
    finally:
        # If unlink failed, the spool has not yet received archive bytes.
        if os.path.exists(spool_name):
            os.unlink(spool_name)


def validate_config(env: Mapping[str, str]) -> dict[str, str]:
    host, port = env.get("RAHGARD_RESTORE_PGHOST", ""), env.get("RAHGARD_RESTORE_PGPORT", "")
    database, marker = env.get("RAHGARD_RESTORE_DATABASE", ""), env.get("RAHGARD_RESTORE_MARKER", "")
    archive, digest = env.get("RAHGARD_RESTORE_ARCHIVE", ""), env.get("RAHGARD_RESTORE_ARCHIVE_SHA256", "")
    count, root_cert = env.get("RAHGARD_RESTORE_EXPECTED_MIGRATIONS", ""), env.get("PGSSLROOTCERT", "")
    spool_dir = env.get("RAHGARD_RESTORE_SPOOL_DIR", "")
    if (not _HOST.fullmatch(host) or not port.isascii() or not port.isdigit()
            or not 1024 <= int(port) <= 65535 or int(port) == 55433
            or not _RESTORE_DB.fullmatch(database) or not _MARKER.fullmatch(marker)
            or not archive or not _SHA256.fullmatch(digest) or not count.isascii() or not count.isdigit()
            or not 13 <= int(count) <= 10000 or not root_cert or not spool_dir
            or not (env.get("PGPASSWORD") or env.get("PGPASSFILE"))):
        raise BackupBlocked("isolated restore rehearsal configuration is incomplete or unsafe")
    archive_path, cert_path = Path(archive).resolve(strict=True), Path(root_cert).resolve(strict=True)
    private_spool = _private_storage(spool_dir)
    if not archive_path.is_file() or not cert_path.is_file():
        raise BackupBlocked("archive or TLS root certificate is invalid")
    return {"host": host, "port": port, "database": database, "marker": marker.lower(),
            "archive": str(archive_path), "sha256": digest.lower(), "count": count,
            "root_cert": str(cert_path), "spool_dir": str(private_spool)}


def rehearse(config: Mapping[str, str], env: Mapping[str, str], *, confirmed: bool) -> None:
    if not confirmed:
        raise BackupBlocked("explicit isolated restore rehearsal confirmation is required")
    child_env = {key: value for key, value in env.items() if key in {
        "PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PGPASSWORD", "PGPASSFILE",
    }}
    child_env.update({"PGSSLMODE": "verify-full", "PGSSLROOTCERT": config["root_cert"],
                      "PGAPPNAME": "rahgard-isolated-restore-rehearsal"})
    endpoint = ["-h", config["host"], "-p", config["port"], "-U", "ai_tourism_restore",
                "-d", config["database"], "-w"]
    # Unlink the exclusive private spool before reading or restoring it. Both
    # pg_restore calls consume the exact same open file, so replacing the
    # original archive path after the hash check cannot change the input.
    spool_dir = _private_storage(config["spool_dir"])
    with _unlinked_spool(spool_dir) as spool:
        digest = hashlib.sha256()
        with Path(config["archive"]).open("rb") as source:
            while chunk := source.read(1024 * 1024):
                digest.update(chunk)
                spool.write(chunk)
        if digest.hexdigest() != config["sha256"]:
            raise BackupBlocked("archive hash did not match the operator-confirmed hash")
        spool.flush()
        spool.seek(0)
        _run(["pg_restore", "--list"], env=child_env, stdout=subprocess.DEVNULL, stdin=spool)
        guard = _run(["psql", *endpoint, "-X", "-q", "-t", "-A", "-F", "\t", "-c", _GUARD_SQL], env=child_env)
        fields = guard.stdout.decode("utf-8").strip().split("\t")
        if (len(fields) != 14 or fields[0] != config["database"] or fields[1] != "ai_tourism_restore"
                or not fields[2].isdigit() or not 170000 <= int(fields[2]) < 180000
                or fields[3] != "1" or fields[4].lower() != config["marker"]
                or fields[5:10] != ["f"] * 5 or fields[10:] != ["0", "0", "0", "t"]):
            raise BackupBlocked("rehearsal database is not empty, isolated, or correctly marked")
        spool.seek(0)
        _run(["pg_restore", *endpoint, "--exit-on-error", "--single-transaction", "--no-owner", "--no-acl"],
             env=child_env, stdout=subprocess.DEVNULL, stdin=spool)
    checked = _run(["psql", *endpoint, "-X", "-q", "-t", "-A", "-F", "\t", "-c", _VERIFY_SQL], env=child_env)
    if checked.stdout.decode("utf-8").strip().split("\t") != [config["database"], config["count"], "t", "t", "t"]:
        raise BackupBlocked("restore completed but expected tables or migration count did not match")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-isolated-restore", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = validate_config(os.environ)
        rehearse(config, os.environ, confirmed=args.confirm_isolated_restore)
    except (BackupBlocked, OSError, UnicodeError):
        print("Restore rehearsal blocked or failed; inspect the isolated target before retrying.", file=sys.stderr)
        return 1
    print("Restore rehearsal passed table and migration-count checks; ownership and ACLs were not restored.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
