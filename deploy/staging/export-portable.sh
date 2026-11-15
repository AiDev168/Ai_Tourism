#!/usr/bin/env bash
# Encrypted, self-contained portability snapshot; does not modify the database.
set -Eeuo pipefail
umask 077
root=/opt/rahgard-staging
test -s "$root/.env"
test -s "$root/secrets/backup_encryption_passphrase"
test -d "$root/state"
test -d "$root/backups"
sha=$(cat "$root/current/RELEASE_COMMIT")
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid release SHA.' >&2; exit 2; }
test -d "$root/releases/$sha"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
tmp=$(mktemp -d "$root/backups/.portable-$stamp.XXXXXX")
out="$root/backups/rahgard-portable-$stamp-$sha.tar.enc"
trap 'rm -rf -- "$tmp"' EXIT
mkdir -m 0700 "$tmp/private"
cp -- "$root/.env" "$tmp/private/host.env"
cp -a -- "$root/secrets" "$tmp/private/secrets"
cp -a -- "$root/state" "$tmp/private/state"
cp -a -- "$root/releases/$sha" "$tmp/release"
compose=(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml")
"${compose[@]}" exec -T db pg_dump -U rahgard_db_owner -d rahgard_pilot_vps_staging -Fc > "$tmp/database.dump"
test -s "$tmp/database.dump"
pg_restore --list "$tmp/database.dump" >/dev/null
(
  cd "$tmp"
  find private release -type f -print0 | sort -z | xargs -0 sha256sum
  sha256sum database.dump
) > "$tmp/MANIFEST.sha256"
(
  cd "$tmp"
  tar -cf - MANIFEST.sha256 database.dump private release
) | openssl enc -aes-256-cbc -salt -pbkdf2 -iter 600000   -pass file:"$root/secrets/backup_encryption_passphrase" -out "$out"
test -s "$out"
(
  cd "$root/backups"
  sha256sum "${out##*/}" > "${out##*/}.sha256"
)
chmod 0600 "$out" "$out.sha256"
printf 'Encrypted portability bundle: %s\nCopy bundle and .sha256 sidecar OFF-HOST; preserve decryption passphrase separately.\n' "$out"
printf 'External DNS/TLS, vLLM, and RAG are NOT included. Re-run a final snapshot after freezing writes at cutover.\n'
