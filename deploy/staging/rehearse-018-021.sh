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
cleanup() {
  status=$?
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
docker exec "$(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml" ps -q db)" pg_restore --list < "$plain" >/dev/null

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
  if docker exec "$isolated" pg_isready -U "$owner" -d "$database" >/dev/null 2>&1; then ready=true; break; fi
  sleep 1
done
[[ "$ready" == true ]] || { echo 'Isolated PostgreSQL did not become ready.' >&2; exit 3; }
docker exec "$isolated" psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -U "$owner" -d "$database" <<'SQL' >/dev/null
CREATE ROLE ai_tourism_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_geo_executor NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
CREATE ROLE rahgard_pilot_geo_migrator NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
GRANT rahgard_pilot_geo_executor TO rahgard_pilot_geo_migrator;
SQL
docker exec -i "$isolated" pg_restore -U "$owner" -d "$database" --exit-on-error --single-transaction < "$plain"

db_scalar() { docker exec "$isolated" psql -X -q -A -t -h 127.0.0.1 -p 5432 -U "$owner" -d "$database" -v ON_ERROR_STOP=1 -c "BEGIN READ ONLY; $1; COMMIT;" | tr -d '\r' | tail -n 1; }
marker=$(db_scalar "SELECT marker_value FROM public.rahgard_private_pilot_marker")
[[ "$marker" =~ ^[a-fA-F0-9]{48}$ ]] || { echo 'Restored marker is invalid.' >&2; exit 3; }
[[ "$(db_scalar "SELECT current_database()")" == "$database" && "$(db_scalar "SELECT current_setting('server_version_num')::integer BETWEEN 170000 AND 179999")" == t ]] || { echo 'Restored database identity/version mismatch.' >&2; exit 3; }
ledger_before=$(db_scalar "SELECT count(*) FROM system.schema_migrations")
[[ "$ledger_before" == 16 ]] || { echo "Expected the verified 0017 ledger before rehearsal, found $ledger_before." >&2; exit 3; }
pre_hash=$(sha256sum "$release_dir/engineering/pilot/sql/017_provisional_itineraries.sql" | cut -d' ' -f1)
[[ "$(db_scalar "SELECT sha256 FROM system.schema_migrations WHERE migration_id='0017_provisional_itineraries'")" == "$pre_hash" ]] || { echo 'Restored 0017 checksum differs from target source.' >&2; exit 3; }
counts_sql="SELECT 'users',count(*) FROM identity.users UNION ALL SELECT 'conversations',count(*) FROM conversation.conversations UNION ALL SELECT 'messages',count(*) FROM conversation.messages UNION ALL SELECT 'trips',count(*) FROM travel.trips UNION ALL SELECT 'itineraries',count(*) FROM travel.itineraries UNION ALL SELECT 'itinerary_stops',count(*) FROM travel.itinerary_stops UNION ALL SELECT 'provisional_itineraries',count(*) FROM travel.provisional_itineraries UNION ALL SELECT 'destinations',count(*) FROM knowledge.destinations UNION ALL SELECT 'destination_sources',count(*) FROM knowledge.destination_sources UNION ALL SELECT 'knowledge_sources',count(*) FROM knowledge.knowledge_sources UNION ALL SELECT 'documents',count(*) FROM knowledge.knowledge_documents UNION ALL SELECT 'chunks',count(*) FROM knowledge.knowledge_chunks UNION ALL SELECT 'published_view',count(*) FROM knowledge.production_destinations ORDER BY 1"
counts_before=$(db_scalar "$counts_sql")
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
  } | docker exec -i "$isolated" sh -lc "IFS= read -r marker; IFS= read -r prior; IFS= read -r migration; export RAHGARD_PILOT_DATABASE_MARKER=\"\$marker\" $prior_env=\"\$prior\" $current_env=\"\$migration\"; exec psql -X -v ON_ERROR_STOP=1 -h 127.0.0.1 -p 5432 -U '$owner' -d '$database'"
  [[ "$(db_scalar "SELECT sha256 FROM system.schema_migrations WHERE migration_id='${ids[$i]}'")" == "$hash" ]] || { echo "Migration checksum failed: ${ids[$i]}" >&2; exit 3; }
  printf 'MIGRATION_REHEARSAL_PASS %s sha256=%s\n' "${ids[$i]}" "$hash"
  prior_hash="$hash"
done

[[ "$(db_scalar "SELECT count(*) FROM system.schema_migrations")" == 20 ]] || { echo 'Final migration count is not 20.' >&2; exit 3; }
counts_after=$(db_scalar "$counts_sql")
[[ "$counts_after" == "$counts_before" ]] || { echo 'Critical restored row counts changed during migration rehearsal.' >&2; exit 3; }
[[ "$(db_scalar "SELECT count(*) FROM knowledge.destination_candidates")" == 0 \
  && "$(db_scalar "SELECT count(*) FROM partner.organizations")" == 0 \
  && "$(db_scalar "SELECT count(*) FROM knowledge.catalogue_publication_events")" == 0 \
  && "$(db_scalar "SELECT count(*) FROM knowledge.production_destinations")" == "$(awk -F'|' '$1=="published_view"{print $2}' <<<"$counts_before")" ]] || { echo 'Unexpected candidate, partner or publication data appeared in the rehearsal.' >&2; exit 3; }
echo 'REHEARSAL_PASS migrations=20 critical_counts_unchanged=true candidates=0 partner_rows=0 publications=0'
echo 'The isolated container and plaintext dump will now be removed; the encrypted backup remains retained.'
