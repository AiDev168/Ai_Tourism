#!/usr/bin/env bash
# Restore an authenticated routine DB backup into a temporary, network-isolated,
# tmpfs-only PostgreSQL 17 container, then rehearse migrations 0018–0021.
# No running Rahgard service or persistent volume is changed.
set -Eeuo pipefail
umask 077
root=/opt/rahgard-staging
release_dir="$(cd "$(dirname "$0")/../.." && pwd)"
database=rahgard_pilot_vps_staging
owner=ai_tourism_owner
backup_name="${1:-}"
[[ "$backup_name" =~ ^rahgard-[A-Za-z0-9_.-]+\.dump\.enc$ ]] || {
  echo 'Usage: rehearse-018-021.sh <encrypted-backup-basename>' >&2; exit 2;
}
backup="$root/backups/$backup_name"
[[ -f "$backup" && ! -L "$backup" && -s "$backup" \
  && -f "$backup.hmac" && ! -L "$backup.hmac" \
  && -f "$backup.sha256" && ! -L "$backup.sha256" ]] || { echo 'Backup or authentication sidecars missing.' >&2; exit 2; }
[[ -f "$root/secrets/backup_encryption_passphrase" && ! -L "$root/secrets/backup_encryption_passphrase" \
  && -s "$root/secrets/backup_encryption_passphrase" \
  && -f "$root/secrets/portable_bundle_hmac_key" && ! -L "$root/secrets/portable_bundle_hmac_key" \
  && -s "$root/secrets/portable_bundle_hmac_key" ]] || { echo 'Protected backup keys unavailable.' >&2; exit 2; }
(
  cd "$root/backups"
  sha256sum --check -- "$backup_name.sha256"
)
python3 - "$root/secrets/portable_bundle_hmac_key" "$backup" "$backup.hmac" <<'PY'
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

[[ "$(findmnt -T /dev/shm -n -o FSTYPE)" == tmpfs && -w /dev/shm ]] || { echo 'A writable tmpfs is required for the decrypted rehearsal dump.' >&2; exit 2; }
plain_dir=$(mktemp -d /dev/shm/rahgard-restore-rehearsal.XXXXXX)
chmod 0700 "$plain_dir"
plain="$plain_dir/database.dump"
isolated="rahgard-restore-$(date -u +%Y%m%d%H%M%S)-$$"
image=rahgard-postgres:17-postgis36-vector087
api_image=""
api_name=""
api_helper=""
api_image_created=false
cleanup() {
  status=$?
  if [[ -n "$api_helper" ]] && docker inspect "$api_helper" >/dev/null 2>&1; then
    labels=$(docker inspect -f '{{index .Config.Labels "rahgard.restore.target"}}|{{index .Config.Labels "rahgard.environment"}}' "$api_helper" 2>/dev/null || true)
    if [[ "$labels" == 'isolated|restore-test' ]]; then docker rm -f "$api_helper" >/dev/null 2>&1 || true; fi
  fi
  if [[ -n "$api_name" ]] && docker inspect "$api_name" >/dev/null 2>&1; then
    labels=$(docker inspect -f '{{index .Config.Labels "rahgard.restore.target"}}|{{index .Config.Labels "rahgard.environment"}}' "$api_name" 2>/dev/null || true)
    if [[ "$labels" == 'isolated|restore-test' ]]; then docker rm -f "$api_name" >/dev/null 2>&1 || true; fi
  fi
  if [[ "$api_image_created" == true ]]; then docker image rm "$api_image" >/dev/null 2>&1 || true; fi
  if docker inspect "$isolated" >/dev/null 2>&1; then
    labels=$(docker inspect -f '{{index .Config.Labels "rahgard.restore.target"}}|{{index .Config.Labels "rahgard.environment"}}' "$isolated" 2>/dev/null || true)
    if [[ "$labels" == 'isolated|restore-test' ]]; then docker rm -f "$isolated" >/dev/null 2>&1 || true; fi
  fi
  rm -rf -- "$plain_dir"
  exit "$status"
}
trap cleanup EXIT
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass file:"$root/secrets/backup_encryption_passphrase" -in "$backup" -out "$plain"
test -s "$plain"
docker image inspect "$image" >/dev/null
docker exec -i "$(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml" ps -q db)" pg_restore --list < "$plain" >/dev/null

# --network none, no -p/--publish, and one explicitly sized tmpfs are enforced
# again by inspection before the restore. This container has no persistent or
# bind mounts and is removed by the guarded trap.
docker run -d --rm --name "$isolated" --network none --memory 2g --cpus 2 \
  --tmpfs /var/lib/postgresql/data:rw,noexec,nosuid,size=1g \
  --label rahgard.restore.target=isolated --label rahgard.environment=restore-test \
  -e POSTGRES_USER="$owner" -e POSTGRES_DB="$database" -e POSTGRES_HOST_AUTH_METHOD=trust "$image" >/dev/null
docker inspect "$isolated" | python3 -c '
import json,sys
x=json.load(sys.stdin)
if len(x)!=1: raise SystemExit("expected one isolated restore container")
c=x[0]; cfg=c.get("Config",{}); labels=cfg.get("Labels") or {}; host=c.get("HostConfig") or {}
if labels.get("rahgard.restore.target")!="isolated" or labels.get("rahgard.environment")!="restore-test": raise SystemExit("isolation labels missing")
if (host.get("NetworkMode")!="none" or host.get("PortBindings") or host.get("Binds") or host.get("Mounts")): raise SystemExit("network, published port, bind mount or persistent mount detected")
tmpfs=host.get("Tmpfs") or {}
if "/var/lib/postgresql/data" not in tmpfs: raise SystemExit("PGDATA is not tmpfs")
if any(m.get("Type")!="tmpfs" for m in c.get("Mounts") or []): raise SystemExit("non-tmpfs mount detected")
'
ready=false
for _ in $(seq 1 60); do
  if docker exec "$isolated" psql -X -q -A -t -h 127.0.0.1 -p 5432 -U "$owner" -d "$database" -c 'SELECT 1' >/dev/null 2>&1; then ready=true; break; fi
  sleep 1
done
[[ "$ready" == true ]] || { echo 'Isolated PostgreSQL did not accept loopback TCP SQL within 60 seconds.' >&2; exit 3; }
docker exec -i "$isolated" psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -U "$owner" -d "$database" <<'SQL' >/dev/null
CREATE ROLE ai_tourism_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_geo_executor NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_geo_migrator NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT rahgard_pilot_geo_executor TO rahgard_pilot_geo_migrator;
SQL
docker exec -i "$isolated" pg_restore -U "$owner" -d "$database" --exit-on-error --single-transaction < "$plain"

db_scalar() { docker exec "$isolated" psql -X -q -A -t -h 127.0.0.1 -p 5432 -U "$owner" -d "$database" -v ON_ERROR_STOP=1 -c "BEGIN READ ONLY; $1; COMMIT;" | tr -d '\r' | tail -n 1; }
db_rows() { docker exec "$isolated" psql -X -q -A -t -h 127.0.0.1 -p 5432 -U "$owner" -d "$database" -v ON_ERROR_STOP=1 -c "BEGIN READ ONLY; $1; COMMIT;" | tr -d '\r' | sed '/^[[:space:]]*$/d'; }
marker=$(db_scalar "SELECT marker_value FROM public.rahgard_private_pilot_marker")
[[ "$marker" =~ ^[a-fA-F0-9]{48}$ ]] || { echo 'Restored marker is invalid.' >&2; exit 3; }
[[ "$(db_scalar "SELECT current_database()")" == "$database" && "$(db_scalar "SELECT current_setting('server_version_num')::integer BETWEEN 170000 AND 179999")" == t ]] || { echo 'Restored database identity/version mismatch.' >&2; exit 3; }
ledger_before=$(db_scalar "SELECT count(*) FROM system.schema_migrations")
[[ "$ledger_before" == 16 ]] || { echo "Expected the verified 0017 ledger before rehearsal, found $ledger_before." >&2; exit 3; }
pre_hash=$(sha256sum "$release_dir/engineering/pilot/sql/017_provisional_itineraries.sql" | cut -d' ' -f1)
[[ "$(db_scalar "SELECT sha256 FROM system.schema_migrations WHERE migration_id='0017_provisional_itineraries'")" == "$pre_hash" ]] || { echo 'Restored 0017 checksum differs from target source.' >&2; exit 3; }
counts_sql="SELECT 'users',count(*) FROM identity.users UNION ALL SELECT 'conversations',count(*) FROM conversation.conversations UNION ALL SELECT 'messages',count(*) FROM conversation.messages UNION ALL SELECT 'trips',count(*) FROM travel.trips UNION ALL SELECT 'itineraries',count(*) FROM travel.itineraries UNION ALL SELECT 'itinerary_stops',count(*) FROM travel.itinerary_stops UNION ALL SELECT 'provisional_itineraries',count(*) FROM travel.provisional_itineraries UNION ALL SELECT 'destinations',count(*) FROM knowledge.destinations UNION ALL SELECT 'destination_sources',count(*) FROM knowledge.destination_sources UNION ALL SELECT 'knowledge_sources',count(*) FROM knowledge.knowledge_sources UNION ALL SELECT 'documents',count(*) FROM knowledge.knowledge_documents UNION ALL SELECT 'chunks',count(*) FROM knowledge.knowledge_chunks UNION ALL SELECT 'published_view',count(*) FROM knowledge.production_destinations ORDER BY 1"
counts_before=$(db_rows "$counts_sql")
source_count=$(awk -F'|' '$1=="published_view"{print $2}' <<<"$counts_before")
[[ "$source_count" =~ ^[0-9]+$ ]] || { echo 'Could not determine the restored publication-view count.' >&2; exit 3; }
echo 'RESTORE_PASS backup_sha256_and_hmac=verified decrypt=pass pg_restore_list=pass isolated_pg17=pass'
echo "RESTORED_LEDGER rows=$ledger_before tip=0017_provisional_itineraries"
echo 'RESTORED_COUNTS_BEGIN'; printf '%s\n' "$counts_before"; echo 'RESTORED_COUNTS_END'

files=(018_national_catalogue_ingestion.sql 019_partner_workspace.sql 020_archive_candidate_publication.sql 021_postgis_security_definer_publication.sql)
ids=(0018_national_catalogue_ingestion 0019_partner_workspace 0020_archive_candidate_publication 0021_postgis_security_definer_publication)
prior_hash="$pre_hash"
for i in "${!files[@]}"; do
  path="$release_dir/engineering/pilot/sql/${files[$i]}"
  hash=$(sha256sum "$path" | cut -d' ' -f1)
  case "$i" in
    0) prior_env=RAHGARD_PILOT_MIGRATION_0017_SHA256; current_env=RAHGARD_PILOT_MIGRATION_0018_SHA256 ;;
    1) prior_env=RAHGARD_PILOT_MIGRATION_0018_SHA256; current_env=RAHGARD_PILOT_MIGRATION_0019_SHA256 ;;
    2) prior_env=RAHGARD_PILOT_MIGRATION_0019_SHA256; current_env=RAHGARD_PILOT_MIGRATION_0020_SHA256 ;;
    3) prior_env=RAHGARD_PILOT_MIGRATION_0020_SHA256; current_env=RAHGARD_PILOT_MIGRATION_0021_SHA256 ;;
  esac
  {
    printf '%s\n%s\n%s\n' "$marker" "$prior_hash" "$hash"
    cat "$path"
  } | docker exec -i "$isolated" sh -lc "IFS= read -r marker; IFS= read -r prior; IFS= read -r migration; export RAHGARD_PILOT_DATABASE_MARKER=\"\$marker\" $prior_env=\"\$prior\" $current_env=\"\$migration\"; exec psql -X -q -A -t -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U '$owner' -d '$database'"
  [[ "$(db_scalar "SELECT sha256 FROM system.schema_migrations WHERE migration_id='${ids[$i]}'")" == "$hash" ]] || { echo "Migration checksum failed: ${ids[$i]}" >&2; exit 3; }
  printf 'MIGRATION_REHEARSAL_PASS %s sha256=%s\n' "${ids[$i]}" "$hash"
  prior_hash="$hash"
done

[[ "$(db_scalar "SELECT count(*) FROM system.schema_migrations")" == 20 ]] || { echo 'Final migration count is not 20.' >&2; exit 3; }
counts_after=$(db_rows "$counts_sql")
[[ "$counts_after" == "$counts_before" ]] || { echo 'Critical restored row counts changed during migration rehearsal.' >&2; exit 3; }
[[ "$(db_scalar "SELECT count(*) FROM knowledge.destination_candidates")" == 0 \
  && "$(db_scalar "SELECT count(*) FROM partner.organizations")" == 0 \
  && "$(db_scalar "SELECT count(*) FROM knowledge.catalogue_publication_events")" == 0 \
  && "$(db_scalar "SELECT count(*) FROM knowledge.production_destinations")" == "$(awk -F'|' '$1=="published_view"{print $2}' <<<"$counts_before")" ]] || { echo 'Unexpected candidate, partner or publication data appeared in the rehearsal.' >&2; exit 3; }
protected_tables="'operations.dataset_import_files','knowledge.destination_candidates','knowledge.destination_candidate_reviews','knowledge.source_candidates','knowledge.source_candidate_reviews','knowledge.destination_localizations','knowledge.destination_aliases','knowledge.destination_access_points','knowledge.destination_visit_duration_evidence','knowledge.destination_operational_assertions','partner.organizations','partner.memberships','partner.invitations','partner.verification_cases','partner.branches','partner.services','partner.service_localizations','partner.service_destinations','partner.schedules','partner.offers','partner.prices','partner.availability_snapshots','partner.review_events','knowledge.source_verification_reviews','knowledge.source_registry_registration_events','knowledge.destination_candidate_evidence','knowledge.catalogue_publication_events'"
rls_count=$(db_scalar "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r' AND c.relrowsecurity AND n.nspname||'.'||c.relname IN ($protected_tables)")
[[ "$rls_count" == 27 ]] || { echo "Expected RLS on 27 new review/partner tables, got $rls_count." >&2; exit 3; }
[[ "$(db_scalar "SELECT NOT rolsuper AND NOT rolbypassrls FROM pg_roles WHERE rolname='ai_tourism_app'")" == t ]] || { echo 'Application role has superuser or RLS-bypass privilege in the rehearsal.' >&2; exit 3; }
policy_count=$(db_scalar "SELECT count(*) FROM pg_policies WHERE schemaname IN ('geo','knowledge','operations','partner')")
[[ "$policy_count" =~ ^[0-9]+$ && "$policy_count" -gt 0 ]] || { echo 'Expected migration-defined review/tenant policies were not found.' >&2; exit 3; }
echo 'REHEARSAL_PASS migrations=20 critical_counts_unchanged=true candidates=0 partner_rows=0 publications=0'
echo "SECURITY_REHEARSAL_PASS protected_rls_tables=$rls_count policies=$policy_count app_role_bypass=false"

# Start the candidate API source against the restored database in the same
# network namespace. The VPS's authorized Docker Hub request returned 403 for
# the pinned Python base image, so create a source layer from the running API
# image instead. The dependency lock and entrypoint must match; this exercises
# the exact candidate backend source without an external image pull.
release_sha=$(cat "$release_dir/RELEASE_COMMIT")
suffix="${release_sha:0:8}-$$"
api_image="rahgard-restore-api:$suffix"
api_name="rahgard-restore-app-$suffix"
[[ "$suffix" =~ ^[0-9a-f]{8}-[0-9]+$ && "$api_name" =~ ^rahgard-restore-app-[0-9a-f]{8}-[0-9]+$ ]] || { echo 'Invalid isolated API test identity.' >&2; exit 2; }
[[ -z "$(docker ps -aq --filter "name=^/${api_name}$")" ]] || { echo 'Isolated API test container name already exists.' >&2; exit 2; }
[[ -z "$(docker image ls -q --filter "reference=$api_image")" ]] || { echo 'Isolated API test image tag already exists.' >&2; exit 2; }
compose=(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml")
live_api_id=$("${compose[@]}" ps -q api)
[[ -n "$live_api_id" && "$(docker inspect -f '{{.State.Running}}' "$live_api_id")" == true ]] || { echo 'Cannot identify the running managed API runtime.' >&2; exit 3; }
runtime_image_id=$(docker inspect -f '{{.Image}}' "$live_api_id")
[[ "$runtime_image_id" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo 'Managed API runtime image identity is invalid.' >&2; exit 3; }
runtime_image=$(docker inspect -f '{{.Config.Image}}' "$live_api_id")
[[ "$runtime_image" =~ ^rahgard-api:[0-9a-f]{40}$ ]] || { echo 'Managed API runtime tag is not the expected immutable release tag.' >&2; exit 3; }
docker image inspect "$runtime_image" >/dev/null
cmp -s "$root/current/uv.lock" "$release_dir/uv.lock" || { echo 'Candidate dependency lock differs from the active runtime; refusing a derived API rehearsal.' >&2; exit 3; }
cmp -s "$root/current/deploy/staging/api-entrypoint.sh" "$release_dir/deploy/staging/api-entrypoint.sh" || { echo 'Candidate entrypoint differs from the active runtime; refusing a derived API rehearsal.' >&2; exit 3; }
api_helper="rahgard-restore-layer-${release_sha:0:8}-$$"
[[ "$api_helper" =~ ^rahgard-restore-layer-[0-9a-f]{8}-[0-9]+$ ]] || { echo 'Invalid candidate-layer helper identity.' >&2; exit 2; }
[[ -z "$(docker ps -aq --filter "name=^/${api_helper}$")" ]] || { echo 'Candidate-layer helper container already exists.' >&2; exit 2; }
docker create --name "$api_helper" --network none \
  --label rahgard.restore.target=isolated --label rahgard.environment=restore-test \
  "$runtime_image" /bin/sh -c 'while :; do sleep 3600; done' >/dev/null
docker cp "$release_dir/backend/app/." "$api_helper:/app/backend/app/"
docker cp "$release_dir/backend/scripts/." "$api_helper:/app/backend/scripts/"
docker cp "$release_dir/scripts/rahgard_archive_preflight.py" "$api_helper:/app/backend/scripts/rahgard_archive_preflight.py"
docker commit "$api_helper" "$api_image" >/dev/null
api_image_created=true
docker rm "$api_helper" >/dev/null
api_helper=""
docker run -d --rm --name "$api_name" --network "container:$isolated" \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m --tmpfs /run/secrets:rw,noexec,nosuid,size=1m \
  --security-opt no-new-privileges:true --cap-drop ALL \
  --label rahgard.restore.target=isolated --label rahgard.environment=restore-test \
  -e APP_ENV=test -e APP_HOST=127.0.0.1 -e APP_PORT=8000 -e LOG_LEVEL=WARNING \
  -e DATABASE_HOST=127.0.0.1 -e DATABASE_PORT=5432 -e DATABASE_NAME="$database" \
  -e DATABASE_USER=ai_tourism_app -e DATABASE_CONNECT_TIMEOUT_SECONDS=3 \
  -e AUTH_ENABLED=false -e AUTH_LOCAL_OWNER_ENABLED=false -e STAGING_AUTH_ENABLED=false \
  -e AUTH_SMS_ADAPTER=disabled -e INTERNAL_CHAT_ENABLED=false -e TOURISM_RAG_ENABLED=false \
  -e AI_PROVIDER_ADMIN_ENABLED=false --entrypoint /bin/sh "$api_image" \
  -c 'while :; do sleep 3600; done' >/dev/null
docker exec -u 0 "$api_name" python -c 'from pathlib import Path; import secrets; p=Path("/run/secrets"); names=("app_db_password","auth_otp_hmac_secret","auth_csrf_secret","auth_rate_limit_secret"); [(p.joinpath(n).write_text(secrets.token_urlsafe(48)),p.joinpath(n).chmod(0o444)) for n in names]'
docker exec -d -w /app/backend "$api_name" /usr/local/bin/rahgard-entrypoint \
  uvicorn app.main:app --host 127.0.0.1 --port 8000 >/dev/null
api_ready=false
for _ in $(seq 1 40); do
  if docker exec "$api_name" python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=2)' >/dev/null 2>&1; then api_ready=true; break; fi
  sleep 1
done
[[ "$api_ready" == true ]] || { echo 'Candidate API did not become ready against the restored, migrated database.' >&2; exit 3; }
api_catalogue=$(docker exec "$api_name" python -c 'import json,urllib.request; r=urllib.request.urlopen("http://127.0.0.1:8000/api/v1/catalog/destinations",timeout=5); print(json.load(r)["count"])')
[[ "$api_catalogue" == "$source_count" ]] || { echo 'Candidate API catalogue count differs from the restored database view.' >&2; exit 3; }
echo "API_REHEARSAL_PASS release=$release_sha runtime_image_id=$runtime_image_id runtime_tag=$runtime_image lock_match=true health=ready catalogue_count=$api_catalogue auth=disabled chat=disabled rag=disabled sms=disabled network=none"
echo 'The isolated container and plaintext dump will now be removed; the encrypted backup remains retained.'
