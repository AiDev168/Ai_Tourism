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
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Mapping
from uuid import uuid4

from persistent_backup import (
    BackupBlocked, _HOST, _LOCAL_CONTAINER, _MARKER, _decrypt_dpapi_envelope,
    _powershell_acl, _private_storage, _run, _verify_windows_acl,
)

_RESTORE_DB = re.compile(r"rahgard_restore_[a-f0-9]{12}\Z")
_SHA256 = re.compile(r"[a-fA-F0-9]{64}\Z")
_TOC_EXTENSION = re.compile(rb"^\s*\d+;\s+\d+\s+\d+\s+EXTENSION\s+-\s+([A-Za-z0-9_]+)(?:\s+.*)?\s*$")
_TOC_EXTENSION_COMMENT = re.compile(
    rb"^\s*\d+;\s+\d+\s+\d+\s+(?:COMMENT|ACL)\s+-\s+EXTENSION\s+([A-Za-z0-9_]+)(?:\s+.*)?\s*$"
)
_TOC_EXTENSION_SCHEMA = re.compile(
    rb"^\s*\d+;\s+\d+\s+\d+\s+SCHEMA\s+-\s+(tiger|topology)(?:\s+.*)?\s*$"
)
_TOC_EXTENSION_SCHEMA_COMMENT = re.compile(
    rb"^\s*\d+;\s+\d+\s+\d+\s+(?:COMMENT|ACL)\s+-\s+SCHEMA\s+(?:-\s+)?(tiger|topology)(?:\s+.*)?\s*$"
)
_TOC_POSTGIS_REFERENCE_DATA = re.compile(
    rb"^\s*\d+;\s+\d+\s+\d+\s+TABLE DATA\s+public\s+spatial_ref_sys(?:\s+.*)?\s*$"
)
_ALLOWED_EXTENSIONS = {
    "fuzzystrmatch", "plpgsql", "postgis", "postgis_tiger_geocoder", "postgis_topology", "vector",
}
_REQUIRED_EXTENSIONS = _ALLOWED_EXTENSIONS - {"plpgsql"}
_REQUIRED_EXTENSION_SCHEMAS = {"tiger", "topology"}
_GUARD_SQL = """SELECT current_database(), current_user, current_setting('server_version_num'),
(SELECT count(*) FROM public.rahgard_restore_rehearsal_marker),
(SELECT min(marker_value) FROM public.rahgard_restore_rehearsal_marker),
rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls,
(SELECT count(*) FROM pg_namespace WHERE nspname NOT LIKE 'pg_%'
 AND nspname NOT IN ('public', 'information_schema', 'tiger', 'topology')),
(SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname NOT LIKE 'pg_%' AND n.nspname <> 'information_schema'
 AND c.relkind IN ('r','p','v','m','S','f')
 AND NOT (n.nspname='public' AND c.relname='rahgard_restore_rehearsal_marker')
 AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid='pg_class'::regclass
                 AND d.objid=c.oid AND d.deptype='e')),
(SELECT count(*) FROM pg_roles r WHERE pg_has_role(current_user, r.oid, 'MEMBER')
 AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls)),
(SELECT count(*) FROM pg_extension WHERE extname NOT IN (
 'fuzzystrmatch', 'plpgsql', 'postgis', 'postgis_tiger_geocoder', 'postgis_topology', 'vector')),
COALESCE((SELECT extversion FROM pg_extension WHERE extname='postgis'), ''),
COALESCE((SELECT extversion FROM pg_extension WHERE extname='vector'), ''),
COALESCE((SELECT extversion FROM pg_extension WHERE extname='plpgsql'), ''),
COALESCE((SELECT extversion FROM pg_extension WHERE extname='fuzzystrmatch'), ''),
COALESCE((SELECT extversion FROM pg_extension WHERE extname='postgis_topology'), ''),
COALESCE((SELECT extversion FROM pg_extension WHERE extname='postgis_tiger_geocoder'), ''),
has_database_privilege(current_user, current_database(), 'CREATE')
FROM pg_roles WHERE rolname=current_user"""
_VERIFY_SQL = """SELECT current_database(), (SELECT count(*) FROM system.schema_migrations),
to_regclass('knowledge.destinations') IS NOT NULL,
to_regclass('travel.trips') IS NOT NULL,
to_regclass('identity.users') IS NOT NULL"""


@contextmanager
def _unlinked_spool(directory: Path):
    descriptor, spool_name = tempfile.mkstemp(prefix="rahgard-restore-", dir=directory)
    spool_path = Path(spool_name)
    try:
        if os.name == "nt":
            os.close(descriptor)
            _powershell_acl(spool_path, mode="secure-file")
            _verify_windows_acl(spool_path, directory=False)
            with spool_path.open("r+b", buffering=0) as spool:
                yield spool
        else:
            with os.fdopen(descriptor, "w+b") as spool:
                os.unlink(spool_name)
                yield spool
    finally:
        # Windows cannot unlink an open file. Its ACL is owner/SYSTEM-only,
        # and it is removed after the handle closes. Cleanup failure is fatal:
        # do not report a completed restore while a private plaintext spool remains.
        if os.path.lexists(spool_name):
            try:
                os.unlink(spool_name)
            except OSError:
                raise BackupBlocked("private restore spool cleanup failed") from None
        if os.path.lexists(spool_name):
            raise BackupBlocked("private restore spool remains after cleanup")


@contextmanager
def _private_toc_file(directory: Path, contents: bytes):
    """Create a short-lived, owner-only pg_restore TOC file."""
    descriptor, toc_name = tempfile.mkstemp(prefix="rahgard-restore-toc-", suffix=".txt", dir=directory)
    toc_path = Path(toc_name)
    try:
        if os.name == "nt":
            os.close(descriptor)
            descriptor = -1
            _powershell_acl(toc_path, mode="secure-file")
            _verify_windows_acl(toc_path, directory=False)
            toc_path.write_bytes(contents)
        else:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb") as toc:
                descriptor = -1
                toc.write(contents)
                toc.flush()
        yield toc_path
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            toc_path.unlink(missing_ok=True)
        except OSError:
            raise BackupBlocked("private restore TOC cleanup failed") from None
        if toc_path.exists():
            raise BackupBlocked("private restore TOC remains after cleanup")


@contextmanager
def _restore_toc_path(directory: Path, contents: bytes, env: Mapping[str, str]):
    """Expose the filtered TOC only to the database client that consumes it."""
    container = env.get("RAHGARD_PILOT_DOCKER_CONTAINER", "")
    if not container:
        with _private_toc_file(directory, contents) as path:
            yield str(path)
        return
    if not _LOCAL_CONTAINER.fullmatch(container):
        raise BackupBlocked("private restore container binding is invalid")
    name = f"rahgard-restore-toc-{uuid4().hex}.txt"
    if not re.fullmatch(r"rahgard-restore-toc-[0-9a-f]{32}\.txt", name):
        raise BackupBlocked("private restore TOC name is invalid")
    path = f"/tmp/{name}"
    child_env = {key: value for key, value in env.items()
                 if key in {"PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}}
    command = ["docker", "exec", "-i", container, "sh", "-c", 'umask 077; cat > "$1"', "sh", path]
    try:
        subprocess.run(command, env=child_env, input=contents, stdout=subprocess.DEVNULL,
                       stderr=subprocess.PIPE, check=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        raise BackupBlocked("private restore TOC could not be staged in the task-owned database container") from None
    try:
        yield path
    finally:
        try:
            subprocess.run(["docker", "exec", container, "rm", "--", path], env=child_env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            raise BackupBlocked("private restore TOC cleanup in the task-owned database container failed") from None


def _filter_extension_toc(contents: bytes) -> bytes:
    """Skip extension DDL only for the exact extensions installed by the operator."""
    if not contents or len(contents) > 20 * 1024 * 1024:
        raise BackupBlocked("restore table-of-contents is empty or exceeds its safety bound")
    found: set[str] = set()
    found_schemas: set[str] = set()
    retained: list[bytes] = []
    for line in contents.splitlines(keepends=True):
        extension_match = _TOC_EXTENSION.match(line.rstrip(b"\r\n"))
        related_match = _TOC_EXTENSION_COMMENT.match(line.rstrip(b"\r\n"))
        schema_match = _TOC_EXTENSION_SCHEMA.match(line.rstrip(b"\r\n"))
        schema_related_match = _TOC_EXTENSION_SCHEMA_COMMENT.match(line.rstrip(b"\r\n"))
        postgis_reference_data = _TOC_POSTGIS_REFERENCE_DATA.match(line.rstrip(b"\r\n"))
        match = extension_match or related_match
        if match:
            name = match.group(1).decode("ascii").lower()
            if name not in _ALLOWED_EXTENSIONS:
                raise BackupBlocked("backup contains an unapproved database extension")
            if extension_match:
                found.add(name)
                continue
            continue
        schema_entry = schema_match or schema_related_match
        if schema_entry:
            name = schema_entry.group(1).decode("ascii").lower()
            if schema_match:
                found_schemas.add(name)
            continue
        if postgis_reference_data:
            # This data belongs to the preinstalled, version-checked PostGIS
            # extension and cannot be restored by the least-privilege role.
            continue
        if b"EXTENSION" in line and re.match(rb"^\s*\d+;", line):
            raise BackupBlocked("backup contains an unrecognized extension-related restore entry")
        retained.append(line)
    if not _REQUIRED_EXTENSIONS.issubset(found):
        raise BackupBlocked("backup is missing a required approved database extension")
    if not _REQUIRED_EXTENSION_SCHEMAS.issubset(found_schemas):
        raise BackupBlocked("backup is missing an expected PostGIS-owned schema entry")
    return b"".join(retained)


def validate_config(env: Mapping[str, str]) -> dict[str, str]:
    host, port = env.get("RAHGARD_RESTORE_PGHOST", ""), env.get("RAHGARD_RESTORE_PGPORT", "")
    database, marker = env.get("RAHGARD_RESTORE_DATABASE", ""), env.get("RAHGARD_RESTORE_MARKER", "")
    archive, digest = env.get("RAHGARD_RESTORE_ARCHIVE", ""), env.get("RAHGARD_RESTORE_ARCHIVE_SHA256", "")
    count, root_cert = env.get("RAHGARD_RESTORE_EXPECTED_MIGRATIONS", ""), env.get("PGSSLROOTCERT", "")
    spool_dir = env.get("RAHGARD_RESTORE_SPOOL_DIR", "")
    docker_container = env.get("RAHGARD_PILOT_DOCKER_CONTAINER", "")
    if (not _HOST.fullmatch(host) or not port.isascii() or not port.isdigit()
            or not 1024 <= int(port) <= 65535 or int(port) == 55433
            or not _RESTORE_DB.fullmatch(database) or not _MARKER.fullmatch(marker)
            or not archive or not _SHA256.fullmatch(digest) or not count.isascii() or not count.isdigit()
            or not 13 <= int(count) <= 10000 or not root_cert or not spool_dir
            or (not docker_container and not (env.get("PGPASSWORD") or env.get("PGPASSFILE")))
            or (docker_container and not _LOCAL_CONTAINER.fullmatch(docker_container))):
        raise BackupBlocked("isolated restore rehearsal configuration is incomplete or unsafe")
    archive_path, cert_path = Path(archive).resolve(strict=True), Path(root_cert).resolve(strict=True)
    private_spool = _private_storage(spool_dir)
    if not archive_path.is_file() or not cert_path.is_file():
        raise BackupBlocked("archive or TLS root certificate is invalid")
    return {"host": host, "port": port, "database": database, "marker": marker.lower(),
            "archive": str(archive_path), "sha256": digest.lower(), "count": count,
            "root_cert": str(cert_path), "spool_dir": str(private_spool),
            "docker_container": docker_container}


def rehearse(config: Mapping[str, str], env: Mapping[str, str], *, confirmed: bool) -> dict | None:
    if not confirmed:
        raise BackupBlocked("explicit isolated restore rehearsal confirmation is required")
    child_env = {key: value for key, value in env.items() if key in {
        "PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "PGPASSWORD", "PGPASSFILE",
        "RAHGARD_PILOT_DOCKER_CONTAINER",
    }}
    child_env.update({"PGSSLMODE": "verify-full", "PGSSLROOTCERT": config["root_cert"],
                      "PGAPPNAME": "rahgard-isolated-restore-rehearsal"})
    endpoint = (["-U", "ai_tourism_restore", "-d", config["database"], "-w"] if config["docker_container"]
                else ["-h", config["host"], "-p", config["port"], "-U", "ai_tourism_restore",
                      "-d", config["database"], "-w"])
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
        guard = _run(["psql", *endpoint, "-X", "-q", "-t", "-A", "-F", "\t", "-c", _GUARD_SQL], env=child_env)
        fields = guard.stdout.decode("utf-8").strip().split("\t")
        if (len(fields) != 21 or fields[0] != config["database"] or fields[1] != "ai_tourism_restore"
                or not fields[2].isdigit() or not 170000 <= int(fields[2]) < 180000
                or fields[3] != "1" or fields[4].lower() != config["marker"]
                or fields[5:10] != ["f"] * 5 or fields[10:12] != ["0", "0"]
                or fields[12:14] != ["0", "0"] or not re.fullmatch(r"3\.6\.[0-9]+", fields[14])
                or fields[15] != "0.8.7" or fields[16] != "1.0" or fields[17] != "1.2"
                or not re.fullmatch(r"3\.6\.[0-9]+", fields[18])
                or not re.fullmatch(r"3\.6\.[0-9]+", fields[19]) or fields[20:] != ["t"]):
            raise BackupBlocked("rehearsal database is not empty, isolated, or correctly marked")
        if os.name == "nt":
            # Encrypted input is never decrypted to the source directory or
            # filesystem temp root; only the already-verified private spool.
            with _unlinked_spool(spool_dir) as plaintext:
                metadata = _decrypt_dpapi_envelope(spool, plaintext)
                plaintext.seek(0)
                listing = _run(["pg_restore", "--list"], env=child_env, stdin=plaintext)
                filtered_toc = _filter_extension_toc(listing.stdout)
                with _restore_toc_path(spool_dir, filtered_toc, child_env) as toc_path:
                    plaintext.seek(0)
                    _run(["pg_restore", *endpoint, "--use-list", str(toc_path), "--exit-on-error",
                          "--single-transaction", "--no-owner", "--no-acl"],
                         env=child_env, stdout=subprocess.DEVNULL, stdin=plaintext)
        else:
            listing = _run(["pg_restore", "--list"], env=child_env, stdin=spool)
            filtered_toc = _filter_extension_toc(listing.stdout)
            with _restore_toc_path(spool_dir, filtered_toc, child_env) as toc_path:
                spool.seek(0)
                _run(["pg_restore", *endpoint, "--use-list", str(toc_path), "--exit-on-error",
                      "--single-transaction", "--no-owner", "--no-acl"],
                     env=child_env, stdout=subprocess.DEVNULL, stdin=spool)
            metadata = None
    checked = _run(["psql", *endpoint, "-X", "-q", "-t", "-A", "-F", "\t", "-c", _VERIFY_SQL], env=child_env)
    if checked.stdout.decode("utf-8").strip().split("\t") != [config["database"], config["count"], "t", "t", "t"]:
        raise BackupBlocked("restore completed but expected tables or migration count did not match")
    return metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-isolated-restore", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = validate_config(os.environ)
        metadata = rehearse(config, os.environ, confirmed=args.confirm_isolated_restore)
    except BackupBlocked as exc:
        print(f"Restore rehearsal blocked: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as exc:
        print(f"Restore rehearsal blocked: {type(exc).__name__}", file=sys.stderr)
        return 1
    if metadata is None:
        print("Restore rehearsal passed table and migration-count checks; ownership and ACLs were not restored.")
    else:
        print(json.dumps({"status": "restore_rehearsal_passed", "envelope": metadata,
                          "ownership_acl_restored": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
