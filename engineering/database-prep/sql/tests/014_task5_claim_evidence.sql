\set ON_ERROR_STOP on
BEGIN;

DO $$
DECLARE
    before_count BIGINT;
    after_count BIGINT;
    fixture_count INTEGER;
    v_destination BIGINT;
    v_document UUID;
    v_chunk UUID;
    v_source BIGINT;
    v_role TEXT;
    v_name TEXT;
    v_url TEXT;
    v_retrieved TIMESTAMPTZ;
    v_from TIMESTAMPTZ;
    v_until TIMESTAMPTZ;
BEGIN
    IF (SELECT COUNT(*) FROM system.schema_migrations
        WHERE migration_id='0012_task5_published_claim_evidence') <> 1 THEN
        RAISE EXCEPTION 'Migration 0012 must be recorded exactly once';
    END IF;

    IF has_table_privilege('ai_tourism_app',
           'knowledge.destination_claim_evidence', 'SELECT')
       OR has_table_privilege('ai_tourism_app',
           'knowledge.destination_claim_evidence', 'INSERT')
       OR has_table_privilege('ai_tourism_app',
           'knowledge.destination_claim_evidence', 'UPDATE')
       OR NOT has_table_privilege('ai_tourism_app',
           'knowledge.production_destination_claim_evidence', 'SELECT') THEN
        RAISE EXCEPTION 'Application role must read only the approved claim evidence view';
    END IF;

    IF EXISTS (
        SELECT 1 FROM knowledge.production_destination_claim_evidence
        WHERE is_published IS DISTINCT FROM TRUE
           OR is_destination_verified IS DISTINCT FROM TRUE
           OR is_document_processed IS DISTINCT FROM TRUE
           OR is_synthetic IS DISTINCT FROM FALSE
           OR is_revoked IS DISTINCT FROM FALSE
           OR is_source_verified IS DISTINCT FROM TRUE
           OR is_source_synthetic IS DISTINCT FROM FALSE
           OR is_source_revoked IS DISTINCT FROM FALSE
           OR content_hash !~ '^[0-9a-f]{64}$'
           OR source_url !~ '^https://') THEN
        RAISE EXCEPTION 'Production claim evidence exposed unapproved or malformed metadata';
    END IF;

    SELECT COUNT(*) INTO before_count
    FROM knowledge.production_destination_claim_evidence;

    -- Exercise the pending/non-publishable path using an existing row only as
    -- a relational FK target. This fixture is synthetic and must stay invisible.
    SELECT d.destination_id, kd.document_id, c.chunk_id, ks.source_id,
           ds.source_role, ks.source_name, ks.url, ds.retrieved_at,
           ds.valid_from, ds.valid_until
      INTO v_destination, v_document, v_chunk, v_source, v_role, v_name, v_url,
           v_retrieved, v_from, v_until
      FROM knowledge.destinations d
      JOIN knowledge.knowledge_documents kd ON kd.destination_id=d.destination_id
      JOIN knowledge.knowledge_chunks c ON c.document_id=kd.document_id
      JOIN knowledge.destination_sources ds ON ds.destination_id=d.destination_id
      JOIN knowledge.knowledge_sources ks ON ks.source_id=ds.source_id
     WHERE ks.url LIKE 'https://%'
       AND kd.language_code IN ('fa', 'fa-IR')
     ORDER BY kd.document_id, c.chunk_id, ks.source_id
     LIMIT 1;

    IF v_destination IS NOT NULL THEN
        INSERT INTO knowledge.destination_claim_evidence (
            destination_id, document_id, chunk_id, claim_key, locale, content_hash,
            source_id, source_name, source_url, source_role, retrieved_at,
            valid_from, valid_until, review_status, verification_status, is_synthetic
        )
        SELECT v_destination, v_document, v_chunk, 'sql-test-only-claim', 'fa-IR',
               c.content_sha256, v_source, v_name, v_url, v_role, v_retrieved,
               v_from, v_until, 'needs_review', 'pending', TRUE
          FROM knowledge.knowledge_chunks c
         WHERE c.chunk_id=v_chunk;

        SELECT COUNT(*) INTO fixture_count
          FROM knowledge.destination_claim_evidence
         WHERE claim_key='sql-test-only-claim' AND is_synthetic=TRUE
           AND review_status='needs_review' AND verification_status='pending';
        IF fixture_count <> 1 THEN
            RAISE EXCEPTION 'Pending synthetic test row was not staged exactly once';
        END IF;
    END IF;

    SELECT COUNT(*) INTO after_count
      FROM knowledge.production_destination_claim_evidence;
    IF after_count <> before_count THEN
        RAISE EXCEPTION 'Pending synthetic claim evidence became traveler-readable';
    END IF;

END $$;

ROLLBACK;
\echo 'PASS: claim identity, approval/revocation filtering, and app-role isolation'
