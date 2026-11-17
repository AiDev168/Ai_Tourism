#!/usr/bin/env bash
# Guarded application-database migration 0018–0021. This script intentionally
# requires explicit operator attestations for the off-host backup and isolated
# restore rehearsal. It does not deploy or restart application containers.
set -Eeuo pipefail
umask 077
root=/opt/rahgard-staging
release_dir="$(cd "$(dirname "$0")/../.." && pwd)"
database=rahgard_pilot_vps_staging
owner=ai_tourism_owner
expected_current_sha="${1:-}"
backup_name="${2:-}"
backup_gate="${3:-}"
approval_gate="${4:-}"

[[ "$expected_current_sha" =~ ^[0-9a-f]{40}$ && "$backup_name" =~ ^rahgard-[A-Za-z0-9_.-]+\.dump\.enc$ \
  && "$backup_gate" == OFFHOST_AND_ISOLATED_RESTORE_VERIFIED \
  && "$approval_gate" == OWNER_APPROVED_APPLY_018_021 ]] || {
  echo 'Usage: upgrade-018-021.sh <expected-current-release-sha> <verified-backup-basename> OFFHOST_AND_ISOLATED_RESTORE_VERIFIED OWNER_APPROVED_APPLY_018_021' >&2
  echo 'The last two arguments are explicit human approval attestations; this script never deploys or restarts app services.' >&2
  exit 2
}
[[ -s "$root/.env" && -s "$root/state/database-marker" && -f "$root/state/database-initialization-complete" ]] || { echo 'Protected pilot state is incomplete.' >&2; exit 2; }
[[ -L "$root/current" && "$(cat "$root/current/RELEASE_COMMIT")" == "$expected_current_sha" ]] || { echo 'Current release changed since preflight; refusing migrations.' >&2; exit 2; }
target_sha=$(cat "$release_dir/RELEASE_COMMIT" 2>/dev/null || git -C "$release_dir" rev-parse HEAD 2>/dev/null || true)
[[ "$target_sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Target source release SHA is unavailable.' >&2; exit 2; }
compose=(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml")
db_id=$("${compose[@]}" ps -q db)
[[ -n "$db_id" && "$(docker inspect -f '{{.State.Running}}' "$db_id")" == true \
  && "$(docker inspect -f '{{.State.Health.Status}}' "$db_id")" == healthy \
  && "$(docker inspect -f '{{.Config.Image}}' "$db_id")" == rahgard-postgres:17-postgis36-vector087 ]] || { echo 'Managed PG17 database is not healthy.' >&2; exit 2; }
volume=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Type}}|{{.Name}}{{end}}{{end}}' "$db_id")
expected_volume=$(sed -n 's/^RAHGARD_PG_VOLUME=//p' "$root/.env" | tail -n 1 | tr -d '\r')
expected_volume=${expected_volume:-rahgard_staging_pgdata}
[[ "$volume" == "volume|$expected_volume" ]] || { echo 'Persistent database volume identity changed.' >&2; exit 2; }

backup_path="$root/backups/$backup_name"
[[ -f "$backup_path" && ! -L "$backup_path" && -s "$backup_path" \
  && -f "$backup_path.hmac" && ! -L "$backup_path.hmac" \
  && -f "$backup_path.sha256" && ! -L "$backup_path.sha256" ]] || { echo 'Verified backup bundle/sidecars are missing.' >&2; exit 2; }
[[ -f "$root/secrets/backup_encryption_passphrase" && ! -L "$root/secrets/backup_encryption_passphrase" \
  && -s "$root/secrets/backup_encryption_passphrase" \
  && -f "$root/secrets/portable_bundle_hmac_key" && ! -L "$root/secrets/portable_bundle_hmac_key" \
  && -s "$root/secrets/portable_bundle_hmac_key" ]] || { echo 'Protected backup keys are unavailable.' >&2; exit 2; }
(
  cd "$root/backups"
  sha256sum --check -- "$backup_name.sha256"
)
python3 - "$root/secrets/portable_bundle_hmac_key" "$backup_path" "$backup_path.hmac" <<'PY'
import hashlib, hmac, os, re, sys
key_path, archive, sidecar = sys.argv[1:]
key = open(key_path, 'rb').read()
if len(key) < 32: raise SystemExit('Independent HMAC key is too short.')
line = open(sidecar, encoding='ascii').read(257)
m = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.-]+)\n', line)
if not m or m.group(2) != os.path.basename(archive): raise SystemExit('Invalid HMAC sidecar.')
mac = hmac.new(key, digestmod=hashlib.sha256)
with open(archive, 'rb') as stream:
    for block in iter(lambda: stream.read(1024 * 1024), b''): mac.update(block)
if not hmac.compare_digest(mac.hexdigest(), m.group(1)): raise SystemExit('Backup HMAC verification failed.')
PY
plain_dir=$(mktemp -d /run/rahgard-migration.XXXXXX)
chmod 0700 "$plain_dir"
trap 'rm -rf -- "$plain_dir"' EXIT
plain="$plain_dir/backup.dump"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass file:"$root/secrets/backup_encryption_passphrase" -in "$backup_path" -out "$plain"
test -s "$plain"
docker exec -i "$db_id" pg_restore --list < "$plain" >/dev/null
rm -f -- "$plain"

# Preflight verifies the complete known migration-ledger prefix and DDL/ledger
# consistency before this script can apply any migration.
bash "$release_dir/deploy/staging/preflight-018-021.sh"
marker=$(cat "$root/state/database-marker")
hashes=()
files=(018_national_catalogue_ingestion.sql 019_partner_workspace.sql 020_archive_candidate_publication.sql 021_postgis_security_definer_publication.sql)
ids=(0018_national_catalogue_ingestion 0019_partner_workspace 0020_archive_candidate_publication 0021_postgis_security_definer_publication)
prior_0017_hash=$(sha256sum "$release_dir/engineering/pilot/sql/017_provisional_itineraries.sql" | cut -d' ' -f1)
for file in "${files[@]}"; do
  path="$release_dir/engineering/pilot/sql/$file"
  [[ -s "$path" ]] || { echo "Missing migration: $file" >&2; exit 2; }
  hashes+=("$(sha256sum "$path" | cut -d' ' -f1)")
done
ledger() { docker exec "$db_id" psql -X -q -A -t -U "$owner" -d "$database" -v ON_ERROR_STOP=1 -c 'BEGIN READ ONLY; SELECT migration_id||chr(58)||rtrim(sha256) FROM system.schema_migrations ORDER BY migration_id; COMMIT;' | tr -d '\r'; }

# Migration SQL consumes exact numbered environment names; map them explicitly
# to avoid spelling mistakes and reject any non-prefix state before DDL.
actual=$(ledger)
for i in "${!ids[@]}"; do
  if grep -Fqx "${ids[$i]}:${hashes[$i]}" <<<"$actual"; then continue; fi
  case "$i" in
    0) [[ $(grep -c . <<<"$actual") -eq 16 ]] || { echo 'Unexpected ledger state before 0018.' >&2; exit 2; } ;;
    *) [[ $(grep -Fxc "${ids[$((i-1))]}:${hashes[$((i-1))]}" <<<"$actual") -eq 1 ]] || { echo "Unexpected ledger prefix before ${ids[$i]}." >&2; exit 2; } ;;
  esac
  case "$i" in
    0) prior_env=RAHGARD_PILOT_MIGRATION_0017_SHA256; current_env=RAHGARD_PILOT_MIGRATION_0018_SHA256 ;;
    1) prior_env=RAHGARD_PILOT_MIGRATION_0018_SHA256; current_env=RAHGARD_PILOT_MIGRATION_0019_SHA256 ;;
    2) prior_env=RAHGARD_PILOT_MIGRATION_0019_SHA256; current_env=RAHGARD_PILOT_MIGRATION_0020_SHA256 ;;
    3) prior_env=RAHGARD_PILOT_MIGRATION_0020_SHA256; current_env=RAHGARD_PILOT_MIGRATION_0021_SHA256 ;;
  esac
  path="$release_dir/engineering/pilot/sql/${files[$i]}"
  if (( i == 0 )); then prior_hash="$prior_0017_hash"; else prior_hash="${hashes[$((i-1))]}"; fi
  {
    printf '%s\n%s\n%s\n' "$marker" "$prior_hash" "${hashes[$i]}"
    cat "$path"
  } | docker exec -i "$db_id" sh -lc "IFS= read -r marker; IFS= read -r prior; IFS= read -r migration; export RAHGARD_PILOT_DATABASE_MARKER=\"\$marker\" $prior_env=\"\$prior\" $current_env=\"\$migration\"; export PGPASSWORD=\"\$(cat /run/secrets/pg_owner_password)\"; exec psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U \"\$POSTGRES_USER\" -d \"\$POSTGRES_DB\""
  actual=$(ledger)
  grep -Fqx "${ids[$i]}:${hashes[$i]}" <<<"$actual" || { echo "Migration ${ids[$i]} checksum was not recorded." >&2; exit 3; }
  echo "MIGRATION_APPLIED ${ids[$i]} sha256=${hashes[$i]}"
done
bash "$release_dir/deploy/staging/preflight-018-021.sh"
echo "PASS: schema migrations 0018–0021 are applied. No app deployment/restart or content publication was performed by this script."
