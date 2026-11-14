#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
cd "$(dirname "$0")"
config="${RAHGARD_DEPLOY_CONFIG:-/opt/rahgard-staging/.env}"
test -f "$config" || { echo 'Create the private non-secret deployment .env first.' >&2; exit 2; }
set -a; . "$config"; set +a
compose=(docker compose --env-file "$config" -f compose.yaml)
database=rahgard_pilot_vps_staging
state_dir="${RAHGARD_STATE_DIR:-/opt/rahgard-staging/state}"
mkdir -p "$state_dir"; chmod 700 "$state_dir"
marker_file="$state_dir/database-marker"
started_file="$state_dir/database-initialization-started"
completed_file="$state_dir/database-initialization-complete"
if [[ -e "$started_file" || -e "$completed_file" ]]; then
  echo 'Initialization has already started or completed. Preserve the database and inspect its ledger; this command never retries.' >&2
  exit 2
fi
if [[ ! -s "$marker_file" ]]; then openssl rand -hex 24 > "$marker_file"; chmod 600 "$marker_file"; fi
marker=$(cat "$marker_file")
[[ "$marker" =~ ^[a-fA-F0-9]{48}$ ]] || { echo 'Database marker is invalid.' >&2; exit 2; }
for item in pg_owner_password app_db_password auth_otp_hmac_secret auth_csrf_secret \
            auth_rate_limit_secret internal_chat_token geo_authorizer_password geo_publisher_password; do
  [[ -s "$RAHGARD_SECRET_DIR/$item" ]] || { echo 'A required protected database/runtime secret is missing.' >&2; exit 2; }
done

db_scalar() {
  "${compose[@]}" exec -T db psql -X -q -A -t -U ai_tourism_owner -d "$database" -v ON_ERROR_STOP=1 -c "$1" 2>/dev/null | tr -d '\r' | tail -1
}
owner_psql() {
  "${compose[@]}" exec -T db sh -lc \
    'export RAHGARD_APP_DB_PASSWORD="$(cat /run/secrets/app_db_password)"; export RAHGARD_GEO_AUTHORIZER_PASSWORD="$(cat /run/secrets/geo_authorizer_password)"; export RAHGARD_GEO_PUBLISHER_PASSWORD="$(cat /run/secrets/geo_publisher_password)"; exec psql -X -v ON_ERROR_STOP=1 -U ai_tourism_owner -d rahgard_pilot_vps_staging "$@"' _ "$@"
}
tcp_psql() {
  "${compose[@]}" exec -T \
    -e "RAHGARD_PILOT_DATABASE_MARKER=$marker" \
    -e "RAHGARD_PILOT_MIGRATION_0012_SHA256=$hash_0012" \
    -e "RAHGARD_PILOT_MIGRATION_0013_SHA256=$hash_0013" \
    -e "RAHGARD_PILOT_MIGRATION_0016_SHA256=$hash_0016" \
    db sh -lc 'export PGPASSWORD="$(cat /run/secrets/pg_owner_password)"; exec psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
}

if ! "${compose[@]}" ps --status running --services | grep -qx db; then
  echo 'Database container is not running; start only the dedicated staging db service first.' >&2; exit 2
fi
db_ready=false
for _ in $(seq 1 60); do
  if "${compose[@]}" exec -T db pg_isready -U ai_tourism_owner -d "$database" >/dev/null 2>&1; then
    db_ready=true
    break
  fi
  sleep 1
done
[[ "$db_ready" == true ]] || { echo 'Dedicated staging PostgreSQL did not become ready before initialization.' >&2; exit 2; }
if db_scalar "SELECT current_database()" | grep -qx "$database"; then :; else
  echo 'Connected database identity did not match the dedicated staging target.' >&2; exit 2
fi
if db_scalar "SELECT to_regclass('system.schema_migrations') IS NULL" | grep -qx t; then :; else
  echo 'Migration ledger already exists; initialization is never a repeatable upgrade.' >&2; exit 2
fi
if [[ -e "$RAHGARD_SECRET_DIR/initialization-claim" ]]; then
  echo 'A prior initialization claim exists without a recorded completed ledger; preserve state for manual recovery.' >&2; exit 2
fi
printf '%s\n' "$marker" > "$RAHGARD_SECRET_DIR/initialization-claim"; chmod 600 "$RAHGARD_SECRET_DIR/initialization-claim"
printf 'started\n' > "$started_file"; chmod 600 "$started_file"

sql_dir=../../engineering/database-prep/sql
legacy=../../engineering/database-prep/legacy/tourism_points.sql
pilot_dir=../../engineering/pilot/sql
staging_migration=../../engineering/pilot/sql/016_staging_invitation_auth.sql
[[ -s "$legacy" && -s "$staging_migration" ]] || { echo 'Required immutable migration inputs are missing.' >&2; exit 2; }
legacy_hash=$(sha256sum "$legacy" | cut -d' ' -f1)

{
  printf '\\getenv app_password RAHGARD_APP_DB_PASSWORD\n\\set app_user ai_tourism_app\n\\set migration_hash %s\n' "$(sha256sum "$sql_dir/000_bootstrap.sql" | cut -d' ' -f1)"
  printf '\\i /opt/rahgard/database-sql/000_bootstrap.sql\n'
} | owner_psql
owner_psql < "$legacy"
owner_psql -c "INSERT INTO system.schema_migrations(migration_id,sha256) VALUES ('0000_legacy_tourism_points_baseline','$legacy_hash')"

apply_base() {
  local migration_id="$1" file="$2" hash
  hash=$(sha256sum "$sql_dir/$file" | cut -d' ' -f1)
  {
    printf '\\set migration_hash %s\n' "$hash"
    if [[ "$migration_id" == 0004_app_role_grants ]]; then
      printf '\\set app_user ai_tourism_app\n'
      local old='GRANT CONNECT ON DATABASE ai_tourism_dev TO :"app_user";'
      [[ $(grep -Fxc "$old" "$sql_dir/$file") == 1 ]] || { echo 'Immutable 0004 adaptation token changed.' >&2; return 2; }
      sed 's/GRANT CONNECT ON DATABASE ai_tourism_dev TO :"app_user";/GRANT CONNECT ON DATABASE rahgard_pilot_vps_staging TO :"app_user";/' "$sql_dir/$file"
    else
      printf '\\i /opt/rahgard/database-sql/%s\n' "$file"
    fi
  } | owner_psql
  [[ $(db_scalar "SELECT sha256 FROM system.schema_migrations WHERE migration_id='$migration_id'") == "$hash" ]] || {
    echo "Migration checksum verification failed for $migration_id." >&2; return 2;
  }
}

apply_base 0001_core_schema 001_core_schema.sql
apply_base 0002_synthetic_knowledge_seed 002_synthetic_knowledge_seed.sql
apply_base 0003_synthetic_e2e_seed 003_synthetic_e2e_seed.sql
apply_base 0004_app_role_grants 004_app_role_grants.sql
apply_base 0005_verified_unesco_destination_seed 005_verified_unesco_destination_seed.sql
apply_base 0006_verified_unesco_destination_seed_batch2 006_verified_unesco_destination_seed_batch2.sql
apply_base 0007_shiraz_dalahoo_wikipedia_dataset_v1 007_shiraz_dalahoo_wikipedia_dataset_v1.sql
apply_base 0008_authentication_foundation 008_authentication_foundation.sql
apply_base 0009_traveler_core 009_traveler_core.sql
apply_base 0010_task31_content_privacy_full_itinerary 010_task31_content_privacy_full_itinerary.sql
apply_base 0011_internal_chat_turns 011_internal_chat_turns.sql
apply_base 0012_task5_published_claim_evidence 012_task5_published_claim_evidence.sql
hash_0012=$(sha256sum "$sql_dir/012_task5_published_claim_evidence.sql" | cut -d' ' -f1)
hash_0013=$(sha256sum "$pilot_dir/013_private_pilot_geo_audit.sql" | cut -d' ' -f1)
hash_0016=$(sha256sum "$staging_migration" | cut -d' ' -f1)

owner_psql <<SQL
CREATE TABLE public.rahgard_private_pilot_marker (
  marker_value TEXT PRIMARY KEY CHECK (marker_value ~ '^[a-fA-F0-9]{48}$')
);
REVOKE ALL ON public.rahgard_private_pilot_marker FROM PUBLIC;
INSERT INTO public.rahgard_private_pilot_marker(marker_value) VALUES ('$marker');
GRANT SELECT ON public.rahgard_private_pilot_marker TO ai_tourism_app;
SQL

owner_psql <<'SQL'
BEGIN;
CREATE ROLE rahgard_pilot_geo_executor NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_geo_migrator NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT rahgard_pilot_geo_executor TO rahgard_pilot_geo_migrator;
GRANT USAGE ON SCHEMA knowledge,operations,system,public TO rahgard_pilot_geo_migrator,rahgard_pilot_geo_executor;
GRANT CREATE ON SCHEMA operations TO rahgard_pilot_geo_migrator,rahgard_pilot_geo_executor;
GRANT SELECT ON knowledge.destinations,knowledge.destination_sources,knowledge.knowledge_sources,
  system.schema_migrations,public.rahgard_private_pilot_marker TO rahgard_pilot_geo_migrator,rahgard_pilot_geo_executor;
GRANT INSERT ON system.schema_migrations TO rahgard_pilot_geo_migrator;
GRANT UPDATE(status,updated_at),REFERENCES(destination_key) ON knowledge.destinations TO rahgard_pilot_geo_migrator;
GRANT UPDATE(status,updated_at) ON knowledge.destinations TO rahgard_pilot_geo_executor;
COMMIT;
SQL

owner_psql -c "GRANT SELECT ON public.rahgard_private_pilot_marker TO rahgard_pilot_geo_executor;"

trap 'owner_psql -c "REVOKE CREATE ON SCHEMA operations FROM rahgard_pilot_geo_migrator,rahgard_pilot_geo_executor; REVOKE rahgard_pilot_geo_executor FROM rahgard_pilot_geo_migrator; REVOKE INSERT ON system.schema_migrations FROM rahgard_pilot_geo_migrator; REVOKE UPDATE(status,updated_at),REFERENCES(destination_key) ON knowledge.destinations FROM rahgard_pilot_geo_migrator; REVOKE SELECT ON knowledge.destinations,knowledge.destination_sources,knowledge.knowledge_sources,system.schema_migrations,public.rahgard_private_pilot_marker FROM rahgard_pilot_geo_migrator; REVOKE USAGE ON SCHEMA knowledge,operations,system,public FROM rahgard_pilot_geo_migrator;" >/dev/null 2>&1 || true' EXIT
{
  printf 'SET ROLE rahgard_pilot_geo_migrator;\n\\set migration_hash %s\n\\i /opt/rahgard/pilot-sql/013_private_pilot_geo_audit.sql\nRESET ROLE;\n' "$hash_0013"
} | tcp_psql
owner_psql -c "REVOKE CREATE ON SCHEMA operations FROM rahgard_pilot_geo_migrator,rahgard_pilot_geo_executor; REVOKE rahgard_pilot_geo_executor FROM rahgard_pilot_geo_migrator; REVOKE INSERT ON system.schema_migrations FROM rahgard_pilot_geo_migrator; REVOKE UPDATE(status,updated_at),REFERENCES(destination_key) ON knowledge.destinations FROM rahgard_pilot_geo_migrator; REVOKE SELECT ON knowledge.destinations,knowledge.destination_sources,knowledge.knowledge_sources,system.schema_migrations,public.rahgard_private_pilot_marker FROM rahgard_pilot_geo_migrator; REVOKE USAGE ON SCHEMA knowledge,operations,system,public FROM rahgard_pilot_geo_migrator;"
{
  printf '\\set pilot_marker %s\n\\set migration_hash %s\n\\i /opt/rahgard/staging-sql/016_staging_invitation_auth.sql\n' "$marker" "$hash_0016"
} | tcp_psql

[[ $(db_scalar "SELECT count(*) FROM system.schema_migrations") == 15 ]] || { echo 'Expected 15 staging migrations (0000-0013 plus 0016) did not verify.' >&2; exit 2; }
[[ $(db_scalar "SELECT count(*) FROM public.rahgard_private_pilot_marker WHERE marker_value='$marker'") == 1 ]] || { echo 'Staging database marker verification failed.' >&2; exit 2; }
[[ $(db_scalar "SELECT count(*) FROM knowledge.production_destinations") == 0 ]] || {
  echo 'Production catalogue is nonempty before the explicit geographic publication gate; review required.' >&2; exit 2;
}
printf 'initialized\n' > "$completed_file"; chmod 600 "$completed_file"
printf 'PASS: dedicated staging schema initialized; migrations=15 (0000-0013 and 0016); production destinations=0; no geo packet was published.\n'
