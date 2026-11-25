\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0024_hash RAHGARD_PILOT_MIGRATION_0024_SHA256
\getenv migration_0025_hash RAHGARD_PILOT_MIGRATION_0025_SHA256
\getenv migration_hash RAHGARD_PILOT_MIGRATION_0026_SHA256

-- Adds general platform-reviewer MFA without granting AI-provider authority.
-- TOTP secrets are ciphertext produced by the application using a separately
-- provisioned AES-256-GCM key. Owner/reviewer access is still capability gated.
BEGIN;
SELECT 1 / CASE WHEN current_database() = 'rahgard_pilot_vps_staging'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND COALESCE(inet_server_port(), 0) <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker) = 1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) = :'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_0024_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_0025_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0024_partner_review_audit_actions' AND sha256=:'migration_0024_hash')
    AND EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0025_owner_control_center' AND sha256=:'migration_0025_hash')
    AND (SELECT count(*) FROM system.schema_migrations) IN (24,26)
    AND (SELECT max(migration_id) FROM system.schema_migrations)='0025_owner_control_center'
    AND NOT EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id NOT IN (
      '0000_legacy_tourism_points_baseline','0001_core_schema','0002_synthetic_knowledge_seed',
      '0003_synthetic_e2e_seed','0004_app_role_grants','0005_verified_unesco_destination_seed',
      '0006_verified_unesco_destination_seed_batch2','0007_shiraz_dalahoo_wikipedia_dataset_v1',
      '0008_authentication_foundation','0009_traveler_core','0010_task31_content_privacy_full_itinerary',
      '0011_internal_chat_turns','0012_task5_published_claim_evidence','0013_private_pilot_geo_audit',
      '0014_local_owner_login','0015_ai_provider_admin','0016_staging_invitation_auth',
      '0017_provisional_itineraries','0018_national_catalogue_ingestion','0019_partner_workspace',
      '0020_archive_candidate_publication','0021_postgis_security_definer_publication',
      '0022_traveler_company_requests','0023_partner_trip_responses',
      '0024_partner_review_audit_actions','0025_owner_control_center'))
    AND NOT EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0026_platform_reviewer_mfa')
    AND EXISTS (SELECT 1 FROM pg_catalog.pg_class WHERE oid='identity.web_sessions'::regclass AND relkind='r')
    THEN 1 ELSE 0 END;

CREATE FUNCTION identity.has_platform_admin_capability(p_actor_id UUID)
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER
SET search_path = pg_catalog, partner, identity
SET row_security = off
AS $$
  SELECT COALESCE(
    partner.has_platform_capability(p_actor_id,'organization_review') OR
    partner.has_platform_capability(p_actor_id,'service_review') OR
    partner.has_platform_capability(p_actor_id,'offer_review') OR
    partner.has_platform_capability(p_actor_id,'admin_overview_read') OR
    identity.has_catalogue_review_capability(p_actor_id,'candidate_review') OR
    identity.has_catalogue_review_capability(p_actor_id,'source_review') OR
    identity.has_catalogue_review_capability(p_actor_id,'catalogue_publish'), FALSE)
$$;
REVOKE ALL ON FUNCTION identity.has_platform_admin_capability(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION identity.has_platform_admin_capability(UUID) TO ai_tourism_app;

CREATE TABLE identity.platform_admin_mfa (
    user_id UUID PRIMARY KEY REFERENCES identity.users(user_id) ON DELETE CASCADE,
    secret_ciphertext BYTEA,
    pending_secret_ciphertext BYTEA,
    enabled_at TIMESTAMPTZ,
    last_totp_counter BIGINT NOT NULL DEFAULT -1 CHECK (last_totp_counter >= -1),
    recovery_hashes BYTEA[] NOT NULL DEFAULT ARRAY[]::BYTEA[],
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((enabled_at IS NULL) = (secret_ciphertext IS NULL)),
    CHECK (cardinality(recovery_hashes) <= 20),
    CHECK (secret_ciphertext IS NULL OR octet_length(secret_ciphertext)=49),
    CHECK (pending_secret_ciphertext IS NULL OR octet_length(pending_secret_ciphertext)=49)
);

CREATE TABLE identity.platform_admin_step_up (
    user_id UUID NOT NULL REFERENCES identity.platform_admin_mfa(user_id) ON DELETE CASCADE,
    session_id UUID NOT NULL REFERENCES identity.web_sessions(session_id) ON DELETE CASCADE,
    verified_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    PRIMARY KEY (user_id,session_id),
    CHECK (expires_at > verified_at AND expires_at <= verified_at + INTERVAL '5 minutes'),
    CHECK (revoked_at IS NULL OR revoked_at >= verified_at)
);
CREATE INDEX ix_platform_admin_step_up_expiry ON identity.platform_admin_step_up(expires_at)
  WHERE revoked_at IS NULL;

CREATE TABLE identity.platform_admin_mfa_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    -- Retain audit history after the authenticated session is revoked/deleted.
    session_id UUID NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('enrollment_started','mfa_enrolled','totp_step_up','recovery_step_up','recovery_reset')),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_platform_admin_mfa_events_actor_time
  ON identity.platform_admin_mfa_events(actor_user_id,occurred_at DESC);

ALTER TABLE identity.platform_admin_mfa ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity.platform_admin_step_up ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity.platform_admin_mfa_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY platform_admin_mfa_self ON identity.platform_admin_mfa
  USING (user_id=partner.current_actor_id() AND identity.has_platform_admin_capability(user_id))
  WITH CHECK (user_id=partner.current_actor_id() AND identity.has_platform_admin_capability(user_id));
CREATE POLICY platform_admin_step_up_self ON identity.platform_admin_step_up
  USING (user_id=partner.current_actor_id() AND identity.has_platform_admin_capability(user_id))
  WITH CHECK (user_id=partner.current_actor_id() AND identity.has_platform_admin_capability(user_id));
CREATE POLICY platform_admin_mfa_events_self ON identity.platform_admin_mfa_events
  FOR SELECT USING (actor_user_id=partner.current_actor_id()
    AND identity.has_platform_admin_capability(actor_user_id));

CREATE FUNCTION identity.record_platform_admin_mfa_event(p_action TEXT,p_session_id UUID)
RETURNS VOID LANGUAGE plpgsql SECURITY DEFINER
SET search_path = pg_catalog, identity, partner
SET row_security = off
AS $$
DECLARE actor UUID := partner.current_actor_id();
BEGIN
  IF actor IS NULL OR NOT identity.has_platform_admin_capability(actor)
     OR p_action NOT IN ('enrollment_started','mfa_enrolled','totp_step_up','recovery_step_up','recovery_reset')
     OR NOT EXISTS (SELECT 1 FROM identity.web_sessions s
                    WHERE s.session_id=p_session_id AND s.user_id=actor) THEN
    RAISE EXCEPTION 'platform MFA audit event rejected' USING ERRCODE='42501';
  END IF;
  INSERT INTO identity.platform_admin_mfa_events(actor_user_id,session_id,action)
  VALUES (actor,p_session_id,p_action);
END
$$;
REVOKE ALL ON FUNCTION identity.record_platform_admin_mfa_event(TEXT,UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION identity.record_platform_admin_mfa_event(TEXT,UUID) TO ai_tourism_app;
GRANT SELECT,INSERT,UPDATE ON identity.platform_admin_mfa,identity.platform_admin_step_up TO ai_tourism_app;
REVOKE ALL ON identity.platform_admin_mfa_events FROM PUBLIC,ai_tourism_app;

INSERT INTO system.schema_migrations(migration_id,sha256)
VALUES ('0026_platform_reviewer_mfa',:'migration_hash');
COMMIT;
