\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0022_hash RAHGARD_PILOT_MIGRATION_0022_SHA256
\getenv migration_hash RAHGARD_PILOT_MIGRATION_0023_SHA256

-- Additive private company replies to an explicitly consented share/revision.
-- Only isolated acceptance is authorized. Does not publish or message anyone.
BEGIN;
SELECT 1 / CASE WHEN current_database() = 'rahgard_pilot_vps_staging'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND inet_server_port() <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker) = 1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) = :'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_0022_hash' ~ '^[a-f0-9]{64}$'
    AND EXISTS (SELECT 1 FROM system.schema_migrations
        WHERE migration_id='0022_traveler_company_requests'
          AND sha256=:'migration_0022_hash')
    AND NOT EXISTS (SELECT 1 FROM system.schema_migrations
        WHERE migration_id='0023_partner_trip_responses')
    THEN 1 ELSE 0 END;

-- Test-only partners must never enter automatic distribution. No partner
-- self-service API may change this operator-governed flag.
ALTER TABLE partner.organizations
  ADD COLUMN is_test BOOLEAN NOT NULL DEFAULT FALSE;

CREATE OR REPLACE VIEW partner.share_eligible_organizations
WITH (security_barrier=true) AS
SELECT organization_id,display_name,organization_type
FROM partner.organizations
WHERE verification_status='verified' AND participation_status='active'
  AND application_status='approved' AND closed_at IS NULL AND NOT is_test;

CREATE TABLE partner.trip_company_responses (
    response_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_request_id UUID NOT NULL,
    share_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    revision_id UUID NOT NULL,
    trip_id UUID NOT NULL REFERENCES travel.trips(trip_id) ON DELETE CASCADE,
    traveler_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE CASCADE,
    submitted_by UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    response_kind TEXT NOT NULL CHECK (response_kind IN ('accepted_as_requested','counter_offer')),
    message TEXT NOT NULL DEFAULT '' CHECK (length(message) <= 2000),
    proposed_price_toman NUMERIC(14,2) CHECK (proposed_price_toman >= 0),
    proposed_start_date DATE,
    proposed_end_date DATE,
    proposed_schedule_notes TEXT NOT NULL DEFAULT '' CHECK (length(proposed_schedule_notes) <= 1500),
    traveler_decision TEXT NOT NULL DEFAULT 'pending' CHECK (traveler_decision IN ('pending','accepted','declined')),
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (share_id, organization_id)
      REFERENCES partner.traveler_request_shares(share_id,organization_id) ON DELETE CASCADE,
    FOREIGN KEY (revision_id, organization_id)
      REFERENCES partner.traveler_request_revisions(revision_id,organization_id) ON DELETE CASCADE,
    UNIQUE (share_id,client_request_id),
    CHECK ((proposed_start_date IS NULL) = (proposed_end_date IS NULL)),
    CHECK (proposed_end_date IS NULL OR proposed_end_date >= proposed_start_date),
    CHECK (response_kind <> 'accepted_as_requested' OR
      (proposed_price_toman IS NULL AND proposed_start_date IS NULL
       AND proposed_schedule_notes='')),
    CHECK (response_kind <> 'counter_offer' OR
      (proposed_price_toman IS NOT NULL OR proposed_start_date IS NOT NULL
       OR length(btrim(proposed_schedule_notes)) > 0)),
    CHECK ((traveler_decision='pending') = (decided_at IS NULL)),
    CHECK (is_synthetic=FALSE)
);
CREATE INDEX ix_trip_company_responses_traveler
  ON partner.trip_company_responses(traveler_id,trip_id,created_at DESC);
CREATE INDEX ix_trip_company_responses_company
  ON partner.trip_company_responses(organization_id,share_id,created_at DESC);

ALTER TABLE partner.trip_company_responses ENABLE ROW LEVEL SECURITY;
CREATE POLICY trip_company_responses_read ON partner.trip_company_responses FOR SELECT
USING (
  traveler_id=partner.current_actor_id()
  OR EXISTS (SELECT 1 FROM partner.traveler_request_shares s
    WHERE s.share_id=trip_company_responses.share_id
      AND s.organization_id=trip_company_responses.organization_id
      AND s.revoked_at IS NULL
      AND partner.has_active_membership(s.organization_id,partner.current_actor_id()))
);
CREATE POLICY trip_company_responses_insert ON partner.trip_company_responses FOR INSERT
WITH CHECK (
  submitted_by=partner.current_actor_id() AND NOT is_synthetic
  AND EXISTS (SELECT 1 FROM partner.traveler_request_shares s
    WHERE s.share_id=trip_company_responses.share_id
      AND s.trip_id=trip_company_responses.trip_id
      AND s.traveler_id=trip_company_responses.traveler_id
      AND s.organization_id=trip_company_responses.organization_id
      AND s.revoked_at IS NULL
      AND partner.has_active_membership(s.organization_id,partner.current_actor_id()))
);
CREATE POLICY trip_company_responses_decide ON partner.trip_company_responses FOR UPDATE
USING (traveler_id=partner.current_actor_id())
WITH CHECK (traveler_id=partner.current_actor_id());

REVOKE ALL ON partner.trip_company_responses FROM PUBLIC;
GRANT SELECT, INSERT ON partner.trip_company_responses TO ai_tourism_app;
GRANT UPDATE (traveler_decision,decided_at) ON partner.trip_company_responses TO ai_tourism_app;

INSERT INTO system.schema_migrations(migration_id,sha256)
VALUES ('0023_partner_trip_responses',:'migration_hash');
COMMIT;
