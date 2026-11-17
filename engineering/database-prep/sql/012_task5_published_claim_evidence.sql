\set ON_ERROR_STOP on
-- Adds an explicit, review-gated spatial claim -> document/chunk -> source
-- identity relation for the owner-RAG boundary. No row is inserted or approved
-- by this migration. The application can read only the filtered view.
BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (
      SELECT 1 FROM system.schema_migrations
      WHERE migration_id='0011_internal_chat_turns'
  ) THEN
    RAISE EXCEPTION 'Migration 0012 requires 0011_internal_chat_turns';
  END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_knowledge_chunks_chunk_document
    ON knowledge.knowledge_chunks (chunk_id, document_id);

CREATE TABLE knowledge.destination_claim_evidence (
    claim_evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    destination_id BIGINT NOT NULL
        REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE,
    document_id UUID NOT NULL
        REFERENCES knowledge.knowledge_documents(document_id) ON DELETE CASCADE,
    chunk_id UUID NOT NULL,
    claim_key TEXT NOT NULL CHECK (length(btrim(claim_key)) BETWEEN 1 AND 240),
    locale TEXT NOT NULL CHECK (locale IN ('fa-IR', 'en-US', 'ar')),
    corpus TEXT NOT NULL DEFAULT 'spatial_destinations'
        CHECK (corpus = 'spatial_destinations'),
    content_hash CHAR(64) NOT NULL
        CHECK (content_hash ~ '^[0-9a-f]{64}$'),
    source_id BIGINT NOT NULL
        REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT,
    source_name TEXT NOT NULL CHECK (length(btrim(source_name)) BETWEEN 1 AND 500),
    source_url TEXT NOT NULL CHECK (source_url ~ '^https://[^[:space:]]+$'),
    source_role TEXT NOT NULL CHECK (length(btrim(source_role)) BETWEEN 1 AND 64),
    source_license TEXT,
    retrieved_at TIMESTAMPTZ,
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    review_status TEXT NOT NULL DEFAULT 'needs_review'
        CHECK (review_status IN ('needs_review', 'approved', 'rejected')),
    verification_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (verification_status IN ('pending', 'verified', 'revoked')),
    is_synthetic BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (chunk_id, claim_key, locale, source_id),
    FOREIGN KEY (chunk_id, document_id)
        REFERENCES knowledge.knowledge_chunks(chunk_id, document_id) ON DELETE CASCADE,
    CHECK (valid_until IS NULL OR valid_from IS NULL OR valid_until >= valid_from),
    CHECK ((review_status = 'approved') = (published_at IS NOT NULL)),
    CHECK (review_status <> 'approved' OR (verification_status = 'verified' AND is_synthetic = FALSE)),
    CHECK ((verification_status = 'revoked') = (revoked_at IS NOT NULL))
);
CREATE INDEX idx_destination_claim_evidence_identity
    ON knowledge.destination_claim_evidence(destination_id, document_id, claim_key, locale);
CREATE INDEX idx_destination_claim_evidence_review
    ON knowledge.destination_claim_evidence(review_status, verification_status, valid_until);

CREATE OR REPLACE VIEW knowledge.production_destination_claim_evidence AS
SELECT
    pd.destination_key AS canonical_entity_key,
    ce.destination_id,
    ce.document_id::TEXT AS document_id,
    ce.chunk_id::TEXT AS chunk_id,
    ce.claim_key,
    ce.content_hash::TEXT AS content_hash,
    ce.locale,
    ce.corpus,
    ce.valid_from,
    ce.valid_until,
    (ce.review_status = 'approved' AND ce.published_at IS NOT NULL) AS is_published,
    (pd.verification_status = 'verified' AND pd.is_synthetic = FALSE) AS is_destination_verified,
    (rd.ingestion_status = 'processed' AND rd.record_origin = 'verified_external') AS is_document_processed,
    (ce.is_synthetic OR rd.is_synthetic OR pd.is_synthetic) AS is_synthetic,
    (ce.verification_status = 'revoked' OR ce.revoked_at IS NOT NULL
        OR ks.verification_status <> 'verified' OR ks.is_synthetic) AS is_revoked,
    ce.source_id::TEXT AS source_id,
    ce.source_name,
    ce.source_url,
    ce.source_role,
    ce.source_license AS license,
    ce.retrieved_at,
    ce.valid_from AS source_valid_from,
    ce.valid_until AS source_valid_until,
    (ks.verification_status = 'verified') AS is_source_verified,
    ks.is_synthetic AS is_source_synthetic,
    (ks.verification_status <> 'verified') AS is_source_revoked
FROM knowledge.destination_claim_evidence ce
JOIN knowledge.production_destinations pd
  ON pd.destination_id = ce.destination_id
JOIN knowledge.production_retrieval_documents rd
  ON rd.document_id = ce.document_id
 AND rd.destination_id = ce.destination_id
JOIN knowledge.production_retrieval_chunks rc
  ON rc.chunk_id = ce.chunk_id
 AND rc.document_id = ce.document_id
 AND rc.destination_id = ce.destination_id
JOIN knowledge.production_destination_sources pds
  ON pds.destination_id = ce.destination_id
 AND pds.source_id = ce.source_id
JOIN knowledge.knowledge_sources ks
  ON ks.source_id = ce.source_id
WHERE ce.review_status = 'approved'
  AND ce.verification_status = 'verified'
  AND ce.is_synthetic = FALSE
  AND ce.revoked_at IS NULL
  AND ce.content_hash = rc.content_sha256
  AND ce.content_hash = encode(sha256(convert_to(rc.content, 'UTF8')), 'hex')
  AND ce.source_name = pds.source_name
  AND ce.source_url = pds.source_url
  AND ce.source_role = pds.source_role
  AND ce.retrieved_at IS NOT DISTINCT FROM pds.retrieved_at
  AND ce.valid_from IS NOT DISTINCT FROM pds.valid_from
  AND ce.valid_until IS NOT DISTINCT FROM pds.valid_until
  AND CASE ce.locale
        WHEN 'fa-IR' THEN rd.language_code IN ('fa', 'fa-IR')
        WHEN 'en-US' THEN rd.language_code IN ('en', 'en-US')
        WHEN 'ar' THEN rd.language_code = 'ar'
      END
  AND (ce.valid_from IS NULL OR ce.valid_from <= NOW())
  AND (ce.valid_until IS NULL OR ce.valid_until >= NOW());

REVOKE ALL ON knowledge.destination_claim_evidence FROM ai_tourism_app;
GRANT SELECT ON knowledge.production_destination_claim_evidence TO ai_tourism_app;

INSERT INTO system.schema_migrations (migration_id, sha256)
VALUES ('0012_task5_published_claim_evidence', :'migration_hash')
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;
