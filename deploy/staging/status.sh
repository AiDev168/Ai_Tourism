#!/usr/bin/env bash
set -Eeuo pipefail
root=/opt/rahgard-staging
test -s "$root/.env"
current=$(readlink -f "$root/current" 2>/dev/null || true)
echo "Current release: ${current##*/}"
docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml" ps
if [[ -f "$root/state/database-initialization-complete" ]]; then
  docker compose --env-file "$root/.env" -f "$root/current/deploy/staging/compose.yaml" exec -T db \
    psql -X -q -A -t -U rahgard_db_owner -d rahgard_pilot_vps_staging \
    -c "SELECT 'migrations='||count(*) FROM system.schema_migrations;"
else
  echo 'Database initialization is not complete.'
fi
