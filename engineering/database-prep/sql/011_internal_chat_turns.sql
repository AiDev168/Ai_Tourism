\set ON_ERROR_STOP on
-- Additive, owner-scoped development Chat reservation and bounded invocation ledger.
-- Apply ONLY to an isolated, approved development/test database.
BEGIN;
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM system.schema_migrations
                 WHERE migration_id='0010_task31_content_privacy_full_itinerary') THEN
    RAISE EXCEPTION 'Migration 0011 requires 0010';
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS integration.chat_daily_user_budget (
  user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE CASCADE,
  budget_day DATE NOT NULL,
  hit_count INTEGER NOT NULL CHECK (hit_count BETWEEN 1 AND 1000),
  PRIMARY KEY (user_id,budget_day)
);
CREATE TABLE IF NOT EXISTS integration.chat_daily_global_budget (
  budget_day DATE PRIMARY KEY,
  hit_count INTEGER NOT NULL CHECK (hit_count BETWEEN 1 AND 100000)
);
CREATE TABLE IF NOT EXISTS conversation.assistant_turns (
  turn_id UUID PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE CASCADE,
  conversation_id UUID NOT NULL REFERENCES conversation.conversations(conversation_id) ON DELETE CASCADE,
  trip_id UUID NOT NULL REFERENCES travel.trips(trip_id) ON DELETE CASCADE,
  idempotency_key TEXT NOT NULL CHECK (length(idempotency_key) BETWEEN 8 AND 128),
  content_sha256 BYTEA NOT NULL CHECK (octet_length(content_sha256)=32),
  status TEXT NOT NULL CHECK (status IN ('reserved','completed','failed')),
  user_message_id UUID NOT NULL REFERENCES conversation.messages(message_id) ON DELETE CASCADE,
  assistant_message_id UUID REFERENCES conversation.messages(message_id) ON DELETE CASCADE,
  consented_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (conversation_id,idempotency_key),
  CHECK ((status='completed')=(assistant_message_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_assistant_turns_owner_trip
  ON conversation.assistant_turns(user_id,trip_id,created_at DESC);
GRANT SELECT,INSERT,UPDATE,DELETE ON
  integration.chat_daily_user_budget, integration.chat_daily_global_budget,
  conversation.assistant_turns TO ai_tourism_app;
INSERT INTO system.schema_migrations (migration_id,sha256)
VALUES ('0011_internal_chat_turns', :'migration_hash')
ON CONFLICT (migration_id) DO NOTHING;
COMMIT;
