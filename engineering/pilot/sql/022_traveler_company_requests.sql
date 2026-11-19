\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0021_hash RAHGARD_PILOT_MIGRATION_0021_SHA256
\getenv migration_hash RAHGARD_PILOT_MIGRATION_0022_SHA256

-- Opt-in, organization-scoped request sharing. No existing row is published or
-- shared by this migration. Consent and an explicit recipient are required.
BEGIN;
SELECT 1 / CASE WHEN current_database() = 'rahgard_pilot_vps_staging'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND inet_server_port() <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker) = 1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) = :'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_0021_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND EXISTS (SELECT 1 FROM system.schema_migrations
                WHERE migration_id='0021_postgis_security_definer_publication'
                  AND sha256=:'migration_0021_hash')
    AND NOT EXISTS (SELECT 1 FROM system.schema_migrations
                    WHERE migration_id='0022_traveler_company_requests')
    THEN 1 ELSE 0 END;

CREATE TABLE partner.traveler_request_shares (
    share_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES travel.trips(trip_id) ON DELETE CASCADE,
    traveler_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT,
    consent_policy_version TEXT NOT NULL CHECK (length(btrim(consent_policy_version)) BETWEEN 1 AND 80),
    include_original_request BOOLEAN NOT NULL DEFAULT FALSE,
    consented_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (trip_id, organization_id),
    UNIQUE (share_id, organization_id),
    CHECK (revoked_at IS NULL OR revoked_at >= consented_at)
);
CREATE INDEX ix_traveler_request_shares_owner ON partner.traveler_request_shares(traveler_id, created_at DESC);
CREATE INDEX ix_traveler_request_shares_org ON partner.traveler_request_shares(organization_id, created_at DESC) WHERE revoked_at IS NULL;

CREATE TABLE travel.trip_requirement_revisions (
    trip_id UUID NOT NULL,
    user_id UUID NOT NULL,
    revision_number INTEGER NOT NULL CHECK (revision_number > 0),
    trip_version INTEGER NOT NULL CHECK (trip_version > 0),
    requirement_snapshot JSONB NOT NULL CHECK (jsonb_typeof(requirement_snapshot)='object'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (trip_id,revision_number),
    FOREIGN KEY (trip_id,user_id) REFERENCES travel.trips(trip_id,user_id) ON DELETE CASCADE
);
ALTER TABLE travel.trip_requirement_revisions ENABLE ROW LEVEL SECURITY;
CREATE POLICY trip_requirement_revision_owner_read ON travel.trip_requirement_revisions FOR SELECT
USING (user_id=partner.current_actor_id());
CREATE POLICY trip_requirement_revision_owner_insert ON travel.trip_requirement_revisions FOR INSERT
WITH CHECK (user_id=partner.current_actor_id());
REVOKE ALL ON travel.trip_requirement_revisions FROM PUBLIC;
GRANT SELECT,INSERT ON travel.trip_requirement_revisions TO ai_tourism_app;

CREATE TABLE partner.traveler_request_revisions (
    revision_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    share_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    revision_number INTEGER NOT NULL CHECK (revision_number > 0),
    trip_version INTEGER NOT NULL CHECK (trip_version > 0),
    event_kind TEXT NOT NULL CHECK (event_kind IN ('request_shared','request_revised')),
    request_snapshot JSONB NOT NULL CHECK (jsonb_typeof(request_snapshot)='object'),
    itinerary_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(itinerary_snapshot)='object'),
    created_by UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    FOREIGN KEY (share_id, organization_id)
        REFERENCES partner.traveler_request_shares(share_id, organization_id) ON DELETE CASCADE,
    UNIQUE (share_id, revision_number),
    UNIQUE (revision_id, organization_id)
);
CREATE INDEX ix_traveler_request_revisions_org ON partner.traveler_request_revisions(organization_id, created_at DESC);

CREATE TABLE partner.traveler_request_inbox (
    inbox_event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    revision_id UUID NOT NULL REFERENCES partner.traveler_request_revisions(revision_id) ON DELETE CASCADE,
    event_kind TEXT NOT NULL CHECK (event_kind IN ('request_shared','request_revised')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    viewed_at TIMESTAMPTZ,
    FOREIGN KEY (revision_id, organization_id)
        REFERENCES partner.traveler_request_revisions(revision_id, organization_id) ON DELETE CASCADE,
    UNIQUE (revision_id)
);
CREATE INDEX ix_traveler_request_inbox_org_unread ON partner.traveler_request_inbox(organization_id, created_at DESC) WHERE viewed_at IS NULL;

CREATE OR REPLACE FUNCTION partner.capture_trip_request_revision(
    p_trip_id UUID, p_event_kind TEXT, p_share_id UUID DEFAULT NULL
)
RETURNS VOID
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog, partner, travel, conversation
SET row_security=off
AS $$
DECLARE
    trip_row travel.trips%ROWTYPE;
    share_row partner.traveler_request_shares%ROWTYPE;
    next_revision INTEGER;
    request_body JSONB;
    itinerary_body JSONB;
    revision_row UUID;
    original_text TEXT;
BEGIN
    SELECT * INTO trip_row FROM travel.trips WHERE trip_id=p_trip_id;
    IF NOT FOUND OR trip_row.is_synthetic OR trip_row.confirmed_requirements IS NULL
       OR trip_row.confirmed_requirements='{}'::jsonb THEN
        RETURN;
    END IF;
    SELECT m.content INTO original_text
      FROM conversation.messages m
     WHERE m.trip_id=p_trip_id AND m.role='user'
     ORDER BY m.created_at,m.message_id LIMIT 1;
    SELECT COALESCE(jsonb_agg(jsonb_build_object(
        'itinerary_id', i.itinerary_id, 'version', i.version, 'title', i.title,
        'day_count', i.day_count, 'stops', COALESCE(stops.items,'[]'::jsonb)
    ) ORDER BY i.version DESC), '[]'::jsonb)
      INTO itinerary_body
      FROM travel.itineraries i
      LEFT JOIN LATERAL (
          SELECT jsonb_agg(jsonb_build_object(
              'destination_id', s.destination_id, 'day_number', s.day_number,
              'stop_order', s.stop_order, 'notes_fa', s.notes_fa
          ) ORDER BY s.day_number,s.stop_order) AS items
            FROM travel.itinerary_stops s WHERE s.itinerary_id=i.itinerary_id AND NOT s.is_synthetic
      ) stops ON TRUE
     WHERE i.trip_id=p_trip_id AND NOT i.is_synthetic;
    itinerary_body := jsonb_build_object(
        'published_itineraries', itinerary_body,
        'provisional', (SELECT jsonb_build_object('day_count',p.day_count,'locale',p.locale,
             'title_by_locale',p.title_by_locale,'days',p.days,'status',p.status)
             FROM travel.provisional_itineraries p WHERE p.trip_id=p_trip_id)
    );
    FOR share_row IN SELECT * FROM partner.traveler_request_shares
        WHERE trip_id=p_trip_id AND revoked_at IS NULL
          AND (p_share_id IS NULL OR share_id=p_share_id)
    LOOP
        request_body := jsonb_build_object('requirements',trip_row.confirmed_requirements,
            'original_request', CASE WHEN share_row.include_original_request THEN original_text ELSE NULL END,
            'trip_id',p_trip_id);
        SELECT COALESCE(MAX(revision_number),0)+1 INTO next_revision
          FROM partner.traveler_request_revisions WHERE share_id=share_row.share_id;
        INSERT INTO partner.traveler_request_revisions(
            share_id,organization_id,revision_number,trip_version,event_kind,
            request_snapshot,itinerary_snapshot,created_by,is_synthetic
        ) VALUES (share_row.share_id,share_row.organization_id,next_revision,trip_row.version,
            p_event_kind,request_body,itinerary_body,trip_row.user_id,FALSE)
        RETURNING revision_id INTO revision_row;
        INSERT INTO partner.traveler_request_inbox(organization_id,revision_id,event_kind)
            VALUES (share_row.organization_id,revision_row,p_event_kind);
    END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION partner.capture_trip_request_revision_from_trip()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog, partner, travel
SET row_security=off
AS $$
BEGIN
    IF OLD.confirmed_requirements IS DISTINCT FROM NEW.confirmed_requirements THEN
        PERFORM partner.capture_trip_request_revision(NEW.trip_id,'request_revised');
    END IF;
    RETURN NEW;
END;
$$;
CREATE OR REPLACE FUNCTION partner.capture_trip_request_revision_from_itinerary()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog, partner, travel
SET row_security=off
AS $$
BEGIN
    PERFORM partner.capture_trip_request_revision(NEW.trip_id,'request_revised');
    RETURN NEW;
END;
$$;
CREATE OR REPLACE FUNCTION partner.capture_trip_request_revision_from_provisional()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog, partner, travel
SET row_security=off
AS $$
BEGIN
    IF TG_OP='DELETE' THEN
        PERFORM partner.capture_trip_request_revision(OLD.trip_id,'request_revised');
        RETURN OLD;
    END IF;
    PERFORM partner.capture_trip_request_revision(NEW.trip_id,'request_revised');
    RETURN NEW;
END;
$$;
CREATE OR REPLACE FUNCTION partner.capture_trip_request_revision_from_share()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog, partner, travel
SET row_security=off
AS $$
BEGIN
    PERFORM partner.capture_trip_request_revision(NEW.trip_id,'request_shared',NEW.share_id);
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_trip_request_revision_profile
AFTER UPDATE OF confirmed_requirements ON travel.trips
FOR EACH ROW EXECUTE FUNCTION partner.capture_trip_request_revision_from_trip();
CREATE TRIGGER trg_trip_request_revision_itinerary
AFTER UPDATE ON travel.itineraries
FOR EACH ROW EXECUTE FUNCTION partner.capture_trip_request_revision_from_itinerary();
CREATE TRIGGER trg_trip_request_revision_provisional
AFTER INSERT OR UPDATE OR DELETE ON travel.provisional_itineraries
FOR EACH ROW EXECUTE FUNCTION partner.capture_trip_request_revision_from_provisional();
CREATE TRIGGER trg_trip_request_revision_share
AFTER INSERT ON partner.traveler_request_shares
FOR EACH ROW EXECUTE FUNCTION partner.capture_trip_request_revision_from_share();

CREATE OR REPLACE FUNCTION partner.current_actor_id() RETURNS UUID
LANGUAGE SQL STABLE SET search_path=pg_catalog
AS $$ SELECT NULLIF(current_setting('app.actor_id', true), '')::uuid $$;

ALTER TABLE partner.traveler_request_shares ENABLE ROW LEVEL SECURITY;
ALTER TABLE partner.traveler_request_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE partner.traveler_request_inbox ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE VIEW partner.share_eligible_organizations WITH (security_barrier=true) AS
SELECT organization_id,display_name,organization_type
FROM partner.organizations
WHERE verification_status='verified' AND participation_status='active' AND application_status='approved';
REVOKE ALL ON partner.share_eligible_organizations FROM PUBLIC;
GRANT SELECT ON partner.share_eligible_organizations TO ai_tourism_app;

CREATE POLICY traveler_share_read ON partner.traveler_request_shares FOR SELECT
USING (traveler_id=partner.current_actor_id() OR
       (revoked_at IS NULL AND partner.has_active_membership(organization_id, partner.current_actor_id())));
CREATE POLICY traveler_share_insert ON partner.traveler_request_shares FOR INSERT
WITH CHECK (traveler_id=partner.current_actor_id()
    AND EXISTS (SELECT 1 FROM travel.trips t WHERE t.trip_id=traveler_request_shares.trip_id AND t.user_id=partner.current_actor_id() AND NOT t.is_synthetic)
    AND EXISTS (SELECT 1 FROM partner.share_eligible_organizations o
       WHERE o.organization_id=traveler_request_shares.organization_id));
CREATE POLICY traveler_share_revoke ON partner.traveler_request_shares FOR UPDATE
USING (traveler_id=partner.current_actor_id())
WITH CHECK (traveler_id=partner.current_actor_id());
CREATE POLICY traveler_revision_read ON partner.traveler_request_revisions FOR SELECT
USING (EXISTS (SELECT 1 FROM partner.traveler_request_shares s WHERE s.share_id=traveler_request_revisions.share_id
       AND s.revoked_at IS NULL
       AND (s.traveler_id=partner.current_actor_id() OR partner.has_active_membership(s.organization_id,partner.current_actor_id()))));
CREATE POLICY traveler_revision_insert ON partner.traveler_request_revisions FOR INSERT
WITH CHECK (created_by=partner.current_actor_id() AND EXISTS (
    SELECT 1 FROM partner.traveler_request_shares s
    WHERE s.share_id=traveler_request_revisions.share_id AND s.traveler_id=partner.current_actor_id() AND s.revoked_at IS NULL));
CREATE POLICY traveler_inbox_read ON partner.traveler_request_inbox FOR SELECT
USING (partner.has_active_membership(organization_id,partner.current_actor_id()));
CREATE POLICY traveler_inbox_view ON partner.traveler_request_inbox FOR UPDATE
USING (partner.has_active_membership(organization_id,partner.current_actor_id()))
WITH CHECK (partner.has_active_membership(organization_id,partner.current_actor_id()));

REVOKE ALL ON partner.traveler_request_shares, partner.traveler_request_revisions, partner.traveler_request_inbox FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE ON partner.traveler_request_shares TO ai_tourism_app;
GRANT SELECT ON partner.traveler_request_revisions TO ai_tourism_app;
GRANT SELECT, UPDATE(viewed_at) ON partner.traveler_request_inbox TO ai_tourism_app;
REVOKE ALL ON FUNCTION partner.capture_trip_request_revision(UUID,TEXT,UUID),
    partner.capture_trip_request_revision_from_trip(), partner.capture_trip_request_revision_from_itinerary(),
    partner.capture_trip_request_revision_from_provisional(),
    partner.capture_trip_request_revision_from_share() FROM PUBLIC;

INSERT INTO system.schema_migrations(migration_id,sha256)
VALUES ('0022_traveler_company_requests',:'migration_hash');
COMMIT;
