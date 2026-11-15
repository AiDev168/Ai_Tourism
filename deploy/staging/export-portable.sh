#!/usr/bin/env bash
# Authenticated, cutover-consistent portability snapshot. Never modifies DB.
set -Eeuo pipefail
umask 077
root=/opt/rahgard-staging
freeze_marker="$root/state/WRITE_FREEZE"

if [[ "${1:-}" != "--cutover-frozen" || $# -ne 1 ]]; then
  echo 'Usage: export-portable.sh --cutover-frozen' >&2
  echo 'Stop writes, create state/WRITE_FREEZE, and stop this Compose project api/web first.' >&2
  exit 2
fi
test -s "$root/.env"
[[ -f "$root/secrets/backup_encryption_passphrase" && ! -L "$root/secrets/backup_encryption_passphrase" && -s "$root/secrets/backup_encryption_passphrase" ]] || {
  echo 'Encryption passphrase must be a regular non-symlink file.' >&2; exit 2;
}
[[ -f "$root/secrets/portable_bundle_hmac_key" && ! -L "$root/secrets/portable_bundle_hmac_key" && -s "$root/secrets/portable_bundle_hmac_key" ]] || {
  echo 'Independent HMAC key must be a regular non-symlink file.' >&2; exit 2;
}
test -f "$freeze_marker" && test ! -L "$freeze_marker" || {
  echo 'A write-freeze marker is required; refusing a potentially inconsistent export.' >&2; exit 2;
}
test -d "$root/state"
test -d "$root/backups"
sha=$(cat "$root/current/RELEASE_COMMIT")
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid release SHA.' >&2; exit 2; }
test -d "$root/releases/$sha"

compose=(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml")
db_owner=ai_tourism_owner
db_name=rahgard_pilot_vps_staging
running=$("${compose[@]}" ps --status running --services)
if grep -Eq '^(api|web)$' <<<"$running"; then
  echo 'Rahgard api/web are still running; stop them before the frozen export.' >&2
  exit 2
fi
writers=$("${compose[@]}" exec -T db psql -X -q -A -t -U "$db_owner" -d "$db_name" \
  -c "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid()")
[[ "$writers" == 0 ]] || {
  echo "Database still has $writers other sessions; ensure all writers/readers are drained before export." >&2; exit 2;
}

# Only operational secrets required by the current Compose contract are copied.
# Backup and portable-integrity keys are deliberately excluded.
required_secrets=(pg_owner_password app_db_password geo_authorizer_password geo_publisher_password auth_otp_hmac_secret auth_csrf_secret auth_rate_limit_secret internal_chat_token sms_ir_production_api_key)
for name in "${required_secrets[@]}"; do
  file="$root/secrets/$name"
  if [[ "$name" == sms_ir_production_api_key ]]; then
    [[ -f "$file" && ! -L "$file" ]] || {
      echo "Compose runtime placeholder/secret is missing or unsafe: $name" >&2; exit 2;
    }
  else
    [[ -f "$file" && ! -L "$file" && -s "$file" ]] || {
      echo "Required runtime secret is missing or unsafe: $name" >&2; exit 2;
    }
  fi
done
for path in "$root/state" "$root/releases/$sha"; do
  if find "$path" -type l -print -quit | grep -q .; then
    echo "Symlink found in portability payload; refusing ambiguous traversal: $path" >&2; exit 2
  fi
done

stamp=$(date -u +%Y%m%dT%H%M%SZ)
tmp=$(mktemp -d "$root/backups/.portable-$stamp.XXXXXX")
nonce=${tmp##*.}
out="$root/backups/rahgard-portable-$stamp-$sha-$nonce.tar.enc"
trap 'rm -rf -- "$tmp"' EXIT
mkdir -m 0700 "$tmp/private" "$tmp/private/secrets"
cp -- "$root/.env" "$tmp/private/host.env"
for name in "${required_secrets[@]}"; do
  install -m 0600 -- "$root/secrets/$name" "$tmp/private/secrets/$name"
done
cp -a -- "$root/state" "$tmp/private/state"
cp -a -- "$root/releases/$sha" "$tmp/release"
cp -- "$freeze_marker" "$tmp/private/state/WRITE_FREEZE"

"${compose[@]}" exec -T db pg_dump -U "$db_owner" -d "$db_name" -Fc > "$tmp/database.dump"
test -s "$tmp/database.dump"
pg_restore --list "$tmp/database.dump" >/dev/null
"${compose[@]}" exec -T db psql -X -q -A -t -U "$db_owner" -d "$db_name" \
  -c "SELECT migration_id||'|'||rtrim(sha256) FROM system.schema_migrations ORDER BY migration_id" \
  > "$tmp/database.migration-ledger.tsv"
test -s "$tmp/database.migration-ledger.tsv"
counts_sql=$(cat <<'SQL'
SELECT 'identity.users', count(*) FROM identity.users UNION ALL
SELECT 'conversation.conversations', count(*) FROM conversation.conversations UNION ALL
SELECT 'conversation.messages', count(*) FROM conversation.messages UNION ALL
SELECT 'travel.trips', count(*) FROM travel.trips UNION ALL
SELECT 'travel.itineraries', count(*) FROM travel.itineraries UNION ALL
SELECT 'travel.itinerary_stops', count(*) FROM travel.itinerary_stops UNION ALL
SELECT 'knowledge.production_destinations', count(*) FROM knowledge.production_destinations
ORDER BY 1
SQL
)
"${compose[@]}" exec -T db psql -X -q -A -t -F '|' -U "$db_owner" -d "$db_name" \
  -c "$counts_sql" > "$tmp/database.critical-counts.tsv"
(
  cd "$tmp"
  find private release -type f -print0 | sort -z | xargs -0 sha256sum
  sha256sum database.dump database.migration-ledger.tsv database.critical-counts.tsv
) > "$tmp/MANIFEST.sha256"
(
  cd "$tmp"
  tar -cf - MANIFEST.sha256 database.dump database.migration-ledger.tsv database.critical-counts.tsv private release
) | openssl enc -aes-256-cbc -salt -pbkdf2 -iter 600000 \
  -pass file:"$root/secrets/backup_encryption_passphrase" -out "$out"
test -s "$out"

# Encrypt-then-MAC: HMAC is checked before decryption. The integrity key is
# independent of the encryption key and is never included in this bundle.
python3 - "$root/secrets/portable_bundle_hmac_key" "$out" "$out.hmac" <<'PY'
import hashlib, hmac, os, sys
key_path, bundle_path, mac_path = sys.argv[1:]
with open(key_path, "rb") as f:
    key = f.read()
if len(key) < 32:
    raise SystemExit("Portable HMAC key must contain at least 32 random bytes.")
mac = hmac.new(key, digestmod=hashlib.sha256)
with open(bundle_path, "rb") as f:
    for block in iter(lambda: f.read(1024 * 1024), b""):
        mac.update(block)
with open(mac_path, "x", encoding="ascii") as f:
    f.write(mac.hexdigest() + "  " + os.path.basename(bundle_path) + "\n")
PY
(
  cd "$root/backups"
  sha256sum "${out##*/}" > "${out##*/}.sha256"
)
chmod 0600 "$out" "$out.hmac" "$out.sha256"
printf 'Authenticated portability bundle: %s\n' "$out"
printf 'Transfer .tar.enc, .hmac, and .sha256 off-host. Independently transfer the encryption passphrase and HMAC key; neither is in the bundle.\n'
printf 'Snapshot is marked write-frozen. External DNS/TLS, vLLM, and RAG are NOT included.\n'
