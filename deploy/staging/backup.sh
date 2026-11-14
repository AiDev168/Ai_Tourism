#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
root=/opt/rahgard-staging
test -s "$root/secrets/backup_encryption_passphrase" || {
  echo 'Create a strong backup_encryption_passphrase file through the protected operator channel first.' >&2; exit 2;
}
compose=(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml")
stamp=$(date -u +%Y%m%dT%H%M%SZ)
tmp="$root/backups/.rahgard-$stamp.dump"
out="$root/backups/rahgard-$stamp.dump.enc"
trap 'rm -f -- "$tmp"' EXIT
"${compose[@]}" exec -T db pg_dump -U rahgard_db_owner -d rahgard_pilot_vps_staging -Fc > "$tmp"
test -s "$tmp"
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 600000 \
  -pass file:"$root/secrets/backup_encryption_passphrase" -in "$tmp" -out "$out"
sha256sum "$out" > "$out.sha256"
chmod 0600 "$out" "$out.sha256"
printf 'Encrypted database backup created: %s (copy it off-host using an approved protected channel).\n' "$out"
