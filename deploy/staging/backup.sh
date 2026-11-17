#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
root=/opt/rahgard-staging
test -s "$root/secrets/backup_encryption_passphrase" || {
  echo 'Create a strong backup_encryption_passphrase file through the protected operator channel first.' >&2; exit 2;
}
test -s "$root/secrets/portable_bundle_hmac_key" || {
  echo 'Create an independent portable_bundle_hmac_key through a protected operator channel first.' >&2; exit 2;
}
[[ -f "$root/secrets/portable_bundle_hmac_key" && ! -L "$root/secrets/portable_bundle_hmac_key" ]] || {
  echo 'Portable HMAC key must be a regular non-symlink file.' >&2; exit 2;
}
compose=(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml")
db_owner=ai_tourism_owner
db_name=rahgard_pilot_vps_staging
stamp=$(date -u +%Y%m%dT%H%M%SZ)
tmp=$(mktemp "$root/backups/.rahgard-$stamp.XXXXXX.dump")
nonce=$(basename "$tmp" .dump)
out="$root/backups/rahgard-$stamp-${nonce##*.}.dump.enc"
trap 'rm -f -- "$tmp"' EXIT
"${compose[@]}" exec -T db pg_dump -U "$db_owner" -d "$db_name" -Fc > "$tmp"
test -s "$tmp"
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 600000 \
  -pass file:"$root/secrets/backup_encryption_passphrase" -in "$tmp" -out "$out"
python3 - "$root/secrets/portable_bundle_hmac_key" "$out" "$out.hmac" <<'PY'
import hashlib, hmac, os, sys
key_path, encrypted_path, mac_path = sys.argv[1:]
with open(key_path, "rb") as f:
    key = f.read()
if len(key) < 32:
    raise SystemExit("Portable HMAC key must contain at least 32 random bytes.")
mac = hmac.new(key, digestmod=hashlib.sha256)
with open(encrypted_path, "rb") as f:
    for block in iter(lambda: f.read(1024 * 1024), b""):
        mac.update(block)
with open(mac_path, "x", encoding="ascii") as f:
    f.write(mac.hexdigest() + "  " + os.path.basename(encrypted_path) + "\n")
PY
sha256sum "$out" > "$out.sha256"
chmod 0600 "$out" "$out.hmac" "$out.sha256"
printf 'Authenticated encrypted database backup created: %s (copy bundle and sidecars off-host using an approved protected channel).\n' "$out"
