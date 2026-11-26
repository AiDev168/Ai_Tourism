\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0024_hash RAHGARD_PILOT_MIGRATION_0024_SHA256
\getenv migration_0025_hash RAHGARD_PILOT_MIGRATION_0025_SHA256
\getenv migration_0026_hash RAHGARD_PILOT_MIGRATION_0026_SHA256
\getenv migration_hash RAHGARD_PILOT_MIGRATION_0027_SHA256

-- Server-side AI provider registry. Reuses identity.platform_admin_mfa from
-- 0026; this migration deliberately does not create a parallel MFA store.
BEGIN;
SELECT 1 / CASE WHEN current_database()='rahgard_pilot_vps_staging'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND COALESCE(inet_server_port(),0) <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker)=1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker)=:'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_0024_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_0025_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_0026_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND EXISTS(SELECT 1 FROM system.schema_migrations WHERE migration_id='0024_partner_review_audit_actions' AND sha256=:'migration_0024_hash')
    AND EXISTS(SELECT 1 FROM system.schema_migrations WHERE migration_id='0025_owner_control_center' AND sha256=:'migration_0025_hash')
    AND EXISTS(SELECT 1 FROM system.schema_migrations WHERE migration_id='0026_platform_reviewer_mfa' AND sha256=:'migration_0026_hash')
    AND (SELECT count(*) FROM system.schema_migrations) IN (25,27)
    AND (SELECT max(migration_id) FROM system.schema_migrations)='0026_platform_reviewer_mfa'
    AND NOT EXISTS(SELECT 1 FROM system.schema_migrations WHERE migration_id='0027_server_ai_provider_admin')
    AND NOT EXISTS(SELECT 1 FROM system.schema_migrations WHERE migration_id NOT IN (
      '0000_legacy_tourism_points_baseline','0001_core_schema','0002_synthetic_knowledge_seed',
      '0003_synthetic_e2e_seed','0004_app_role_grants','0005_verified_unesco_destination_seed',
      '0006_verified_unesco_destination_seed_batch2','0007_shiraz_dalahoo_wikipedia_dataset_v1',
      '0008_authentication_foundation','0009_traveler_core','0010_task31_content_privacy_full_itinerary',
      '0011_internal_chat_turns','0012_task5_published_claim_evidence','0013_private_pilot_geo_audit',
      '0014_local_owner_login','0015_ai_provider_admin','0016_staging_invitation_auth',
      '0017_provisional_itineraries','0018_national_catalogue_ingestion','0019_partner_workspace',
      '0020_archive_candidate_publication','0021_postgis_security_definer_publication',
      '0022_traveler_company_requests','0023_partner_trip_responses','0024_partner_review_audit_actions',
      '0025_owner_control_center','0026_platform_reviewer_mfa'))
    AND ((SELECT count(*) FROM system.schema_migrations)=25
         OR (EXISTS(SELECT 1 FROM system.schema_migrations WHERE migration_id='0014_local_owner_login')
             AND EXISTS(SELECT 1 FROM system.schema_migrations WHERE migration_id='0015_ai_provider_admin')))
    AND to_regnamespace('ai_provider') IS NULL
    AND to_regclass('identity.platform_admin_mfa') IS NOT NULL
    AND NOT EXISTS(SELECT 1 FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
                    AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls))
    THEN 1 ELSE 0 END;

CREATE SCHEMA ai_provider;
REVOKE ALL ON SCHEMA ai_provider FROM PUBLIC;

CREATE TABLE ai_provider.profiles (
    profile_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE CHECK(length(btrim(name)) BETWEEN 1 AND 100),
    provider_kind TEXT NOT NULL CHECK(provider_kind IN ('lm_studio','openai_compatible')),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    archived_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1 CHECK(version>0),
    created_by UUID NOT NULL REFERENCES identity.users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK(archived_at IS NULL OR enabled=FALSE)
);
CREATE TABLE ai_provider.revisions (
    revision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID NOT NULL REFERENCES ai_provider.profiles(profile_id),
    revision_no INTEGER NOT NULL CHECK(revision_no>0),
    config JSONB NOT NULL CHECK(jsonb_typeof(config)='object'),
    secret_ref TEXT CHECK(secret_ref IS NULL OR length(secret_ref) BETWEEN 8 AND 512),
    created_by UUID NOT NULL REFERENCES identity.users(user_id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(profile_id,revision_no)
);
CREATE INDEX ix_ai_provider_revisions_profile ON ai_provider.revisions(profile_id,revision_no DESC);
CREATE TABLE ai_provider.revision_validations (
    validation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    revision_id UUID NOT NULL REFERENCES ai_provider.revisions(revision_id),
    outcome TEXT NOT NULL CHECK(outcome IN ('valid','invalid','unavailable')),
    details JSONB NOT NULL DEFAULT '{}'::jsonb CHECK(jsonb_typeof(details)='object'),
    validated_by UUID REFERENCES identity.users(user_id),
    validated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_ai_provider_validations_latest ON ai_provider.revision_validations(revision_id,validated_at DESC);
CREATE TABLE ai_provider.active_routes (
    capability TEXT PRIMARY KEY CHECK(capability IN ('chat','vision','embedding','reranking')),
    revision_id UUID REFERENCES ai_provider.revisions(revision_id),
    generation BIGINT NOT NULL DEFAULT 0 CHECK(generation>=0),
    updated_by UUID REFERENCES identity.users(user_id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO ai_provider.active_routes(capability) VALUES('chat'),('vision'),('embedding'),('reranking');
CREATE TABLE ai_provider.fallback_policy (
    capability TEXT PRIMARY KEY REFERENCES ai_provider.active_routes(capability),
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ordered_revision_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    updated_by UUID REFERENCES identity.users(user_id),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK(enabled OR cardinality(ordered_revision_ids)=0)
);
INSERT INTO ai_provider.fallback_policy(capability) VALUES('chat'),('vision'),('embedding'),('reranking');
CREATE TABLE ai_provider.audit_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id UUID REFERENCES identity.users(user_id),
    action TEXT NOT NULL CHECK(length(action) BETWEEN 1 AND 80),
    target_type TEXT NOT NULL CHECK(length(target_type) BETWEEN 1 AND 40),
    target_id TEXT,
    outcome TEXT NOT NULL CHECK(outcome IN ('success','denied','failure')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb CHECK(jsonb_typeof(metadata)='object'),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_ai_provider_audit_recent ON ai_provider.audit_events(occurred_at DESC);
CREATE TABLE ai_provider.usage_events (
    usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capability TEXT NOT NULL CHECK(capability IN ('chat','vision','embedding','reranking')),
    revision_id UUID REFERENCES ai_provider.revisions(revision_id),
    outcome TEXT NOT NULL CHECK(outcome IN ('success','unavailable','rejected')),
    latency_ms INTEGER CHECK(latency_ms IS NULL OR latency_ms>=0),
    input_units INTEGER CHECK(input_units IS NULL OR input_units>=0),
    output_units INTEGER CHECK(output_units IS NULL OR output_units>=0),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_ai_provider_usage_recent ON ai_provider.usage_events(occurred_at DESC);

CREATE TABLE identity.ai_provider_admin_grants (
    user_id UUID PRIMARY KEY REFERENCES identity.users(user_id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    granted_by UUID REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    grant_reason TEXT NOT NULL CHECK(length(btrim(grant_reason)) BETWEEN 10 AND 1000),
    revoked_at TIMESTAMPTZ,
    revoked_by UUID REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    revoke_reason TEXT,
    CHECK(revoked_at IS NULL OR revoked_at>=granted_at),
    CHECK((revoked_at IS NULL)=(revoke_reason IS NULL)),
    CHECK(revoked_at IS NULL OR length(btrim(revoke_reason)) BETWEEN 10 AND 1000)
);
CREATE TABLE identity.ai_provider_admin_grant_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    target_user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    action TEXT NOT NULL CHECK(action IN ('granted','revoked')),
    reason TEXT NOT NULL CHECK(length(btrim(reason)) BETWEEN 10 AND 1000),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK(actor_user_id<>target_user_id)
);
CREATE INDEX ix_provider_admin_grant_events_target ON identity.ai_provider_admin_grant_events(target_user_id,occurred_at DESC);
ALTER TABLE identity.ai_provider_admin_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity.ai_provider_admin_grant_events ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON identity.ai_provider_admin_grants,identity.ai_provider_admin_grant_events FROM PUBLIC,ai_tourism_app;

CREATE FUNCTION identity.has_ai_provider_admin_capability(p_user_id UUID)
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER
SET search_path=pg_catalog,identity,partner SET row_security=off
AS $$
  SELECT p_user_id=partner.current_actor_id()
    AND identity.has_platform_admin_capability(p_user_id)
    AND EXISTS(
    SELECT 1 FROM identity.ai_provider_admin_grants g
    WHERE g.user_id=p_user_id AND g.revoked_at IS NULL)
$$;
REVOKE ALL ON FUNCTION identity.has_ai_provider_admin_capability(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION identity.has_ai_provider_admin_capability(UUID) TO ai_tourism_app;

CREATE FUNCTION identity.has_privileged_admin_step_up()
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER
SET search_path=pg_catalog,identity,partner
AS $$
  SELECT (
      identity.has_platform_admin_capability(partner.current_actor_id())
      OR identity.has_ai_provider_admin_capability(partner.current_actor_id()))
    AND EXISTS (
      SELECT 1 FROM identity.platform_admin_mfa m
      JOIN identity.platform_admin_step_up s USING(user_id)
      WHERE m.user_id=partner.current_actor_id() AND m.enabled_at IS NOT NULL
        AND s.session_id::text=NULLIF(current_setting('app.session_id',true),'')
        AND s.revoked_at IS NULL AND s.expires_at>pg_catalog.now())
$$;
REVOKE ALL ON FUNCTION identity.has_privileged_admin_step_up() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION identity.has_privileged_admin_step_up() TO ai_tourism_app;

-- Provider administration is an additional scoped grant for an existing
-- platform administrator. It reuses the existing MFA RLS policies and audit
-- function rather than weakening or changing those identity-table policies.
-- The trusted
-- assistant runtime gets read-only route access plus usage inserts through a
-- transaction-local marker set only by the backend adapter.
CREATE FUNCTION identity.has_ai_provider_admin_step_up()
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER
SET search_path=pg_catalog,identity,partner
AS $$
  SELECT identity.has_ai_provider_admin_capability(partner.current_actor_id())
    AND identity.has_platform_admin_capability(partner.current_actor_id())
    AND identity.has_privileged_admin_step_up()
$$;
REVOKE ALL ON FUNCTION identity.has_ai_provider_admin_step_up() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION identity.has_ai_provider_admin_step_up() TO ai_tourism_app;

ALTER TABLE ai_provider.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_provider.revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_provider.revision_validations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_provider.active_routes ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_provider.fallback_policy ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_provider.audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_provider.usage_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY profiles_read ON ai_provider.profiles FOR SELECT
  USING (identity.has_ai_provider_admin_capability(partner.current_actor_id())
    OR current_setting('app.provider_runtime',true)='true');
CREATE POLICY profiles_insert ON ai_provider.profiles FOR INSERT
  WITH CHECK (created_by=partner.current_actor_id() AND identity.has_ai_provider_admin_step_up());
CREATE POLICY profiles_update ON ai_provider.profiles FOR UPDATE
  USING (identity.has_ai_provider_admin_capability(partner.current_actor_id()))
  WITH CHECK (identity.has_ai_provider_admin_step_up());

CREATE POLICY revisions_read ON ai_provider.revisions FOR SELECT
  USING (identity.has_ai_provider_admin_capability(partner.current_actor_id())
    OR current_setting('app.provider_runtime',true)='true');
CREATE POLICY revisions_insert ON ai_provider.revisions FOR INSERT
  WITH CHECK (created_by=partner.current_actor_id() AND identity.has_ai_provider_admin_step_up());

CREATE POLICY validations_read ON ai_provider.revision_validations FOR SELECT
  USING (identity.has_ai_provider_admin_capability(partner.current_actor_id())
    OR current_setting('app.provider_runtime',true)='true');
CREATE POLICY validations_insert ON ai_provider.revision_validations FOR INSERT
  WITH CHECK (identity.has_ai_provider_admin_step_up()
    AND (validated_by IS NULL OR validated_by=partner.current_actor_id()));

CREATE POLICY routes_read ON ai_provider.active_routes FOR SELECT
  USING (identity.has_ai_provider_admin_capability(partner.current_actor_id())
    OR current_setting('app.provider_runtime',true)='true');
CREATE POLICY routes_update ON ai_provider.active_routes FOR UPDATE
  USING (identity.has_ai_provider_admin_capability(partner.current_actor_id()))
  WITH CHECK (identity.has_ai_provider_admin_step_up()
    AND (updated_by IS NULL OR updated_by=partner.current_actor_id()));

CREATE POLICY fallback_read ON ai_provider.fallback_policy FOR SELECT
  USING (identity.has_ai_provider_admin_capability(partner.current_actor_id())
    OR current_setting('app.provider_runtime',true)='true');
CREATE POLICY fallback_update ON ai_provider.fallback_policy FOR UPDATE
  USING (identity.has_ai_provider_admin_capability(partner.current_actor_id()))
  WITH CHECK (identity.has_ai_provider_admin_step_up()
    AND (updated_by IS NULL OR updated_by=partner.current_actor_id()));

CREATE POLICY audit_read ON ai_provider.audit_events FOR SELECT
  USING (identity.has_ai_provider_admin_capability(partner.current_actor_id()));
CREATE POLICY audit_insert ON ai_provider.audit_events FOR INSERT
  WITH CHECK (identity.has_ai_provider_admin_step_up() AND actor_id=partner.current_actor_id());

CREATE POLICY usage_read ON ai_provider.usage_events FOR SELECT
  USING (identity.has_ai_provider_admin_capability(partner.current_actor_id()));
CREATE POLICY usage_runtime_insert ON ai_provider.usage_events FOR INSERT
  WITH CHECK (current_setting('app.provider_runtime',true)='true');

GRANT USAGE ON SCHEMA ai_provider TO ai_tourism_app;
GRANT SELECT,INSERT,UPDATE ON ai_provider.profiles,ai_provider.revisions,ai_provider.active_routes,ai_provider.fallback_policy TO ai_tourism_app;
GRANT SELECT,INSERT ON ai_provider.revision_validations,ai_provider.audit_events,ai_provider.usage_events TO ai_tourism_app;
REVOKE UPDATE,DELETE ON ai_provider.revisions,ai_provider.revision_validations,ai_provider.audit_events,ai_provider.usage_events FROM ai_tourism_app;
REVOKE ALL ON ALL TABLES IN SCHEMA ai_provider FROM PUBLIC;
INSERT INTO system.schema_migrations(migration_id,sha256)
VALUES('0027_server_ai_provider_admin',:'migration_hash');
COMMIT;
