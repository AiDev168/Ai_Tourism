#!/usr/bin/env bash
# Restore a fresh post-0021 backup into an isolated PG17 clone and prove the
# candidate runtime against the already-migrated schema without applying DDL.
set -Eeuo pipefail
umask 077

root=/opt/rahgard-staging
release_dir="${RAHGARD_REHEARSAL_RELEASE_DIR:-}"
backup_name="${1:-}"
release_sha="${2:-}"
api_image="${3:-}"
web_image="${4:-}"
database=rahgard_pilot_vps_staging
owner=ai_tourism_owner
expected_current_sha=5e2664fb51e18f52549aa37a8b5793e12ace09b2
expected_migrations=20

[[ "$release_sha" =~ ^[0-9a-f]{40}$ && "$backup_name" =~ ^rahgard-[A-Za-z0-9_.-]+\.dump\.enc$ \
  && "$api_image" == "rahgard-api:$release_sha" && "$web_image" == "rahgard-web:$release_sha" \
  && -d "$release_dir" && "$(cat "$release_dir/RELEASE_COMMIT")" == "$release_sha" ]] || {
  echo 'Usage: RAHGARD_REHEARSAL_RELEASE_DIR=<verified-release> rehearse-20-20.sh <backup-name> <source-sha> <api-image> <web-image>' >&2
  exit 2
}
[[ "$(cat "$root/current/RELEASE_COMMIT")" == "$expected_current_sha" ]] || {
  echo 'Live application is not the expected safe rollback release; refusing rehearsal.' >&2; exit 2;
}
backup="$root/backups/$backup_name"
[[ -f "$backup" && ! -L "$backup" && -s "$backup" \
  && -f "$backup.hmac" && ! -L "$backup.hmac" \
  && -f "$backup.sha256" && ! -L "$backup.sha256" ]] || { echo 'Fresh backup or sidecars are unavailable.' >&2; exit 2; }
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
line = open(sidecar, encoding='ascii').read(257)
match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.-]+)\n', line)
if len(key) < 32 or not match or match.group(2) != os.path.basename(archive):
    raise SystemExit('Backup HMAC key or sidecar is invalid.')
mac = hmac.new(key, digestmod=hashlib.sha256)
with open(archive, 'rb') as stream:
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        mac.update(block)
if not hmac.compare_digest(mac.hexdigest(), match.group(1)):
    raise SystemExit('Backup HMAC verification failed.')
PY

[[ "$(findmnt -T /dev/shm -n -o FSTYPE)" == tmpfs && -w /dev/shm ]] || { echo 'Writable tmpfs is required.' >&2; exit 2; }
plain_dir=$(mktemp -d /dev/shm/rahgard-20-20.XXXXXX)
chmod 0700 "$plain_dir"
plain="$plain_dir/database.dump"
suffix="${release_sha:0:8}-$$"
isolated="rahgard-current-schema-$suffix"
network="rahgard-current-schema-net-$suffix"
api_name="rahgard-current-api-$suffix"
web_name="rahgard-current-web-$suffix"
rollback_name=""
network_created=false
cleanup() {
  status=$?
  for name in "$rollback_name" "$web_name" "$api_name" "$isolated"; do
    if docker inspect "$name" >/dev/null 2>&1; then
      labels=$(docker inspect -f '{{index .Config.Labels "rahgard.test"}}|{{index .Config.Labels "org.opencontainers.image.revision"}}' "$name" 2>/dev/null || true)
      if [[ "$labels" == "schema-20-20|$release_sha" ]]; then docker rm -f "$name" >/dev/null 2>&1 || true; fi
    fi
  done
  if [[ "$network_created" == true ]] && docker network inspect "$network" >/dev/null 2>&1; then
    labels=$(docker network inspect -f '{{index .Labels "rahgard.test"}}|{{index .Labels "org.opencontainers.image.revision"}}' "$network" 2>/dev/null || true)
    if [[ "$labels" == "schema-20-20|$release_sha" ]]; then docker network rm "$network" >/dev/null 2>&1 || true; fi
  fi
  rm -rf -- "$plain_dir"
  exit "$status"
}
trap cleanup EXIT

openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 -pass file:"$root/secrets/backup_encryption_passphrase" -in "$backup" -out "$plain"
test -s "$plain"
compose=(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml")
live_db_id=$("${compose[@]}" ps -q db)
[[ -n "$live_db_id" && "$(docker inspect -f '{{.State.Running}}' "$live_db_id")" == true \
  && "$(docker inspect -f '{{.State.Health.Status}}' "$live_db_id")" == healthy \
  && "$(docker inspect -f '{{.Config.Image}}' "$live_db_id")" == rahgard-postgres:17-postgis36-vector087 \
  && "$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Type}}|{{.Name}}{{end}}{{end}}' "$live_db_id")" == volume\|rahgard_staging_pgdata ]] || {
  echo 'Live DB identity, image, health, or persistent volume changed; refusing rehearsal.' >&2; exit 2;
}
docker exec -i "$live_db_id" pg_restore --list < "$plain" >/dev/null
live_ledger=$(docker exec "$live_db_id" psql -X -q -A -t -U "$owner" -d "$database" -c 'BEGIN READ ONLY; SELECT migration_id||chr(58)||rtrim(sha256) FROM system.schema_migrations ORDER BY migration_id; COMMIT;' | tr -d '\r')
[[ "$(grep -c . <<<"$live_ledger")" == "$expected_migrations" ]] || {
  echo 'Current live DB ledger is not at exactly 20 migrations; refusing 20-to-20 rehearsal.' >&2; exit 2;
}

platform_image=rahgard-postgres:17-postgis36-vector087
docker image inspect "$platform_image" >/dev/null
docker image inspect "$api_image" >/dev/null
docker image inspect "$web_image" >/dev/null
read -r api_id api_os api_arch api_revision < <(docker image inspect --format '{{.Id}} {{.Os}} {{.Architecture}} {{index .Config.Labels "org.opencontainers.image.revision"}}' "$api_image")
read -r web_id web_os web_arch web_revision < <(docker image inspect --format '{{.Id}} {{.Os}} {{.Architecture}} {{index .Config.Labels "org.opencontainers.image.revision"}}' "$web_image")
[[ "$api_os/$api_arch" == linux/amd64 && "$web_os/$web_arch" == linux/amd64 \
  && "$api_revision" == "$release_sha" && "$web_revision" == "$release_sha" ]] || {
  echo 'Candidate API/Web image platform or source revision label is wrong.' >&2; exit 3;
}
[[ -z "$(docker ps -aq --filter "name=^/${isolated}$")" && -z "$(docker network ls -q --filter "name=^${network}$")" ]] || {
  echo 'Isolated test identity already exists.' >&2; exit 2;
}
docker network create --internal --driver bridge --label rahgard.test=schema-20-20 \
  --label "org.opencontainers.image.revision=$release_sha" "$network" >/dev/null
network_created=true
docker network inspect "$network" | python3 -c 'import json,sys; n=json.load(sys.stdin)[0]; assert n["Internal"] and n["Driver"]=="bridge" and n["Labels"].get("rahgard.test")=="schema-20-20"'
docker run -d --rm --name "$isolated" --network "$network" --network-alias db --memory 2g --cpus 2 \
  --tmpfs /var/lib/postgresql/data:rw,noexec,nosuid,size=1g \
  --label rahgard.test=schema-20-20 --label "org.opencontainers.image.revision=$release_sha" \
  -e POSTGRES_USER="$owner" -e POSTGRES_DB="$database" -e POSTGRES_HOST_AUTH_METHOD=trust "$platform_image" >/dev/null
docker inspect "$isolated" | python3 -c 'import json,sys; c=json.load(sys.stdin)[0]; h=c["HostConfig"]; assert h["NetworkMode"]==sys.argv[1] and not h["PortBindings"] and not h["Binds"] and not h.get("Mounts",[]) and "/var/lib/postgresql/data" in h["Tmpfs"] and all(m["Type"]=="tmpfs" for m in c.get("Mounts",[]))' "$network"
ready=false
for _ in $(seq 1 60); do
  if docker exec "$isolated" psql -X -q -A -t -h 127.0.0.1 -U "$owner" -d "$database" -c 'SELECT 1' >/dev/null 2>&1; then ready=true; break; fi
  sleep 1
done
[[ "$ready" == true ]] || { echo 'Disposable PostgreSQL 17 did not become ready.' >&2; exit 3; }
docker exec -i "$isolated" psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -U "$owner" -d "$database" <<'SQL' >/dev/null
CREATE ROLE ai_tourism_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_geo_executor NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_geo_migrator NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT rahgard_pilot_geo_executor TO rahgard_pilot_geo_migrator;
SQL
docker exec -i "$isolated" pg_restore -U "$owner" -d "$database" --exit-on-error --single-transaction < "$plain"

db_scalar() { docker exec "$isolated" psql -X -q -A -t -h 127.0.0.1 -U "$owner" -d "$database" -v ON_ERROR_STOP=1 -c "BEGIN READ ONLY; $1; COMMIT;" | tr -d '\r' | tail -n 1; }
db_rows() { docker exec "$isolated" psql -X -q -A -t -F '|' -h 127.0.0.1 -U "$owner" -d "$database" -v ON_ERROR_STOP=1 -c "BEGIN READ ONLY; $1; COMMIT;" | tr -d '\r' | sed '/^[[:space:]]*$/d'; }
live_db_rows() { docker exec "$live_db_id" psql -X -q -A -t -F '|' -U "$owner" -d "$database" -v ON_ERROR_STOP=1 -c "BEGIN READ ONLY; $1; COMMIT;" | tr -d '\r' | sed '/^[[:space:]]*$/d'; }
test "$(db_scalar "SELECT current_setting('server_version_num')::integer BETWEEN 170000 AND 179999")" = t
test "$(db_scalar "SELECT count(*) FROM system.schema_migrations")" = "$expected_migrations"
restored_ledger=$(db_rows "SELECT migration_id||chr(58)||rtrim(sha256) FROM system.schema_migrations ORDER BY migration_id")
[[ "$restored_ledger" == "$live_ledger" ]] || { echo 'Restored full migration ledger differs from the current live ledger.' >&2; exit 3; }
host_marker=$(cat "$root/state/database-marker")
[[ "$host_marker" =~ ^[a-fA-F0-9]{48}$ && "$(db_scalar "SELECT count(*) FROM public.rahgard_private_pilot_marker WHERE marker_value='$host_marker'")" == 1 ]] || {
  echo 'Restored database marker does not match protected host state.' >&2; exit 3;
}
expected_ids=(0018_national_catalogue_ingestion 0019_partner_workspace 0020_archive_candidate_publication 0021_postgis_security_definer_publication)
expected_files=(018_national_catalogue_ingestion.sql 019_partner_workspace.sql 020_archive_candidate_publication.sql 021_postgis_security_definer_publication.sql)
for i in "${!expected_ids[@]}"; do
  migration_file="$release_dir/engineering/pilot/sql/${expected_files[$i]}"
  expected_hash=$(sha256sum "$migration_file" | cut -d' ' -f1)
  crlf_hash=$(python3 - "$migration_file" <<'PY'
import hashlib, pathlib, sys
source = pathlib.Path(sys.argv[1]).read_bytes()
lf = source.replace(b"\r\n", b"\n")
if b"\r" in lf:
    raise SystemExit("Migration contains unsupported mixed line endings.")
print(hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest())
PY
)
  actual_hash=$(db_scalar "SELECT rtrim(sha256) FROM system.schema_migrations WHERE migration_id='${expected_ids[$i]}'")
  if [[ "$actual_hash" == "$expected_hash" ]]; then
    line_ending=lf
  elif [[ "$actual_hash" == "$crlf_hash" ]]; then
    line_ending=crlf
  else
    echo "20-entry restore has wrong migration content checksum: ${expected_ids[$i]}" >&2
    exit 3
  fi
  echo "MIGRATION_CHECKSUM_20_20_PASS id=${expected_ids[$i]} line_endings=$line_ending"
done
counts_sql="SELECT 'users',count(*) FROM identity.users UNION ALL SELECT 'sessions',count(*) FROM identity.web_sessions UNION ALL SELECT 'conversations',count(*) FROM conversation.conversations UNION ALL SELECT 'messages',count(*) FROM conversation.messages UNION ALL SELECT 'trips',count(*) FROM travel.trips UNION ALL SELECT 'itineraries',count(*) FROM travel.itineraries UNION ALL SELECT 'itinerary_stops',count(*) FROM travel.itinerary_stops UNION ALL SELECT 'provisional_itineraries',count(*) FROM travel.provisional_itineraries UNION ALL SELECT 'destinations',count(*) FROM knowledge.destinations UNION ALL SELECT 'destination_sources',count(*) FROM knowledge.destination_sources UNION ALL SELECT 'knowledge_sources',count(*) FROM knowledge.knowledge_sources UNION ALL SELECT 'documents',count(*) FROM knowledge.knowledge_documents UNION ALL SELECT 'chunks',count(*) FROM knowledge.knowledge_chunks UNION ALL SELECT 'published',count(*) FROM knowledge.production_destinations UNION ALL SELECT 'candidates',count(*) FROM knowledge.destination_candidates UNION ALL SELECT 'candidate_evidence',count(*) FROM knowledge.destination_candidate_evidence UNION ALL SELECT 'publication_events',count(*) FROM knowledge.catalogue_publication_events UNION ALL SELECT 'partner_orgs',count(*) FROM partner.organizations UNION ALL SELECT 'partner_services',count(*) FROM partner.services UNION ALL SELECT 'partner_schedules',count(*) FROM partner.schedules UNION ALL SELECT 'partner_offers',count(*) FROM partner.offers UNION ALL SELECT 'partner_prices',count(*) FROM partner.prices UNION ALL SELECT 'partner_availability',count(*) FROM partner.availability_snapshots ORDER BY 1"
counts_before=$(db_rows "$counts_sql")
live_counts=$(live_db_rows "$counts_sql")
[[ "$counts_before" == "$live_counts" ]] || { echo 'Restored aggregate counts differ from the current live DB snapshot.' >&2; exit 3; }
[[ "$(db_scalar "SELECT count(*) FROM knowledge.destination_candidates")" == 0 \
  && "$(db_scalar "SELECT count(*) FROM partner.organizations")" == 0 \
  && "$(db_scalar "SELECT count(*) FROM knowledge.catalogue_publication_events")" == 0 \
  && "$(db_scalar "SELECT count(*) FROM knowledge.production_destinations")" == 0 ]] || {
  echo 'The restore contains candidate/partner/publication data outside this rehearsal scope.' >&2; exit 3;
}
[[ "$(db_scalar "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE c.relkind='r' AND c.relrowsecurity AND n.nspname||'.'||c.relname IN ('operations.dataset_import_files','knowledge.destination_candidates','knowledge.destination_candidate_reviews','knowledge.source_candidates','knowledge.source_candidate_reviews','knowledge.destination_localizations','knowledge.destination_aliases','knowledge.destination_access_points','knowledge.destination_visit_duration_evidence','knowledge.destination_operational_assertions','partner.organizations','partner.memberships','partner.invitations','partner.verification_cases','partner.branches','partner.services','partner.service_localizations','partner.service_destinations','partner.schedules','partner.offers','partner.prices','partner.availability_snapshots','partner.review_events','knowledge.source_verification_reviews','knowledge.source_registry_registration_events','knowledge.destination_candidate_evidence','knowledge.catalogue_publication_events')")" == 27 ]] || {
  echo 'Expected 27 RLS-protected tables in the restored database.' >&2; exit 3;
}
[[ "$(db_scalar "SELECT count(*) FROM pg_policies WHERE schemaname IN ('geo','knowledge','operations','partner')")" == 67 ]] || {
  echo 'Expected 67 row-level security policies in the restored database.' >&2; exit 3;
}
[[ "$(db_scalar "SELECT NOT rolsuper AND NOT rolbypassrls FROM pg_roles WHERE rolname='ai_tourism_app'")" == t ]] || {
  echo 'Application role has elevated or RLS-bypass privileges in the restored database.' >&2; exit 3;
}
echo "RESTORE_20_20_PASS migrations=20 no_ddl=true data_counts=preserved rls_tables=27 policies=67 candidates=0 partner_rows=0 publications=0"
printf 'RESTORED_COUNTS_BEGIN\n%s\nRESTORED_COUNTS_END\n' "$counts_before"

"$release_dir/scripts/ops/test_rahgard_web_image_pwa.sh" "$web_image" "$release_sha"

runtime_secrets() {
  local name="$1"
  docker exec -u 0 "$name" python -c 'from pathlib import Path; import secrets; p=Path("/run/secrets"); names=("app_db_password","auth_otp_hmac_secret","auth_csrf_secret","auth_rate_limit_secret"); [(p.joinpath(n).write_text(secrets.token_urlsafe(48)),p.joinpath(n).chmod(0o444)) for n in names]'
  docker exec -d -w /app/backend "$name" /usr/local/bin/rahgard-entrypoint uvicorn app.main:app --host 0.0.0.0 --port 8000 >/dev/null
}
start_api() {
  local name="$1" image="$2" alias="$3"
  docker run -d --rm --name "$name" --network "$network" --network-alias "$alias" \
    --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m --tmpfs /run/secrets:rw,noexec,nosuid,size=1m \
    --security-opt no-new-privileges:true --cap-drop ALL \
    --label rahgard.test=schema-20-20 --label "org.opencontainers.image.revision=$release_sha" \
    -e APP_ENV=test -e APP_HOST=0.0.0.0 -e APP_PORT=8000 -e LOG_LEVEL=WARNING \
    -e DATABASE_HOST=db -e DATABASE_PORT=5432 -e DATABASE_NAME="$database" -e DATABASE_USER=ai_tourism_app \
    -e DATABASE_CONNECT_TIMEOUT_SECONDS=3 -e AUTH_ENABLED=false -e AUTH_LOCAL_OWNER_ENABLED=false \
    -e STAGING_AUTH_ENABLED=false -e AUTH_SMS_ADAPTER=disabled -e INTERNAL_CHAT_ENABLED=false \
    -e TOURISM_RAG_ENABLED=false -e AI_PROVIDER_ADMIN_ENABLED=false \
    --entrypoint /bin/sh "$image" -c 'while :; do sleep 3600; done' >/dev/null
  runtime_secrets "$name"
  local ready=false
  for _ in $(seq 1 40); do
    if docker exec "$name" python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=2)' >/dev/null 2>&1; then ready=true; break; fi
    sleep 1
  done
  [[ "$ready" == true ]] || { echo "API image did not become ready: $image" >&2; exit 3; }
}
start_api "$api_name" "$api_image" api
new_catalogue=$(docker exec "$api_name" python -c 'import json,urllib.request; print(json.load(urllib.request.urlopen("http://127.0.0.1:8000/api/v1/catalog/destinations",timeout=5))["count"])')
[[ "$new_catalogue" == 0 ]] || { echo 'Candidate API returned a non-empty catalogue in the 20-entry clone.' >&2; exit 3; }
echo "API_20_20_PASS source=$release_sha image_id=$api_id health=ready catalogue_count=0 auth=disabled chat=disabled rag=disabled sms=disabled network=internal"

docker run -d --name "$web_name" --network "$network" --network-alias web --read-only \
  --tmpfs /var/cache/nginx:rw,noexec,nosuid,size=32m --tmpfs /var/run:rw,noexec,nosuid,size=4m \
  --security-opt no-new-privileges:true --cap-drop ALL --cap-add CHOWN --cap-add SETUID --cap-add SETGID \
  --label rahgard.test=schema-20-20 --label "org.opencontainers.image.revision=$release_sha" \
  --entrypoint nginx "$web_image" -g 'daemon off;' >/dev/null
proxy=$(docker exec "$api_name" python -c 'import json,urllib.request; print(json.load(urllib.request.urlopen("http://web:8080/api/v1/catalog/destinations",timeout=8))["count"])')
[[ "$proxy" == 0 ]] || { echo 'Web reverse-proxy catalogue response was non-empty or inconsistent.' >&2; exit 3; }
echo "WEB_PROXY_20_20_PASS image_id=$web_id catalogue_count=0 network=internal"

docker rm -f "$web_name" "$api_name" >/dev/null
web_name=""
api_name=""
rollback_name="rahgard-current-api-rollback-$suffix"
[[ -z "$(docker ps -aq --filter "name=^/${rollback_name}$")" ]] || { echo 'Rollback test identity already exists.' >&2; exit 2; }
start_api "$rollback_name" "rahgard-api:$expected_current_sha" rollback-api
rollback_catalogue=$(docker exec "$rollback_name" python -c 'import json,urllib.request; print(json.load(urllib.request.urlopen("http://127.0.0.1:8000/api/v1/catalog/destinations",timeout=5))["count"])')
[[ "$rollback_catalogue" == 0 ]] || { echo 'Previous API compatibility check returned a non-empty catalogue.' >&2; exit 3; }
docker rm -f "$rollback_name" >/dev/null
echo "OLD_API_20_20_PASS image=rahgard-api:$expected_current_sha health=ready catalogue_count=0 data_rollback=not_performed"
echo 'SCHEMA_20_20_REHEARSAL_PASS live_services_touched=false live_database_touched=false migrations_applied=0'
