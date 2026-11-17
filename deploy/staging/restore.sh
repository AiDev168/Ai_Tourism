#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
root=/opt/rahgard-staging
db_owner=ai_tourism_owner
db_name=rahgard_pilot_vps_staging
file="${1:-}"
confirm="${2:-}"
[[ -f "$file" && "$confirm" == rahgard_pilot_vps_staging ]] || {
  echo 'Usage: restore.sh <encrypted-backup-file> rahgard_pilot_vps_staging' >&2; exit 2;
}
test -s "$root/secrets/backup_encryption_passphrase"
[[ -f "$root/secrets/portable_bundle_hmac_key" && ! -L "$root/secrets/portable_bundle_hmac_key" && -s "$root/secrets/portable_bundle_hmac_key" ]] || {
  echo 'Independent backup HMAC key is unavailable; refusing unauthenticated restore.' >&2; exit 2;
}
[[ -f "$file.hmac" && ! -L "$file.hmac" && -s "$file.hmac" ]] || {
  echo 'This backup has no authenticated HMAC sidecar (legacy backup retained but not restorable by this guarded command).' >&2; exit 2;
}
python3 - "$root/secrets/portable_bundle_hmac_key" "$file" "$file.hmac" <<'PY'
import hashlib, hmac, os, re, sys
key_path, encrypted_path, mac_path = sys.argv[1:]
with open(key_path, "rb") as f:
    key = f.read()
if len(key) < 32:
    raise SystemExit("Backup HMAC key must contain at least 32 random bytes.")
with open(mac_path, "r", encoding="ascii") as f:
    line = f.read(257)
if len(line) > 256:
    raise SystemExit("Backup HMAC sidecar is too large.")
m = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.-]+)\n", line)
if not m or m.group(2) != os.path.basename(encrypted_path):
    raise SystemExit("Invalid backup HMAC sidecar; refusing restore.")
mac = hmac.new(key, digestmod=hashlib.sha256)
with open(encrypted_path, "rb") as f:
    for block in iter(lambda: f.read(1024 * 1024), b""):
        mac.update(block)
if not hmac.compare_digest(mac.hexdigest(), m.group(1)):
    raise SystemExit("Backup authentication failed; refusing decrypt/restore.")
PY
sha256sum --check "$file.sha256"
tmp="$root/backups/.restore-$(date -u +%s).dump"
trap 'rm -f -- "$tmp"' EXIT
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
  -pass file:"$root/secrets/backup_encryption_passphrase" -in "$file" -out "$tmp"
pg_restore --list "$tmp" >/dev/null
compose=(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml")
"$root/current/deploy/staging/backup.sh"
"${compose[@]}" stop web api
"${compose[@]}" exec -T db pg_restore --clean --if-exists --no-owner --role="$db_owner" \
  -U "$db_owner" -d "$db_name" < "$tmp"
"${compose[@]}" start db api web
printf 'Restore completed to the explicitly confirmed isolated staging database. Verify application and row counts before reopening access.\n'
