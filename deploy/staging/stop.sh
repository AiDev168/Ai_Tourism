#!/usr/bin/env bash
set -Eeuo pipefail
root=/opt/rahgard-staging
test -s "$root/.env"
docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml" stop web api db
echo 'Rahgard containers stopped. Named PostgreSQL volume and files were preserved.'
