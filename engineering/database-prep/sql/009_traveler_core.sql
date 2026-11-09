\set ON_ERROR_STOP on

-- Task 3.0 traveler persistence contract.  This migration is additive: old
-- fixture rows retain their existing values and the 0000-0008 files remain
-- immutable.  Runtime traveler content is always written with a server-derived
-- user_id; the nullable legacy columns are retained for historical fixtures.
BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM system.schema_migrations
        WHERE migration_id='0008_authentication_foundation'
    ) THEN
        RAISE EXCEPTION 'Migration 0009 requires Migration 0008 authentication foundation';
    END IF;
END $$;

-- Conversation and trip optimistic concurrency plus create retry keys.
ALTER TABLE conversation.conversations
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1
        CHECK (version > 0),
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ADD COLUMN IF NOT EXISTS create_idempotency_key TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_conversations_owner_create_key
    ON conversation.conversations (user_id, create_idempotency_key)
    WHERE user_id IS NOT NULL AND create_idempotency_key IS NOT NULL;

ALTER TABLE travel.trips
    ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1
        CHECK (version > 0),
    ADD COLUMN IF NOT EXISTS create_idempotency_key TEXT,
    ADD COLUMN IF NOT EXISTS confirmed_requirements JSONB NOT NULL DEFAULT '{}'::JSONB,
    ADD COLUMN IF NOT EXISTS budget_amount_original NUMERIC(20,4),
    ADD COLUMN IF NOT EXISTS budget_currency_iso CHAR(3),
    ADD COLUMN IF NOT EXISTS budget_unit TEXT,
    ADD COLUMN IF NOT EXISTS budget_raw_text TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_trips_owner_create_key
    ON travel.trips (user_id, create_idempotency_key)
    WHERE user_id IS NOT NULL AND create_idempotency_key IS NOT NULL;

ALTER TABLE travel.trips ALTER COLUMN origin_text DROP NOT NULL;
ALTER TABLE travel.trips ALTER COLUMN traveler_count DROP NOT NULL;
ALTER TABLE travel.trips ALTER COLUMN traveler_count DROP DEFAULT;
ALTER TABLE travel.trips DROP CONSTRAINT IF EXISTS trips_duration_days_check;
ALTER TABLE travel.trips
    ADD CONSTRAINT trips_duration_days_365_check
        CHECK (duration_days IS NULL OR duration_days BETWEEN 1 AND 365),
    ADD CONSTRAINT trips_traveler_count_nullable_check
        CHECK (traveler_count IS NULL OR traveler_count BETWEEN 1 AND 50),
    ADD CONSTRAINT trips_budget_original_complete_check CHECK (
        (budget_amount_original IS NULL AND budget_currency_iso IS NULL AND budget_unit IS NULL AND budget_raw_text IS NULL)
        OR
        (budget_amount_original IS NOT NULL AND budget_currency_iso IS NOT NULL
            AND budget_currency_iso = 'IRR' AND budget_unit IS NOT NULL
            AND budget_unit IN ('rial', 'toman') AND budget_raw_text IS NOT NULL
            AND budget_amount_original >= 0)
    );

-- A persisted message is attached to the trip whose request it records. This
-- lets a trip be deleted without retaining its raw text in conversation history.
ALTER TABLE conversation.messages
    ADD COLUMN IF NOT EXISTS trip_id UUID
        REFERENCES travel.trips(trip_id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_messages_trip_created
    ON conversation.messages (trip_id, created_at, message_id)
    WHERE trip_id IS NOT NULL;

-- `version` remains the itinerary generation number (unique per trip).
-- `revision` is the optimistic edit token for that itinerary row.
ALTER TABLE travel.itineraries
    ADD COLUMN IF NOT EXISTS revision INTEGER NOT NULL DEFAULT 1
        CHECK (revision > 0),
    ADD COLUMN IF NOT EXISTS title_by_locale JSONB NOT NULL DEFAULT '{}'::JSONB
        CHECK (jsonb_typeof(title_by_locale) = 'object');

ALTER TABLE travel.itinerary_stops
    ADD COLUMN IF NOT EXISTS notes_by_locale JSONB NOT NULL DEFAULT '{}'::JSONB
        CHECK (jsonb_typeof(notes_by_locale) = 'object'),
    ADD COLUMN IF NOT EXISTS recommendation_id UUID
        REFERENCES recommendation.recommendations(recommendation_id) ON DELETE CASCADE;

ALTER TABLE recommendation.recommendations
    ADD COLUMN IF NOT EXISTS evidence JSONB NOT NULL DEFAULT '[]'::JSONB
        CHECK (jsonb_typeof(evidence) = 'array'),
    ADD COLUMN IF NOT EXISTS explanation_by_locale JSONB NOT NULL DEFAULT '{}'::JSONB
        CHECK (jsonb_typeof(explanation_by_locale) = 'object');

-- Owner deletion and explicit trip/conversation deletion remove user content.
-- The raw historical seed is synthetic and is not deleted by these actions.
ALTER TABLE conversation.conversations
    DROP CONSTRAINT IF EXISTS conversations_user_id_fkey;
ALTER TABLE conversation.conversations
    ADD CONSTRAINT conversations_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE;

ALTER TABLE travel.trips
    DROP CONSTRAINT IF EXISTS trips_user_id_fkey,
    DROP CONSTRAINT IF EXISTS trips_conversation_id_fkey;
ALTER TABLE travel.trips
    ADD CONSTRAINT trips_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE,
    ADD CONSTRAINT trips_conversation_id_fkey
        FOREIGN KEY (conversation_id) REFERENCES conversation.conversations(conversation_id) ON DELETE CASCADE;

-- Free-text feedback and click associations can contain personal context or
-- be linked to a deleted trip. Remove them with the associated user content.
ALTER TABLE operations.feedback
    DROP CONSTRAINT IF EXISTS feedback_user_id_fkey,
    DROP CONSTRAINT IF EXISTS feedback_conversation_id_fkey,
    DROP CONSTRAINT IF EXISTS feedback_trip_id_fkey,
    DROP CONSTRAINT IF EXISTS feedback_recommendation_id_fkey;
ALTER TABLE operations.feedback
    ADD CONSTRAINT feedback_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE,
    ADD CONSTRAINT feedback_conversation_id_fkey
        FOREIGN KEY (conversation_id) REFERENCES conversation.conversations(conversation_id) ON DELETE CASCADE,
    ADD CONSTRAINT feedback_trip_id_fkey
        FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE,
    ADD CONSTRAINT feedback_recommendation_id_fkey
        FOREIGN KEY (recommendation_id) REFERENCES recommendation.recommendations(recommendation_id) ON DELETE CASCADE;

ALTER TABLE integration.outbound_clicks
    DROP CONSTRAINT IF EXISTS outbound_clicks_user_id_fkey,
    DROP CONSTRAINT IF EXISTS outbound_clicks_trip_id_fkey;
ALTER TABLE integration.outbound_clicks
    ADD CONSTRAINT outbound_clicks_user_id_fkey
        FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE,
    ADD CONSTRAINT outbound_clicks_trip_id_fkey
        FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE;

INSERT INTO system.schema_migrations (migration_id, sha256)
VALUES ('0009_traveler_core', :'migration_hash')
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;
