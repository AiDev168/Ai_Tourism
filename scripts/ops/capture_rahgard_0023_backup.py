"""Capture the exact verified PG17/0023 database as an encrypted off-host rehearsal input.

The target is hard-bound to the existing SSH alias, database, protected marker
file, PostgreSQL volume, legacy release marker and observed API/Web image tags.
It performs SELECT-only identity/count checks plus a transaction-consistent
pg_dump; it does not freeze, stop or write to the live application/database.
This is a migration-rehearsal database archive, not a complete relocation bundle.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from check_rahgard_v2_ledger import check_current_snapshot

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "docs/operations/evidence/issue27/R3-live-snapshot-2026-11-25.json"
MAX_ENCRYPTED_BYTES = 1024 * 1024 * 1024
MIN_FREE_BYTES = 2 * MAX_ENCRYPTED_BYTES

REMOTE = r'''
import hashlib, json, os, pathlib, re, subprocess, sys
root = pathlib.Path('/opt/rahgard-staging')
db_container = 'rahgard-staging-db-1'
db_name = 'rahgard_pilot_vps_staging'
def output(command, phase):
    try:
        return subprocess.check_output(command, stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        raise SystemExit('PHASE=' + phase)
def require(value, phase):
    if not value:
        raise SystemExit('PHASE=' + phase)
release = (root / 'current/RELEASE_COMMIT').read_text().strip()
require(release == expected['legacy_release_marker'] and re.fullmatch(r'[0-9a-f]{40}', release), 'RELEASE_MARKER')
require(output(['docker','inspect','-f','{{.Config.Image}}|{{.State.Health.Status}}','rahgard-staging-api-1'],'API_IMAGE') == expected['api_image'] + '|healthy', 'API_IMAGE')
require(output(['docker','inspect','-f','{{.Config.Image}}|{{.State.Health.Status}}','rahgard-staging-web-1'],'WEB_IMAGE') == expected['web_image'] + '|healthy', 'WEB_IMAGE')
require(output(['docker','inspect','-f','{{.Config.Image}}|{{.State.Health.Status}}',db_container],'DB_IMAGE') == 'rahgard-postgres:17-postgis36-vector087|healthy', 'DB_IMAGE')
require(output(['docker','inspect','-f','{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Type}}|{{.Name}}{{end}}{{end}}',db_container],'DB_VOLUME') == 'volume|rahgard_staging_pgdata', 'DB_VOLUME')
marker = (root / 'state/database-marker').read_text().strip()
require(re.fullmatch(r'[0-9a-fA-F]{48}', marker), 'HOST_MARKER')
target = ['-U','ai_tourism_owner','-d',db_name]
version = output(['docker','exec',db_container,'psql','-XqAt',*target,'-c',"SELECT current_setting('server_version_num')::integer"],'PG_VERSION')
require(version.isdigit() and 170000 <= int(version) < 180000, 'PG_VERSION')
marker_count = output(['docker','exec',db_container,'psql','-XqAt','-v','ON_ERROR_STOP=1',*target,'-c',"SELECT count(*) FROM public.rahgard_private_pilot_marker WHERE marker_value='"+marker+"'"],'DB_MARKER')
require(marker_count == '1', 'DB_MARKER')
ledger = output(['docker','exec',db_container,'psql','-XqAt',*target,'-c',"SELECT migration_id||'|'||rtrim(sha256) FROM system.schema_migrations ORDER BY migration_id"],'MIGRATION_LEDGER')
require(hashlib.sha256(ledger.encode()).hexdigest() == expected['ledger_sha256'], 'MIGRATION_LEDGER')
counts_sql = "SELECT 'users',count(*) FROM identity.users UNION ALL SELECT 'sessions',count(*) FROM identity.web_sessions UNION ALL SELECT 'trips',count(*) FROM travel.trips UNION ALL SELECT 'conversations',count(*) FROM conversation.conversations UNION ALL SELECT 'itineraries',count(*) FROM travel.itineraries UNION ALL SELECT 'organizations',count(*) FROM partner.organizations UNION ALL SELECT 'published_destinations',count(*) FROM knowledge.production_destinations ORDER BY 1"
counts = output(['docker','exec',db_container,'psql','-XqAt','-F','|',*target,'-c',counts_sql],'AGGREGATE_COUNTS')
require(counts == expected['aggregate_counts_text'], 'AGGREGATE_COUNTS')
size_text = output(['docker','exec',db_container,'psql','-XqAt',*target,'-c','SELECT pg_database_size(current_database())'],'DATABASE_SIZE')
require(size_text.isdigit() and 0 < int(size_text) <= expected['max_database_bytes'], 'DATABASE_SIZE')
password = bytes.fromhex(PASSPHRASE_HEX)
assert len(password) == 32
read_fd, write_fd = os.pipe()
os.write(write_fd, password)
os.close(write_fd)
dump = subprocess.Popen(['timeout','900','docker','exec','-e','PGOPTIONS=-c default_transaction_read_only=on -c statement_timeout=840000',db_container,'pg_dump',*target,'-Fc'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
try:
    encrypted = subprocess.run(['openssl','enc','-aes-256-cbc','-salt','-pbkdf2','-iter','600000','-pass',f'fd:{read_fd}'],stdin=dump.stdout,stdout=sys.stdout.buffer,stderr=subprocess.DEVNULL,pass_fds=(read_fd,)).returncode
finally:
    os.close(read_fd)
    dump.stdout.close()
require(dump.wait() == 0 and encrypted == 0, 'PG_DUMP_ENCRYPT')
assert (root / 'current/RELEASE_COMMIT').read_text().strip() == release
'''


def _private_paths(backup_dir: Path, key_dir: Path) -> tuple[Path, Path]:
    if not backup_dir.is_dir() or not key_dir.is_dir():
        raise ValueError("Create separate private backup and key directories first")
    if backup_dir.resolve() == key_dir.resolve() or backup_dir.resolve() in key_dir.resolve().parents or key_dir.resolve() in backup_dir.resolve().parents:
        raise ValueError("Backup and key directories must be distinct and non-nested")
    if ROOT in backup_dir.resolve().parents or ROOT in key_dir.resolve().parents:
        raise ValueError("Backup and key directories must be outside the Git checkout")
    sys.path.insert(0, str(ROOT / "engineering/pilot"))
    from persistent_backup import _private_storage
    return _private_storage(str(backup_dir)), _private_storage(str(key_dir))


def _save_private(path: Path, payload: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        if os.name == "nt":
            os.close(fd)
            fd = -1
            sys.path.insert(0, str(ROOT / "engineering/pilot"))
            from persistent_backup import _powershell_acl, _verify_windows_acl, _windows_current_sid
            # Windows may assign a privileged-token group as owner for files
            # created from an elevated process. These files are newly created
            # by this tool inside our verified private directory, so bind the
            # owner to the interactive caller before installing the DACL.
            current_sid = _windows_current_sid()
            subprocess.run(["icacls.exe", str(path), "/setowner", f"*{current_sid}"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=True, timeout=15)
            _powershell_acl(path, mode="secure-file")
            _verify_windows_acl(path, directory=False)
            with path.open("wb") as stream:
                stream.write(payload)
        else:
            with os.fdopen(fd, "wb") as stream:
                fd = -1
                stream.write(payload)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        if fd >= 0:
            os.close(fd)


def capture(manifest: dict, source_sha: str, backup_dir: Path, key_dir: Path) -> dict:
    check_current_snapshot(manifest, source_sha)
    backup_dir, key_dir = _private_paths(backup_dir, key_dir)
    free = shutil.disk_usage(backup_dir).free
    if free < MIN_FREE_BYTES:
        raise ValueError("Insufficient free space for bounded encrypted archive and restore spool")
    db = manifest["vps"]["database"]
    ledger_text = "\n".join(f"{row['migration_id']}|{row['sha256']}" for row in db["migration_ledger"])
    counts_text = "\n".join(f"{key}|{db['aggregate_counts'][key]}" for key in sorted(db["aggregate_counts"]))
    expected = {
        "legacy_release_marker": manifest["vps"]["legacy_release_marker"],
        "api_image": manifest["vps"]["api_image"], "web_image": manifest["vps"]["web_image"],
        "ledger_sha256": hashlib.sha256(ledger_text.encode()).hexdigest(),
        "aggregate_counts_text": counts_text, "max_database_bytes": MAX_ENCRYPTED_BYTES,
    }
    # PostgreSQL returns UNION rows sorted by label; match the manifest's sorted order.
    passphrase = secrets.token_hex(32).encode("ascii") + b"\n"
    remote_prefix = (
        "import base64,json\n"
        f"expected=json.loads(base64.b64decode({base64.b64encode(json.dumps(expected, separators=(',', ':')).encode()).decode()!r}))\n"
        f"PASSPHRASE_HEX={passphrase.strip().decode('ascii')!r}\n"
    )
    remote_script = (remote_prefix + REMOTE).encode("utf-8")
    hmac_key = secrets.token_bytes(32)
    process = subprocess.Popen(
        ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=10",
         "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=2", "rahgard-vps", "sudo -n python3 -I -"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    try:
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(remote_script)
        process.stdin.close()
        encrypted = process.stdout.read(MAX_ENCRYPTED_BYTES + 1)
        if len(encrypted) > MAX_ENCRYPTED_BYTES:
            process.kill()
            raise ValueError("Encrypted database archive exceeds 1 GiB safety bound")
        status = process.wait(timeout=960)
        remote_error = process.stderr.read(2048) if process.stderr else b""
        if status != 0 or not encrypted.startswith(b"Salted__"):
            match = re.search(rb"PHASE=([A-Z_]+)", remote_error)
            phase = match.group(1).decode("ascii") if match else "SSH_OR_REMOTE_COMMAND"
            raise ValueError(f"VPS read-only backup failed at {phase}; no success artifact was written")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if process.stdout:
            process.stdout.close()
        if process.stderr:
            process.stderr.close()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    name = f"rahgard-pg17-0023-{stamp}-{secrets.token_hex(4)}.dump.enc"
    digest = hashlib.sha256(encrypted).hexdigest()
    signature = hmac.digest(hmac_key, encrypted, "sha256").hex()
    created: list[Path] = []
    try:
        for path, payload in (
            (key_dir / f"{name}.passphrase", passphrase),
            (key_dir / f"{name}.hmac-key", hmac_key),
            (backup_dir / name, encrypted),
            (backup_dir / f"{name}.sha256", f"{digest}  {name}\n".encode("ascii")),
            (backup_dir / f"{name}.hmac", f"{signature}  {name}\n".encode("ascii")),
        ):
            _save_private(path, payload)
            created.append(path)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return {"status": "encrypted_database_snapshot_created", "archive": name,
            "sha256": digest, "bytes": len(encrypted), "verified_source_sha": source_sha,
            "ledger_rows": len(db["migration_ledger"]), "ledger_head": db["migration_ledger"][-1]["migration_id"],
            "data_scope": "PostgreSQL custom archive only; no host files or secrets included"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_sha")
    parser.add_argument("backup_dir", type=Path)
    parser.add_argument("key_dir", type=Path)
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[0-9a-f]{40}", args.source_sha):
            raise ValueError("Invalid source SHA")
        manifest = json.loads(args.snapshot.read_text(encoding="utf-8"))
        print(json.dumps(capture(manifest, args.source_sha, args.backup_dir, args.key_dir), sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        print(f"BLOCKED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
