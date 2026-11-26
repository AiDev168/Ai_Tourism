#!/usr/bin/env bash
set -Eeuo pipefail
root=/opt/rahgard-staging
db_owner=ai_tourism_owner
db_name=rahgard_pilot_vps_staging
test -s "$root/.env"
current=$(readlink -f "$root/current" 2>/dev/null || true)
echo "Current release: ${current##*/}"
source "$current/deploy/staging/compose-runtime.sh"
compose=()
rahgard_compose_init "$root/.env" "$current" compose
"${compose[@]}" ps
if [[ -f "$root/state/database-initialization-complete" ]]; then
  "${compose[@]}" exec -T db \
    psql -X -q -A -t -U "$db_owner" -d "$db_name" \
    -c "SELECT 'migrations='||count(*) FROM system.schema_migrations;"
else
  echo 'Database initialization is not complete.'
fi
