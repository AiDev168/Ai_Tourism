\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0018_hash RAHGARD_PILOT_MIGRATION_0018_SHA256
\getenv migration_hash RAHGARD_PILOT_MIGRATION_0019_SHA256

-- Isolated-private partner data-entry schema. No partner accounts/data are seeded.
-- Feature/API activation remains controlled by PARTNER_WORKSPACE_ENABLED and
-- governance approvals; this migration does not grant reviewer capability.
BEGIN;
SELECT 1 / CASE WHEN current_database() = 'rahgard_pilot_vps_staging'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND inet_server_port() <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker) = 1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) = :'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_0018_hash' ~ '^[a-f0-9]{64}$'
    AND EXISTS (SELECT 1 FROM system.schema_migrations
                WHERE migration_id='0018_national_catalogue_ingestion'
                  AND sha256=:'migration_0018_hash')
    AND NOT EXISTS (SELECT 1 FROM system.schema_migrations
                    WHERE migration_id='0019_partner_workspace')
    THEN 1 ELSE 0 END;

CREATE SCHEMA partner;
REVOKE ALL ON SCHEMA partner FROM PUBLIC;

CREATE TABLE partner.organizations (
    organization_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    legal_name TEXT NOT NULL CHECK (length(btrim(legal_name)) BETWEEN 1 AND 240),
    display_name TEXT NOT NULL CHECK (length(btrim(display_name)) BETWEEN 1 AND 240),
    organization_type TEXT NOT NULL CHECK (organization_type IN ('company','individual_business','nonprofit','public_body','other')),
    registration_country CHAR(2) NOT NULL CHECK (registration_country ~ '^[A-Z]{2}$'),
    registration_number TEXT,
    primary_admin_area_id BIGINT REFERENCES geo.admin_areas(admin_area_id) ON DELETE RESTRICT,
    verification_status TEXT NOT NULL DEFAULT 'pending' CHECK (verification_status IN ('pending','verified','rejected','suspended')),
    participation_status TEXT NOT NULL DEFAULT 'inactive' CHECK (participation_status IN ('inactive','active','suspended','closed')),
    application_status TEXT NOT NULL DEFAULT 'draft' CHECK (application_status IN ('draft','submitted','needs_information','approved','rejected','withdrawn')),
    created_by UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at TIMESTAMPTZ
);
CREATE INDEX ix_partner_org_creator ON partner.organizations(created_by, created_at DESC);
CREATE INDEX ix_partner_org_lifecycle ON partner.organizations(verification_status, participation_status, application_status);

CREATE TABLE partner.memberships (
    membership_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT,
    user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    role TEXT NOT NULL CHECK (role IN ('owner','manager','editor','availability_operator','viewer')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('invited','active','revoked','suspended')),
    invited_by UUID REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    accepted_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, user_id),
    UNIQUE (organization_id, membership_id),
    CHECK ((status='revoked') = (revoked_at IS NOT NULL))
);
CREATE INDEX ix_partner_memberships_user_status ON partner.memberships(user_id, status, organization_id);

-- No rows are created by the migration. Grants can only be managed through a
-- separately approved operator/provisioning action, never company self-service.
CREATE TABLE partner.platform_grants (
    user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    capability TEXT NOT NULL CHECK (capability IN ('organization_review','service_review','offer_review')),
    granted_by UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    reason TEXT NOT NULL CHECK (length(btrim(reason)) BETWEEN 10 AND 1000),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    PRIMARY KEY (user_id, capability, granted_at),
    CHECK (revoked_at IS NULL OR revoked_at >= granted_at)
);
CREATE INDEX ix_partner_platform_grants_active ON partner.platform_grants(user_id, capability) WHERE revoked_at IS NULL;

CREATE TABLE partner.invitations (
    invitation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT,
    email_digest BYTEA NOT NULL CHECK (octet_length(email_digest)=32),
    token_hash BYTEA NOT NULL UNIQUE CHECK (octet_length(token_hash)=32),
    proposed_role TEXT NOT NULL CHECK (proposed_role IN ('manager','editor','availability_operator','viewer')),
    invited_by UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (expires_at > created_at),
    CHECK (accepted_at IS NULL OR revoked_at IS NULL)
);
CREATE INDEX ix_partner_invitations_org_expiry ON partner.invitations(organization_id, expires_at);

CREATE TABLE partner.verification_cases (
    case_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','submitted','needs_information','verified','rejected','withdrawn')),
    evidence_refs JSONB NOT NULL DEFAULT '[]'::JSONB CHECK (jsonb_typeof(evidence_refs)='array'),
    submitted_by UUID REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    reviewer_user_id UUID REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    policy_version TEXT NOT NULL,
    decision_reason TEXT,
    submitted_at TIMESTAMPTZ,
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (status NOT IN ('verified','rejected') OR (reviewer_user_id IS NOT NULL AND reviewer_user_id <> submitted_by AND decided_at IS NOT NULL))
);
CREATE INDEX ix_partner_verification_org_time ON partner.verification_cases(organization_id, created_at DESC);

CREATE TABLE partner.branches (
    branch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT,
    display_name TEXT NOT NULL CHECK (length(btrim(display_name)) BETWEEN 1 AND 240),
    address_text TEXT,
    admin_area_id BIGINT REFERENCES geo.admin_areas(admin_area_id) ON DELETE RESTRICT,
    location geometry(Point,4326),
    location_role TEXT NOT NULL DEFAULT 'unknown' CHECK (location_role IN ('service_location','entrance','approximate_reference','unknown')),
    coordinate_source TEXT,
    contact_public TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','submitted','approved','suspended','withdrawn')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, branch_id),
    CHECK (location IS NULL OR location_role <> 'unknown'),
    CHECK (location_role <> 'entrance' OR (location IS NOT NULL AND coordinate_source IS NOT NULL))
);
CREATE INDEX ix_partner_branches_org_status ON partner.branches(organization_id, status);
CREATE INDEX ix_partner_branches_location ON partner.branches USING GIST(location) WHERE location IS NOT NULL;

CREATE TABLE partner.services (
    service_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT,
    branch_id UUID,
    service_type TEXT NOT NULL CHECK (length(btrim(service_type)) BETWEEN 1 AND 80),
    service_key TEXT NOT NULL CHECK (length(btrim(service_key)) BETWEEN 1 AND 160),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','submitted','approved','published','suspended','withdrawn','rejected')),
    public_fields JSONB NOT NULL DEFAULT '{}'::JSONB CHECK (jsonb_typeof(public_fields)='object'),
    internal_notes TEXT,
    created_by UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ,
    UNIQUE (organization_id, service_id),
    UNIQUE (organization_id, service_key),
    FOREIGN KEY (organization_id, branch_id) REFERENCES partner.branches(organization_id, branch_id) ON DELETE RESTRICT,
    CHECK (status <> 'published' OR published_at IS NOT NULL)
);
CREATE INDEX ix_partner_services_org_status ON partner.services(organization_id, status, updated_at DESC);

CREATE TABLE partner.service_localizations (
    organization_id UUID NOT NULL,
    service_id UUID NOT NULL,
    locale TEXT NOT NULL CHECK (locale IN ('fa-IR','en-US','ar')),
    display_name TEXT NOT NULL CHECK (length(btrim(display_name)) BETWEEN 1 AND 240),
    description TEXT,
    content_status TEXT NOT NULL DEFAULT 'draft' CHECK (content_status IN ('draft','submitted','approved','rejected','withdrawn')),
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (service_id, locale),
    FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT
);

CREATE TABLE partner.service_destinations (
    organization_id UUID NOT NULL,
    service_id UUID NOT NULL,
    destination_id BIGINT NOT NULL REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT,
    relation_type TEXT NOT NULL CHECK (relation_type IN ('at','serves','near','route_endpoint')),
    evidence_note TEXT,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','submitted','approved','rejected','withdrawn')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (service_id, destination_id),
    FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT
);
CREATE INDEX ix_partner_service_destinations_destination ON partner.service_destinations(destination_id, status);

CREATE TABLE partner.schedules (
    schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    service_id UUID NOT NULL,
    schedule_type TEXT NOT NULL CHECK (schedule_type IN ('opening_window','departure','appointment','event','other')),
    timezone TEXT,
    starts_at TIMESTAMPTZ,
    ends_at TIMESTAMPTZ,
    recurrence JSONB CHECK (recurrence IS NULL OR jsonb_typeof(recurrence)='object'),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','submitted','approved','withdrawn','expired')),
    observed_at TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, schedule_id),
    UNIQUE (organization_id, service_id, schedule_id),
    FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT,
    CHECK (ends_at IS NULL OR starts_at IS NULL OR ends_at >= starts_at),
    CHECK (valid_until IS NULL OR observed_at IS NULL OR valid_until >= observed_at),
    CHECK ((starts_at IS NULL AND ends_at IS NULL) OR timezone IS NOT NULL)
);
CREATE INDEX ix_partner_schedules_service_state ON partner.schedules(organization_id, service_id, status, starts_at);

CREATE TABLE partner.offers (
    offer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    service_id UUID NOT NULL,
    schedule_id UUID,
    offer_type TEXT NOT NULL CHECK (length(btrim(offer_type)) BETWEEN 1 AND 80),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','submitted','approved','published','suspended','withdrawn','rejected')),
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    capacity_limit INTEGER CHECK (capacity_limit IS NULL OR capacity_limit >= 0),
    created_by UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ,
    UNIQUE (organization_id, offer_id),
    UNIQUE (organization_id, offer_id, schedule_id),
    FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT,
    FOREIGN KEY (organization_id, service_id, schedule_id) REFERENCES partner.schedules(organization_id, service_id, schedule_id) ON DELETE RESTRICT,
    CHECK (valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from),
    CHECK (status <> 'published' OR published_at IS NOT NULL)
);
CREATE INDEX ix_partner_offers_service_state ON partner.offers(organization_id, service_id, status, valid_from, valid_until);

CREATE TABLE partner.prices (
    price_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    offer_id UUID NOT NULL,
    price_state TEXT NOT NULL CHECK (price_state IN ('known','unknown','not_applicable','conflicting')),
    amount NUMERIC(14,2),
    currency CHAR(3),
    denomination TEXT,
    unit TEXT,
    tax_included BOOLEAN,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    observed_at TIMESTAMPTZ,
    source_kind TEXT NOT NULL CHECK (source_kind IN ('partner_asserted','approved_feed','platform_observation')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (organization_id, offer_id) REFERENCES partner.offers(organization_id, offer_id) ON DELETE RESTRICT,
    CHECK (price_state <> 'known' OR (amount IS NOT NULL AND currency IS NOT NULL AND denomination IS NOT NULL AND unit IS NOT NULL AND observed_at IS NOT NULL)),
    CHECK (price_state = 'known' OR (amount IS NULL AND currency IS NULL AND denomination IS NULL AND unit IS NULL AND tax_included IS NULL)),
    CHECK (amount IS NULL OR amount >= 0),
    CHECK (currency IS NULL OR currency ~ '^[A-Z]{3}$'),
    CHECK (valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from)
);
CREATE INDEX ix_partner_prices_offer_observed ON partner.prices(organization_id, offer_id, observed_at DESC);

CREATE TABLE partner.availability_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    offer_id UUID NOT NULL,
    schedule_id UUID,
    occurrence_starts_at TIMESTAMPTZ,
    occurrence_ends_at TIMESTAMPTZ,
    availability_state TEXT NOT NULL CHECK (availability_state IN ('available','unavailable','limited','unknown','conflicting')),
    available_count INTEGER CHECK (available_count IS NULL OR available_count >= 0),
    source_kind TEXT NOT NULL CHECK (source_kind IN ('partner_asserted','approved_feed','platform_observation')),
    observed_at TIMESTAMPTZ,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    created_by UUID REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (organization_id, offer_id, schedule_id)
        REFERENCES partner.offers(organization_id, offer_id, schedule_id) ON DELETE RESTRICT,
    CHECK ((availability_state='unknown' AND available_count IS NULL) OR availability_state <> 'unknown'),
    CHECK (availability_state <> 'available' OR observed_at IS NOT NULL),
    CHECK (occurrence_ends_at IS NULL OR occurrence_starts_at IS NULL OR occurrence_ends_at >= occurrence_starts_at),
    CHECK (valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from)
);
CREATE INDEX ix_partner_availability_offer_occurrence ON partner.availability_snapshots(organization_id, offer_id, occurrence_starts_at, observed_at DESC);

CREATE TABLE partner.review_events (
    review_event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT,
    entity_type TEXT NOT NULL CHECK (entity_type IN ('organization','verification_case','branch','service','offer','price','schedule','availability')),
    entity_id UUID NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approve','reject','request_changes','suspend','reinstate')),
    reviewer_user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    reason TEXT NOT NULL CHECK (length(btrim(reason)) BETWEEN 10 AND 2000),
    policy_version TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_partner_review_events_org_time ON partner.review_events(organization_id, occurred_at DESC);

CREATE FUNCTION partner.current_actor_id() RETURNS UUID
LANGUAGE SQL STABLE
SET search_path = pg_catalog
AS $$ SELECT NULLIF(current_setting('app.actor_id', true), '')::uuid $$;

CREATE FUNCTION partner.has_active_membership(p_organization_id UUID, p_actor_id UUID)
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER
SET search_path = pg_catalog, partner
SET row_security = off
AS $$ SELECT EXISTS (
    SELECT 1 FROM partner.memberships m
    WHERE m.organization_id = p_organization_id
      AND m.user_id = p_actor_id
      AND m.status = 'active'
) $$;
CREATE FUNCTION partner.has_active_role(p_organization_id UUID, p_actor_id UUID, p_roles TEXT[])
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER
SET search_path = pg_catalog, partner
SET row_security = off
AS $$ SELECT EXISTS (
    SELECT 1 FROM partner.memberships m
    WHERE m.organization_id = p_organization_id
      AND m.user_id = p_actor_id
      AND m.status = 'active'
      AND m.role = ANY(p_roles)
) $$;
CREATE FUNCTION partner.has_platform_capability(p_actor_id UUID, p_capability TEXT)
RETURNS BOOLEAN LANGUAGE SQL STABLE SECURITY DEFINER
SET search_path = pg_catalog, partner
SET row_security = off
AS $$ SELECT EXISTS (
    SELECT 1 FROM partner.platform_grants g
    WHERE g.user_id = p_actor_id AND g.capability = p_capability AND g.revoked_at IS NULL
) $$;
REVOKE ALL ON FUNCTION partner.current_actor_id() FROM PUBLIC;
REVOKE ALL ON FUNCTION partner.has_active_membership(UUID,UUID) FROM PUBLIC;
REVOKE ALL ON FUNCTION partner.has_active_role(UUID,UUID,TEXT[]) FROM PUBLIC;
REVOKE ALL ON FUNCTION partner.has_platform_capability(UUID,TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION partner.current_actor_id() TO ai_tourism_app;
GRANT EXECUTE ON FUNCTION partner.has_active_membership(UUID,UUID) TO ai_tourism_app;
GRANT EXECUTE ON FUNCTION partner.has_active_role(UUID,UUID,TEXT[]) TO ai_tourism_app;
GRANT EXECUTE ON FUNCTION partner.has_platform_capability(UUID,TEXT) TO ai_tourism_app;

DO $$ DECLARE t TEXT; BEGIN
  FOREACH t IN ARRAY ARRAY['organizations','memberships','invitations','verification_cases','branches','services',
    'service_localizations','service_destinations','schedules','offers','prices','availability_snapshots','review_events'] LOOP
    EXECUTE format('ALTER TABLE partner.%I ENABLE ROW LEVEL SECURITY', t);
  END LOOP;
END $$;

CREATE POLICY organizations_read_member ON partner.organizations FOR SELECT
USING (created_by = partner.current_actor_id() OR partner.has_active_membership(organization_id, partner.current_actor_id())
    OR partner.has_platform_capability(partner.current_actor_id(),'organization_review'));
CREATE POLICY organizations_insert_self ON partner.organizations FOR INSERT
WITH CHECK (created_by = partner.current_actor_id() AND verification_status='pending' AND participation_status='inactive');
CREATE POLICY organizations_update_member ON partner.organizations FOR UPDATE
USING (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager']))
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager'])
    AND verification_status IN ('pending','rejected') AND participation_status='inactive'
    AND application_status IN ('draft','submitted','needs_information','withdrawn'));
CREATE POLICY organizations_platform_review ON partner.organizations FOR UPDATE
USING (partner.has_platform_capability(partner.current_actor_id(),'organization_review'))
WITH CHECK (partner.has_platform_capability(partner.current_actor_id(),'organization_review'));

CREATE POLICY memberships_read_scoped ON partner.memberships FOR SELECT
USING (user_id = partner.current_actor_id() OR partner.has_active_membership(organization_id, partner.current_actor_id()));
CREATE POLICY memberships_insert_owner_self ON partner.memberships FOR INSERT
WITH CHECK (user_id = partner.current_actor_id() AND role='owner' AND status='active'
    AND EXISTS (SELECT 1 FROM partner.organizations o
                WHERE o.organization_id=partner.memberships.organization_id
                  AND o.created_by=partner.current_actor_id()));
CREATE POLICY memberships_update_scoped ON partner.memberships FOR UPDATE
USING (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager']))
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager']));

CREATE POLICY invitations_select_manager ON partner.invitations FOR SELECT
USING (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager']));
CREATE POLICY invitations_insert_manager ON partner.invitations FOR INSERT
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager'])
    AND invited_by=partner.current_actor_id());
CREATE POLICY invitations_update_manager ON partner.invitations FOR UPDATE
USING (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager']))
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager']));

CREATE POLICY verification_case_select ON partner.verification_cases FOR SELECT
USING (partner.has_active_membership(organization_id, partner.current_actor_id())
    OR partner.has_platform_capability(partner.current_actor_id(),'organization_review'));
CREATE POLICY verification_case_submit ON partner.verification_cases FOR INSERT
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager'])
    AND submitted_by=partner.current_actor_id() AND reviewer_user_id IS NULL
    AND status IN ('draft','submitted','withdrawn'));
CREATE POLICY verification_case_update_self ON partner.verification_cases FOR UPDATE
USING (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager'])
    AND reviewer_user_id IS NULL)
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager'])
    AND reviewer_user_id IS NULL AND status IN ('draft','submitted','needs_information','withdrawn'));
CREATE POLICY verification_case_platform_review ON partner.verification_cases FOR UPDATE
USING (partner.has_platform_capability(partner.current_actor_id(),'organization_review'))
WITH CHECK (partner.has_platform_capability(partner.current_actor_id(),'organization_review')
    AND reviewer_user_id=partner.current_actor_id() AND reviewer_user_id<>submitted_by
    AND status IN ('needs_information','verified','rejected','withdrawn'));

CREATE POLICY branches_select_member ON partner.branches FOR SELECT
USING (partner.has_active_membership(organization_id, partner.current_actor_id()));
CREATE POLICY branches_select_reviewer ON partner.branches FOR SELECT
USING (partner.has_platform_capability(partner.current_actor_id(),'service_review'));
CREATE POLICY branches_insert_editor ON partner.branches FOR INSERT
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor'])
    AND status IN ('draft','submitted') AND (status<>'approved'));
CREATE POLICY branches_update_editor ON partner.branches FOR UPDATE
USING (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor']))
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor']) AND status IN ('draft','submitted','suspended','withdrawn'));
CREATE POLICY branches_platform_review ON partner.branches FOR UPDATE
USING (partner.has_platform_capability(partner.current_actor_id(),'service_review'))
WITH CHECK (partner.has_platform_capability(partner.current_actor_id(),'service_review'));

CREATE POLICY services_select_member ON partner.services FOR SELECT
USING (partner.has_active_membership(organization_id, partner.current_actor_id()));
CREATE POLICY services_select_reviewer ON partner.services FOR SELECT
USING (partner.has_platform_capability(partner.current_actor_id(),'service_review'));
CREATE POLICY services_insert_editor ON partner.services FOR INSERT
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor'])
    AND created_by=partner.current_actor_id() AND status IN ('draft','submitted') AND published_at IS NULL);
CREATE POLICY services_update_editor ON partner.services FOR UPDATE
USING (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor']) AND status IN ('draft','submitted'))
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor'])
    AND status IN ('draft','submitted') AND published_at IS NULL);
CREATE POLICY services_platform_review ON partner.services FOR UPDATE
USING (partner.has_platform_capability(partner.current_actor_id(),'service_review'))
WITH CHECK (partner.has_platform_capability(partner.current_actor_id(),'service_review'));

CREATE POLICY service_localizations_select ON partner.service_localizations FOR SELECT
USING (partner.has_active_membership(organization_id, partner.current_actor_id())
    OR partner.has_platform_capability(partner.current_actor_id(),'service_review'));
CREATE POLICY service_localizations_write ON partner.service_localizations FOR ALL
USING (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor']))
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor'])
    AND content_status IN ('draft','submitted','withdrawn'));
CREATE POLICY service_localizations_platform ON partner.service_localizations FOR UPDATE
USING (partner.has_platform_capability(partner.current_actor_id(),'service_review'))
WITH CHECK (partner.has_platform_capability(partner.current_actor_id(),'service_review'));

CREATE POLICY service_destinations_select ON partner.service_destinations FOR SELECT
USING (partner.has_active_membership(organization_id, partner.current_actor_id())
    OR partner.has_platform_capability(partner.current_actor_id(),'service_review'));
CREATE POLICY service_destinations_write ON partner.service_destinations FOR ALL
USING (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor']))
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor'])
    AND status IN ('draft','submitted','rejected','withdrawn'));
CREATE POLICY service_destinations_platform ON partner.service_destinations FOR UPDATE
USING (partner.has_platform_capability(partner.current_actor_id(),'service_review'))
WITH CHECK (partner.has_platform_capability(partner.current_actor_id(),'service_review'));

CREATE POLICY schedules_select ON partner.schedules FOR SELECT
USING (partner.has_active_membership(organization_id, partner.current_actor_id())
    OR partner.has_platform_capability(partner.current_actor_id(),'offer_review'));
CREATE POLICY schedules_write ON partner.schedules FOR ALL
USING (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor','availability_operator']))
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor','availability_operator'])
    AND status IN ('draft','submitted','withdrawn','expired'));
CREATE POLICY schedules_platform ON partner.schedules FOR UPDATE
USING (partner.has_platform_capability(partner.current_actor_id(),'offer_review'))
WITH CHECK (partner.has_platform_capability(partner.current_actor_id(),'offer_review'));

CREATE POLICY offers_select ON partner.offers FOR SELECT
USING (partner.has_active_membership(organization_id, partner.current_actor_id())
    OR partner.has_platform_capability(partner.current_actor_id(),'offer_review'));
CREATE POLICY offers_write ON partner.offers FOR ALL
USING (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor']))
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor'])
    AND status IN ('draft','submitted','withdrawn','rejected') AND published_at IS NULL);
CREATE POLICY offers_platform ON partner.offers FOR UPDATE
USING (partner.has_platform_capability(partner.current_actor_id(),'offer_review'))
WITH CHECK (partner.has_platform_capability(partner.current_actor_id(),'offer_review'));

CREATE POLICY prices_select ON partner.prices FOR SELECT
USING (partner.has_active_membership(organization_id, partner.current_actor_id())
    OR partner.has_platform_capability(partner.current_actor_id(),'offer_review'));
CREATE POLICY prices_insert ON partner.prices FOR INSERT
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','editor','availability_operator']));
CREATE POLICY availability_select ON partner.availability_snapshots FOR SELECT
USING (partner.has_active_membership(organization_id, partner.current_actor_id())
    OR partner.has_platform_capability(partner.current_actor_id(),'offer_review'));
CREATE POLICY availability_insert ON partner.availability_snapshots FOR INSERT
WITH CHECK (partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner','manager','availability_operator'])
    AND (created_by IS NULL OR created_by=partner.current_actor_id()));
CREATE POLICY review_events_member_read ON partner.review_events FOR SELECT
USING (partner.has_active_membership(organization_id, partner.current_actor_id())
    OR partner.has_platform_capability(partner.current_actor_id(),'organization_review')
    OR partner.has_platform_capability(partner.current_actor_id(),'service_review')
    OR partner.has_platform_capability(partner.current_actor_id(),'offer_review'));
CREATE POLICY review_events_platform_insert ON partner.review_events FOR INSERT
WITH CHECK (reviewer_user_id=partner.current_actor_id()
    AND ((entity_type='organization' AND partner.has_platform_capability(partner.current_actor_id(),'organization_review'))
      OR (entity_type IN ('service','branch') AND partner.has_platform_capability(partner.current_actor_id(),'service_review'))
      OR (entity_type IN ('offer','price','schedule','availability') AND partner.has_platform_capability(partner.current_actor_id(),'offer_review'))));

REVOKE ALL ON ALL TABLES IN SCHEMA partner FROM PUBLIC;
GRANT USAGE ON SCHEMA partner TO ai_tourism_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA partner TO ai_tourism_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA partner TO ai_tourism_app;

INSERT INTO system.schema_migrations(migration_id, sha256)
VALUES ('0019_partner_workspace', :'migration_hash');
COMMIT;
