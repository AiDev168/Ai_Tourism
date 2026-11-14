#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
root=/opt/rahgard-staging
file="${1:-}"
confirm="${2:-}"
[[ -f "$file" && "$confirm" == rahgard_pilot_vps_staging ]] || {
  echo 'Usage: restore.sh <encrypted-backup-file> rahgard_pilot_vps_staging' >&2; exit 2;
}
test -s "$root/secrets/backup_encryption_passphrase"
sha256sum --check "$file.sha256"
tmp="$root/backups/.restore-$(date -u +%s).dump"
trap 'rm -f -- "$tmp"' EXIT
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
  -pass file:"$root/secrets/backup_encryption_passphrase" -in "$file" -out "$tmp"
pg_restore --list "$tmp" >/dev/null
compose=(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml")
"$root/current/deploy/staging/backup.sh"
"${compose[@]}" stop web api
"${compose[@]}" exec -T db pg_restore --clean --if-exists --no-owner --role=rahgard_db_owner \
  -U rahgard_db_owner -d rahgard_pilot_vps_staging < "$tmp"
"${compose[@]}" start db api web
printf 'Restore completed to the explicitly confirmed isolated staging database. Verify application and row counts before reopening access.\n'
