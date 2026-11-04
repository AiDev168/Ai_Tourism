\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_space_3d UUID;
    v_space_4d UUID;
    v_top_document_key TEXT;
    v_top_4d_document_key TEXT;
    v_bad_dimension_rejected BOOLEAN := FALSE;
BEGIN
    -- The storage contract is dimension-agnostic: a future model may use a
    -- different dimension without changing the knowledge_chunks table.
    INSERT INTO knowledge.embedding_spaces
        (space_key, provider_type, provider_name, model_name, model_revision,
         vector_dimension, similarity_metric, preprocessing_version,
         is_active, lifecycle_status)
    VALUES
        ('qa-rag-contract-3d', 'test', 'local-test', 'deterministic-test-3d', 'v1',
         3, 'cosine', 'fixture-v1', FALSE, 'test_only')
    RETURNING embedding_space_id INTO v_space_3d;

    INSERT INTO knowledge.embedding_spaces
        (space_key, provider_type, provider_name, model_name, model_revision,
         vector_dimension, similarity_metric, preprocessing_version,
         is_active, lifecycle_status)
    VALUES
        ('qa-rag-contract-4d', 'test', 'local-test', 'deterministic-test-4d', 'v1',
         4, 'cosine', 'fixture-v1', FALSE, 'test_only')
    RETURNING embedding_space_id INTO v_space_4d;

    INSERT INTO knowledge.chunk_embeddings (chunk_id, embedding_space_id, embedding)
    SELECT c.chunk_id, v_space_3d, x.vector_value
      FROM (VALUES
        ('qa-forest-01', 0, '[1,0,0]'::VECTOR),
        ('qa-desert-04', 0, '[0,1,0]'::VECTOR),
        ('qa-coast-06', 0, '[0,0,1]'::VECTOR)
      ) AS x(document_key, chunk_index, vector_value)
      JOIN knowledge.knowledge_documents d ON d.document_key = x.document_key
      JOIN knowledge.knowledge_chunks c
        ON c.document_id = d.document_id AND c.chunk_index = x.chunk_index;

    INSERT INTO knowledge.chunk_embeddings (chunk_id, embedding_space_id, embedding)
    SELECT c.chunk_id, v_space_4d, x.vector_value
      FROM (VALUES
        ('qa-mountain-02', 0, '[1,0,0,0]'::VECTOR),
        ('qa-waterfall-03', 0, '[0,1,0,0]'::VECTOR)
      ) AS x(document_key, chunk_index, vector_value)
      JOIN knowledge.knowledge_documents d ON d.document_key = x.document_key
      JOIN knowledge.knowledge_chunks c
        ON c.document_id = d.document_id AND c.chunk_index = x.chunk_index;

    -- Use a materialized filtered candidate set: all vectors in a space must
    -- have the dimension recorded for that space.
    WITH candidates AS MATERIALIZED (
        SELECT d.document_key, e.embedding
          FROM knowledge.chunk_embeddings e
          JOIN knowledge.knowledge_chunks c ON c.chunk_id = e.chunk_id
          JOIN knowledge.knowledge_documents d ON d.document_id = c.document_id
         WHERE e.embedding_space_id = v_space_3d
    )
    SELECT document_key INTO v_top_document_key
      FROM candidates
     ORDER BY embedding <=> '[0.98,0.02,0]'::VECTOR
     LIMIT 1;

    IF v_top_document_key <> 'qa-forest-01' THEN
        RAISE EXCEPTION 'Expected qa-forest-01 as nearest vector result; got %', v_top_document_key;
    END IF;

    WITH candidates AS MATERIALIZED (
        SELECT d.document_key, e.embedding
          FROM knowledge.chunk_embeddings e
          JOIN knowledge.knowledge_chunks c ON c.chunk_id = e.chunk_id
          JOIN knowledge.knowledge_documents d ON d.document_id = c.document_id
         WHERE e.embedding_space_id = v_space_4d
    )
    SELECT document_key INTO v_top_4d_document_key
      FROM candidates
     ORDER BY embedding <=> '[0.99,0.01,0,0]'::VECTOR
     LIMIT 1;

    IF v_top_4d_document_key <> 'qa-mountain-02' THEN
        RAISE EXCEPTION 'Expected qa-mountain-02 in the 4D embedding space; got %', v_top_4d_document_key;
    END IF;

    -- Enforce the configured vector dimension and prove a bad vector is rejected.
    BEGIN
        INSERT INTO knowledge.chunk_embeddings (chunk_id, embedding_space_id, embedding)
        SELECT c.chunk_id, v_space_3d, '[1,0]'::VECTOR
          FROM knowledge.knowledge_documents d
          JOIN knowledge.knowledge_chunks c ON c.document_id = d.document_id
         WHERE d.document_key = 'qa-forest-01' AND c.chunk_index = 1;
        RAISE EXCEPTION 'Dimension guard did not reject a 2D vector in a 3D space';
    EXCEPTION WHEN check_violation THEN
        v_bad_dimension_rejected := TRUE;
    END;

    IF NOT v_bad_dimension_rejected THEN
        RAISE EXCEPTION 'Expected dimension mismatch rejection';
    END IF;

    RAISE NOTICE 'PASS: document->chunk->embedding persistence, 3D and 4D retrieval, nearest-neighbor result and dimension guard.';
END $$;

-- Keep the production-like fixture database clean: all RAG contract rows above
-- are rolled back after the smoke test.
ROLLBACK;
