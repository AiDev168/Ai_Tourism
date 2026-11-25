"""Historical capture for the exact post-0021 / 20-row ledger only.

Do not use this helper for the current 0023 live schema. Use
capture_rahgard_0023_backup.py, which checks the current image/volume/marker,
complete 22-row ledger and aggregate counts before streaming a database-only
archive. Neither helper captures PostgreSQL cluster globals or host assets.
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
from datetime import UTC, datetime
from pathlib import Path

REMOTE = r"""
import os, pathlib, re, subprocess, sys
root = pathlib.Path('/opt/rahgard-staging')
db = 'rahgard-staging-db-1'
release = (root / 'current/RELEASE_COMMIT').read_text().strip()
assert release == sys.argv[1] and re.fullmatch('[0-9a-f]{40}', release)
actual_volume = subprocess.check_output([
    'docker', 'inspect', '-f',
    '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Type}}|{{.Name}}{{end}}{{end}}',
    db,
]).decode().strip()
assert actual_volume == 'volume|rahgard_staging_pgdata'
marker = (root / 'state/database-marker').read_text().strip()
assert re.fullmatch('[0-9a-fA-F]{48}', marker)
target = ['-U', 'ai_tourism_owner', '-d', 'rahgard_pilot_vps_staging']
sql = (
    "BEGIN READ ONLY; SELECT current_setting('server_version_num')::int BETWEEN 170000 AND 179999"
    " AND (SELECT count(*) FROM public.rahgard_private_pilot_marker"
    " WHERE marker_value='" + marker + "') = 1"
    " AND (SELECT count(*) FROM system.schema_migrations) = 20"
    " AND EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id="
    "'0021_postgis_security_definer_publication'); COMMIT;"
)
checked = subprocess.check_output(['docker', 'exec', db, 'psql', '-XqAt',
    '-v', 'ON_ERROR_STOP=1', *target, '-c', sql])
assert checked.strip() == b't'
password = sys.stdin.buffer.readline(66)
assert re.fullmatch(rb'[0-9a-f]{64}\n', password)
r, w = os.pipe()
os.write(w, password)
os.close(w)
dump = subprocess.Popen(['timeout', '100', 'docker', 'exec', '-e',
    'PGOPTIONS=-c default_transaction_read_only=on -c statement_timeout=90000',
    db, 'pg_dump', *target, '-Fc'], stdout=subprocess.PIPE)
try:
    status = subprocess.run(['openssl', 'enc', '-aes-256-cbc', '-salt', '-pbkdf2',
        '-iter', '600000', '-pass', f'fd:{r}'], stdin=dump.stdout, pass_fds=(r,)).returncode
finally:
    os.close(r)
    dump.stdout.close()
assert dump.wait() == 0 and status == 0
assert (root / 'current/RELEASE_COMMIT').read_text().strip() == release
"""


def save_private(path: Path, data: bytes) -> None:
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "wb") as stream:
        stream.write(data)


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("expected_live_sha")
    cli.add_argument("backup_dir", type=Path, help="Precreated private directory outside Git")
    cli.add_argument("key_dir", type=Path, help="Separate precreated directory with a protected ACL")
    args = cli.parse_args()
    if len(args.expected_live_sha) != 40 or any(c not in "0123456789abcdef" for c in args.expected_live_sha):
        cli.error("Expected the measured full VPS SHA")
    backup_dir, key_dir = args.backup_dir.resolve(strict=True), args.key_dir.resolve(strict=True)
    repo = Path(__file__).resolve().parents[2]
    if (
        backup_dir == key_dir
        or backup_dir.is_relative_to(key_dir)
        or key_dir.is_relative_to(backup_dir)
        or any(not path.is_dir() or path.is_relative_to(repo) for path in (backup_dir, key_dir))
    ):
        cli.error("Use separate private backup and key directories outside the repository")
    password = secrets.token_hex(32).encode("ascii") + b"\n"
    mac_key = secrets.token_bytes(32)
    encoded = base64.b64encode(REMOTE.encode()).decode("ascii")
    command = f"""python3 -I -c 'import base64;exec(base64.b64decode("{encoded}"))' {args.expected_live_sha}"""
    process = subprocess.Popen(
        ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=8",
         "-o", "ServerAliveInterval=5", "-o", "ServerAliveCountMax=2", "zoneroot@rahgard-vps", command],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert process.stdin is not None and process.stdout is not None
    try:
        process.stdin.write(password)
        process.stdin.close()
        encrypted = process.stdout.read(64 * 1024 * 1024 + 1)
        if len(encrypted) > 64 * 1024 * 1024:
            raise ValueError("Encrypted dump exceeds this runner's 64 MiB bound")
        if process.wait(timeout=120) or not encrypted.startswith(b"Salted__"):
            raise ValueError("Read-only VPS snapshot or expected OpenSSL envelope failed")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        process.stdout.close()
    name = "rahgard-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4) + ".dump.enc"
    digest = hashlib.sha256(encrypted).hexdigest()
    signature = hmac.digest(mac_key, encrypted, "sha256").hex()
    save_private(key_dir / f"{name}.passphrase", password)
    save_private(key_dir / f"{name}.hmac-key", mac_key)
    save_private(backup_dir / name, encrypted)
    save_private(backup_dir / f"{name}.sha256", f"{digest}  {name}\n".encode())
    save_private(backup_dir / f"{name}.hmac", f"{signature}  {name}\n".encode())
    print(json.dumps({"backup": name, "sha256": digest, "bytes": len(encrypted), "source_sha": args.expected_live_sha}))


if __name__ == "__main__":
    main()
