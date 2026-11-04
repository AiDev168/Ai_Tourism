BEGIN;

CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS conversation;
CREATE SCHEMA IF NOT EXISTS travel;
CREATE SCHEMA IF NOT EXISTS knowledge;
CREATE SCHEMA IF NOT EXISTS recommendation;
CREATE SCHEMA IF NOT EXISTS integration;
CREATE SCHEMA IF NOT EXISTS operations;
CREATE SCHEMA IF NOT EXISTS system;

-- ---------------------------------------------------------------------------
-- Upgrade the original project-supplied tourism_points.sql baseline safely.
-- The 15 imported records remain unverified and must never be treated as live
-- recommendations until independently reviewed and sourced.
-- ---------------------------------------------------------------------------

ALTER TABLE knowledge.knowledge_sources
    ADD COLUMN IF NOT EXISTS is_synthetic BOOLEAN NOT NULL DEFAULT FALSE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_sources_source_name
    ON knowledge.knowledge_sources (source_name);

ALTER TABLE knowledge.destinations
    ADD COLUMN IF NOT EXISTS destination_key TEXT,
    ADD COLUMN IF NOT EXISTS country_code CHAR(2) NOT NULL DEFAULT 'IR',
    ADD COLUMN IF NOT EXISTS aliases TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    ADD COLUMN IF NOT EXISTS parent_destination_id BIGINT,
    ADD COLUMN IF NOT EXISTS record_origin TEXT NOT NULL DEFAULT 'user_supplied_unverified',
    ADD COLUMN IF NOT EXISTS verification_status TEXT NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS coordinate_role TEXT NOT NULL DEFAULT 'unknown',
    ADD COLUMN IF NOT EXISTS location GEOGRAPHY(Point, 4326);

UPDATE knowledge.destinations
SET destination_key = 'legacy-' || destination_id::TEXT
WHERE destination_key IS NULL;

UPDATE knowledge.destinations
SET location = CASE
    WHEN latitude IS NULL OR longitude IS NULL THEN NULL
    ELSE ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)::GEOGRAPHY
END;

ALTER TABLE knowledge.destinations
    ALTER COLUMN destination_key SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_destinations_destination_key
    ON knowledge.destinations (destination_key);

CREATE UNIQUE INDEX IF NOT EXISTS uq_destinations_canonical_identity
    ON knowledge.destinations (canonical_name, province_name, COALESCE(city_name, ''));

ALTER TABLE knowledge.destinations
    DROP CONSTRAINT IF EXISTS chk_destination_status;
ALTER TABLE knowledge.destinations
    ADD CONSTRAINT chk_destination_status
    CHECK (status IN ('draft', 'active', 'inactive', 'archived', 'needs_review', 'test_only'));

ALTER TABLE knowledge.destinations
    ADD CONSTRAINT chk_destination_record_origin
    CHECK (record_origin IN ('user_supplied_unverified', 'verified_external', 'synthetic_fixture'));

ALTER TABLE knowledge.destinations
    ADD CONSTRAINT chk_destination_verification_status
    CHECK (verification_status IN ('pending', 'verified', 'rejected', 'stale', 'not_applicable'));

ALTER TABLE knowledge.destinations
    ADD CONSTRAINT chk_destination_synthetic_origin
    CHECK (is_synthetic = (record_origin = 'synthetic_fixture'));

ALTER TABLE knowledge.destinations
    ADD CONSTRAINT chk_destination_coordinates_pair
    CHECK ((latitude IS NULL) = (longitude IS NULL));

ALTER TABLE knowledge.destinations
    ADD CONSTRAINT chk_destination_coordinate_role
    CHECK (
        (latitude IS NULL AND longitude IS NULL AND coordinate_role = 'unknown')
        OR
        (latitude IS NOT NULL AND longitude IS NOT NULL AND coordinate_role IN (
            'property_reference', 'representative_point', 'visitor_entrance', 'test_fixture'
        ))
    );

ALTER TABLE knowledge.destinations
    ADD CONSTRAINT chk_destination_country_code
    CHECK (country_code ~ '^[A-Z]{2}$');

ALTER TABLE knowledge.destinations
    ADD CONSTRAINT chk_destination_type_key
    CHECK (destination_type ~ '^[a-z][a-z0-9_]{1,63}$');

ALTER TABLE knowledge.destinations
    ADD CONSTRAINT fk_destination_parent
    FOREIGN KEY (parent_destination_id)
    REFERENCES knowledge.destinations(destination_id)
    ON DELETE SET NULL;

CREATE OR REPLACE FUNCTION knowledge.sync_destination_location()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.latitude IS NULL OR NEW.longitude IS NULL THEN
        NEW.location := NULL;
    ELSE
        NEW.location := ST_SetSRID(
            ST_MakePoint(NEW.longitude, NEW.latitude), 4326
        )::GEOGRAPHY;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sync_destination_location ON knowledge.destinations;
CREATE TRIGGER trg_sync_destination_location
BEFORE INSERT OR UPDATE OF latitude, longitude
ON knowledge.destinations
FOR EACH ROW
EXECUTE FUNCTION knowledge.sync_destination_location();

DROP INDEX IF EXISTS knowledge.idx_destinations_geo;
CREATE INDEX IF NOT EXISTS idx_destinations_location_gist
    ON knowledge.destinations USING GIST (location);
CREATE INDEX IF NOT EXISTS idx_destinations_aliases_gin
    ON knowledge.destinations USING GIN (aliases);
CREATE INDEX IF NOT EXISTS idx_destinations_origin_status
    ON knowledge.destinations (record_origin, verification_status, status);
CREATE INDEX IF NOT EXISTS idx_destinations_province_city
    ON knowledge.destinations (province_name, city_name);

-- ---------------------------------------------------------------------------
-- Identity and privacy.
-- Passwords are hashes only; external identity providers can use auth_subject.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS identity.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_subject TEXT UNIQUE,
    email TEXT,
    phone_e164 TEXT,
    display_name TEXT,
    password_hash TEXT,
    account_status TEXT NOT NULL DEFAULT 'active'
        CHECK (account_status IN ('active', 'disabled', 'pending_deletion', 'deleted')),
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (email IS NOT NULL OR phone_e164 IS NOT NULL OR auth_subject IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_ci
    ON identity.users (LOWER(email)) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_status_created
    ON identity.users (account_status, created_at DESC);

CREATE TABLE IF NOT EXISTS identity.user_consents (
    consent_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE CASCADE,
    consent_type TEXT NOT NULL,
    policy_version TEXT NOT NULL,
    is_granted BOOLEAN NOT NULL,
    granted_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    consent_source TEXT NOT NULL DEFAULT 'pwa',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, consent_type, policy_version),
    CHECK (revoked_at IS NULL OR granted_at IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_user_consents_user
    ON identity.user_consents (user_id, consent_type);

CREATE TABLE IF NOT EXISTS identity.user_preferences (
    preference_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE CASCADE,
    preference_key TEXT NOT NULL,
    preference_value JSONB NOT NULL,
    weight NUMERIC(5,4) NOT NULL DEFAULT 0.5 CHECK (weight BETWEEN 0 AND 1),
    confidence NUMERIC(5,4) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    preference_source TEXT NOT NULL DEFAULT 'user_explicit',
    is_long_term BOOLEAN NOT NULL DEFAULT TRUE,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, preference_key)
);
CREATE INDEX IF NOT EXISTS idx_user_preferences_user
    ON identity.user_preferences (user_id, is_long_term);

-- ---------------------------------------------------------------------------
-- Conversation. Conversation context is structured JSON, but user-visible
-- message content remains separate and is not copied into model telemetry.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS conversation.conversations (
    conversation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES identity.users(user_id) ON DELETE SET NULL,
    channel TEXT NOT NULL DEFAULT 'pwa'
        CHECK (channel IN ('pwa', 'web', 'mobile_web', 'admin_test')),
    language_code TEXT NOT NULL DEFAULT 'fa',
    conversation_status TEXT NOT NULL DEFAULT 'active'
        CHECK (conversation_status IN ('active', 'completed', 'archived', 'deleted')),
    structured_context JSONB NOT NULL DEFAULT '{}'::JSONB,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_message_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_conversations_user_started
    ON conversation.conversations (user_id, started_at DESC);

CREATE TABLE IF NOT EXISTS conversation.messages (
    message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversation.conversations(conversation_id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    message_type TEXT NOT NULL DEFAULT 'text'
        CHECK (message_type IN ('text', 'structured', 'tool_call', 'tool_result', 'system_notice')),
    provider_name TEXT,
    model_name TEXT,
    input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
    latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    idempotency_key TEXT,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (conversation_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
    ON conversation.messages (conversation_id, created_at, message_id);

-- ---------------------------------------------------------------------------
-- Travel request, explicit constraints/interests, and editable itinerary.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS travel.trips (
    trip_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES identity.users(user_id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES conversation.conversations(conversation_id) ON DELETE SET NULL,
    trip_title TEXT,
    origin_text TEXT NOT NULL,
    origin_location GEOGRAPHY(Point, 4326),
    start_date DATE,
    end_date DATE,
    duration_days SMALLINT CHECK (duration_days IS NULL OR duration_days BETWEEN 1 AND 30),
    budget_min NUMERIC(14,2),
    budget_max NUMERIC(14,2),
    currency CHAR(3) NOT NULL DEFAULT 'IRR',
    traveler_count SMALLINT NOT NULL DEFAULT 1 CHECK (traveler_count BETWEEN 1 AND 50),
    extracted_requirements JSONB NOT NULL DEFAULT '{}'::JSONB,
    extraction_confidence NUMERIC(5,4) CHECK (extraction_confidence IS NULL OR extraction_confidence BETWEEN 0 AND 1),
    trip_status TEXT NOT NULL DEFAULT 'draft'
        CHECK (trip_status IN ('draft', 'ready', 'planned', 'completed', 'cancelled', 'archived')),
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (end_date IS NULL OR start_date IS NULL OR end_date >= start_date),
    CHECK (budget_min IS NULL OR budget_min >= 0),
    CHECK (budget_max IS NULL OR budget_max >= 0),
    CHECK (budget_min IS NULL OR budget_max IS NULL OR budget_max >= budget_min),
    CHECK (currency ~ '^[A-Z]{3}$')
);
CREATE INDEX IF NOT EXISTS idx_trips_user_created
    ON travel.trips (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trips_status_dates
    ON travel.trips (trip_status, start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_trips_origin_gist
    ON travel.trips USING GIST (origin_location);

CREATE TABLE IF NOT EXISTS travel.trip_constraints (
    constraint_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES travel.trips(trip_id) ON DELETE CASCADE,
    constraint_key TEXT NOT NULL,
    operator TEXT NOT NULL DEFAULT 'equals',
    constraint_value JSONB NOT NULL,
    constraint_strength TEXT NOT NULL DEFAULT 'hard'
        CHECK (constraint_strength IN ('hard', 'soft')),
    weight NUMERIC(5,4) NOT NULL DEFAULT 1.0 CHECK (weight BETWEEN 0 AND 1),
    confidence NUMERIC(5,4) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    source_message_id UUID REFERENCES conversation.messages(message_id) ON DELETE SET NULL,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (trip_id, constraint_key)
);
CREATE INDEX IF NOT EXISTS idx_trip_constraints_trip_strength
    ON travel.trip_constraints (trip_id, constraint_strength);

CREATE TABLE IF NOT EXISTS travel.trip_interests (
    trip_interest_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES travel.trips(trip_id) ON DELETE CASCADE,
    interest_key TEXT NOT NULL,
    weight NUMERIC(5,4) NOT NULL DEFAULT 0.5 CHECK (weight BETWEEN 0 AND 1),
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (trip_id, interest_key)
);
CREATE INDEX IF NOT EXISTS idx_trip_interests_trip
    ON travel.trip_interests (trip_id, is_required DESC, weight DESC);

-- ---------------------------------------------------------------------------
-- Knowledge catalog, source provenance, RAG documents/chunks and replaceable
-- embedding spaces. Embedding dimension is validated by trigger per space.
-- Exact search remains the baseline; ANN indexes are deferred until measured.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS knowledge.destination_categories (
    category_id BIGSERIAL PRIMARY KEY,
    category_key TEXT NOT NULL UNIQUE,
    name_fa TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order SMALLINT NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS knowledge.destination_category_map (
    destination_id BIGINT NOT NULL REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE,
    category_id BIGINT NOT NULL REFERENCES knowledge.destination_categories(category_id) ON DELETE RESTRICT,
    mapping_source TEXT NOT NULL DEFAULT 'curated',
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (destination_id, category_id)
);
CREATE INDEX IF NOT EXISTS idx_destination_category_map_category
    ON knowledge.destination_category_map (category_id, destination_id);

CREATE TABLE IF NOT EXISTS knowledge.knowledge_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_key TEXT NOT NULL UNIQUE,
    source_id BIGINT NOT NULL REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT,
    destination_id BIGINT REFERENCES knowledge.destinations(destination_id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    language_code TEXT NOT NULL DEFAULT 'fa',
    document_type TEXT NOT NULL DEFAULT 'destination_profile',
    canonical_url TEXT,
    raw_content TEXT NOT NULL,
    content_sha256 CHAR(64) NOT NULL,
    ingestion_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (ingestion_status IN ('pending', 'processed', 'failed', 'stale', 'test_only')),
    record_origin TEXT NOT NULL
        CHECK (record_origin IN ('user_supplied_unverified', 'verified_external', 'synthetic_fixture')),
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    retrieved_at TIMESTAMPTZ,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (is_synthetic = (record_origin = 'synthetic_fixture')),
    CHECK (valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_source_status
    ON knowledge.knowledge_documents (source_id, ingestion_status);
CREATE INDEX IF NOT EXISTS idx_knowledge_documents_destination
    ON knowledge.knowledge_documents (destination_id);

CREATE TABLE IF NOT EXISTS knowledge.knowledge_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES knowledge.knowledge_documents(document_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    content TEXT NOT NULL,
    char_count INTEGER NOT NULL CHECK (char_count >= 0),
    token_count INTEGER CHECK (token_count IS NULL OR token_count >= 0),
    content_sha256 CHAR(64) NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (document_id, chunk_index)
);
CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_document
    ON knowledge.knowledge_chunks (document_id, chunk_index);

CREATE TABLE IF NOT EXISTS knowledge.embedding_spaces (
    embedding_space_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    space_key TEXT NOT NULL UNIQUE,
    provider_type TEXT NOT NULL CHECK (provider_type IN ('local', 'remote', 'test')),
    provider_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_revision TEXT NOT NULL DEFAULT 'unspecified',
    vector_dimension SMALLINT NOT NULL CHECK (vector_dimension BETWEEN 1 AND 16000),
    similarity_metric TEXT NOT NULL DEFAULT 'cosine'
        CHECK (similarity_metric IN ('cosine', 'l2', 'inner_product')),
    preprocessing_version TEXT NOT NULL DEFAULT 'v1',
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    lifecycle_status TEXT NOT NULL DEFAULT 'candidate'
        CHECK (lifecycle_status IN ('candidate', 'active', 'retired', 'test_only')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider_type, provider_name, model_name, model_revision, vector_dimension, preprocessing_version)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_one_active_embedding_space
    ON knowledge.embedding_spaces (is_active)
    WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS knowledge.chunk_embeddings (
    chunk_embedding_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id UUID NOT NULL REFERENCES knowledge.knowledge_chunks(chunk_id) ON DELETE CASCADE,
    embedding_space_id UUID NOT NULL REFERENCES knowledge.embedding_spaces(embedding_space_id) ON DELETE CASCADE,
    embedding VECTOR NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (chunk_id, embedding_space_id)
);
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_space_chunk
    ON knowledge.chunk_embeddings (embedding_space_id, chunk_id);

CREATE OR REPLACE FUNCTION knowledge.enforce_chunk_embedding_dimension()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    expected_dimension SMALLINT;
BEGIN
    SELECT vector_dimension
      INTO expected_dimension
      FROM knowledge.embedding_spaces
     WHERE embedding_space_id = NEW.embedding_space_id;

    IF expected_dimension IS NULL THEN
        RAISE EXCEPTION 'Embedding space % does not exist', NEW.embedding_space_id
            USING ERRCODE = '23503';
    END IF;

    IF vector_dims(NEW.embedding) <> expected_dimension THEN
        RAISE EXCEPTION 'Embedding dimension mismatch: expected %, got %',
            expected_dimension, vector_dims(NEW.embedding)
            USING ERRCODE = '23514';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_enforce_chunk_embedding_dimension ON knowledge.chunk_embeddings;
CREATE TRIGGER trg_enforce_chunk_embedding_dimension
BEFORE INSERT OR UPDATE OF embedding, embedding_space_id
ON knowledge.chunk_embeddings
FOR EACH ROW
EXECUTE FUNCTION knowledge.enforce_chunk_embedding_dimension();

-- ---------------------------------------------------------------------------
-- Recommendations and explainability evidence. Hard constraints stay outside
-- LLM authority and are enforced by application decision logic.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS recommendation.recommendation_requests (
    recommendation_request_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES travel.trips(trip_id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversation.conversations(conversation_id) ON DELETE SET NULL,
    algorithm_version TEXT NOT NULL,
    retrieval_version TEXT,
    input_snapshot JSONB NOT NULL DEFAULT '{}'::JSONB,
    request_status TEXT NOT NULL DEFAULT 'created'
        CHECK (request_status IN ('created', 'processing', 'completed', 'failed', 'cancelled')),
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_recommendation_requests_trip_created
    ON recommendation.recommendation_requests (trip_id, created_at DESC);

CREATE TABLE IF NOT EXISTS recommendation.recommendations (
    recommendation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_request_id UUID NOT NULL REFERENCES recommendation.recommendation_requests(recommendation_request_id) ON DELETE CASCADE,
    destination_id BIGINT NOT NULL REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT,
    rank SMALLINT NOT NULL CHECK (rank > 0),
    final_score NUMERIC(7,6) NOT NULL CHECK (final_score BETWEEN 0 AND 1),
    confidence NUMERIC(5,4) CHECK (confidence IS NULL OR confidence BETWEEN 0 AND 1),
    explanation_fa TEXT NOT NULL,
    warnings JSONB NOT NULL DEFAULT '[]'::JSONB,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (recommendation_request_id, destination_id),
    UNIQUE (recommendation_request_id, rank)
);
CREATE INDEX IF NOT EXISTS idx_recommendations_request_rank
    ON recommendation.recommendations (recommendation_request_id, rank);

CREATE TABLE IF NOT EXISTS recommendation.recommendation_score_components (
    score_component_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recommendation_id UUID NOT NULL REFERENCES recommendation.recommendations(recommendation_id) ON DELETE CASCADE,
    component_key TEXT NOT NULL,
    raw_score NUMERIC(12,6),
    normalized_score NUMERIC(7,6) CHECK (normalized_score IS NULL OR normalized_score BETWEEN 0 AND 1),
    weight NUMERIC(7,6) NOT NULL CHECK (weight BETWEEN 0 AND 1),
    weighted_score NUMERIC(12,6) NOT NULL,
    component_reason TEXT,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (recommendation_id, component_key)
);
CREATE INDEX IF NOT EXISTS idx_score_components_recommendation
    ON recommendation.recommendation_score_components (recommendation_id);

-- ---------------------------------------------------------------------------
-- Itinerary MVP: editable 1-3 day plan, without booking/payment transactions.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS travel.itineraries (
    itinerary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL REFERENCES travel.trips(trip_id) ON DELETE CASCADE,
    recommendation_request_id UUID REFERENCES recommendation.recommendation_requests(recommendation_request_id) ON DELETE SET NULL,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version > 0),
    title TEXT NOT NULL,
    day_count SMALLINT NOT NULL CHECK (day_count BETWEEN 1 AND 3),
    itinerary_status TEXT NOT NULL DEFAULT 'draft'
        CHECK (itinerary_status IN ('draft', 'presented', 'accepted', 'edited', 'archived')),
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (trip_id, version)
);
CREATE INDEX IF NOT EXISTS idx_itineraries_trip_version
    ON travel.itineraries (trip_id, version DESC);

CREATE TABLE IF NOT EXISTS travel.itinerary_stops (
    itinerary_stop_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    itinerary_id UUID NOT NULL REFERENCES travel.itineraries(itinerary_id) ON DELETE CASCADE,
    destination_id BIGINT NOT NULL REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT,
    day_number SMALLINT NOT NULL CHECK (day_number BETWEEN 1 AND 3),
    stop_order SMALLINT NOT NULL CHECK (stop_order > 0),
    planned_start_time TIME,
    duration_minutes SMALLINT CHECK (duration_minutes IS NULL OR duration_minutes BETWEEN 1 AND 1440),
    travel_to_next_estimate_minutes SMALLINT CHECK (travel_to_next_estimate_minutes IS NULL OR travel_to_next_estimate_minutes >= 0),
    notes_fa TEXT,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (itinerary_id, day_number, stop_order)
);
CREATE INDEX IF NOT EXISTS idx_itinerary_stops_itinerary_day
    ON travel.itinerary_stops (itinerary_id, day_number, stop_order);

-- ---------------------------------------------------------------------------
-- External booking redirects only. There are deliberately no booking,
-- payment, refund, ticket or reservation transaction tables in MVP.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS integration.external_links (
    external_link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    destination_id BIGINT REFERENCES knowledge.destinations(destination_id) ON DELETE SET NULL,
    provider_name TEXT NOT NULL,
    service_type TEXT NOT NULL
        CHECK (service_type IN ('hotel', 'flight', 'train', 'tour', 'car_rental', 'official_info', 'other')),
    label_fa TEXT NOT NULL,
    target_url TEXT NOT NULL CHECK (target_url ~ '^https?://'),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_external_links_destination_service
    ON integration.external_links (destination_id, service_type, is_active);

CREATE TABLE IF NOT EXISTS integration.outbound_clicks (
    outbound_click_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_link_id UUID NOT NULL REFERENCES integration.external_links(external_link_id) ON DELETE RESTRICT,
    user_id UUID REFERENCES identity.users(user_id) ON DELETE SET NULL,
    trip_id UUID REFERENCES travel.trips(trip_id) ON DELETE SET NULL,
    recommendation_id UUID REFERENCES recommendation.recommendations(recommendation_id) ON DELETE SET NULL,
    session_id UUID,
    clicked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE INDEX IF NOT EXISTS idx_outbound_clicks_link_time
    ON integration.outbound_clicks (external_link_id, clicked_at DESC);

-- ---------------------------------------------------------------------------
-- Feedback and operational observability. Do not store raw API keys, full
-- prompts, payment details, or unnecessary sensitive user payloads here.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS operations.feedback (
    feedback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES identity.users(user_id) ON DELETE SET NULL,
    conversation_id UUID REFERENCES conversation.conversations(conversation_id) ON DELETE SET NULL,
    trip_id UUID REFERENCES travel.trips(trip_id) ON DELETE SET NULL,
    recommendation_id UUID REFERENCES recommendation.recommendations(recommendation_id) ON DELETE SET NULL,
    feedback_type TEXT NOT NULL
        CHECK (feedback_type IN ('recommendation_rating', 'answer_quality', 'itinerary_quality', 'bug_report', 'other')),
    rating SMALLINT CHECK (rating IS NULL OR rating BETWEEN 1 AND 5),
    comment TEXT,
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (user_id IS NOT NULL OR conversation_id IS NOT NULL OR trip_id IS NOT NULL OR recommendation_id IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_feedback_type_created
    ON operations.feedback (feedback_type, created_at DESC);

CREATE TABLE IF NOT EXISTS operations.ai_model_calls (
    ai_model_call_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    correlation_id UUID,
    provider_name TEXT NOT NULL,
    model_name TEXT NOT NULL,
    task_type TEXT NOT NULL,
    call_status TEXT NOT NULL
        CHECK (call_status IN ('success', 'timeout', 'rate_limited', 'provider_error', 'validation_error')),
    input_tokens INTEGER CHECK (input_tokens IS NULL OR input_tokens >= 0),
    output_tokens INTEGER CHECK (output_tokens IS NULL OR output_tokens >= 0),
    latency_ms INTEGER CHECK (latency_ms IS NULL OR latency_ms >= 0),
    estimated_cost NUMERIC(14,8) CHECK (estimated_cost IS NULL OR estimated_cost >= 0),
    cost_currency CHAR(3),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ai_model_calls_provider_created
    ON operations.ai_model_calls (provider_name, created_at DESC);

CREATE TABLE IF NOT EXISTS operations.audit_events (
    audit_event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID REFERENCES identity.users(user_id) ON DELETE SET NULL,
    actor_type TEXT NOT NULL DEFAULT 'user'
        CHECK (actor_type IN ('user', 'system', 'administrator', 'service')),
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    correlation_id UUID,
    metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_audit_events_resource_time
    ON operations.audit_events (resource_type, resource_id, created_at DESC);

CREATE TABLE IF NOT EXISTS operations.dataset_import_batches (
    dataset_import_batch_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_key TEXT NOT NULL UNIQUE,
    data_class TEXT NOT NULL
        CHECK (data_class IN ('verified_external', 'user_supplied_unverified', 'synthetic_fixture')),
    source_id BIGINT REFERENCES knowledge.knowledge_sources(source_id) ON DELETE SET NULL,
    record_counts JSONB NOT NULL DEFAULT '{}'::JSONB,
    source_checksum CHAR(64),
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes TEXT
);

-- Make sure the original 15 records get stable, explicit provenance labels.
UPDATE knowledge.destinations
SET record_origin = 'user_supplied_unverified',
    verification_status = 'pending',
    is_synthetic = FALSE,
    status = 'needs_review'
WHERE destination_key LIKE 'legacy-%';

-- Explicit publication/retrieval gates. Application production queries should
-- use these views rather than querying raw catalogue/document tables directly.
CREATE OR REPLACE VIEW knowledge.production_destinations AS
SELECT d.*
FROM knowledge.destinations d
WHERE d.status = 'active'
  AND d.verification_status = 'verified'
  AND d.location IS NOT NULL
  AND d.coordinate_role <> 'unknown'
  AND d.record_origin = 'verified_external'
  AND d.is_synthetic = FALSE
  AND EXISTS (
      SELECT 1
      FROM knowledge.destination_sources ds
      JOIN knowledge.knowledge_sources s ON s.source_id = ds.source_id
      WHERE ds.destination_id = d.destination_id
        AND s.verification_status = 'verified'
        AND s.is_synthetic = FALSE
        AND (ds.valid_from IS NULL OR ds.valid_from <= NOW())
        AND (ds.valid_until IS NULL OR ds.valid_until >= NOW())
  );

CREATE OR REPLACE VIEW knowledge.production_destination_sources AS
SELECT ds.destination_id, ds.source_id, ds.source_role, ds.evidence_note,
       ds.retrieved_at, ds.valid_from, ds.valid_until,
       s.source_name, s.source_type, s.url AS source_url,
       s.reliability_score
FROM knowledge.destination_sources ds
JOIN knowledge.production_destinations d ON d.destination_id = ds.destination_id
JOIN knowledge.knowledge_sources s ON s.source_id = ds.source_id
WHERE s.verification_status = 'verified'
  AND s.is_synthetic = FALSE
  AND (ds.valid_from IS NULL OR ds.valid_from <= NOW())
  AND (ds.valid_until IS NULL OR ds.valid_until >= NOW());

CREATE OR REPLACE VIEW knowledge.production_destination_categories AS
SELECT c.category_id, c.category_key, c.name_fa, c.description, c.sort_order
FROM knowledge.destination_categories c
WHERE c.is_active = TRUE
  AND EXISTS (
      SELECT 1
      FROM knowledge.destination_category_map m
      JOIN knowledge.production_destinations d ON d.destination_id = m.destination_id
      WHERE m.category_id = c.category_id AND m.is_synthetic = FALSE
  );

CREATE OR REPLACE VIEW knowledge.production_destination_category_map AS
SELECT m.destination_id, m.category_id, m.mapping_source, m.created_at
FROM knowledge.destination_category_map m
JOIN knowledge.production_destinations d ON d.destination_id = m.destination_id
JOIN knowledge.production_destination_categories c ON c.category_id = m.category_id
WHERE m.is_synthetic = FALSE;

CREATE OR REPLACE VIEW knowledge.production_destination_tags AS
SELECT t.destination_id, t.tag
FROM knowledge.destination_tags t
JOIN knowledge.production_destinations d ON d.destination_id = t.destination_id;

CREATE OR REPLACE VIEW knowledge.production_retrieval_documents AS
SELECT d.*,
       s.source_name AS provenance_source_name,
       s.source_type AS provenance_source_type,
       s.url AS provenance_source_url,
       s.reliability_score AS provenance_reliability_score
FROM knowledge.knowledge_documents d
JOIN knowledge.knowledge_sources s ON s.source_id = d.source_id
WHERE d.ingestion_status = 'processed'
  AND d.record_origin = 'verified_external'
  AND d.is_synthetic = FALSE
  AND s.verification_status = 'verified'
  AND s.is_synthetic = FALSE
  AND (d.valid_from IS NULL OR d.valid_from <= NOW())
  AND (d.valid_until IS NULL OR d.valid_until >= NOW())
  AND (
      d.destination_id IS NULL
      OR EXISTS (
          SELECT 1
          FROM knowledge.production_destinations pd
          WHERE pd.destination_id = d.destination_id
      )
  );

CREATE OR REPLACE VIEW knowledge.production_retrieval_chunks AS
SELECT c.chunk_id, c.document_id, d.destination_id,
       d.document_key, d.title, d.language_code, d.document_type,
       d.canonical_url, d.provenance_source_name, d.provenance_source_type,
       d.provenance_source_url, d.provenance_reliability_score,
       c.chunk_index, c.content, c.char_count, c.token_count,
       c.content_sha256, c.metadata, c.created_at
FROM knowledge.knowledge_chunks c
JOIN knowledge.production_retrieval_documents d ON d.document_id = c.document_id
WHERE c.is_synthetic = FALSE;

CREATE OR REPLACE VIEW knowledge.active_embedding_spaces AS
SELECT embedding_space_id, space_key, provider_type, provider_name,
       model_name, model_revision, vector_dimension, similarity_metric,
       preprocessing_version, lifecycle_status, created_at
FROM knowledge.embedding_spaces
WHERE is_active = TRUE AND lifecycle_status = 'active';

CREATE OR REPLACE VIEW knowledge.production_chunk_embeddings AS
SELECT e.chunk_embedding_id, e.chunk_id, e.embedding_space_id,
       s.space_key, s.provider_type, s.provider_name, s.model_name,
       s.model_revision, s.vector_dimension, s.similarity_metric,
       s.preprocessing_version, e.embedding, e.created_at, e.updated_at
FROM knowledge.chunk_embeddings e
JOIN knowledge.production_retrieval_chunks c ON c.chunk_id = e.chunk_id
JOIN knowledge.active_embedding_spaces s ON s.embedding_space_id = e.embedding_space_id;

INSERT INTO system.schema_migrations (migration_id, sha256)
VALUES ('0001_core_schema', :'migration_hash')
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;
