"""Operator-triggered backup of a separately provisioned private pilot database.

This tool does not provision a database, schedule backups, choose retention, or
restore into any database. It needs the operator's explicit confirmation, a
PG17 database bearing the private-pilot marker, verify-full TLS, and a
separately provisioned non-superuser ai_tourism_backup role. Secrets are read
only from the process environment. Never point this tool at a shared DB.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Mapping
from uuid import uuid4

_DATABASE = re.compile(r"rahgard_pilot_[a-z0-9_]{3,40}\Z")
_MARKER = re.compile(r"[a-fA-F0-9]{32,128}\Z")
_HOST = re.compile(r"[a-zA-Z0-9.-]{1,253}\Z")
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_MARKER_SQL = """SELECT current_database(), current_user,
current_setting('server_version_num'),
(SELECT count(*) FROM public.rahgard_private_pilot_marker),
(SELECT min(marker_value) FROM public.rahgard_private_pilot_marker),
rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls,
(SELECT count(*) FROM pg_roles r WHERE pg_has_role(current_user, r.oid, 'MEMBER')
 AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls)),
has_database_privilege(current_user, current_database(), 'CREATE')
FROM pg_roles WHERE rolname=current_user"""


class BackupBlocked(ValueError):
    """A safety precondition or a database tool invocation failed."""


def _private_storage(path: str) -> Path:
    """Require verifiably private, owner-controlled storage outside the repo."""
    directory = Path(path).resolve(strict=True)
    if directory == _REPOSITORY_ROOT or _REPOSITORY_ROOT in directory.parents:
        raise BackupBlocked("private data storage must be outside the repository")
    # Windows inherited ACLs need a native ACL audit, which this tool does not
    # yet implement. Never assume directory ACLs are private on that platform.
    if os.name != "posix" or not hasattr(os, "geteuid"):
        raise BackupBlocked("private directory permissions cannot be verified on this platform")
    info = directory.stat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise BackupBlocked("private directory must be owned by the operator and mode 0700 or stricter")
    return directory


def validate_config(env: Mapping[str, str]) -> dict[str, str]:
    host = env.get("RAHGARD_PILOT_PGHOST", "")
    port = env.get("RAHGARD_PILOT_PGPORT", "")
    database = env.get("RAHGARD_PILOT_DATABASE", "")
    marker = env.get("RAHGARD_PILOT_DATABASE_MARKER", "")
    backup_dir = env.get("RAHGARD_PILOT_BACKUP_DIR", "")
    root_cert = env.get("PGSSLROOTCERT", "")
    if (
        not _HOST.fullmatch(host)
        or not port.isascii() or not port.isdigit()
        or not 1024 <= int(port) <= 65535 or int(port) == 55433
        or not _DATABASE.fullmatch(database)
        or not _MARKER.fullmatch(marker)
        or not backup_dir or not root_cert
        or not (env.get("PGPASSWORD") or env.get("PGPASSFILE"))
    ):
        raise BackupBlocked("private pilot backup configuration is incomplete or unsafe")
    directory = _private_storage(backup_dir)
    certificate = Path(root_cert).resolve(strict=True)
    if not directory.is_dir() or not certificate.is_file():
        raise BackupBlocked("backup directory or TLS root certificate is invalid")
    return {"host": host, "port": port, "database": database,
            "marker": marker.lower(), "backup_dir": str(directory), "root_cert": str(certificate)}


def _run(command: list[str], *, env: Mapping[str, str], stdout=subprocess.PIPE, stdin=None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, env=dict(env), stdout=stdout, stdin=stdin, stderr=subprocess.DEVNULL,
                              check=True, timeout=3600)
    except (OSError, subprocess.SubprocessError) as exc:
        raise BackupBlocked("database backup or verification command failed") from exc


def backup(config: Mapping[str, str], env: Mapping[str, str], *, confirmed: bool) -> Path:
    if not confirmed:
        raise BackupBlocked("explicit private-pilot backup confirmation is required")
    child_env = {key: value for key, value in env.items() if key in {
        "PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP",
        "PGPASSWORD", "PGPASSFILE",
    }}
    child_env.update({"PGSSLMODE": "verify-full", "PGSSLROOTCERT": config["root_cert"],
                      "PGAPPNAME": "rahgard-private-pilot-backup"})
    endpoint = ["-h", config["host"], "-p", config["port"], "-U", "ai_tourism_backup",
                "-d", config["database"], "-w"]
    check = _run(["psql", *endpoint, "-X", "-q", "-t", "-A", "-F", "\t", "-c", _MARKER_SQL], env=child_env)
    fields = check.stdout.decode("utf-8").strip().split("\t")
    if (len(fields) != 12 or fields[0] != config["database"] or fields[1] != "ai_tourism_backup"
            or not fields[2].isdigit() or not 170000 <= int(fields[2]) < 180000
            or fields[3] != "1" or fields[4].lower() != config["marker"]
            or fields[5:10] != ["f"] * 5 or fields[10:] != ["0", "f"]):
        raise BackupBlocked("private pilot database marker, engine, or backup role did not match")
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    directory = _private_storage(config["backup_dir"])
    final = directory / f"rahgard-pilot-{timestamp}-{uuid4().hex}.dump"
    partial = final.with_suffix(".partial")
    created = False
    try:
        # Owner-only files inside a verified private directory.
        descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        created = True
        with os.fdopen(descriptor, "wb") as output:
            _run(["pg_dump", *endpoint, "--format=custom"], env=child_env, stdout=output)
        _run(["pg_restore", "--list", str(partial)], env=child_env, stdout=subprocess.DEVNULL)
        partial.rename(final)
        return final
    except Exception:
        if created:
            partial.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-private-pilot", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = validate_config(os.environ)
        path = backup(config, os.environ, confirmed=args.confirm_private_pilot)
    except (BackupBlocked, OSError, UnicodeError):
        print("Private pilot backup blocked; verify operator configuration and privileges.", file=sys.stderr)
        return 1
    print(f"Verified archive created: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
