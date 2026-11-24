\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0024_hash RAHGARD_PILOT_MIGRATION_0024_SHA256
\getenv migration_hash RAHGARD_PILOT_MIGRATION_0025_SHA256

-- Additive owner overview capability and operator-grant audit. No grants are
-- created here, and no application role receives direct access to grant data.
BEGIN;
SELECT 1 / CASE WHEN current_database() = 'rahgard_pilot_vps_staging'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND COALESCE(inet_server_port(), 0) <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker) = 1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) = :'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_0024_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND EXISTS (SELECT 1 FROM system.schema_migrations
        WHERE migration_id='0024_partner_review_audit_actions'
          AND sha256=:'migration_0024_hash')
    AND (SELECT count(*) FROM system.schema_migrations) IN (23,25)
    AND (SELECT max(migration_id) FROM system.schema_migrations)='0024_partner_review_audit_actions'
    AND NOT EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id NOT IN (
      '0000_legacy_tourism_points_baseline','0001_core_schema','0002_synthetic_knowledge_seed',
      '0003_synthetic_e2e_seed','0004_app_role_grants','0005_verified_unesco_destination_seed',
      '0006_verified_unesco_destination_seed_batch2','0007_shiraz_dalahoo_wikipedia_dataset_v1',
      '0008_authentication_foundation','0009_traveler_core','0010_task31_content_privacy_full_itinerary',
      '0011_internal_chat_turns','0012_task5_published_claim_evidence','0013_private_pilot_geo_audit',
      '0014_local_owner_login','0015_ai_provider_admin','0016_staging_invitation_auth',
      '0017_provisional_itineraries','0018_national_catalogue_ingestion','0019_partner_workspace',
      '0020_archive_candidate_publication','0021_postgis_security_definer_publication',
      '0022_traveler_company_requests','0023_partner_trip_responses','0024_partner_review_audit_actions'))
    AND ((SELECT count(*) FROM system.schema_migrations)=23
         OR (EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0014_local_owner_login')
             AND EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0015_ai_provider_admin')))
    AND NOT EXISTS (SELECT 1 FROM system.schema_migrations
        WHERE migration_id='0025_owner_control_center')
    AND EXISTS (SELECT 1 FROM pg_catalog.pg_constraint
        WHERE conrelid='partner.platform_grants'::regclass
          AND conname='platform_grants_capability_check' AND contype='c')
    THEN 1 ELSE 0 END;

ALTER TABLE partner.platform_grants DROP CONSTRAINT platform_grants_capability_check;
ALTER TABLE partner.platform_grants ADD CONSTRAINT platform_grants_capability_check
  CHECK (capability IN ('organization_review','service_review','offer_review','admin_overview_read'));

CREATE TABLE partner.platform_grant_events (
    event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    grant_domain TEXT NOT NULL CHECK (grant_domain IN ('partner','catalogue')),
    target_user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    capability TEXT NOT NULL CHECK (capability IN (
      'organization_review','service_review','offer_review','admin_overview_read',
      'candidate_review','source_review','catalogue_publish')),
    action TEXT NOT NULL CHECK (action IN ('granted','revoked')),
    actor_user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    reason TEXT NOT NULL CHECK (length(btrim(reason)) BETWEEN 10 AND 1000),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (target_user_id <> actor_user_id),
    CHECK ((grant_domain='partner' AND capability IN (
      'organization_review','service_review','offer_review','admin_overview_read'))
      OR (grant_domain='catalogue' AND capability IN (
      'candidate_review','source_review','catalogue_publish')))
);
CREATE INDEX ix_platform_grant_events_target ON partner.platform_grant_events
  (target_user_id, occurred_at DESC);
REVOKE ALL ON partner.platform_grant_events FROM PUBLIC, ai_tourism_app;

CREATE FUNCTION partner.admin_grant_counts()
RETURNS TABLE(grant_domain TEXT, capability TEXT, active_grant_count BIGINT)
LANGUAGE SQL STABLE SECURITY DEFINER
SET search_path = pg_catalog, partner, identity
SET row_security = off
AS $$
  WITH allowed AS (
    SELECT partner.has_platform_capability(partner.current_actor_id(),'admin_overview_read') AS ok
  ), cap_list(grant_domain, capability) AS (VALUES
    ('partner','organization_review'),('partner','service_review'),
    ('partner','offer_review'),('partner','admin_overview_read'),
    ('catalogue','candidate_review'),('catalogue','source_review'),
    ('catalogue','catalogue_publish')
  ), counts AS (
    SELECT 'partner'::TEXT AS grant_domain, g.capability, count(*)::BIGINT AS n
      FROM partner.platform_grants g WHERE g.revoked_at IS NULL GROUP BY g.capability
    UNION ALL
    SELECT 'catalogue'::TEXT, g.capability, count(*)::BIGINT
      FROM identity.catalogue_review_grants g WHERE g.revoked_at IS NULL GROUP BY g.capability
  )
  SELECT c.grant_domain, c.capability, COALESCE(n.n,0)
    FROM cap_list c CROSS JOIN allowed a
    LEFT JOIN counts n USING (grant_domain,capability)
   WHERE a.ok
   ORDER BY c.grant_domain,c.capability
$$;
REVOKE ALL ON FUNCTION partner.admin_grant_counts() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION partner.admin_grant_counts() TO ai_tourism_app;

INSERT INTO system.schema_migrations(migration_id, sha256)
VALUES ('0025_owner_control_center', :'migration_hash');
COMMIT;
