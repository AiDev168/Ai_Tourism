#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
root=/opt/rahgard-staging
sha="${1:-}"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Usage: deploy.sh <tested-commit-sha>' >&2; exit 2; }
release="$root/releases/$sha"
test "$(cat "$release/RELEASE_COMMIT")" = "$sha"
test -s "$root/.env"
build_images=$(sed -n 's/^RAHGARD_BUILD_IMAGES=//p' "$root/.env" | tail -1)
build_images="${build_images:-true}"
build_images="${build_images%$'\r'}"
state="$root/state"
[[ -f "$state/database-initialization-complete" ]] || {
  echo 'The isolated database is not initialized; deploy will not initialize or recreate it.' >&2; exit 2;
}
previous=""; previous_sha=""; previous_compose=(); db_id=""
source "$release/deploy/staging/compose-runtime.sh"
if [[ -L "$root/current" ]]; then
  previous=$(readlink -f "$root/current")
  previous_sha=$(cat "$previous/RELEASE_COMMIT")
  [[ "$previous_sha" =~ ^[0-9a-f]{40}$ ]]
  rahgard_compose_init "$root/.env" "$previous" previous_compose
  db_id=$("${previous_compose[@]}" ps -q db)
  [[ -n "$db_id" && "$(docker inspect -f '{{.State.Running}}' "$db_id")" == true ]]
  [[ "$(docker inspect -f '{{.State.Health.Status}}' "$db_id")" == healthy ]]
  [[ "$(docker inspect -f '{{.Config.Image}}' "$db_id")" == 'rahgard-postgres:17-postgis36-vector087' ]]
  volume_name=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/var/lib/postgresql/data"}}{{.Type}}|{{.Name}}{{end}}{{end}}' "$db_id")
  expected_volume=$(sed -n 's/^RAHGARD_PG_VOLUME=//p' "$root/.env" | tail -1)
  expected_volume="${expected_volume:-rahgard_staging_pgdata}"
  expected_volume="${expected_volume%$'\r'}"
  [[ "$volume_name" == "volume|$expected_volume" ]] || {
    echo 'Existing PostgreSQL data volume identity is unexpected; refusing application upgrade.' >&2; exit 2;
  }
else
  echo 'No current release exists; this guarded upgrade requires an initialized running pilot.' >&2
  exit 2
fi

set_release_sha() {
  local value="$1"
  [[ "$value" =~ ^[0-9a-f]{40}$ ]]
  if grep -q '^RAHGARD_RELEASE_SHA=' "$root/.env"; then
    sed -i "s/^RAHGARD_RELEASE_SHA=.*/RAHGARD_RELEASE_SHA=$value/" "$root/.env"
  else
    printf 'RAHGARD_RELEASE_SHA=%s\n' "$value" >> "$root/.env"
  fi
  chmod 0600 "$root/.env"
}
compose=()
rahgard_compose_init "$root/.env" "$release" compose
next="$root/.current-$sha"
rollback() {
  local status=$?
  if (( status != 0 )); then
    echo 'Release health failed; reverting application symlink and retaining the database volume.' >&2
    if [[ -n "$previous" ]]; then
      set_release_sha "$previous_sha"
      ln -s "$previous" "$next"; mv -Tf "$next" "$root/current"
      "${previous_compose[@]}" up -d --no-build --no-deps api web || true
      [[ "$(docker inspect -f '{{.State.Running}}' "$db_id" 2>/dev/null || true)" == true ]] || echo 'Database container identity changed; investigate before writes.' >&2
    else
      rm -f "$root/current"
    fi
  fi
  exit "$status"
}
case "$build_images" in
  true|1|yes)
    RAHGARD_RELEASE_SHA="$sha" "${compose[@]}" build --pull=false
    ;;
  false|0|no)
    for image in "rahgard-api:$sha" "rahgard-web:$sha" 'rahgard-postgres:17-postgis36-vector087'; do
      docker image inspect "$image" >/dev/null 2>&1 || {
        echo "Required prebuilt image is missing; release was not started: $image" >&2
        exit 2
      }
    done
    ;;
  *)
    echo 'RAHGARD_BUILD_IMAGES must be true or false.' >&2
    exit 2
    ;;
esac
test -s "$release/scripts/ops/test_rahgard_web_image_pwa.sh" || {
  echo 'Release is missing the mandatory PWA image acceptance gate; current release was not changed.' >&2
  exit 2
}
bash "$release/scripts/ops/test_rahgard_web_image_pwa.sh" "rahgard-web:$sha" "$sha"

# Do not change the release marker or current symlink until the candidate Web
# image has served all essential PWA resources through its unprivileged Nginx
# worker. Container health alone does not establish functional readiness.
set_release_sha "$sha"
ln -s "$release" "$next"
mv -Tf "$next" "$root/current"
trap rollback EXIT
docker exec "$db_id" pg_isready -U ai_tourism_owner -d rahgard_pilot_vps_staging >/dev/null
"${compose[@]}" up -d --no-deps --no-build api web
api_id=$("${compose[@]}" ps -q api); web_id=$("${compose[@]}" ps -q web)
[[ -n "$api_id" && -n "$web_id" ]]
for _ in $(seq 1 60); do
  api_health=$(docker inspect -f '{{.State.Health.Status}}' "$api_id" 2>/dev/null || true)
  web_health=$(docker inspect -f '{{.State.Health.Status}}' "$web_id" 2>/dev/null || true)
  [[ "$api_health" == healthy && "$web_health" == healthy ]] && break
  sleep 2
done
[[ "$(docker inspect -f '{{.State.Health.Status}}' "$api_id")" == healthy ]]
[[ "$(docker inspect -f '{{.State.Health.Status}}' "$web_id")" == healthy ]]
[[ "$(docker inspect -f '{{.State.Running}}' "$db_id")" == true ]]
[[ "$(docker inspect -f '{{.Config.Image}}' "$api_id")" == "rahgard-api:$sha" ]]
[[ "$(docker inspect -f '{{.Config.Image}}' "$web_id")" == "rahgard-web:$sha" ]]
[[ "$(docker inspect -f '{{.State.Health.Status}}' "$db_id")" == healthy ]]
"${compose[@]}" ps
curl --fail --silent --show-error --max-time 10 "http://127.0.0.1:${RAHGARD_WEB_BIND_PORT:-18080}/" >/dev/null
docker exec "$api_id" python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health/ready",timeout=5)'
trap - EXIT
printf 'PASS: application release %s is running; PostgreSQL named volume was preserved.\n' "$sha"
