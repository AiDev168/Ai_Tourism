#!/usr/bin/env bash
set -Eeuo pipefail
root=/opt/rahgard-staging
test -s "$root/.env"
current=$(readlink -f "$root/current")
source "$current/deploy/staging/compose-runtime.sh"
compose=()
rahgard_compose_init "$root/.env" "$current" compose
"${compose[@]}" stop web api db
echo 'Rahgard containers stopped. Named PostgreSQL volume and files were preserved.'
