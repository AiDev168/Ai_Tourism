\set ON_ERROR_STOP on

-- The bootstrap/superuser role is used only for migrations and administration.
-- Create or rotate a separate least-privilege application login.
SELECT CASE
    WHEN EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user')
    THEN format('ALTER ROLE %I WITH LOGIN PASSWORD %L', :'app_user', :'app_password')
    ELSE format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password')
END
\gexec

BEGIN;

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS system;
CREATE TABLE IF NOT EXISTS system.schema_migrations (
    migration_id TEXT PRIMARY KEY,
    sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMIT;
