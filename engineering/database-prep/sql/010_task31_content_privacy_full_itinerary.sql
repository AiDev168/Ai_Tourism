\set ON_ERROR_STOP on

-- Task 3.1 additive contracts. This migration creates review-only proposal
-- storage and an approved-only non-spatial culinary read view. It imports no
-- candidate records and never mutates canonical destination/source documents.
BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM system.schema_migrations
        WHERE migration_id = '0009_traveler_core'
    ) THEN
        RAISE EXCEPTION 'Migration 0010 requires Migration 0009 traveler core';
    END IF;
END $$;

-- A verified phone may retain its verification timestamp after its original
-- one-time challenge has reached its bounded cleanup point.
ALTER TABLE identity.verified_phones
    ALTER COLUMN challenge_id DROP NOT NULL;
ALTER TABLE identity.verified_phones
    DROP CONSTRAINT IF EXISTS verified_phones_challenge_id_fkey;
ALTER TABLE identity.verified_phones
    ADD CONSTRAINT verified_phones_challenge_id_fkey
    FOREIGN KEY (challenge_id) REFERENCES identity.otp_challenges(challenge_id)
    ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_otp_challenges_cleanup
    ON identity.otp_challenges (created_at, challenge_id);

-- Call with an operator-selected retention cutoff and a bounded batch size.
-- Raw phone numbers are never returned. A currently usable sent challenge is
-- protected even if an overly broad cutoff is supplied.
CREATE OR REPLACE FUNCTION identity.purge_terminal_otp_challenges(
    p_cutoff TIMESTAMPTZ,
    p_batch_limit INTEGER
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_deleted INTEGER := 0;
BEGIN
    IF p_cutoff IS NULL OR p_cutoff > NOW() THEN
        RAISE EXCEPTION 'cleanup cutoff must be a non-future timestamp';
    END IF;
    IF p_batch_limit IS NULL OR p_batch_limit < 1 OR p_batch_limit > 1000 THEN
        RAISE EXCEPTION 'cleanup batch limit must be between 1 and 1000';
    END IF;

    WITH eligible AS (
        SELECT c.challenge_id
        FROM identity.otp_challenges c
        WHERE c.created_at < p_cutoff
          AND (
              c.delivery_status = 'failed'
              OR c.consumed_at IS NOT NULL
              OR c.superseded_at IS NOT NULL
              OR c.locked_at IS NOT NULL
              OR c.expires_at <= NOW()
          )
          AND NOT (
              c.delivery_status = 'sent'
              AND c.consumed_at IS NULL
              AND c.superseded_at IS NULL
              AND c.locked_at IS NULL
              AND c.expires_at > NOW()
          )
        ORDER BY c.created_at, c.challenge_id
        LIMIT p_batch_limit
        FOR UPDATE SKIP LOCKED
    )
    DELETE FROM identity.otp_challenges c
    USING eligible e
    WHERE c.challenge_id = e.challenge_id;

    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    RETURN v_deleted;
END;
$$;
REVOKE ALL ON FUNCTION identity.purge_terminal_otp_challenges(TIMESTAMPTZ, INTEGER) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION identity.purge_terminal_otp_challenges(TIMESTAMPTZ, INTEGER) TO ai_tourism_app;

-- Spatial content enrichment is an immutable review proposal referencing an
-- existing canonical destination. It is deliberately not a destination row.
CREATE TABLE IF NOT EXISTS knowledge.destination_enrichment_proposals (
    proposal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_key TEXT NOT NULL UNIQUE,
    dataset_import_batch_id UUID NOT NULL
        REFERENCES operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT,
    target_destination_id BIGINT NOT NULL
        REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT,
    target_destination_key TEXT NOT NULL,
    record_action TEXT NOT NULL
        CHECK (record_action = 'stage_existing_record_enrichment_review'),
    payload JSONB NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    payload_sha256 CHAR(64) NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    review_status TEXT NOT NULL DEFAULT 'needs_review'
        CHECK (review_status = 'needs_review'),
    record_origin TEXT NOT NULL DEFAULT 'verified_external'
        CHECK (record_origin = 'verified_external'),
    verification_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (verification_status = 'pending'),
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE CHECK (is_synthetic = FALSE),
    approval_confidence NUMERIC(5,4) NOT NULL DEFAULT 0
        CHECK (approval_confidence = 0),
    publishable BOOLEAN NOT NULL DEFAULT FALSE CHECK (publishable = FALSE),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (length(btrim(proposal_key)) > 0),
    CHECK (length(btrim(target_destination_key)) > 0)
);
CREATE INDEX IF NOT EXISTS idx_destination_enrichment_proposals_target
    ON knowledge.destination_enrichment_proposals (target_destination_id, created_at DESC);

CREATE TABLE IF NOT EXISTS knowledge.destination_enrichment_proposal_sources (
    proposal_source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL
        REFERENCES knowledge.destination_enrichment_proposals(proposal_id) ON DELETE CASCADE,
    claim_key TEXT NOT NULL,
    source_key TEXT NOT NULL,
    source_id BIGINT REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL CHECK (source_url ~ '^https?://[^[:space:]]+$'),
    source_license TEXT,
    source_role TEXT NOT NULL,
    evidence_note TEXT,
    retrieved_at TIMESTAMPTZ,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (proposal_id, claim_key, source_key, source_role),
    CHECK (length(btrim(claim_key)) > 0 AND length(btrim(source_key)) > 0),
    CHECK (length(btrim(source_name)) > 0 AND length(btrim(source_role)) > 0),
    CHECK (valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from)
);
CREATE INDEX IF NOT EXISTS idx_destination_proposal_sources_claim
    ON knowledge.destination_enrichment_proposal_sources (proposal_id, claim_key);

-- Non-spatial culinary candidate and review contract. Existing legacy food
-- destination IDs are optional identity references only; the production read
-- view below never joins or emits them.
CREATE TABLE IF NOT EXISTS knowledge.culinary_knowledge_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_key TEXT NOT NULL UNIQUE,
    record_key TEXT NOT NULL,
    dataset_import_batch_id UUID NOT NULL
        REFERENCES operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT,
    record_action TEXT NOT NULL CHECK (record_action IN (
        'stage_existing_record_enrichment_review',
        'stage_new_non_spatial_candidate_review'
    )),
    legacy_destination_id BIGINT
        REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT,
    category TEXT NOT NULL CHECK (category ~ '^[a-z][a-z0-9_]{1,63}$'),
    names_by_locale JSONB NOT NULL CHECK (
        jsonb_typeof(names_by_locale) = 'object'
        AND names_by_locale ?& ARRAY['fa-IR', 'en-US', 'ar']
        AND jsonb_typeof(names_by_locale->'fa-IR') = 'string'
        AND jsonb_typeof(names_by_locale->'en-US') = 'string'
        AND jsonb_typeof(names_by_locale->'ar') = 'string'
        AND length(btrim(names_by_locale->>'fa-IR')) > 0
        AND length(btrim(names_by_locale->>'en-US')) > 0
        AND length(btrim(names_by_locale->>'ar')) > 0
    ),
    descriptions_by_locale JSONB NOT NULL CHECK (
        jsonb_typeof(descriptions_by_locale) = 'object'
        AND descriptions_by_locale ?& ARRAY['fa-IR', 'en-US', 'ar']
        AND jsonb_typeof(descriptions_by_locale->'fa-IR') = 'string'
        AND jsonb_typeof(descriptions_by_locale->'en-US') = 'string'
        AND jsonb_typeof(descriptions_by_locale->'ar') = 'string'
        AND length(btrim(descriptions_by_locale->>'fa-IR')) > 0
        AND length(btrim(descriptions_by_locale->>'en-US')) > 0
        AND length(btrim(descriptions_by_locale->>'ar')) > 0
    ),
    claims JSONB NOT NULL CHECK (
        jsonb_typeof(claims) = 'array' AND jsonb_array_length(claims) > 0
    ),
    payload JSONB NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    payload_sha256 CHAR(64) NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    review_status TEXT NOT NULL DEFAULT 'pending_review'
        CHECK (review_status IN ('pending_review', 'approved', 'rejected', 'withdrawn')),
    record_origin TEXT NOT NULL DEFAULT 'verified_external'
        CHECK (record_origin = 'verified_external'),
    verification_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (verification_status IN ('pending', 'verified', 'rejected', 'stale')),
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE CHECK (is_synthetic = FALSE),
    approval_confidence NUMERIC(5,4) NOT NULL DEFAULT 0
        CHECK (approval_confidence BETWEEN 0 AND 1),
    publishable BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (length(btrim(item_key)) > 0 AND length(btrim(record_key)) > 0),
    CHECK (
        (record_action = 'stage_existing_record_enrichment_review' AND legacy_destination_id IS NOT NULL)
        OR
        (record_action = 'stage_new_non_spatial_candidate_review' AND legacy_destination_id IS NULL)
    ),
    CHECK (
        (review_status = 'approved' AND publishable = TRUE AND verification_status = 'verified'
            AND approval_confidence > 0 AND published_at IS NOT NULL)
        OR
        (review_status <> 'approved' AND publishable = FALSE AND published_at IS NULL
            AND approval_confidence = 0)
    )
);
CREATE INDEX IF NOT EXISTS idx_culinary_knowledge_review
    ON knowledge.culinary_knowledge_items (review_status, updated_at DESC);

CREATE TABLE IF NOT EXISTS knowledge.culinary_item_sources (
    item_source_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID NOT NULL
        REFERENCES knowledge.culinary_knowledge_items(item_id) ON DELETE CASCADE,
    claim_key TEXT NOT NULL,
    source_key TEXT NOT NULL,
    source_id BIGINT REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL CHECK (source_url ~ '^https?://[^[:space:]]+$'),
    source_license TEXT,
    source_role TEXT NOT NULL,
    evidence_note TEXT,
    retrieved_at TIMESTAMPTZ,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (item_id, claim_key, source_key, source_role),
    CHECK (length(btrim(claim_key)) > 0 AND length(btrim(source_key)) > 0),
    CHECK (length(btrim(source_name)) > 0 AND length(btrim(source_role)) > 0),
    CHECK (valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from)
);
CREATE INDEX IF NOT EXISTS idx_culinary_item_sources_claim
    ON knowledge.culinary_item_sources (item_id, claim_key);

-- Only reviewed, explicitly published, verified, source-backed and fully
-- localized non-spatial items are readable by the application. No spatial
-- destination join, coordinates, or legacy destination identity is projected.
CREATE OR REPLACE VIEW knowledge.production_culinary_knowledge AS
WITH valid_sources AS (
    SELECT cis.item_id, cis.claim_key, cis.source_key, cis.source_name,
           cis.source_url, cis.source_license, cis.source_role,
           cis.evidence_note, cis.retrieved_at, cis.valid_from, cis.valid_until
    FROM knowledge.culinary_item_sources cis
    JOIN knowledge.knowledge_sources ks ON ks.source_id = cis.source_id
    WHERE cis.source_id IS NOT NULL
      AND cis.retrieved_at IS NOT NULL
      AND ks.verification_status = 'verified'
      AND ks.is_synthetic = FALSE
      AND (cis.valid_from IS NULL OR cis.valid_from <= NOW())
      AND (cis.valid_until IS NULL OR cis.valid_until >= NOW())
),
localized_claims AS (
    SELECT i.item_id,
           jsonb_agg(
               jsonb_build_object(
                   'claim_key', claim.value->>'claim_id',
                   'locale', locale.key,
                   'text', locale.value
               ) ORDER BY claim.value->>'claim_id', locale.key
           ) AS claims
    FROM knowledge.culinary_knowledge_items i
    CROSS JOIN LATERAL jsonb_array_elements(i.claims) AS claim(value)
    CROSS JOIN LATERAL jsonb_each_text(
        CASE WHEN jsonb_typeof(claim.value->'text_by_locale') = 'object'
             THEN claim.value->'text_by_locale' ELSE '{}'::JSONB END
    ) AS locale(key, value)
    GROUP BY i.item_id
),
claim_provenance AS (
    SELECT vs.item_id,
           jsonb_agg(
               jsonb_build_object(
                   'claim_key', vs.claim_key,
                   'source_key', vs.source_key,
                   'source_name', vs.source_name,
                   'source_url', vs.source_url,
                   'license', vs.source_license,
                   'source_role', vs.source_role,
                   'evidence_note', vs.evidence_note,
                   'retrieved_at', vs.retrieved_at,
                   'valid_from', vs.valid_from,
                   'valid_until', vs.valid_until
               ) ORDER BY vs.claim_key, vs.source_key
           ) AS provenance
    FROM valid_sources vs
    GROUP BY vs.item_id
)
SELECT i.item_id, i.item_key, i.category, i.record_key,
       i.names_by_locale, i.descriptions_by_locale,
       lc.claims, cp.provenance, i.updated_at
FROM knowledge.culinary_knowledge_items i
JOIN localized_claims lc ON lc.item_id = i.item_id
JOIN claim_provenance cp ON cp.item_id = i.item_id
WHERE i.review_status = 'approved'
  AND i.publishable = TRUE
  AND i.verification_status = 'verified'
  AND i.record_origin = 'verified_external'
  AND i.is_synthetic = FALSE
  AND i.approval_confidence > 0
  AND i.published_at IS NOT NULL
  AND i.names_by_locale ?& ARRAY['fa-IR', 'en-US', 'ar']
  AND i.descriptions_by_locale ?& ARRAY['fa-IR', 'en-US', 'ar']
  AND NOT EXISTS (
      SELECT 1
      FROM jsonb_array_elements(i.claims) AS claim(value)
      WHERE COALESCE(NULLIF(btrim(claim.value->>'claim_id'), ''), '') = ''
         OR jsonb_typeof(claim.value->'text_by_locale') IS DISTINCT FROM 'object'
         OR NOT (claim.value->'text_by_locale' ?& ARRAY['fa-IR', 'en-US', 'ar'])
         OR EXISTS (
             SELECT 1 FROM unnest(ARRAY['fa-IR', 'en-US', 'ar']) AS locale(code)
             WHERE jsonb_typeof(claim.value->'text_by_locale'->locale.code) IS DISTINCT FROM 'string'
                OR COALESCE(NULLIF(btrim(claim.value->'text_by_locale'->>locale.code), ''), '') = ''
         )
         OR NOT EXISTS (
             SELECT 1 FROM valid_sources vs
             WHERE vs.item_id = i.item_id
               AND vs.claim_key = claim.value->>'claim_id'
         )
  );

REVOKE ALL ON
    knowledge.destination_enrichment_proposals,
    knowledge.destination_enrichment_proposal_sources,
    knowledge.culinary_knowledge_items,
    knowledge.culinary_item_sources
FROM ai_tourism_app;
GRANT SELECT ON knowledge.production_culinary_knowledge TO ai_tourism_app;

-- Preserve the 0009 additive migration and remove its three-day product cap.
ALTER TABLE travel.itineraries
    DROP CONSTRAINT IF EXISTS itineraries_day_count_check;
ALTER TABLE travel.itineraries
    ADD CONSTRAINT itineraries_day_count_365_check
    CHECK (day_count BETWEEN 1 AND 365);

ALTER TABLE travel.itinerary_stops
    DROP CONSTRAINT IF EXISTS itinerary_stops_day_number_check,
    DROP CONSTRAINT IF EXISTS itinerary_stops_stop_order_check;
ALTER TABLE travel.itinerary_stops
    ADD CONSTRAINT itinerary_stops_day_number_365_check
        CHECK (day_number BETWEEN 1 AND 365),
    ADD CONSTRAINT itinerary_stops_stop_order_50_check
        CHECK (stop_order BETWEEN 1 AND 50);

CREATE OR REPLACE FUNCTION travel.enforce_itinerary_duration()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_trip_duration INTEGER;
BEGIN
    SELECT t.duration_days INTO v_trip_duration
    FROM travel.trips t
    WHERE t.trip_id = NEW.trip_id
    FOR UPDATE;
    IF NOT FOUND OR v_trip_duration IS NULL OR NEW.day_count > v_trip_duration THEN
        RAISE EXCEPTION 'itinerary duration exceeds confirmed trip duration' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_enforce_itinerary_duration ON travel.itineraries;
CREATE TRIGGER trg_enforce_itinerary_duration
BEFORE INSERT OR UPDATE OF trip_id, day_count
ON travel.itineraries
FOR EACH ROW EXECUTE FUNCTION travel.enforce_itinerary_duration();

CREATE OR REPLACE FUNCTION travel.enforce_trip_duration_against_itineraries()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM travel.itineraries i
        WHERE i.trip_id = NEW.trip_id
          AND (NEW.duration_days IS NULL OR i.day_count > NEW.duration_days OR EXISTS (
              SELECT 1 FROM travel.itinerary_stops s
              WHERE s.itinerary_id = i.itinerary_id
                AND s.day_number > NEW.duration_days
          ))
    ) THEN
        RAISE EXCEPTION 'trip duration conflicts with an existing itinerary' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_enforce_trip_duration_against_itineraries ON travel.trips;
CREATE TRIGGER trg_enforce_trip_duration_against_itineraries
BEFORE UPDATE OF duration_days
ON travel.trips
FOR EACH ROW EXECUTE FUNCTION travel.enforce_trip_duration_against_itineraries();

CREATE OR REPLACE FUNCTION travel.enforce_itinerary_stop_bounds()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    v_day_count INTEGER;
    v_trip_duration INTEGER;
    v_trip_id UUID;
    v_total_stops INTEGER;
    v_day_stops INTEGER;
BEGIN
    SELECT i.trip_id INTO v_trip_id
    FROM travel.itineraries i
    WHERE i.itinerary_id = NEW.itinerary_id;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'itinerary stop parent is unavailable' USING ERRCODE = '23503';
    END IF;
    -- Use a consistent trip-then-itinerary lock order so duration edits and
    -- concurrent stop inserts cannot violate confirmed-duration bounds.
    SELECT t.duration_days INTO v_trip_duration
    FROM travel.trips t
    WHERE t.trip_id = v_trip_id
    FOR UPDATE;
    SELECT i.day_count INTO v_day_count
    FROM travel.itineraries i
    WHERE i.itinerary_id = NEW.itinerary_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'itinerary stop parent is unavailable' USING ERRCODE = '23503';
    END IF;
    IF v_trip_duration IS NULL OR v_day_count > v_trip_duration THEN
        RAISE EXCEPTION 'itinerary duration exceeds confirmed trip duration' USING ERRCODE = '23514';
    END IF;
    IF NEW.day_number > v_day_count THEN
        RAISE EXCEPTION 'itinerary stop day exceeds itinerary day count' USING ERRCODE = '23514';
    END IF;

    SELECT COUNT(*) INTO v_total_stops
    FROM travel.itinerary_stops s
    WHERE s.itinerary_id = NEW.itinerary_id
      AND (TG_OP <> 'UPDATE' OR s.itinerary_stop_id <> NEW.itinerary_stop_id);
    IF v_total_stops >= 1000 THEN
        RAISE EXCEPTION 'itinerary exceeds the 1000-stop technical bound' USING ERRCODE = '23514';
    END IF;

    SELECT COUNT(*) INTO v_day_stops
    FROM travel.itinerary_stops s
    WHERE s.itinerary_id = NEW.itinerary_id
      AND s.day_number = NEW.day_number
      AND (TG_OP <> 'UPDATE' OR s.itinerary_stop_id <> NEW.itinerary_stop_id);
    IF v_day_stops >= 50 THEN
        RAISE EXCEPTION 'itinerary day exceeds the 50-stop technical bound' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_enforce_itinerary_stop_bounds ON travel.itinerary_stops;
CREATE TRIGGER trg_enforce_itinerary_stop_bounds
BEFORE INSERT OR UPDATE OF itinerary_id, day_number
ON travel.itinerary_stops
FOR EACH ROW EXECUTE FUNCTION travel.enforce_itinerary_stop_bounds();

INSERT INTO system.schema_migrations (migration_id, sha256)
VALUES ('0010_task31_content_privacy_full_itinerary', :'migration_hash')
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;
