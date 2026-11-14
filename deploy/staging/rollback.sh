#!/usr/bin/env bash
set -Eeuo pipefail
root=/opt/rahgard-staging
sha="${1:-}"
confirm="${2:-}"
[[ "$sha" =~ ^[0-9a-f]{40}$ && "$confirm" == schema-compatible ]] || {
  echo 'Usage: rollback.sh <previous-tested-commit-sha> schema-compatible' >&2
  echo 'Operator must verify the older code supports the current migration ledger first.' >&2; exit 2;
}
release="$root/releases/$sha"
test -s "$release/RELEASE_COMMIT" && test "$(cat "$release/RELEASE_COMMIT")" = "$sha"
old=$(readlink -f "$root/current")
ln -s "$release" "$root/.current-rollback"
mv -Tf "$root/.current-rollback" "$root/current"
if ! docker compose --env-file "$root/.env" -f "$release/deploy/staging/compose.yaml" up -d --no-build; then
  ln -s "$old" "$root/.current-rollback"; mv -Tf "$root/.current-rollback" "$root/current"
  docker compose --env-file "$root/.env" -f "$old/deploy/staging/compose.yaml" up -d --no-build || true
  exit 1
fi
echo "Application rolled back to $sha; database was not modified."
