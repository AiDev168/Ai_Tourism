#!/usr/bin/env bash
# Starts the exact archived API image against an isolated restored PG target.
# No ports are published; only health and approved-catalogue counts are read.
set -Eeuo pipefail
umask 077
bundle_dir="${1:-}"
target_container="${2:-}"
target_db="${3:-}"
[[ -d "$bundle_dir" && ! -L "$bundle_dir" && -n "$target_container" \
   && "$target_db" =~ ^rahgard_restore_[A-Za-z0-9_]{1,45}$ ]] || {
  echo 'Usage: restore-portable-app-check.sh <authenticated-extraction-dir> <isolated-pg-container> <rahgard_restore_dbname>' >&2
  exit 2
}
bundle_dir=$(realpath -e -- "$bundle_dir")
(
  cd -- "$bundle_dir"
  sha256sum --check MANIFEST.sha256 >/dev/null
)
release_sha=$(cat "$bundle_dir/release/RELEASE_COMMIT")
[[ "$release_sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Invalid archived release SHA.' >&2; exit 2; }
test -s "$bundle_dir/private/secrets/app_db_password"

docker inspect "$target_container" | python3 -c '
import json,sys
x=json.load(sys.stdin)
if len(x)!=1: raise SystemExit("Expected exactly one target container.")
c=x[0]; labels=c.get("Config",{}).get("Labels") or {}
if labels.get("rahgard.restore.target")!="isolated" or labels.get("rahgard.environment") not in {"restore-test","qa","test"}:
    raise SystemExit("Target lacks isolated restore labels.")
if c.get("State",{}).get("Running") is not True: raise SystemExit("Target database is not running.")
if not any(m.get("Type")=="tmpfs" and m.get("Destination")=="/var/lib/postgresql/data" for m in c.get("Mounts") or []):
    raise SystemExit("Target database does not use tmpfs.")
if any(v for v in (c.get("NetworkSettings",{}).get("Ports") or {}).values() if v):
    raise SystemExit("Target database has a published port.")
'
source_count=$(docker exec "$target_container" psql -X -q -A -t -U ai_tourism_owner -d "$target_db" \
  -c 'SELECT count(*) FROM knowledge.production_destinations')
[[ "$source_count" =~ ^[0-9]+$ ]] || { echo 'Cannot read restored catalogue through owner role.' >&2; exit 2; }

run_suffix="${release_sha:0:8}-$$"
image="rahgard-restore-check:${run_suffix}"
app_name="rahgard-restore-api-${run_suffix}"
secret_volume="rahgard-restore-secrets-${run_suffix}"
[[ "$app_name" =~ ^rahgard-restore-api-[0-9a-f]{8}-[0-9]+$ \
   && "$secret_volume" =~ ^rahgard-restore-secrets-[0-9a-f]{8}-[0-9]+$ ]] || exit 2
running=$(docker ps -aq --filter "name=^/${app_name}$")
[[ -z "$running" ]] || { echo 'Restore-check container name already exists; refusing reuse.' >&2; exit 2; }
volume_exists=$(docker volume ls -q --filter "name=^${secret_volume}$")
[[ -z "$volume_exists" ]] || { echo 'Restore-check secret volume already exists; refusing reuse.' >&2; exit 2; }
image_exists=$(docker image ls -q --filter "reference=$image")
[[ -z "$image_exists" ]] || { echo 'Restore-check image tag already exists; refusing reuse.' >&2; exit 2; }
cleanup() {
  docker rm -f "$app_name" >/dev/null 2>&1 || true
  docker volume rm "$secret_volume" >/dev/null 2>&1 || true
  docker image rm "$image" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker build --pull=false -f "$bundle_dir/release/deploy/staging/Dockerfile.api" -t "$image" "$bundle_dir/release" >/dev/null
docker volume create "$secret_volume" >/dev/null
app_uid=$(docker run --rm --entrypoint sh "$image" -c 'id -u rahgard')
app_gid=$(docker run --rm --entrypoint sh "$image" -c 'id -g rahgard')
[[ "$app_uid" =~ ^[0-9]+$ && "$app_gid" =~ ^[0-9]+$ ]] || { echo 'Cannot resolve application runtime UID/GID.' >&2; exit 2; }
docker run --rm --user 0 \
  --mount "type=bind,src=$bundle_dir/private/secrets,dst=/source,readonly" \
  --mount "type=volume,src=$secret_volume,dst=/target" \
  --entrypoint sh "$image" -ceu "cp -a /source/. /target/; chmod 0440 /target/*; chown -R $app_uid:$app_gid /target"

# Keep credential files mounted read-only. The application entrypoint consumes
# them server-side and never returns them or places them in request logs.
docker run -d --name "$app_name" --rm \
  --network "container:$target_container" \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  --security-opt no-new-privileges:true --cap-drop ALL \
  --mount "type=volume,src=$secret_volume,dst=/run/secrets,readonly" \
  -e APP_ENV=test -e APP_HOST=0.0.0.0 -e APP_PORT=8000 -e LOG_LEVEL=WARNING \
  -e DATABASE_HOST=127.0.0.1 -e DATABASE_PORT=5432 -e DATABASE_NAME="$target_db" \
  -e DATABASE_USER=ai_tourism_app -e DATABASE_CONNECT_TIMEOUT_SECONDS=3 \
  -e AUTH_ENABLED=false -e AUTH_SMS_ADAPTER=disabled -e AUTH_LOCAL_OWNER_ENABLED=false \
  -e STAGING_AUTH_ENABLED=false -e AUTH_COOKIE_SECURE=true \
  -e INTERNAL_CHAT_ENABLED=false -e TOURISM_RAG_ENABLED=false "$image" >/dev/null

ready=false
for _ in $(seq 1 30); do
  if docker exec "$app_name" python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health/ready", timeout=2)' >/dev/null 2>&1; then
    ready=true; break
  fi
  if [[ $(docker inspect -f '{{.State.Running}}' "$app_name" 2>/dev/null || true) != true ]]; then
    docker logs "$app_name" >&2
    echo 'Restored API process exited; inspect the redacted startup logs above.' >&2
    exit 3
  fi
  sleep 1
done
[[ "$ready" == true ]] || { docker logs "$app_name" >&2; echo 'Restored API did not become ready.' >&2; exit 3; }
api_count=$(docker exec "$app_name" python -c '
import json,urllib.request
with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/catalog/destinations",timeout=5) as r:
    payload=json.load(r)
print(payload["count"])
')
[[ "$api_count" == "$source_count" ]] || { echo 'Restored API catalogue count differs from restored DB view.' >&2; exit 3; }
printf 'PASS: archived API release=%s starts and passes /health/ready against isolated PostgreSQL 17.\n' "$release_sha"
printf 'PASS: authenticated catalogue endpoint returns %s approved destinations; no host ports were published.\n' "$api_count"
