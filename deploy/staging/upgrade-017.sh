#!/usr/bin/env bash
# One-time guarded application migration for provisional traveler itineraries.
# This script never initializes or recreates PostgreSQL and never modifies rows
# in existing traveler/catalogue tables.
set -Eeuo pipefail
umask 077
root=/opt/rahgard-staging
release_dir="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$release_dir"
config="$root/.env"
state="$root/state"
marker_file="$state/database-marker"
backup_dir="$root/backups"
database=rahgard_pilot_vps_staging

[[ -s "$config" && -s "$marker_file" ]] || { echo 'Private pilot config or database marker is missing.' >&2; exit 2; }
[[ -f "$root/state/database-initialization-complete" ]] || { echo 'The existing staging database is not marked initialized.' >&2; exit 2; }
[[ -f "$root/current/RELEASE_COMMIT" ]] || { echo 'No running managed release is recorded.' >&2; exit 2; }
[[ -s "$root/secrets/backup_encryption_passphrase" && -s "$root/secrets/portable_bundle_hmac_key" ]] || {
  echo 'Protected backup keys are required before applying this migration.' >&2; exit 2;
}
marker=$(cat "$marker_file")
[[ "$marker" =~ ^[a-fA-F0-9]{48}$ ]] || { echo 'The protected database marker is invalid.' >&2; exit 2; }

set -a; . <(sed 's/\r$//' "$config"); set +a
compose=(docker compose --env-file "$config" -f "$release_dir/deploy/staging/compose.yaml")
db_id=$("${compose[@]}" ps -q db)
[[ -n "$db_id" && "$(docker inspect -f '{{.State.Running}}' "$db_id")" == true ]] || {
  echo 'The managed staging PostgreSQL container is not running.' >&2; exit 2;
}
[[ "$(docker inspect -f '{{.Config.Image}}' "$db_id")" == 'rahgard-postgres:17-postgis36-vector087' ]] || {
  echo 'The database image does not match the guarded PostgreSQL 17 pilot image.' >&2; exit 2;
}
volume_name=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Type}}|{{.Name}}{{end}}{{end}}' "$db_id")
expected_volume=${RAHGARD_PG_VOLUME:-rahgard_staging_pgdata}
[[ "$volume_name" == "volume|$expected_volume" ]] || { echo 'Persistent PostgreSQL volume identity is unexpected.' >&2; exit 2; }
docker exec "$db_id" pg_isready -U ai_tourism_owner -d "$database" >/dev/null

pilot_sql="$release_dir/engineering/pilot/sql"
migration="$pilot_sql/017_provisional_itineraries.sql"
legacy=database/tourism_points.sql
[[ -s "$migration" && -s "$legacy" ]] || { echo 'Migration input or baseline ledger source is missing.' >&2; exit 2; }
hash_0016=$(sha256sum engineering/pilot/sql/016_staging_invitation_auth.sql | cut -d' ' -f1)
hash_0017=$(sha256sum "$migration" | cut -d' ' -f1)

db_scalar() {
  docker exec "$db_id" psql -X -q -A -t -U ai_tourism_owner -d "$database" \
    -v ON_ERROR_STOP=1 -c "$1" 2>/dev/null | tr -d '\r' | tail -1
}
[[ "$(db_scalar 'SELECT current_database()')" == "$database" ]] || { echo 'Connected database identity is wrong.' >&2; exit 2; }
[[ "$(db_scalar "SELECT current_setting('server_version_num')::integer BETWEEN 170000 AND 179999")" == t ]] || {
  echo 'Target database is not PostgreSQL 17.' >&2; exit 2;
}
[[ "$(db_scalar "SELECT count(*) FROM public.rahgard_private_pilot_marker WHERE marker_value='$marker'")" == 1 ]] || {
  echo 'Protected pilot marker does not match this database.' >&2; exit 2;
}

# Verify the exact 15-row checksum ledger before touching schema. Migration
# source hashes are computed from this immutable release, including the legacy
# baseline and the private staging migrations.
expected_ledger="0000_legacy_tourism_points_baseline:$(sha256sum "$legacy" | cut -d' ' -f1)"
append_ledger() {
  local id="$1" file="$2"
  expected_ledger+=",$id:$(sha256sum "$file" | cut -d' ' -f1)"
}
append_ledger 0001_core_schema engineering/database-prep/sql/001_core_schema.sql
append_ledger 0002_synthetic_knowledge_seed engineering/database-prep/sql/002_synthetic_knowledge_seed.sql
append_ledger 0003_synthetic_e2e_seed engineering/database-prep/sql/003_synthetic_e2e_seed.sql
append_ledger 0004_app_role_grants engineering/database-prep/sql/004_app_role_grants.sql
append_ledger 0005_verified_unesco_destination_seed engineering/database-prep/sql/005_verified_unesco_destination_seed.sql
append_ledger 0006_verified_unesco_destination_seed_batch2 engineering/database-prep/sql/006_verified_unesco_destination_seed_batch2.sql
append_ledger 0007_shiraz_dalahoo_wikipedia_dataset_v1 engineering/database-prep/sql/007_shiraz_dalahoo_wikipedia_dataset_v1.sql
append_ledger 0008_authentication_foundation engineering/database-prep/sql/008_authentication_foundation.sql
append_ledger 0009_traveler_core engineering/database-prep/sql/009_traveler_core.sql
append_ledger 0010_task31_content_privacy_full_itinerary engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql
append_ledger 0011_internal_chat_turns engineering/database-prep/sql/011_internal_chat_turns.sql
append_ledger 0012_task5_published_claim_evidence engineering/database-prep/sql/012_task5_published_claim_evidence.sql
append_ledger 0013_private_pilot_geo_audit engineering/pilot/sql/013_private_pilot_geo_audit.sql
append_ledger 0016_staging_invitation_auth engineering/pilot/sql/016_staging_invitation_auth.sql
actual_ledger=$(db_scalar "SELECT COALESCE(string_agg(migration_id || ':' || sha256, ',' ORDER BY migration_id), '') FROM system.schema_migrations")
[[ "$actual_ledger" == "$expected_ledger" ]] || {
  echo 'Migration requires the exact checksum-verified current ledger (0000-0013 plus 0016); no changes were made.' >&2; exit 2;
}
[[ "$(db_scalar "SELECT count(*) FROM system.schema_migrations WHERE migration_id='0017_provisional_itineraries'")" == 0 ]] || {
  echo 'Migration 0017 already exists; this runner never reapplies migrations.' >&2; exit 2;
}

# Make a fresh encrypted backup using the established operator procedure.
# Verify its HMAC, SHA-256, decryption and pg_restore readability before DDL.
mkdir -p "$backup_dir"; chmod 700 "$backup_dir"
backup_output=$("$root/current/deploy/staging/backup.sh")
backup_path=$(printf '%s\n' "$backup_output" | sed -n 's/^Authenticated encrypted database backup created: \(.*\) (copy bundle.*$/\1/p' | tail -1)
[[ -n "$backup_path" && -f "$backup_path" && -f "$backup_path.hmac" && -f "$backup_path.sha256" ]] || {
  echo 'Could not identify a complete authenticated pre-migration backup.' >&2; exit 2;
}
sha256sum -c "$backup_path.sha256" >/dev/null || { echo 'Pre-migration backup SHA-256 check failed.' >&2; exit 2; }
python3 - "$root/secrets/portable_bundle_hmac_key" "$backup_path" "$backup_path.hmac" <<'PY'
import hashlib, hmac, pathlib, sys
key_path, archive_path, mac_path = map(pathlib.Path, sys.argv[1:])
key = key_path.read_bytes()
if len(key) < 32:
    raise SystemExit("Protected backup HMAC key is too short.")
digest = hmac.new(key, digestmod=hashlib.sha256)
with archive_path.open("rb") as stream:
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
recorded = mac_path.read_text(encoding="ascii").split()[0]
if not hmac.compare_digest(digest.hexdigest(), recorded):
    raise SystemExit("Pre-migration backup HMAC verification failed.")
PY
decrypted=$(mktemp "$backup_dir/.pre-017.XXXXXX.dump")
trap 'rm -f -- "$decrypted"' EXIT
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
  -pass file:"$root/secrets/backup_encryption_passphrase" -in "$backup_path" -out "$decrypted"
# The verified Postgres image carries the matching client tools; the Ubuntu
# host is intentionally not required to install PostgreSQL utilities.
docker exec -i "$db_id" pg_restore --list < "$decrypted" >/dev/null

# Read-only invariants before the migration. These counts are rechecked after
# commit; the DDL must not change any traveler or published catalogue row.
before=$(db_scalar "SELECT (SELECT count(*) FROM identity.users)||':'||(SELECT count(*) FROM conversation.conversations)||':'||(SELECT count(*) FROM conversation.messages)||':'||(SELECT count(*) FROM travel.trips)||':'||(SELECT count(*) FROM travel.itineraries)||':'||(SELECT count(*) FROM travel.itinerary_stops)||':'||(SELECT count(*) FROM knowledge.production_destinations)")

# Keep marker/checksum values off command-line arguments: stream three values
# before the SQL input and read them into environment variables in the DB
# container. The psql client then consumes only the migration text.
{
  printf '%s\n%s\n%s\n' "$marker" "$hash_0016" "$hash_0017"
  cat "$migration"
} | docker exec -i "$db_id" sh -lc '
  IFS= read -r marker
  IFS= read -r hash16
  IFS= read -r hash17
  export RAHGARD_PILOT_DATABASE_MARKER="$marker"
  export RAHGARD_PILOT_MIGRATION_0016_SHA256="$hash16"
  export RAHGARD_PILOT_MIGRATION_0017_SHA256="$hash17"
  export PGPASSWORD="$(cat /run/secrets/pg_owner_password)"
  exec psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB"
'

[[ "$(db_scalar "SELECT count(*) FROM system.schema_migrations")" == 16 ]] || { echo 'Expected exactly 16 migrations after upgrade.' >&2; exit 2; }
[[ "$(db_scalar "SELECT sha256 FROM system.schema_migrations WHERE migration_id='0017_provisional_itineraries'")" == "$hash_0017" ]] || {
  echo 'Migration 0017 checksum verification failed.' >&2; exit 2;
}
[[ "$(db_scalar "SELECT to_regclass('travel.provisional_itineraries') IS NOT NULL")" == t ]] || {
  echo 'Provisional itinerary table is missing after migration.' >&2; exit 2;
}
after=$(db_scalar "SELECT (SELECT count(*) FROM identity.users)||':'||(SELECT count(*) FROM conversation.conversations)||':'||(SELECT count(*) FROM conversation.messages)||':'||(SELECT count(*) FROM travel.trips)||':'||(SELECT count(*) FROM travel.itineraries)||':'||(SELECT count(*) FROM travel.itinerary_stops)||':'||(SELECT count(*) FROM knowledge.production_destinations)")
[[ "$after" == "$before" ]] || { echo 'Existing traveler/catalogue row counts changed unexpectedly; preserve backup and stop.' >&2; exit 2; }
[[ "$(db_scalar 'SELECT count(*) FROM travel.provisional_itineraries')" == 0 ]] || {
  echo 'The new draft table was unexpectedly populated; preserve state for review.' >&2; exit 2;
}
trap - EXIT
rm -f -- "$decrypted"
printf 'PASS: additive migration 0017 applied once; migrations=16; existing critical row counts unchanged; authenticated backup=%s\n' "$(basename "$backup_path")"
