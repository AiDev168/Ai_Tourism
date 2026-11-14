\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0013_hash RAHGARD_PILOT_MIGRATION_0013_SHA256
\getenv migration_hash RAHGARD_PILOT_MIGRATION_0016_SHA256

-- Invitation-only traveler authentication for an isolated Internet staging
-- deployment. This is additive and never enables the local-owner/admin path.
BEGIN;
SELECT 1 / CASE WHEN current_database() = 'rahgard_pilot_vps_staging'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND inet_server_port() <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker) = 1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) = :'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_0013_hash' ~ '^[a-f0-9]{64}$'
    AND EXISTS (SELECT 1 FROM system.schema_migrations
                WHERE migration_id='0013_private_pilot_geo_audit'
                  AND sha256=:'migration_0013_hash')
    AND NOT EXISTS (SELECT 1 FROM system.schema_migrations
                    WHERE migration_id='0016_staging_invitation_auth')
    THEN 1 ELSE 0 END;

CREATE TABLE identity.staging_invites (
    invite_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_digest BYTEA NOT NULL UNIQUE CHECK (octet_length(token_digest)=32),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    consumed_by UUID REFERENCES identity.users(user_id) ON DELETE SET NULL,
    CHECK (expires_at > created_at AND expires_at <= created_at + INTERVAL '14 days'),
    CHECK ((consumed_at IS NULL) = (consumed_by IS NULL))
);

CREATE TABLE identity.staging_password_credentials (
    user_id UUID PRIMARY KEY REFERENCES identity.users(user_id) ON DELETE CASCADE,
    login_name TEXT NOT NULL UNIQUE CHECK (
        login_name = lower(login_name) AND length(login_name) BETWEEN 5 AND 254
        AND login_name ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'
    ),
    salt BYTEA NOT NULL CHECK (octet_length(salt)=32),
    verifier BYTEA NOT NULL CHECK (octet_length(verifier)=32),
    iterations INTEGER NOT NULL CHECK (iterations=600000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE identity.staging_auth_limits (
    dimension TEXT NOT NULL CHECK (dimension IN ('login_name','global','invite')),
    subject_digest BYTEA NOT NULL CHECK (octet_length(subject_digest)=32),
    window_started_at TIMESTAMPTZ NOT NULL,
    hit_count INTEGER NOT NULL CHECK (hit_count > 0),
    PRIMARY KEY (dimension, subject_digest, window_started_at)
);
CREATE INDEX ix_staging_auth_limits_window
    ON identity.staging_auth_limits(window_started_at);

REVOKE ALL ON identity.staging_invites, identity.staging_password_credentials,
    identity.staging_auth_limits FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON identity.staging_invites TO ai_tourism_app;
GRANT SELECT, INSERT ON identity.staging_password_credentials TO ai_tourism_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON identity.staging_auth_limits TO ai_tourism_app;
INSERT INTO system.schema_migrations(migration_id,sha256)
VALUES ('0016_staging_invitation_auth', :'migration_hash');
COMMIT;
