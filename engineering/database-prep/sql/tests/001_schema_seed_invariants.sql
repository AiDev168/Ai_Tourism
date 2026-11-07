\set ON_ERROR_STOP on

DO $$
DECLARE
    actual_count INTEGER;
    missing_count INTEGER;
    v_count BIGINT;
    v_has_shiraz BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM system.schema_migrations
        WHERE migration_id = '0007_shiraz_dalahoo_wikipedia_dataset_v1'
    ) INTO v_has_shiraz;

    -- Exactly 30 application/system tables are expected in the owned schemas.
    SELECT COUNT(*) INTO actual_count
    FROM pg_catalog.pg_tables
    WHERE schemaname IN ('identity', 'conversation', 'travel', 'knowledge',
                         'recommendation', 'integration', 'operations', 'system');

    IF actual_count <> 30 THEN
        RAISE EXCEPTION 'Expected exactly 30 owned tables; found %', actual_count;
    END IF;

    WITH expected(schema_name, table_name) AS (
        VALUES
        ('identity','users'), ('identity','user_consents'), ('identity','user_preferences'),
        ('conversation','conversations'), ('conversation','messages'),
        ('travel','trips'), ('travel','trip_constraints'), ('travel','trip_interests'),
        ('travel','itineraries'), ('travel','itinerary_stops'),
        ('knowledge','knowledge_sources'), ('knowledge','destinations'),
        ('knowledge','destination_sources'), ('knowledge','destination_tags'),
        ('knowledge','destination_categories'), ('knowledge','destination_category_map'),
        ('knowledge','knowledge_documents'), ('knowledge','knowledge_chunks'),
        ('knowledge','embedding_spaces'), ('knowledge','chunk_embeddings'),
        ('recommendation','recommendation_requests'), ('recommendation','recommendations'),
        ('recommendation','recommendation_score_components'),
        ('integration','external_links'), ('integration','outbound_clicks'),
        ('operations','feedback'), ('operations','ai_model_calls'),
        ('operations','audit_events'), ('operations','dataset_import_batches'),
        ('system','schema_migrations')
    )
    SELECT COUNT(*) INTO missing_count
    FROM expected e
    LEFT JOIN pg_catalog.pg_tables p
      ON p.schemaname = e.schema_name AND p.tablename = e.table_name
    WHERE p.tablename IS NULL;

    IF missing_count <> 0 THEN
        RAISE EXCEPTION 'Missing % expected tables', missing_count;
    END IF;

    -- Exact dataset counts. These checks fail loudly if a seed is incomplete or duplicated.
    SELECT COUNT(*) INTO v_count FROM system.schema_migrations;
    IF (v_has_shiraz AND v_count <> 8) OR (NOT v_has_shiraz AND v_count <> 7) THEN
        RAISE EXCEPTION 'Expected exactly the complete 0006 (7 entries) or 0007 (8 entries) migration ledger; found % entries', v_count;
    END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.knowledge_sources;
    IF (v_has_shiraz AND v_count <> 58) OR (NOT v_has_shiraz AND v_count <> 40) THEN
        RAISE EXCEPTION 'Expected 40 sources at 0006 or 58 at 0007; found %', v_count;
    END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.knowledge_sources
     WHERE source_name = 'Supplied tourism-points dataset (project attachment)'
       AND verification_status = 'pending' AND is_synthetic = FALSE;
    IF v_count <> 1 THEN RAISE EXCEPTION 'The supplied legacy source must remain pending and non-synthetic'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.knowledge_sources
     WHERE source_name = 'AI Tourism QA Synthetic Fixture Pack v1'
       AND verification_status = 'pending' AND is_synthetic = TRUE;
    IF v_count <> 1 THEN RAISE EXCEPTION 'The QA source must remain explicitly synthetic and pending'; END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.destinations;
    IF (v_has_shiraz AND v_count <> 66) OR (NOT v_has_shiraz AND v_count <> 44) THEN
        RAISE EXCEPTION 'Expected 44 destinations at 0006 or 66 at 0007; found %', v_count;
    END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.destinations
     WHERE record_origin = 'user_supplied_unverified'
       AND verification_status = 'pending'
       AND status = 'needs_review'
       AND latitude IS NULL AND longitude IS NULL;
    IF (v_has_shiraz AND v_count <> 14) OR (NOT v_has_shiraz AND v_count <> 15) THEN
        RAISE EXCEPTION 'Expected 15 legacy rows at 0006 or 14 after Maragheh enrichment at 0007; found %', v_count;
    END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.destinations
     WHERE record_origin = 'verified_external' AND verification_status = 'verified'
       AND status = 'needs_review' AND is_synthetic = FALSE
       AND coordinate_role = 'property_reference' AND location IS NOT NULL;
    IF v_count <> 17 THEN RAISE EXCEPTION 'Expected 17 source-verified UNESCO properties held in needs_review with property-reference coordinates, found %', v_count; END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.destinations
     WHERE record_origin = 'synthetic_fixture'
       AND is_synthetic = TRUE
       AND verification_status = 'not_applicable'
       AND status = 'test_only';
    IF v_count <> 12 THEN RAISE EXCEPTION 'Expected 12 synthetic test-only destinations, found %', v_count; END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.destination_sources;
    IF (v_has_shiraz AND v_count <> 116) OR (NOT v_has_shiraz AND v_count <> 65) THEN
        RAISE EXCEPTION 'Expected 65 destination-source links at 0006 or 116 at 0007; found %', v_count;
    END IF;
    SELECT COUNT(DISTINCT destination_id) INTO v_count FROM knowledge.destination_sources;
    IF (v_has_shiraz AND v_count <> 66) OR (NOT v_has_shiraz AND v_count <> 44) THEN
        RAISE EXCEPTION 'Every destination must have provenance (44 at 0006, 66 at 0007); covered %', v_count;
    END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.destination_tags;
    IF (v_has_shiraz AND v_count <> 208) OR (NOT v_has_shiraz AND v_count <> 88) THEN
        RAISE EXCEPTION 'Expected 88 destination tags at 0006 or 208 at 0007; found %', v_count;
    END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.destination_categories;
    IF v_count <> 12 THEN RAISE EXCEPTION 'Expected 12 controlled taxonomy categories, found %', v_count; END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.destination_categories WHERE is_active = TRUE;
    IF v_count <> 12 THEN RAISE EXCEPTION 'All 12 canonical taxonomy categories must be active; found %', v_count; END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.destination_category_map;
    IF (v_has_shiraz AND v_count <> 47) OR (NOT v_has_shiraz AND v_count <> 30) THEN
        RAISE EXCEPTION 'Expected 30 category mappings at 0006 or 47 at 0007; found %', v_count;
    END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.destination_category_map
     WHERE is_synthetic = TRUE AND mapping_source = 'synthetic_fixture';
    IF v_count <> 12 THEN RAISE EXCEPTION 'Exactly 12 QA category mappings must be marked synthetic'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.destination_category_map WHERE is_synthetic = FALSE;
    IF (v_has_shiraz AND v_count <> 35) OR (NOT v_has_shiraz AND v_count <> 18) THEN
        RAISE EXCEPTION 'Expected 18 non-synthetic curated category mappings at 0006 or 35 at 0007; found %', v_count;
    END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.knowledge_documents;
    IF (v_has_shiraz AND v_count <> 52) OR (NOT v_has_shiraz AND v_count <> 29) THEN
        RAISE EXCEPTION 'Expected 29 knowledge documents at 0006 or 52 at 0007; found %', v_count;
    END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.knowledge_documents WHERE is_synthetic = FALSE AND record_origin = 'verified_external' AND ingestion_status = 'processed';
    IF (v_has_shiraz AND v_count <> 40) OR (NOT v_has_shiraz AND v_count <> 17) THEN
        RAISE EXCEPTION 'Expected 17 verified external documents at 0006 or 40 at 0007; found %', v_count;
    END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.knowledge_chunks;
    IF (v_has_shiraz AND v_count <> 81) OR (NOT v_has_shiraz AND v_count <> 58) THEN
        RAISE EXCEPTION 'Expected 58 chunks at 0006 or 81 at 0007; found %', v_count;
    END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.knowledge_chunks WHERE is_synthetic = FALSE;
    IF (v_has_shiraz AND v_count <> 57) OR (NOT v_has_shiraz AND v_count <> 34) THEN
        RAISE EXCEPTION 'Expected 34 verified external chunks at 0006 or 57 at 0007; found %', v_count;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM knowledge.knowledge_chunks c
        WHERE c.char_count <> CHAR_LENGTH(c.content)
           OR LENGTH(c.content_sha256) <> 64
    ) THEN RAISE EXCEPTION 'A knowledge chunk has an invalid character count or SHA-256 length'; END IF;

    IF EXISTS (
        SELECT 1
        FROM knowledge.knowledge_chunks c
        JOIN knowledge.knowledge_documents d ON d.document_id = c.document_id
        WHERE c.is_synthetic IS DISTINCT FROM d.is_synthetic
    ) THEN RAISE EXCEPTION 'Chunk synthetic classification does not match its parent document'; END IF;

    -- Verify hashes again inside PostgreSQL after SQL literal parsing and UTF-8 storage.
    IF EXISTS (
        SELECT 1
        FROM knowledge.knowledge_documents d
        WHERE d.is_synthetic = TRUE
          AND d.content_sha256 <> encode(sha256(convert_to(d.raw_content, 'UTF8')), 'hex')
    ) THEN RAISE EXCEPTION 'Stored synthetic document SHA-256 does not match raw_content'; END IF;

    IF EXISTS (
        SELECT 1
        FROM knowledge.knowledge_chunks c
        WHERE c.is_synthetic = TRUE
          AND c.content_sha256 <> encode(sha256(convert_to(c.content, 'UTF8')), 'hex')
    ) THEN RAISE EXCEPTION 'Stored synthetic chunk SHA-256 does not match content'; END IF;

    IF EXISTS (
        SELECT 1
        FROM knowledge.knowledge_documents d
        LEFT JOIN knowledge.knowledge_chunks c ON c.document_id = d.document_id
        WHERE d.is_synthetic = TRUE
        GROUP BY d.document_id
        HAVING COUNT(c.chunk_id) <> 2
    ) THEN RAISE EXCEPTION 'Every synthetic QA document must contain exactly 2 chunks'; END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.embedding_spaces;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Expected 0 persistent embedding spaces before choosing a model, found %', v_count; END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.chunk_embeddings;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Expected 0 persistent embeddings before the RAG provider is selected, found %', v_count; END IF;

    SELECT COUNT(*) INTO v_count FROM identity.users WHERE is_synthetic = TRUE;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Expected one synthetic QA user, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM identity.user_consents WHERE is_synthetic = TRUE;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Expected one synthetic consent, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM identity.user_preferences WHERE is_synthetic = TRUE;
    IF v_count <> 3 THEN RAISE EXCEPTION 'Expected 3 synthetic preferences, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM conversation.conversations WHERE is_synthetic = TRUE;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Expected one synthetic conversation, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM conversation.messages WHERE is_synthetic = TRUE;
    IF v_count <> 4 THEN RAISE EXCEPTION 'Expected 4 synthetic messages, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM travel.trips WHERE is_synthetic = TRUE;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Expected one synthetic trip, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM travel.trip_constraints WHERE is_synthetic = TRUE;
    IF v_count <> 3 THEN RAISE EXCEPTION 'Expected 3 synthetic trip constraints, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM travel.trip_interests WHERE is_synthetic = TRUE;
    IF v_count <> 3 THEN RAISE EXCEPTION 'Expected 3 synthetic trip interests, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM recommendation.recommendation_requests WHERE is_synthetic = TRUE;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Expected one synthetic recommendation request, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM recommendation.recommendations WHERE is_synthetic = TRUE;
    IF v_count <> 3 THEN RAISE EXCEPTION 'Expected 3 synthetic recommendations, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM recommendation.recommendation_score_components WHERE is_synthetic = TRUE;
    IF v_count <> 9 THEN RAISE EXCEPTION 'Expected 9 synthetic score components, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM travel.itineraries WHERE is_synthetic = TRUE;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Expected one synthetic itinerary, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM travel.itinerary_stops WHERE is_synthetic = TRUE;
    IF v_count <> 6 THEN RAISE EXCEPTION 'Expected 6 synthetic itinerary stops, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM integration.external_links WHERE is_synthetic = TRUE;
    IF v_count <> 3 THEN RAISE EXCEPTION 'Expected 3 synthetic external links, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM integration.outbound_clicks;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Expected 0 outbound clicks; no real click occurred, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM operations.feedback WHERE is_synthetic = TRUE;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Expected one synthetic feedback row, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM operations.ai_model_calls;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Expected 0 AI usage events; no real provider call occurred, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM operations.audit_events;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Expected 0 audit rows; no live application action occurred, found %', v_count; END IF;
    SELECT COUNT(*) INTO v_count FROM operations.dataset_import_batches;
    IF (v_has_shiraz AND v_count <> 6) OR (NOT v_has_shiraz AND v_count <> 5) THEN
        RAISE EXCEPTION 'Expected 5 dataset batches at 0006 or 6 at 0007; found %', v_count;
    END IF;
    SELECT COUNT(*) INTO v_count FROM operations.dataset_import_batches
     WHERE batch_key IN ('legacy-user-supplied-destinations-v1', 'synthetic-knowledge-fixtures-v1', 'synthetic-e2e-flow-v1', 'verified-unesco-iran-sites-v1', 'verified-unesco-iran-sites-v2', 'shiraz-dalahoo-wikipedia-v1');
    IF (v_has_shiraz AND v_count <> 6) OR (NOT v_has_shiraz AND v_count <> 5) THEN
        RAISE EXCEPTION 'Dataset import batch names do not match the selected migration state';
    END IF;
    IF (SELECT source_checksum FROM operations.dataset_import_batches
        WHERE batch_key = 'legacy-user-supplied-destinations-v1') IS NULL
    THEN RAISE EXCEPTION 'Legacy import batch must preserve the source SQL checksum'; END IF;
    SELECT COUNT(*) INTO v_count FROM system.schema_migrations;
    IF (v_has_shiraz AND v_count <> 8) OR (NOT v_has_shiraz AND v_count <> 7) THEN
        RAISE EXCEPTION 'Expected 7 tracked migration entries at 0006 or 8 at 0007; found %', v_count;
    END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.production_destinations;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Verified UNESCO seeds must remain unpublished until explicit review'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_retrieval_documents;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Documents linked to needs_review destinations must remain outside production RAG'; END IF;

    -- No seeded synthetic destination or document may appear as production-active.
    IF EXISTS (
        SELECT 1 FROM knowledge.destinations
        WHERE is_synthetic = TRUE AND (status <> 'test_only' OR record_origin <> 'synthetic_fixture')
    ) THEN RAISE EXCEPTION 'Synthetic destination escaped test_only guard'; END IF;

    IF EXISTS (
        SELECT 1 FROM knowledge.knowledge_documents
        WHERE is_synthetic = TRUE AND (ingestion_status <> 'test_only' OR record_origin <> 'synthetic_fixture')
    ) THEN RAISE EXCEPTION 'Synthetic document escaped test_only guard'; END IF;

    -- Synthetic demo graph must remain synthetic across all user-facing tables.
    IF EXISTS (SELECT 1 FROM conversation.messages WHERE is_synthetic = FALSE)
       OR EXISTS (SELECT 1 FROM recommendation.recommendations WHERE is_synthetic = FALSE)
       OR EXISTS (SELECT 1 FROM travel.itinerary_stops WHERE is_synthetic = FALSE)
    THEN RAISE EXCEPTION 'Unexpected non-synthetic rows in the seeded QA graph'; END IF;

    RAISE NOTICE 'PASS: exact 0006/0007 table-state row counts, provenance and synthetic-data isolation.';
END $$;
