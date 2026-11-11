\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0013_hash RAHGARD_PILOT_MIGRATION_0013_SHA256
BEGIN;

SELECT 1 / CASE WHEN current_database() ~ '^rahgard_pilot_[a-z0-9_]{3,40}$'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND inet_server_port() <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker) = 1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) = :'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_0013_hash' ~ '^[a-f0-9]{64}$'
    AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
                    AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls))
    AND EXISTS (SELECT 1 FROM system.schema_migrations
                WHERE migration_id='0013_private_pilot_geo_audit' AND sha256=:'migration_0013_hash')
    AND EXISTS (SELECT 1 FROM knowledge.production_destinations
                WHERE destination_key IN ('shiraz-hafezieh-v1','shiraz-eram-garden-v1',
                                          'shiraz-vakil-bazaar-v1','unesco-persepolis-v1'))
    THEN 1 ELSE 0 END;

CREATE TABLE identity.local_owner_credentials (
    owner_id UUID PRIMARY KEY REFERENCES identity.users(user_id) ON DELETE CASCADE,
    login_name TEXT NOT NULL UNIQUE CHECK (login_name ~ '^[a-z][a-z0-9._-]{2,39}$'),
    salt BYTEA NOT NULL CHECK (octet_length(salt) = 32),
    verifier BYTEA NOT NULL CHECK (octet_length(verifier) = 32),
    iterations INTEGER NOT NULL CHECK (iterations BETWEEN 250000 AND 1000000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now()
);
CREATE UNIQUE INDEX uq_local_owner_single_account ON identity.local_owner_credentials ((true));

CREATE TABLE identity.local_owner_login_limits (
    dimension TEXT NOT NULL CHECK (dimension IN ('login', 'peer')),
    subject_digest BYTEA NOT NULL CHECK (octet_length(subject_digest) = 32),
    window_started_at TIMESTAMPTZ NOT NULL,
    hit_count INTEGER NOT NULL CHECK (hit_count > 0),
    PRIMARY KEY (dimension, subject_digest, window_started_at)
);
CREATE INDEX idx_local_owner_login_limits_window ON identity.local_owner_login_limits(window_started_at);

REVOKE ALL ON identity.local_owner_credentials, identity.local_owner_login_limits FROM PUBLIC;
GRANT SELECT ON identity.local_owner_credentials TO ai_tourism_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON identity.local_owner_login_limits TO ai_tourism_app;

INSERT INTO system.schema_migrations (migration_id, sha256)
VALUES ('0014_local_owner_login', :'migration_hash');
COMMIT;
