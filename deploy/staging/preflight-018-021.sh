#!/usr/bin/env bash
# Read-only compatibility check for the additive national-catalogue upgrade.
# It never runs migrations, changes services, or writes to the database.
set -Eeuo pipefail
root=/opt/rahgard-staging
release_dir="$(cd "$(dirname "$0")/../.." && pwd)"
database=rahgard_pilot_vps_staging
owner=ai_tourism_owner

[[ -s "$root/.env" && -s "$root/state/database-marker" && -f "$root/state/database-initialization-complete" ]] || {
  echo 'BLOCKED: managed pilot config, marker, or initialization record is missing.' >&2; exit 2;
}
[[ -L "$root/current" && -s "$root/current/RELEASE_COMMIT" ]] || { echo 'BLOCKED: current managed release is not recorded.' >&2; exit 2; }
current_sha=$(cat "$root/current/RELEASE_COMMIT")
[[ "$current_sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'BLOCKED: invalid current release marker.' >&2; exit 2; }
compose=(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml")
db_id=$("${compose[@]}" ps -q db)
[[ -n "$db_id" && "$(docker inspect -f '{{.State.Running}}' "$db_id")" == true ]] || { echo 'BLOCKED: managed database container is not running.' >&2; exit 2; }
[[ "$(docker inspect -f '{{.State.Health.Status}}' "$db_id")" == healthy ]] || { echo 'BLOCKED: database health is not healthy.' >&2; exit 2; }
[[ "$(docker inspect -f '{{.Config.Image}}' "$db_id")" == rahgard-postgres:17-postgis36-vector087 ]] || { echo 'BLOCKED: unexpected database image.' >&2; exit 2; }
volume=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Type}}|{{.Name}}{{end}}{{end}}' "$db_id")
expected_volume=$(sed -n 's/^RAHGARD_PG_VOLUME=//p' "$root/.env" | tail -n 1 | tr -d '\r')
expected_volume=${expected_volume:-rahgard_staging_pgdata}
[[ "$volume" == "volume|$expected_volume" ]] || { echo 'BLOCKED: database persistent-volume identity mismatch.' >&2; exit 2; }

sql_root="$release_dir"
for f in database/tourism_points.sql engineering/database-prep/sql/001_core_schema.sql \
  engineering/database-prep/sql/002_synthetic_knowledge_seed.sql engineering/database-prep/sql/003_synthetic_e2e_seed.sql \
  engineering/database-prep/sql/004_app_role_grants.sql engineering/database-prep/sql/005_verified_unesco_destination_seed.sql \
  engineering/database-prep/sql/006_verified_unesco_destination_seed_batch2.sql engineering/database-prep/sql/007_shiraz_dalahoo_wikipedia_dataset_v1.sql \
  engineering/database-prep/sql/008_authentication_foundation.sql engineering/database-prep/sql/009_traveler_core.sql \
  engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql engineering/database-prep/sql/011_internal_chat_turns.sql \
  engineering/database-prep/sql/012_task5_published_claim_evidence.sql engineering/pilot/sql/013_private_pilot_geo_audit.sql \
  engineering/pilot/sql/016_staging_invitation_auth.sql engineering/pilot/sql/017_provisional_itineraries.sql \
  engineering/pilot/sql/018_national_catalogue_ingestion.sql engineering/pilot/sql/019_partner_workspace.sql \
  engineering/pilot/sql/020_archive_candidate_publication.sql engineering/pilot/sql/021_postgis_security_definer_publication.sql; do
  [[ -s "$sql_root/$f" ]] || { echo "BLOCKED: required migration source missing: $f" >&2; exit 2; }
done

ids=(0000_legacy_tourism_points_baseline 0001_core_schema 0002_synthetic_knowledge_seed 0003_synthetic_e2e_seed 0004_app_role_grants 0005_verified_unesco_destination_seed 0006_verified_unesco_destination_seed_batch2 0007_shiraz_dalahoo_wikipedia_dataset_v1 0008_authentication_foundation 0009_traveler_core 0010_task31_content_privacy_full_itinerary 0011_internal_chat_turns 0012_task5_published_claim_evidence 0013_private_pilot_geo_audit 0016_staging_invitation_auth 0017_provisional_itineraries 0018_national_catalogue_ingestion 0019_partner_workspace 0020_archive_candidate_publication 0021_postgis_security_definer_publication)
files=(database/tourism_points.sql engineering/database-prep/sql/001_core_schema.sql engineering/database-prep/sql/002_synthetic_knowledge_seed.sql engineering/database-prep/sql/003_synthetic_e2e_seed.sql engineering/database-prep/sql/004_app_role_grants.sql engineering/database-prep/sql/005_verified_unesco_destination_seed.sql engineering/database-prep/sql/006_verified_unesco_destination_seed_batch2.sql engineering/database-prep/sql/007_shiraz_dalahoo_wikipedia_dataset_v1.sql engineering/database-prep/sql/008_authentication_foundation.sql engineering/database-prep/sql/009_traveler_core.sql engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql engineering/database-prep/sql/011_internal_chat_turns.sql engineering/database-prep/sql/012_task5_published_claim_evidence.sql engineering/pilot/sql/013_private_pilot_geo_audit.sql engineering/pilot/sql/016_staging_invitation_auth.sql engineering/pilot/sql/017_provisional_itineraries.sql engineering/pilot/sql/018_national_catalogue_ingestion.sql engineering/pilot/sql/019_partner_workspace.sql engineering/pilot/sql/020_archive_candidate_publication.sql engineering/pilot/sql/021_postgis_security_definer_publication.sql)
expected=()
for i in "${!ids[@]}"; do expected+=("${ids[$i]}:$(sha256sum "$sql_root/${files[$i]}" | cut -d' ' -f1)"); done
db_scalar() { docker exec "$db_id" psql -X -q -A -t -U "$owner" -d "$database" -v ON_ERROR_STOP=1 -c "BEGIN READ ONLY; $1; COMMIT;" | tr -d '\r' | tail -n 1; }
[[ "$(db_scalar "SELECT current_database()")" == "$database" ]] || { echo 'BLOCKED: connected database identity mismatch.' >&2; exit 2; }
[[ "$(db_scalar "SELECT current_setting('server_version_num')::integer BETWEEN 170000 AND 179999")" == t ]] || { echo 'BLOCKED: database is not PostgreSQL 17.' >&2; exit 2; }
marker=$(cat "$root/state/database-marker")
[[ "$marker" =~ ^[a-fA-F0-9]{48}$ && "$(db_scalar "SELECT count(*) FROM public.rahgard_private_pilot_marker WHERE marker_value='$marker'")" == 1 ]] || { echo 'BLOCKED: database marker does not match the protected host marker.' >&2; exit 2; }
actual=()
while IFS= read -r line; do [[ -n "$line" ]] && actual+=("$line"); done < <(docker exec "$db_id" psql -X -q -A -t -F '|' -U "$owner" -d "$database" -v ON_ERROR_STOP=1 -c 'BEGIN READ ONLY; SELECT migration_id||chr(58)||rtrim(sha256) FROM system.schema_migrations ORDER BY migration_id; COMMIT;' | tr -d '\r')
(( ${#actual[@]} >= 16 && ${#actual[@]} <= 20 )) || { echo 'BLOCKED: migration count is outside the supported 0017–0021 ledger boundary.' >&2; exit 2; }
for i in "${!actual[@]}"; do [[ "${actual[$i]}" == "${expected[$i]}" ]] || { echo "BLOCKED: ledger mismatch at entry $i; no changes made." >&2; exit 2; }; done

# Ledger/object consistency catches DDL applied without its transaction ledger row.
check_object() { local object="$1" want="$2" got; got=$(db_scalar "SELECT (to_regclass('$object') IS NOT NULL)::text"); [[ "$got" == "$want" ]] || { echo "BLOCKED: schema object/ledger mismatch at $object." >&2; exit 2; }; }
applied=$(( ${#actual[@]} - 16 ))
if (( applied >= 1 )); then check_object knowledge.destination_candidates true; check_object geo.admin_areas true; else check_object knowledge.destination_candidates false; check_object geo.admin_areas false; fi
if (( applied >= 2 )); then check_object partner.organizations true; check_object partner.services true; else check_object partner.organizations false; check_object partner.services false; fi
if (( applied >= 3 )); then check_object knowledge.catalogue_publication_events true; check_object knowledge.destination_candidate_evidence true; else check_object knowledge.catalogue_publication_events false; check_object knowledge.destination_candidate_evidence false; fi
if (( applied >= 4 )); then
  [[ "$(db_scalar "SELECT pg_get_functiondef('knowledge.sync_destination_location()'::regprocedure) LIKE '%public.ST_MakePoint%' AND pg_get_functiondef('knowledge.sync_destination_location()'::regprocedure) LIKE '%public.geography%'")" == t ]] || { echo 'BLOCKED: migration 0021 implementation does not match its ledger.' >&2; exit 2; }
else
  [[ "$(db_scalar "SELECT NOT (pg_get_functiondef('knowledge.sync_destination_location()'::regprocedure) LIKE '%public.ST_MakePoint%')")" == t ]] || { echo 'BLOCKED: migration 0021 function is present without its ledger entry.' >&2; exit 2; }
fi

target_sha=$(cat "$release_dir/RELEASE_COMMIT" 2>/dev/null || git -C "$release_dir" rev-parse HEAD 2>/dev/null || printf 'working-tree-package')
[[ "$target_sha" == working-tree-package || "$target_sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'BLOCKED: invalid target release marker.' >&2; exit 2; }
echo "PASS_READ_ONLY_PREFLIGHT current_release=$current_sha target_release=$target_sha db=$database pg17=pass volume=$expected_volume migrations=${#actual[@]}/20 pending=$((20-${#actual[@]}))"
echo 'No DDL, DML, service changes, publication, or secret values were accessed.'
