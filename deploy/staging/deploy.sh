#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
root=/opt/rahgard-staging
sha="${1:-}"
[[ "$sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'Usage: deploy.sh <tested-commit-sha>' >&2; exit 2; }
release="$root/releases/$sha"
test "$(cat "$release/RELEASE_COMMIT")" = "$sha"
test -s "$root/.env"
grep -q "^RAHGARD_RELEASE_SHA=$sha$" "$root/.env" || {
  sed -i "s/^RAHGARD_RELEASE_SHA=.*/RAHGARD_RELEASE_SHA=$sha/" "$root/.env"
  chmod 0600 "$root/.env"
}
state="$root/state"
[[ -f "$state/database-initialization-complete" ]] || {
  echo 'The isolated database is not initialized. Run initialize-db.sh once, after reviewing its target guards.' >&2; exit 2;
}
compose=(docker compose --env-file "$root/.env" -f "$release/deploy/staging/compose.yaml")
previous=""
if [[ -L "$root/current" ]]; then previous=$(readlink -f "$root/current"); fi
next="$root/.current-$sha"
ln -s "$release" "$next"
mv -Tf "$next" "$root/current"
rollback() {
  local status=$?
  if (( status != 0 )); then
    echo 'Release health failed; reverting application symlink and retaining the database volume.' >&2
    if [[ -n "$previous" ]]; then
      ln -s "$previous" "$next"; mv -Tf "$next" "$root/current"
      docker compose --env-file "$root/.env" -f "$previous/deploy/staging/compose.yaml" up -d --no-build || true
    else
      rm -f "$root/current"
      "${compose[@]}" down --remove-orphans || true
    fi
  fi
  exit "$status"
}
trap rollback EXIT
"${compose[@]}" build --pull=false
"${compose[@]}" up -d db
for _ in $(seq 1 60); do
  if "${compose[@]}" exec -T db pg_isready -U ai_tourism_owner -d rahgard_pilot_vps_staging >/dev/null 2>&1; then break; fi
  sleep 2
done
"${compose[@]}" exec -T db pg_isready -U ai_tourism_owner -d rahgard_pilot_vps_staging >/dev/null
"${compose[@]}" up -d --remove-orphans
"${compose[@]}" ps
curl --fail --silent --show-error --max-time 10 "http://127.0.0.1:${RAHGARD_WEB_BIND_PORT:-18080}/" >/dev/null
trap - EXIT
printf 'PASS: application release %s is running; PostgreSQL named volume was preserved.\n' "$sha"
