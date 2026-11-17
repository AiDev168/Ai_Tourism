#!/bin/bash
set -euo pipefail
password_file=/run/secrets/app_db_password
test -r "$password_file"
export RAHGARD_APP_DB_PASSWORD="$(cat "$password_file")"
test -n "$RAHGARD_APP_DB_PASSWORD"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
\getenv app_password RAHGARD_APP_DB_PASSWORD
SELECT format('CREATE ROLE ai_tourism_app LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='ai_tourism_app')
\gexec
GRANT CONNECT ON DATABASE rahgard_pilot_vps_staging TO ai_tourism_app;
SQL
unset RAHGARD_APP_DB_PASSWORD
