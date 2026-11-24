\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0023_hash RAHGARD_PILOT_MIGRATION_0023_SHA256
\getenv migration_hash RAHGARD_PILOT_MIGRATION_0024_SHA256

-- Additive partner review audit vocabulary and least-privilege guard.
-- This migration does not grant reviewer capabilities or alter existing rows.
BEGIN;
SELECT 1 / CASE WHEN current_database() = 'rahgard_pilot_vps_staging'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    -- Unix-socket connections report NULL. Treat that as a non-shared port;
    -- the guarded container rehearsal uses a socket and has no host port map.
    AND COALESCE(inet_server_port(), 0) <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker) = 1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) = :'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_0023_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND EXISTS (SELECT 1 FROM system.schema_migrations
        WHERE migration_id='0023_partner_trip_responses'
                  AND sha256=:'migration_0023_hash')
    -- The production ledger has 22 rows because local-owner/provider-admin
    -- migrations 0014/0015 are not part of that runtime. The isolated full-app
    -- E2E schema may contain those two additional, exact migration rows.
    AND (SELECT count(*) FROM system.schema_migrations) IN (22,24)
    AND NOT EXISTS (
        SELECT 1 FROM system.schema_migrations
        WHERE migration_id NOT IN (
          '0000_legacy_tourism_points_baseline','0001_core_schema',
          '0002_synthetic_knowledge_seed','0003_synthetic_e2e_seed',
          '0004_app_role_grants','0005_verified_unesco_destination_seed',
          '0006_verified_unesco_destination_seed_batch2','0007_shiraz_dalahoo_wikipedia_dataset_v1',
          '0008_authentication_foundation','0009_traveler_core',
          '0010_task31_content_privacy_full_itinerary','0011_internal_chat_turns',
          '0012_task5_published_claim_evidence','0013_private_pilot_geo_audit',
          '0014_local_owner_login','0015_ai_provider_admin',
          '0016_staging_invitation_auth','0017_provisional_itineraries',
          '0018_national_catalogue_ingestion','0019_partner_workspace',
          '0020_archive_candidate_publication','0021_postgis_security_definer_publication',
          '0022_traveler_company_requests','0023_partner_trip_responses'
        )
    )
    AND ((SELECT count(*) FROM system.schema_migrations)=22 OR (
         EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0014_local_owner_login')
         AND EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0015_ai_provider_admin')
    ))
    AND (SELECT max(migration_id) FROM system.schema_migrations)='0023_partner_trip_responses'
    AND NOT EXISTS (SELECT 1 FROM system.schema_migrations
        WHERE migration_id='0024_partner_review_audit_actions')
    AND (SELECT count(*) FROM pg_catalog.pg_constraint
         WHERE conrelid='partner.review_events'::regclass
           AND contype='c' AND pg_catalog.pg_get_constraintdef(oid) ILIKE '%decision%')=1
    AND EXISTS (SELECT 1 FROM pg_catalog.pg_constraint
                WHERE conrelid='partner.review_events'::regclass
                  AND conname='review_events_decision_check'
                  AND contype='c'
                  AND pg_catalog.pg_get_constraintdef(oid) ILIKE '%approve%reject%request_changes%suspend%reinstate%')
    THEN 1 ELSE 0 END;

-- Platform grants are provisioned by an operator. The application role must
-- use the SECURITY DEFINER capability check, never mutate the grant ledger.
REVOKE ALL ON partner.platform_grants FROM ai_tourism_app;

ALTER TABLE partner.review_events DROP CONSTRAINT review_events_decision_check;

ALTER TABLE partner.review_events
  ADD CONSTRAINT review_events_decision_check
  CHECK (decision IN ('approve','reject','request_changes','suspend','reinstate','activate','deactivate'));

-- Verification decisions are represented as verification_case audit events.
-- The original INSERT policy allowed organization/service/offer events but
-- omitted this entity type, causing the authorized reviewer transition to
-- fail and roll back under RLS. Keep the capability check and actor binding.
DROP POLICY review_events_platform_insert ON partner.review_events;
CREATE POLICY review_events_platform_insert ON partner.review_events FOR INSERT
WITH CHECK (reviewer_user_id=partner.current_actor_id()
    AND ((entity_type IN ('organization','verification_case')
          AND partner.has_platform_capability(partner.current_actor_id(),'organization_review'))
      OR (entity_type IN ('service','branch') AND partner.has_platform_capability(partner.current_actor_id(),'service_review'))
      OR (entity_type IN ('offer','price','schedule','availability') AND partner.has_platform_capability(partner.current_actor_id(),'offer_review'))));

INSERT INTO system.schema_migrations(migration_id, sha256)
VALUES ('0024_partner_review_audit_actions', :'migration_hash');
COMMIT;
