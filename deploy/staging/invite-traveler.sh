#!/usr/bin/env bash
set -Eeuo pipefail
root=/opt/rahgard-staging
test -s "$root/.env"
compose=(docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml")
# `compose run` invokes the image entrypoint so mounted secrets are loaded for
# this one operator command. No invitation-management HTTP route exists.
"${compose[@]}" run --rm --no-deps api python -m scripts.create_staging_invite "$@"
