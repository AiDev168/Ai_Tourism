\set ON_ERROR_STOP on

DO $$
DECLARE
    v_superuser BOOLEAN;
    v_createdb BOOLEAN;
    v_createrole BOOLEAN;
    v_canlogin BOOLEAN;
BEGIN
    SELECT rolsuper, rolcreatedb, rolcreaterole, rolcanlogin
      INTO v_superuser, v_createdb, v_createrole, v_canlogin
      FROM pg_roles
     WHERE rolname = 'ai_tourism_app';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Application role ai_tourism_app does not exist';
    END IF;
    IF v_superuser OR v_createdb OR v_createrole OR NOT v_canlogin THEN
        RAISE EXCEPTION 'Application role must be login-enabled and must not be superuser, createdb or createrole';
    END IF;
    IF NOT has_database_privilege('ai_tourism_app', current_database(), 'CONNECT') THEN
        RAISE EXCEPTION 'Application role is missing CONNECT';
    END IF;
    IF NOT has_schema_privilege('ai_tourism_app', 'knowledge', 'USAGE') THEN
        RAISE EXCEPTION 'Application role is missing knowledge schema USAGE';
    END IF;
    IF has_table_privilege('ai_tourism_app', 'knowledge.destinations', 'SELECT')
       OR has_table_privilege('ai_tourism_app', 'knowledge.knowledge_sources', 'SELECT')
       OR has_table_privilege('ai_tourism_app', 'knowledge.knowledge_documents', 'SELECT')
       OR has_table_privilege('ai_tourism_app', 'knowledge.knowledge_chunks', 'SELECT')
       OR has_table_privilege('ai_tourism_app', 'knowledge.embedding_spaces', 'SELECT')
       OR has_table_privilege('ai_tourism_app', 'knowledge.chunk_embeddings', 'SELECT') THEN
        RAISE EXCEPTION 'Application role must not read raw knowledge tables or unverified data';
    END IF;
    IF NOT has_table_privilege('ai_tourism_app', 'knowledge.production_destinations', 'SELECT')
       OR NOT has_table_privilege('ai_tourism_app', 'knowledge.production_retrieval_documents', 'SELECT')
       OR NOT has_table_privilege('ai_tourism_app', 'knowledge.production_retrieval_chunks', 'SELECT')
       OR NOT has_table_privilege('ai_tourism_app', 'knowledge.production_chunk_embeddings', 'SELECT')
       OR NOT has_table_privilege('ai_tourism_app', 'knowledge.active_embedding_spaces', 'SELECT') THEN
        RAISE EXCEPTION 'Application role is missing SELECT on one or more verified production retrieval views';
    END IF;
    IF has_table_privilege('ai_tourism_app', 'knowledge.production_destinations', 'UPDATE')
       OR has_table_privilege('ai_tourism_app', 'knowledge.production_retrieval_documents', 'INSERT')
       OR has_table_privilege('ai_tourism_app', 'knowledge.production_chunk_embeddings', 'INSERT') THEN
        RAISE EXCEPTION 'Application role must not write through production knowledge views';
    END IF;
    IF has_table_privilege('ai_tourism_app', 'operations.dataset_import_batches', 'SELECT')
       OR has_table_privilege('ai_tourism_app', 'operations.dataset_import_batches', 'INSERT')
       OR has_table_privilege('ai_tourism_app', 'operations.dataset_import_batches', 'UPDATE') THEN
        RAISE EXCEPTION 'Application role must not manipulate controlled dataset import batches';
    END IF;
    IF NOT has_table_privilege('ai_tourism_app', 'travel.trips', 'INSERT')
       OR NOT has_table_privilege('ai_tourism_app', 'conversation.messages', 'INSERT') THEN
        RAISE EXCEPTION 'Application role is missing required trip/conversation write privileges';
    END IF;
    IF has_schema_privilege('ai_tourism_app', 'system', 'USAGE') THEN
        RAISE EXCEPTION 'Application role must not access the system migration schema';
    END IF;
    IF has_table_privilege('ai_tourism_app', 'system.schema_migrations', 'SELECT') THEN
        RAISE EXCEPTION 'Application role must not read migration ledger';
    END IF;

    RAISE NOTICE 'PASS: least-privilege application role; only verified knowledge views are readable and system migration schema remains private.';
END $$;


-- Execute representative operations with the actual runtime role, not only
-- has_*_privilege metadata. All test writes are rolled back.
BEGIN;
SET LOCAL ROLE ai_tourism_app;

DO $$
BEGIN
    PERFORM COUNT(*) FROM knowledge.production_destinations;
    PERFORM COUNT(*) FROM knowledge.production_retrieval_documents;
    PERFORM COUNT(*) FROM knowledge.production_retrieval_chunks;
    PERFORM COUNT(*) FROM knowledge.active_embedding_spaces;

    BEGIN
        PERFORM COUNT(*) FROM knowledge.destinations;
        RAISE EXCEPTION 'Runtime role unexpectedly read raw destinations';
    EXCEPTION WHEN insufficient_privilege THEN
        NULL;
    END;

    INSERT INTO conversation.messages
        (conversation_id, role, content, is_synthetic)
    VALUES
        ('20000000-0000-4000-8000-000000000001', 'user',
         'پیام موقت برای آزمون مجوز نقش اپلیکیشن.', TRUE);

    BEGIN
        INSERT INTO knowledge.knowledge_documents
            (document_key, source_id, title, raw_content, content_sha256,
             ingestion_status, record_origin, is_synthetic)
        VALUES
            ('forbidden-runtime-document', 1, 'forbidden', 'must be rejected',
             repeat('a',64), 'test_only', 'synthetic_fixture', TRUE);
        RAISE EXCEPTION 'Runtime role unexpectedly inserted a knowledge document';
    EXCEPTION WHEN insufficient_privilege THEN
        NULL;
    END;
END $$;

ROLLBACK;
