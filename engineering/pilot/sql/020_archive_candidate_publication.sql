\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0019_hash RAHGARD_PILOT_MIGRATION_0019_SHA256
\getenv migration_hash RAHGARD_PILOT_MIGRATION_0020_SHA256

-- Human-attested source verification, field-level candidate evidence, and
-- single-record publication. No archive row is promoted by this migration.
BEGIN;
SELECT 1 / CASE WHEN current_database() = 'rahgard_pilot_vps_staging'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND inet_server_port() <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker) = 1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) = :'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_0019_hash' ~ '^[a-f0-9]{64}$'
    AND EXISTS (SELECT 1 FROM system.schema_migrations
                WHERE migration_id='0019_partner_workspace' AND sha256=:'migration_0019_hash')
    AND NOT EXISTS (SELECT 1 FROM system.schema_migrations
                    WHERE migration_id='0020_archive_candidate_publication')
    THEN 1 ELSE 0 END;

CREATE TABLE knowledge.source_verification_reviews (
    verification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id BIGINT NOT NULL REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT,
    decision TEXT NOT NULL CHECK (decision IN ('verified','rejected')),
    source_url TEXT NOT NULL CHECK (source_url ~ '^https://'),
    publisher TEXT NOT NULL CHECK (length(btrim(publisher)) BETWEEN 1 AND 240),
    page_title TEXT NOT NULL CHECK (length(btrim(page_title)) BETWEEN 1 AND 500),
    evidence_excerpt TEXT NOT NULL CHECK (length(btrim(evidence_excerpt)) BETWEEN 1 AND 600),
    inspected_at TIMESTAMPTZ NOT NULL,
    reviewer_user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    policy_version TEXT NOT NULL CHECK (length(btrim(policy_version)) BETWEEN 1 AND 80),
    decided_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_source_verification_latest ON knowledge.source_verification_reviews(source_id,decided_at DESC);

CREATE TABLE knowledge.source_registry_registration_events (
    registration_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id BIGINT NOT NULL REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT,
    publisher TEXT NOT NULL CHECK (length(btrim(publisher)) BETWEEN 1 AND 240),
    page_title TEXT NOT NULL CHECK (length(btrim(page_title)) BETWEEN 1 AND 500),
    registered_url TEXT NOT NULL CHECK (registered_url ~ '^https://[^[:space:]]+$'),
    license_note TEXT,
    registration_note TEXT NOT NULL CHECK (length(btrim(registration_note)) BETWEEN 1 AND 1000),
    registrar_user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    policy_version TEXT NOT NULL CHECK (length(btrim(policy_version)) BETWEEN 1 AND 80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_source_registration_source_time ON knowledge.source_registry_registration_events(source_id,created_at DESC);

CREATE TABLE knowledge.destination_candidate_evidence (
    evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL REFERENCES knowledge.destination_candidates(candidate_id) ON DELETE RESTRICT,
    source_id BIGINT NOT NULL REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT,
    field_key TEXT NOT NULL CHECK (field_key IN ('identity','province','city','coordinates','description')),
    claim_value TEXT NOT NULL CHECK (length(btrim(claim_value)) BETWEEN 1 AND 8000),
    source_url TEXT NOT NULL CHECK (source_url ~ '^https://'),
    evidence_excerpt TEXT NOT NULL CHECK (length(btrim(evidence_excerpt)) BETWEEN 1 AND 600),
    retrieved_at TIMESTAMPTZ NOT NULL,
    reviewer_user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    policy_version TEXT NOT NULL CHECK (length(btrim(policy_version)) BETWEEN 1 AND 80),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(candidate_id,source_id,field_key,claim_value,source_url)
);
CREATE INDEX ix_candidate_evidence_candidate ON knowledge.destination_candidate_evidence(candidate_id,field_key,created_at DESC);

CREATE TABLE knowledge.catalogue_publication_events (
    publication_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    candidate_id UUID NOT NULL UNIQUE REFERENCES knowledge.destination_candidates(candidate_id) ON DELETE RESTRICT,
    destination_id BIGINT NOT NULL UNIQUE REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT,
    evidence_ids JSONB NOT NULL CHECK (jsonb_typeof(evidence_ids)='array' AND jsonb_array_length(evidence_ids)>=4),
    reviewer_user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
    policy_version TEXT NOT NULL CHECK (length(btrim(policy_version)) BETWEEN 1 AND 80),
    published_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

REVOKE ALL ON knowledge.source_verification_reviews,knowledge.source_registry_registration_events,knowledge.destination_candidate_evidence,
    knowledge.catalogue_publication_events FROM PUBLIC;
GRANT SELECT,INSERT ON knowledge.source_verification_reviews,knowledge.source_registry_registration_events,
    knowledge.destination_candidate_evidence,knowledge.catalogue_publication_events TO ai_tourism_app;
GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA knowledge TO ai_tourism_app;

ALTER TABLE knowledge.source_verification_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.source_registry_registration_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.destination_candidate_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE knowledge.catalogue_publication_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY source_verification_reviewers ON knowledge.source_verification_reviews FOR SELECT
USING (identity.has_catalogue_review_capability(identity.current_app_actor_id(),'source_review'));
CREATE POLICY source_verification_review_insert ON knowledge.source_verification_reviews FOR INSERT
WITH CHECK (reviewer_user_id=identity.current_app_actor_id()
    AND identity.has_catalogue_review_capability(identity.current_app_actor_id(),'source_review'));
CREATE POLICY source_registry_event_reviewers ON knowledge.source_registry_registration_events FOR SELECT
USING (identity.has_catalogue_review_capability(identity.current_app_actor_id(),'source_review'));
CREATE POLICY source_registry_event_insert ON knowledge.source_registry_registration_events FOR INSERT
WITH CHECK (registrar_user_id=identity.current_app_actor_id()
    AND identity.has_catalogue_review_capability(identity.current_app_actor_id(),'source_review'));
CREATE POLICY candidate_evidence_reviewers ON knowledge.destination_candidate_evidence FOR SELECT
USING (identity.has_catalogue_review_capability(identity.current_app_actor_id(),'candidate_review')
    OR identity.has_catalogue_review_capability(identity.current_app_actor_id(),'catalogue_publish'));
CREATE POLICY candidate_evidence_insert ON knowledge.destination_candidate_evidence FOR INSERT
WITH CHECK (reviewer_user_id=identity.current_app_actor_id()
    AND identity.has_catalogue_review_capability(identity.current_app_actor_id(),'source_review'));
CREATE POLICY publication_reviewers ON knowledge.catalogue_publication_events FOR SELECT
USING (identity.has_catalogue_review_capability(identity.current_app_actor_id(),'catalogue_publish'));
CREATE POLICY publication_insert ON knowledge.catalogue_publication_events FOR INSERT
WITH CHECK (reviewer_user_id=identity.current_app_actor_id()
    AND identity.has_catalogue_review_capability(identity.current_app_actor_id(),'catalogue_publish'));

CREATE FUNCTION knowledge.verify_archive_source(
    p_source_id BIGINT,p_publisher TEXT,p_page_title TEXT,p_excerpt TEXT,
    p_inspected_at TIMESTAMPTZ,p_policy_version TEXT,p_actor UUID
) RETURNS UUID
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,knowledge,identity SET row_security=off AS $$
DECLARE s knowledge.knowledge_sources%ROWTYPE; result UUID;
BEGIN
    IF p_actor IS DISTINCT FROM identity.current_app_actor_id()
       OR NOT identity.has_catalogue_review_capability(p_actor,'source_review') THEN
        RAISE EXCEPTION 'source_review_not_granted' USING ERRCODE='42501';
    END IF;
    IF p_inspected_at > now() OR p_inspected_at < now()-interval '180 days'
       OR length(btrim(p_excerpt)) NOT BETWEEN 1 AND 600
       OR length(btrim(p_publisher)) NOT BETWEEN 1 AND 240
       OR length(btrim(p_page_title)) NOT BETWEEN 1 AND 500 THEN
        RAISE EXCEPTION 'source_review_evidence_invalid' USING ERRCODE='22023';
    END IF;
    SELECT * INTO s FROM knowledge.knowledge_sources WHERE source_id=p_source_id FOR UPDATE;
    IF NOT FOUND OR s.is_synthetic OR s.verification_status NOT IN ('pending','stale')
       OR s.url IS NULL OR s.url !~ '^https://' THEN
        RAISE EXCEPTION 'source_not_verifiable' USING ERRCODE='22023';
    END IF;
    INSERT INTO knowledge.source_verification_reviews
      (source_id,decision,source_url,publisher,page_title,evidence_excerpt,inspected_at,reviewer_user_id,policy_version)
    VALUES(p_source_id,'verified',s.url,btrim(p_publisher),btrim(p_page_title),btrim(p_excerpt),p_inspected_at,p_actor,p_policy_version)
    RETURNING verification_id INTO result;
    UPDATE knowledge.knowledge_sources SET verification_status='verified',reliability_score=0.95,updated_at=now()
      WHERE source_id=p_source_id;
    RETURN result;
END $$;
REVOKE ALL ON FUNCTION knowledge.verify_archive_source(BIGINT,TEXT,TEXT,TEXT,TIMESTAMPTZ,TEXT,UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION knowledge.verify_archive_source(BIGINT,TEXT,TEXT,TEXT,TIMESTAMPTZ,TEXT,UUID) TO ai_tourism_app;

CREATE FUNCTION knowledge.publish_archive_destination(
    p_candidate UUID,p_destination_key TEXT,p_coordinate_role TEXT,p_actor UUID,p_policy_version TEXT
) RETURNS BIGINT
LANGUAGE plpgsql SECURITY DEFINER
SET search_path=pg_catalog,knowledge,identity,operations SET row_security=off AS $$
DECLARE c knowledge.destination_candidates%ROWTYPE; d BIGINT; province TEXT; city TEXT; description_text TEXT;
        evidence_set JSONB;
BEGIN
    IF p_actor IS DISTINCT FROM identity.current_app_actor_id()
       OR NOT identity.has_catalogue_review_capability(p_actor,'catalogue_publish') THEN
        RAISE EXCEPTION 'catalogue_publish_not_granted' USING ERRCODE='42501';
    END IF;
    IF p_destination_key !~ '^[a-z0-9][a-z0-9_-]{2,239}$'
       OR p_coordinate_role NOT IN ('property_reference','representative_point') THEN
        RAISE EXCEPTION 'publication_identity_invalid' USING ERRCODE='22023';
    END IF;
    SELECT * INTO c FROM knowledge.destination_candidates WHERE candidate_id=p_candidate FOR UPDATE;
    IF NOT FOUND OR c.candidate_kind<>'destination_identity' OR c.candidate_status<>'approved_new_identity'
       OR c.proposed_name_fa IS NULL OR c.proposed_destination_type IS NULL
       OR c.proposed_latitude IS NULL OR c.proposed_longitude IS NULL THEN
        RAISE EXCEPTION 'candidate_not_ready_for_publication' USING ERRCODE='22023';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM knowledge.destination_candidate_reviews r WHERE r.candidate_id=p_candidate
        AND r.decision='approve_new_identity' AND r.identity_relation='unresolved') THEN
        RAISE EXCEPTION 'candidate_identity_review_missing' USING ERRCODE='22023';
    END IF;
    IF c.raw_coordinate_role IS DISTINCT FROM p_coordinate_role THEN
        RAISE EXCEPTION 'coordinate_role_must_match_reviewed_archive_role' USING ERRCODE='22023';
    END IF;
    IF EXISTS(SELECT 1 FROM knowledge.destinations WHERE destination_key=p_destination_key)
       OR EXISTS(SELECT 1 FROM knowledge.destinations WHERE canonical_name=c.proposed_name_fa
           AND province_name=c.raw_province AND COALESCE(city_name,'')=COALESCE(c.raw_city,'')) THEN
        RAISE EXCEPTION 'canonical_identity_already_exists' USING ERRCODE='23505';
    END IF;
    IF NOT EXISTS(SELECT 1 FROM knowledge.destination_candidate_evidence e
       JOIN knowledge.knowledge_sources s USING(source_id)
       WHERE e.candidate_id=p_candidate AND e.field_key='identity' AND s.verification_status='verified' AND NOT s.is_synthetic
         AND btrim(e.claim_value)=btrim(c.proposed_name_fa))
       OR NOT EXISTS(SELECT 1 FROM knowledge.destination_candidate_evidence e JOIN knowledge.knowledge_sources s USING(source_id)
       WHERE e.candidate_id=p_candidate AND e.field_key='province' AND s.verification_status='verified' AND NOT s.is_synthetic)
       OR NOT EXISTS(SELECT 1 FROM knowledge.destination_candidate_evidence e JOIN knowledge.knowledge_sources s USING(source_id)
       WHERE e.candidate_id=p_candidate AND e.field_key='coordinates' AND s.verification_status='verified' AND NOT s.is_synthetic
         AND CASE WHEN e.claim_value ~ '^[-+]?[0-9]+([.][0-9]+)?[[:space:]]*,[[:space:]]*[-+]?[0-9]+([.][0-9]+)?$'
           THEN abs(split_part(e.claim_value,',',1)::numeric-c.proposed_latitude::numeric)<0.000005
             AND abs(btrim(split_part(e.claim_value,',',2))::numeric-c.proposed_longitude::numeric)<0.000005
           ELSE FALSE END)
       OR NOT EXISTS(SELECT 1 FROM knowledge.destination_candidate_evidence e JOIN knowledge.knowledge_sources s USING(source_id)
       WHERE e.candidate_id=p_candidate AND e.field_key='description' AND s.verification_status='verified' AND NOT s.is_synthetic) THEN
        RAISE EXCEPTION 'required_verified_field_evidence_missing' USING ERRCODE='22023';
    END IF;
    SELECT claim_value INTO province FROM knowledge.destination_candidate_evidence e
      JOIN knowledge.knowledge_sources s USING(source_id) WHERE e.candidate_id=p_candidate AND e.field_key='province'
      AND s.verification_status='verified' AND NOT s.is_synthetic ORDER BY e.created_at DESC LIMIT 1;
    SELECT claim_value INTO city FROM knowledge.destination_candidate_evidence e
      JOIN knowledge.knowledge_sources s USING(source_id) WHERE e.candidate_id=p_candidate AND e.field_key='city'
      AND s.verification_status='verified' AND NOT s.is_synthetic ORDER BY e.created_at DESC LIMIT 1;
    SELECT claim_value INTO description_text FROM knowledge.destination_candidate_evidence e
      JOIN knowledge.knowledge_sources s USING(source_id) WHERE e.candidate_id=p_candidate AND e.field_key='description'
      AND s.verification_status='verified' AND NOT s.is_synthetic ORDER BY e.created_at DESC LIMIT 1;
    IF province IS NULL OR description_text IS NULL OR length(description_text)>8000 THEN
      RAISE EXCEPTION 'required_destination_claim_invalid' USING ERRCODE='22023';
    END IF;
    IF EXISTS (
      SELECT required.field_key
      FROM (VALUES ('identity'),('province'),('coordinates'),('description')) AS required(field_key)
      WHERE NOT EXISTS (
        SELECT 1 FROM knowledge.destination_candidate_reviews r
        JOIN knowledge.destination_candidate_evidence e ON e.candidate_id=r.candidate_id
        JOIN knowledge.knowledge_sources s ON s.source_id=e.source_id
        WHERE r.candidate_id=p_candidate AND r.decision='approve_new_identity'
          AND r.evidence_refs @> jsonb_build_array(e.evidence_id::text)
          AND e.field_key=required.field_key
          AND s.verification_status='verified' AND NOT s.is_synthetic
      )
    ) THEN
      RAISE EXCEPTION 'publication_evidence_not_in_identity_review' USING ERRCODE='22023';
    END IF;
    INSERT INTO knowledge.destinations(destination_key,canonical_name,destination_type,province_name,city_name,
      description,latitude,longitude,coordinate_role,status,record_origin,verification_status,is_synthetic)
    VALUES(p_destination_key,c.proposed_name_fa,c.proposed_destination_type,province,city,description_text,
      c.proposed_latitude,c.proposed_longitude,p_coordinate_role,'active','verified_external','verified',FALSE)
    RETURNING destination_id INTO d;
    INSERT INTO knowledge.destination_sources(destination_id,source_id,source_role,evidence_note,retrieved_at)
      SELECT DISTINCT d,e.source_id,'primary','Supports reviewed destination field evidence; see archive candidate evidence.',e.retrieved_at
      FROM knowledge.destination_candidate_evidence e JOIN knowledge.knowledge_sources s USING(source_id)
      WHERE e.candidate_id=p_candidate AND s.verification_status='verified' AND NOT s.is_synthetic
      ON CONFLICT(destination_id,source_id) DO NOTHING;
    INSERT INTO knowledge.destination_localizations(destination_id,locale,display_name,short_description,description,
      translation_status,content_status)
      VALUES(d,'fa-IR',c.proposed_name_fa,left(description_text,500),description_text,'editor_reviewed','approved');
    SELECT jsonb_agg(e.evidence_id ORDER BY e.evidence_id) INTO evidence_set
      FROM knowledge.destination_candidate_reviews r
      JOIN knowledge.destination_candidate_evidence e ON e.candidate_id=r.candidate_id
      JOIN knowledge.knowledge_sources s ON s.source_id=e.source_id
      WHERE r.candidate_id=p_candidate AND r.decision='approve_new_identity'
        AND r.evidence_refs @> jsonb_build_array(e.evidence_id::text)
        AND s.verification_status='verified' AND NOT s.is_synthetic;
    INSERT INTO knowledge.catalogue_publication_events(candidate_id,destination_id,evidence_ids,reviewer_user_id,policy_version)
      VALUES(p_candidate,d,evidence_set,p_actor,p_policy_version);
    UPDATE knowledge.destination_candidates SET canonical_destination_id=d,updated_at=now() WHERE candidate_id=p_candidate;
    RETURN d;
END $$;
REVOKE ALL ON FUNCTION knowledge.publish_archive_destination(UUID,TEXT,TEXT,UUID,TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION knowledge.publish_archive_destination(UUID,TEXT,TEXT,UUID,TEXT) TO ai_tourism_app;

INSERT INTO system.schema_migrations(migration_id,sha256)
VALUES('0020_archive_candidate_publication',:'migration_hash');
COMMIT;
