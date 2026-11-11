\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0014_hash RAHGARD_PILOT_MIGRATION_0014_SHA256
\getenv migration_hash RAHGARD_PILOT_MIGRATION_0015_SHA256

-- Additive provider-control schema. Apply only with the marked local-pilot
-- migration operator; do not execute against development/shared databases.
BEGIN;
SELECT 1 / CASE WHEN current_database() ~ '^rahgard_pilot_[a-z0-9_]{3,40}$'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND inet_server_port() <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker) = 1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) = :'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_0014_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND EXISTS (SELECT 1 FROM system.schema_migrations
                WHERE migration_id='0014_local_owner_login' AND sha256=:'migration_0014_hash')
    AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
                    AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls))
    AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles r
                    WHERE pg_has_role(current_user, r.oid, 'MEMBER')
                      AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls))
    AND NOT EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0015_ai_provider_admin')
    THEN 1 ELSE 0 END;

CREATE SCHEMA ai_provider;
REVOKE ALL ON SCHEMA ai_provider FROM PUBLIC;

CREATE TABLE ai_provider.profiles (
    profile_id UUID PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
    name TEXT NOT NULL CHECK (length(btrim(name)) BETWEEN 1 AND 100),
    provider_kind TEXT NOT NULL CHECK (provider_kind IN ('lm_studio','openai_compatible')),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    archived_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    created_by UUID NOT NULL REFERENCES identity.users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    UNIQUE (name),
    CHECK (archived_at IS NULL OR enabled = FALSE)
);

CREATE TABLE ai_provider.revisions (
    revision_id UUID PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES ai_provider.profiles(profile_id),
    revision_no INTEGER NOT NULL CHECK (revision_no > 0),
    -- Config must be non-secret, validated metadata. Secret values are stored
    -- only in the OS vault; this column is an opaque vault reference.
    config JSONB NOT NULL CHECK (pg_catalog.jsonb_typeof(config) = 'object'),
    secret_ref TEXT CHECK (secret_ref IS NULL OR length(secret_ref) BETWEEN 8 AND 512),
    created_by UUID NOT NULL REFERENCES identity.users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    UNIQUE (profile_id, revision_no)
);
CREATE INDEX ix_ai_provider_revisions_profile ON ai_provider.revisions(profile_id, revision_no DESC);

CREATE TABLE ai_provider.revision_validations (
    validation_id UUID PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
    revision_id UUID NOT NULL REFERENCES ai_provider.revisions(revision_id),
    outcome TEXT NOT NULL CHECK (outcome IN ('valid','invalid','unavailable')),
    details JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (pg_catalog.jsonb_typeof(details)='object'),
    validated_by UUID REFERENCES identity.users(user_id),
    validated_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now()
);
CREATE INDEX ix_ai_provider_validations_latest ON ai_provider.revision_validations(revision_id, validated_at DESC);

CREATE TABLE ai_provider.active_routes (
    capability TEXT PRIMARY KEY CHECK (capability IN ('chat','vision','embedding','reranking')),
    revision_id UUID REFERENCES ai_provider.revisions(revision_id),
    generation BIGINT NOT NULL DEFAULT 0 CHECK (generation >= 0),
    updated_by UUID REFERENCES identity.users(user_id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now()
);
INSERT INTO ai_provider.active_routes(capability) VALUES ('chat'),('vision'),('embedding'),('reranking');

CREATE TABLE ai_provider.fallback_policy (
    capability TEXT PRIMARY KEY REFERENCES ai_provider.active_routes(capability),
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ordered_revision_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    updated_by UUID REFERENCES identity.users(user_id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    CHECK (enabled OR cardinality(ordered_revision_ids)=0)
);
INSERT INTO ai_provider.fallback_policy(capability) VALUES ('chat'),('vision'),('embedding'),('reranking');

CREATE TABLE ai_provider.audit_events (
    event_id UUID PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
    actor_id UUID REFERENCES identity.users(user_id),
    action TEXT NOT NULL CHECK (length(action) BETWEEN 1 AND 80),
    target_type TEXT NOT NULL CHECK (length(target_type) BETWEEN 1 AND 40),
    target_id TEXT,
    outcome TEXT NOT NULL CHECK (outcome IN ('success','denied','failure')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (pg_catalog.jsonb_typeof(metadata)='object'),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now()
);
CREATE INDEX ix_ai_provider_audit_recent ON ai_provider.audit_events(occurred_at DESC);

-- Usage is populated only by real bounded Gateway calls; zero rows means no
-- instrumented invocation, not a fabricated successful metric.
CREATE TABLE ai_provider.usage_events (
    usage_id UUID PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
    capability TEXT NOT NULL CHECK (capability IN ('chat','vision','embedding','reranking')),
    revision_id UUID REFERENCES ai_provider.revisions(revision_id),
    outcome TEXT NOT NULL CHECK (outcome IN ('success','unavailable','rejected')),
    latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    input_units INTEGER CHECK (input_units IS NULL OR input_units >= 0),
    output_units INTEGER CHECK (output_units IS NULL OR output_units >= 0),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now()
);
CREATE INDEX ix_ai_provider_usage_recent ON ai_provider.usage_events(occurred_at DESC);

-- Provider-admin authority is independent from traveler and local-owner roles.
CREATE TABLE identity.ai_provider_admin_grants (
    user_id UUID PRIMARY KEY REFERENCES identity.users(user_id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    granted_by UUID REFERENCES identity.users(user_id),
    revoked_at TIMESTAMPTZ,
    CHECK (revoked_at IS NULL OR revoked_at >= granted_at)
);
CREATE TABLE identity.ai_provider_admin_mfa (
    user_id UUID PRIMARY KEY REFERENCES identity.ai_provider_admin_grants(user_id) ON DELETE CASCADE,
    secret_ref TEXT,
    pending_secret_ref TEXT,
    enabled_at TIMESTAMPTZ,
    last_totp_counter BIGINT NOT NULL DEFAULT -1 CHECK (last_totp_counter >= -1),
    recovery_hashes BYTEA[] NOT NULL DEFAULT ARRAY[]::BYTEA[],
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    CHECK ((enabled_at IS NULL) = (secret_ref IS NULL)),
    CHECK (cardinality(recovery_hashes) <= 20)
);
CREATE TABLE identity.ai_provider_admin_step_up (
    user_id UUID NOT NULL REFERENCES identity.ai_provider_admin_mfa(user_id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES identity.web_sessions(session_id) ON DELETE CASCADE,
    verified_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, session_id),
    CHECK (expires_at > verified_at AND expires_at <= verified_at + INTERVAL '15 minutes'),
    CHECK (revoked_at IS NULL OR revoked_at >= verified_at)
);

-- Backend role is the only runtime reader/writer; route-level capability,
-- session, CSRF and step-up checks remain mandatory for every admin operation.
GRANT USAGE ON SCHEMA ai_provider TO ai_tourism_app;
GRANT SELECT, INSERT, UPDATE ON ai_provider.profiles, ai_provider.revisions,
    ai_provider.active_routes, ai_provider.fallback_policy TO ai_tourism_app;
GRANT SELECT, INSERT ON ai_provider.revision_validations, ai_provider.audit_events,
    ai_provider.usage_events TO ai_tourism_app;
GRANT SELECT ON identity.ai_provider_admin_grants TO ai_tourism_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON identity.ai_provider_admin_mfa,
    identity.ai_provider_admin_step_up TO ai_tourism_app;
REVOKE UPDATE, DELETE ON ai_provider.revisions, ai_provider.revision_validations,
    ai_provider.audit_events, ai_provider.usage_events FROM ai_tourism_app;
REVOKE ALL ON ai_provider.profiles, ai_provider.revisions, ai_provider.active_routes,
    ai_provider.fallback_policy, ai_provider.revision_validations,
    ai_provider.audit_events, ai_provider.usage_events FROM PUBLIC;
REVOKE ALL ON identity.ai_provider_admin_grants, identity.ai_provider_admin_mfa,
    identity.ai_provider_admin_step_up FROM PUBLIC;

INSERT INTO system.schema_migrations(migration_id, sha256)
VALUES ('0015_ai_provider_admin', :'migration_hash');
COMMIT;
