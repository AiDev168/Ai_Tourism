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
python3 "$bundle_dir/release/deploy/staging/verify-portable-images.py" \
  "$bundle_dir/runtime-images.tar" "$bundle_dir/runtime-image-identities.tsv" "$release_sha"

docker inspect "$target_container" | python3 -c '
import json,sys
x=json.load(sys.stdin)
if len(x)!=1: raise SystemExit("Expected exactly one target container.")
c=x[0]; labels=c.get("Config",{}).get("Labels") or {}
if labels.get("rahgard.restore.target")!="isolated" or labels.get("rahgard.environment") not in {"restore-test","qa","test"}:
    raise SystemExit("Target lacks isolated restore labels.")
if c.get("State",{}).get("Running") is not True: raise SystemExit("Target database is not running.")
host=c.get("HostConfig") or {}
if host.get("NetworkMode")!="none": raise SystemExit("Target database must have Docker network mode none.")
tmpfs=host.get("Tmpfs") or {}
if "/var/lib/postgresql/data" not in tmpfs:
    raise SystemExit("Target database does not use tmpfs.")
if host.get("Binds") or host.get("Mounts"):
    raise SystemExit("Target database has an unexpected persistent/bind mount configuration.")
if any(m.get("Type")!="tmpfs" or m.get("Destination") not in tmpfs for m in c.get("Mounts") or []):
    raise SystemExit("Target database has an unexpected persistent/bind mount.")
if any(v for v in (c.get("NetworkSettings",{}).get("Ports") or {}).values() if v):
    raise SystemExit("Target database has a published port.")
'
source_count=$(docker exec "$target_container" psql -X -q -A -t -U ai_tourism_owner -d "$target_db" \
  -c 'SELECT count(*) FROM knowledge.production_destinations')
[[ "$source_count" =~ ^[0-9]+$ ]] || { echo 'Cannot read restored catalogue through owner role.' >&2; exit 2; }

run_suffix="${release_sha:0:8}-$$"
source_image="rahgard-api:${release_sha}"
source_web_image="rahgard-web:${release_sha}"
app_name="rahgard-restore-api-${run_suffix}"
web_app_name="rahgard-restore-web-${run_suffix}"
secret_volume="rahgard-restore-secrets-${run_suffix}"
admin_volume="rahgard-restore-admin-${run_suffix}"
keyring_volume="rahgard-restore-keyring-${run_suffix}"
runtime_dir="${TMPDIR:-/tmp}/rahgard-restore-runtime-${run_suffix}"
[[ -f "$bundle_dir/private/state/platform-mfa-status" && ! -L "$bundle_dir/private/state/platform-mfa-status" \
   && -f "$bundle_dir/private/state/provider-admin-status" && ! -L "$bundle_dir/private/state/provider-admin-status" ]] || {
  echo 'Portable protected runtime state is missing or unsafe.' >&2; exit 2;
}
mfa_status=$(cat "$bundle_dir/private/state/platform-mfa-status")
provider_status=$(cat "$bundle_dir/private/state/provider-admin-status")
[[ "$mfa_status" == mfa_enabled || "$mfa_status" == mfa_disabled ]] || { echo 'Invalid archived MFA state.' >&2; exit 2; }
[[ "$provider_status" == true || "$provider_status" == false ]] || { echo 'Invalid archived provider-admin state.' >&2; exit 2; }
provider_volume="rahgard_restore_provider_${run_suffix}"
provider_target=none
if [[ "$provider_status" == true ]]; then provider_target="$provider_volume"; fi
[[ "$app_name" =~ ^rahgard-restore-api-[0-9a-f]{8}-[0-9]+$ \
   && "$secret_volume" =~ ^rahgard-restore-secrets-[0-9a-f]{8}-[0-9]+$ \
   && "$admin_volume" =~ ^rahgard-restore-admin-[0-9a-f]{8}-[0-9]+$ \
   && "$keyring_volume" =~ ^rahgard-restore-keyring-[0-9a-f]{8}-[0-9]+$ \
   && "$provider_volume" =~ ^rahgard_restore_provider_[0-9a-f]{8}-[0-9]+$ ]] || exit 2
running=$(docker ps -aq --filter "name=^/${app_name}$")
[[ -z "$running" ]] || { echo 'Restore-check container name already exists; refusing reuse.' >&2; exit 2; }
for volume in "$secret_volume" "$admin_volume" "$keyring_volume"; do
  [[ -z "$(docker volume ls -q --filter "name=^${volume}$")" ]] || {
    echo 'Restore-check runtime volume already exists; refusing reuse.' >&2; exit 2;
  }
done
if [[ "$provider_status" == true ]]; then
  [[ -z "$(docker volume ls -q --filter "name=^${provider_volume}$")" ]] || {
    echo 'Restore-check provider vault volume already exists; refusing reuse.' >&2; exit 2;
  }
fi
created_secret_volume=false
created_admin_volume=false
created_keyring_volume=false
created_provider_volume=false
created_app_container=false
created_web_container=false
cleanup() {
  if [[ "$created_web_container" == true ]]; then
    container_label=$(docker inspect --format '{{index .Config.Labels "rahgard.restore.target"}}' "$web_app_name" 2>/dev/null || true)
    [[ "$container_label" != isolated ]] || docker rm -f "$web_app_name" >/dev/null 2>&1 || true
  fi
  if [[ "$created_app_container" == true ]]; then
    container_label=$(docker inspect --format '{{index .Config.Labels "rahgard.restore.target"}}' "$app_name" 2>/dev/null || true)
    [[ "$container_label" != isolated ]] || docker rm -f "$app_name" >/dev/null 2>&1 || true
  fi
  [[ "$created_secret_volume" != true ]] || docker volume rm "$secret_volume" >/dev/null 2>&1 || true
  [[ "$created_admin_volume" != true ]] || docker volume rm "$admin_volume" >/dev/null 2>&1 || true
  [[ "$created_keyring_volume" != true ]] || docker volume rm "$keyring_volume" >/dev/null 2>&1 || true
  [[ "$created_provider_volume" != true ]] || docker volume rm "$provider_volume" >/dev/null 2>&1 || true
  [[ ! -d "$runtime_dir" ]] || rm -rf -- "$runtime_dir"
}
trap cleanup EXIT
expected_api_id=$(awk -F'|' -v tag="$source_image" '$1==tag {print $2}' "$bundle_dir/runtime-image-identities.tsv")
expected_web_id=$(awk -F'|' -v tag="$source_web_image" '$1==tag {print $2}' "$bundle_dir/runtime-image-identities.tsv")
[[ "$expected_api_id" =~ ^sha256:[0-9a-f]{64}$ && "$expected_web_id" =~ ^sha256:[0-9a-f]{64}$ ]] || { echo 'Portable API/Web image identity record is incomplete.' >&2; exit 2; }
for pair in "$source_image|$expected_api_id" "$source_web_image|$expected_web_id"; do
  image_name=${pair%%|*}; expected_id=${pair#*|}
  if docker image inspect "$image_name" >/dev/null 2>&1; then
    actual_id=$(docker image inspect --format '{{.Id}}' "$image_name")
    [[ "$actual_id" == "$expected_id" ]] || { echo "Cached immutable image conflicts with portable bundle: $image_name" >&2; exit 2; }
  else
    needs_load=true
  fi
done
if [[ "${needs_load:-false}" == true ]]; then
  docker load --input "$bundle_dir/runtime-images.tar" >/dev/null
fi
for pair in "$source_image|$expected_api_id" "$source_web_image|$expected_web_id"; do
  image_name=${pair%%|*}; expected_id=${pair#*|}
  actual_id=$(docker image inspect --format '{{.Id}}' "$image_name")
  [[ "$actual_id" == "$expected_id" ]] || { echo "Loaded immutable image identity mismatch: $image_name" >&2; exit 2; }
done
image="$source_image"
printf 'Using verified portable API/Web image IDs for immutable release %s.\n' "$release_sha"
docker volume create --label rahgard.restore.target=isolated --label rahgard.environment=restore-test "$secret_volume" >/dev/null
created_secret_volume=true
app_uid=$(docker run --rm --entrypoint sh "$image" -c 'id -u rahgard')
app_gid=$(docker run --rm --entrypoint sh "$image" -c 'id -g rahgard')
[[ "$app_uid" =~ ^[0-9]+$ && "$app_gid" =~ ^[0-9]+$ ]] || { echo 'Cannot resolve application runtime UID/GID.' >&2; exit 2; }
docker run --rm --user 0 \
  --mount "type=bind,src=$bundle_dir/private/secrets,dst=/source,readonly" \
  --mount "type=volume,src=$secret_volume,dst=/target" \
  --entrypoint sh "$image" -ceu "cp -a /source/. /target/; chmod 0440 /target/*; chown -R $app_uid:$app_gid /target"

if [[ -e "$runtime_dir" ]]; then echo 'Restore runtime target already exists; refusing reuse.' >&2; exit 2; fi
runtime_restore="$bundle_dir/release/deploy/staging/restore-portable-runtime.sh"
[[ -f "$runtime_restore" && ! -L "$runtime_restore" ]] || { echo 'Portable release is missing the runtime overlay restore verifier.' >&2; exit 2; }
bash "$runtime_restore" "$bundle_dir" "$runtime_dir" "$provider_target" "$provider_target"
if [[ "$provider_status" == true ]]; then created_provider_volume=true; fi
if [[ "$mfa_status" == mfa_enabled ]]; then
  [[ -z "$(docker volume ls -q --filter "name=^${admin_volume}$")" ]] || { echo 'Restore MFA volume name already exists.' >&2; exit 2; }
  docker volume create --label rahgard.restore.target=isolated --label rahgard.environment=restore-test "$admin_volume" >/dev/null
  created_admin_volume=true
  docker run --rm --user 0 --network none \
    --mount "type=bind,src=$runtime_dir/admin-secrets,dst=/source,readonly" \
    --mount "type=volume,src=$admin_volume,dst=/target" \
    --entrypoint sh "$image" -ceu "cp /source/platform_admin_mfa_encryption_key_hex /target/; cp /source/platform_admin_recovery_pepper /target/; chmod 0400 /target/*; chown -R $app_uid:$app_gid /target"
fi
if [[ "$provider_status" == true ]]; then
  [[ -z "$(docker volume ls -q --filter "name=^${keyring_volume}$")" ]] || { echo 'Restore provider-keyring volume name already exists.' >&2; exit 2; }
  docker volume create --label rahgard.restore.target=isolated --label rahgard.environment=restore-test "$keyring_volume" >/dev/null
  created_keyring_volume=true
  docker run --rm --user 0 --network none \
    --mount "type=bind,src=$runtime_dir/provider-keyring,dst=/source,readonly" \
    --mount "type=volume,src=$keyring_volume,dst=/target" \
    --entrypoint sh "$image" -ceu "cp /source/ai_provider_vault_keyring.json /target/; chmod 0400 /target/ai_provider_vault_keyring.json; chown -R $app_uid:$app_gid /target"
fi
for volume in "$secret_volume" "$admin_volume" "$keyring_volume"; do
  if [[ "$volume" == "$secret_volume" || ( "$volume" == "$admin_volume" && "$mfa_status" == mfa_enabled ) || ( "$volume" == "$keyring_volume" && "$provider_status" == true ) ]]; then
    labels=$(docker volume inspect --format '{{index .Labels "rahgard.restore.target"}}|{{index .Labels "rahgard.environment"}}' "$volume")
    [[ "$labels" == 'isolated|restore-test' ]] || { echo 'A restored runtime volume lacks isolated restore-test labels.' >&2; exit 2; }
  fi
done

# Keep credential files mounted read-only. The application entrypoint consumes
# them server-side and never returns them or places them in request logs.
api_mounts=(--mount "type=volume,src=$secret_volume,dst=/run/secrets,readonly")
api_env=(-e APP_ENV=staging -e APP_HOST=0.0.0.0 -e APP_PORT=8000 -e LOG_LEVEL=WARNING \
  -e DATABASE_HOST=127.0.0.1 -e DATABASE_PORT=5432 -e DATABASE_NAME="$target_db" \
  -e DATABASE_USER=ai_tourism_app -e DATABASE_CONNECT_TIMEOUT_SECONDS=3 \
  -e AUTH_ENABLED=true -e AUTH_SMS_ADAPTER=disabled -e AUTH_LOCAL_OWNER_ENABLED=false \
  -e STAGING_AUTH_ENABLED=false -e STAGING_PUBLIC_HOST=restore.invalid \
  -e AUTH_ALLOWED_ORIGINS=https://restore.invalid -e AUTH_COOKIE_SECURE=true \
  -e INTERNAL_CHAT_ENABLED=false -e TOURISM_RAG_ENABLED=false \
  -e AI_PROVIDER_ADMIN_ENABLED="$provider_status")
if [[ "$mfa_status" == mfa_enabled ]]; then
  api_mounts+=(--mount "type=volume,src=$admin_volume,dst=/run/rahgard-admin-secrets,readonly")
  api_env+=(-e PLATFORM_ADMIN_MFA_ENCRYPTION_KEY_FILE=/run/rahgard-admin-secrets/platform_admin_mfa_encryption_key_hex \
    -e PLATFORM_ADMIN_RECOVERY_PEPPER_FILE=/run/rahgard-admin-secrets/platform_admin_recovery_pepper)
fi
if [[ "$provider_status" == true ]]; then
  api_mounts+=(--mount "type=volume,src=$provider_volume,dst=/var/lib/rahgard/provider-vault,readonly" \
    --mount "type=volume,src=$keyring_volume,dst=/run/rahgard-provider-keyring,readonly")
  api_env+=(-e AI_PROVIDER_VAULT_DIR=/var/lib/rahgard/provider-vault \
    -e AI_PROVIDER_VAULT_KEY_FILE=/run/rahgard-provider-keyring/ai_provider_vault_keyring.json)
fi
start_and_check_api() {
docker run -d --name "$app_name" --rm \
  --label rahgard.restore.target=isolated --label rahgard.environment=restore-test \
  --network "container:$target_container" \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  --security-opt no-new-privileges:true --cap-drop ALL \
  "${api_mounts[@]}" "${api_env[@]}" "$image" >/dev/null
created_app_container=true
app_labels=$(docker inspect --format '{{index .Config.Labels "rahgard.restore.target"}}|{{index .Config.Labels "rahgard.environment"}}' "$app_name")
[[ "$app_labels" == 'isolated|restore-test' ]] || { echo 'Restored API container lacks isolated restore-test labels.' >&2; exit 2; }

ready=false
for _ in $(seq 1 30); do
  if docker exec "$app_name" python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health/ready", timeout=2)' >/dev/null 2>&1; then
    ready=true; break
  fi
  if [[ $(docker inspect -f '{{.State.Running}}' "$app_name" 2>/dev/null || true) != true ]]; then
    echo 'Restored API process exited; startup diagnostics were intentionally not emitted.' >&2
    exit 3
  fi
  sleep 1
done
[[ "$ready" == true ]] || { echo 'Restored API did not become ready; startup diagnostics were intentionally not emitted.' >&2; exit 3; }
}
start_and_check_api
api_count=$(docker exec "$app_name" python -c '
import json,urllib.request
with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/catalog/destinations",timeout=5) as r:
    payload=json.load(r)
print(payload["count"])
')
[[ "$api_count" == "$source_count" ]] || { echo 'Restored API catalogue count differs from restored DB view.' >&2; exit 3; }
restore_web_config="$runtime_dir/nginx-web-restore.conf"
python3 "$bundle_dir/release/scripts/ops/prepare_rahgard_restore_web_config.py" \
  "$bundle_dir/release/deploy/staging/nginx-web.conf" "$restore_web_config" >/dev/null
chmod 0600 "$restore_web_config"
start_and_check_web() {
  [[ -z "$(docker ps -aq --filter "name=^/${web_app_name}$")" ]] || {
    echo 'Restore-check Web container name already exists; refusing reuse.' >&2; exit 2;
  }
  docker run -d --name "$web_app_name" --rm \
    --label rahgard.restore.target=isolated --label rahgard.environment=restore-test \
    --network "container:$app_name" \
    --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16m \
    --tmpfs /var/cache/nginx:rw,noexec,nosuid,size=16m \
    --tmpfs /var/run:rw,noexec,nosuid,size=16m \
    --mount "type=bind,src=$restore_web_config,dst=/etc/nginx/conf.d/default.conf,readonly" \
    --security-opt no-new-privileges:true --cap-drop ALL \
    "$source_web_image" >/dev/null
  created_web_container=true
  web_labels=$(docker inspect --format '{{index .Config.Labels "rahgard.restore.target"}}|{{index .Config.Labels "rahgard.environment"}}' "$web_app_name")
  [[ "$web_labels" == 'isolated|restore-test' ]] || { echo 'Restored Web container lacks isolated restore-test labels.' >&2; exit 2; }
  ready=false
  for _ in $(seq 1 20); do
    if [[ $(docker inspect -f '{{.State.Running}}' "$web_app_name" 2>/dev/null || true) != true ]]; then
      echo 'Restored Web process exited; startup diagnostics were intentionally not emitted.' >&2
      exit 3
    fi
    if docker exec "$app_name" python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8080/", timeout=2)' >/dev/null 2>&1; then
      ready=true; break
    fi
    sleep 1
  done
  [[ "$ready" == true ]] || { echo 'Restored Web image did not become ready; startup diagnostics were intentionally not emitted.' >&2; exit 3; }
  docker exec -e "RAHGARD_RESTORE_EXPECTED_CATALOG_COUNT=$api_count" "$app_name" python -c '
import json, os, re, urllib.request
base = "http://127.0.0.1:8080"
def get(path):
    with urllib.request.urlopen(base + path, timeout=5) as response:
        return response.status, response.headers, response.read()
status, _, body = get("/")
html = body.decode("utf-8")
assert status == 200 and "<html" in html.lower(), "web_shell_not_served"
assets = re.findall(r"(?:src|href)=\"(/assets/[^\"]+\.(?:js|css))\"", html)
assert len(assets) >= 2 and any(path.endswith(".js") for path in assets) and any(path.endswith(".css") for path in assets), "hashed_assets_missing"
for path in assets:
    asset_status, asset_headers, asset_body = get(path)
    assert asset_status == 200 and asset_body and "immutable" in asset_headers.get("Cache-Control", ""), "hashed_asset_unavailable"
manifest_status, manifest_headers, manifest_body = get("/manifest.webmanifest")
assert manifest_status == 200 and "manifest+json" in manifest_headers.get("Content-Type", ""), "pwa_manifest_unavailable"
json.loads(manifest_body)
sw_status, sw_headers, sw_body = get("/sw.js")
assert sw_status == 200 and sw_body and "no-store" in sw_headers.get("Cache-Control", ""), "service_worker_unavailable"
auth_status, _, auth_body = get("/api/v1/auth/method")
assert auth_status == 200 and isinstance(json.loads(auth_body), dict), "web_to_api_auth_proxy_failed"
catalog_status, _, catalog_body = get("/api/v1/catalog/destinations")
assert catalog_status == 200 and json.loads(catalog_body).get("count") == int(os.environ["RAHGARD_RESTORE_EXPECTED_CATALOG_COUNT"]), "web_to_api_catalogue_proxy_failed"
print("web_http=200 api_proxy=200 manifest=200 sw=200 hashed_assets=" + str(len(assets)))
'
}
start_and_check_web
docker stop "$web_app_name" >/dev/null
created_web_container=false
docker stop "$app_name" >/dev/null
created_app_container=false
start_and_check_api
start_and_check_web
printf 'PASS: archived API and Web release=%s survive restart with restored MFA/provider overlays; API, hashed PWA assets, manifest, service worker and Web-to-API proxy passed against isolated PostgreSQL 17.\n' "$release_sha"
printf 'PASS: authenticated catalogue endpoint returns %s approved destinations; no host ports were published.\n' "$api_count"
printf 'Imported immutable image tags remain cached; verify the outer bundle checksum before any later use.\n'
