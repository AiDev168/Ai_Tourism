\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_source_id BIGINT;
    v_destination_id BIGINT;
    v_category_id BIGINT;
    v_document_id UUID;
    v_chunk_id UUID;
    v_space_id UUID;
    v_count BIGINT;
BEGIN
    -- Empty initial state: nothing supplied by the legacy/unverified or synthetic
    -- fixture seeds may enter production-facing views.
    SELECT COUNT(*) INTO v_count FROM knowledge.production_destinations;
    IF v_count <> 0 THEN
        RAISE EXCEPTION 'Fresh pre-Codex fixture database must publish no destinations; found %', v_count;
    END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_retrieval_documents;
    IF v_count <> 0 THEN
        RAISE EXCEPTION 'Fresh pre-Codex fixture database must expose no production retrieval documents; found %', v_count;
    END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_destination_categories;
    IF v_count <> 0 THEN
        RAISE EXCEPTION 'Categories without at least one published destination must not be exposed as production categories';
    END IF;

    SELECT COUNT(*) INTO v_count FROM knowledge.production_destination_sources;
    IF v_count <> 0 THEN RAISE EXCEPTION 'No unverified destination provenance may be visible'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_destination_category_map;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Synthetic taxonomy mappings must not be visible'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_destination_tags;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Tags for unverified or synthetic destinations must not be visible'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_retrieval_chunks;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Synthetic/unverified chunks must not be retrievable'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.active_embedding_spaces;
    IF v_count <> 0 THEN RAISE EXCEPTION 'No active embedding space should exist before provider selection'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_chunk_embeddings;
    IF v_count <> 0 THEN RAISE EXCEPTION 'No ineligible vectors may be exposed'; END IF;

    -- Create a fully marked *temporary* verified-path fixture. This is only a
    -- contract test and is rolled back below; it is not real tourism content.
    INSERT INTO knowledge.knowledge_sources
        (source_name, source_type, verification_status, reliability_score, url, notes, is_synthetic)
    VALUES
        ('TEMP QA publication-gate positive control', 'test_control', 'verified', 1.0,
         'https://example.invalid/temporary-control', 'Transaction-only fixture; rolled back.', FALSE)
    RETURNING source_id INTO v_source_id;

    INSERT INTO knowledge.destinations
        (destination_key, canonical_name, destination_type, province_name, city_name,
         description, latitude, longitude, coordinate_role, status, data_confidence,
         record_origin, verification_status, is_synthetic)
    VALUES
        ('temp-publication-gate-control', 'مقصد موقت کنترل انتشار', 'test_location',
         'استان آزمایشی', 'شهر آزمایشی', 'رکورد موقت فقط برای آزمون View انتشار.',
         0.1, 0.1, 'visitor_entrance', 'active', 1.0, 'verified_external', 'verified', FALSE)
    RETURNING destination_id INTO v_destination_id;

    INSERT INTO knowledge.destination_sources
        (destination_id, source_id, source_role, evidence_note, retrieved_at)
    VALUES
        (v_destination_id, v_source_id, 'verification', 'Temporary publication-gate positive control.', NOW());

    INSERT INTO knowledge.destination_categories
        (category_key, name_fa, description, sort_order, is_active)
    VALUES
        ('temp-publication-gate-control', 'دسته موقت آزمون', 'Transaction-only test category.', 999, TRUE)
    RETURNING category_id INTO v_category_id;

    INSERT INTO knowledge.destination_category_map
        (destination_id, category_id, mapping_source, is_synthetic)
    VALUES (v_destination_id, v_category_id, 'test_control', FALSE);

    INSERT INTO knowledge.destination_tags (destination_id, tag)
    VALUES (v_destination_id, 'temp_publication_gate_control');

    INSERT INTO knowledge.knowledge_documents
        (document_key, source_id, destination_id, title, language_code,
         raw_content, content_sha256, ingestion_status, record_origin,
         is_synthetic, retrieved_at)
    VALUES
        ('temp-publication-gate-document', v_source_id, v_destination_id,
         'Temporary publication gate control', 'fa',
         'Temporary content used only to test verified retrieval views.', repeat('a',64),
         'processed', 'verified_external', FALSE, NOW())
    RETURNING document_id INTO v_document_id;

    INSERT INTO knowledge.knowledge_chunks
        (document_id, chunk_index, content, char_count, content_sha256, is_synthetic)
    VALUES
        (v_document_id, 0, 'Temporary retrieval chunk.', 26, repeat('b',64), FALSE)
    RETURNING chunk_id INTO v_chunk_id;

    INSERT INTO knowledge.embedding_spaces
        (space_key, provider_type, provider_name, model_name, model_revision,
         vector_dimension, similarity_metric, preprocessing_version,
         is_active, lifecycle_status)
    VALUES
        ('temp-publication-gate-space', 'test', 'temporary-control', 'temporary-3d',
         'v1', 3, 'cosine', 'test-v1', TRUE, 'active')
    RETURNING embedding_space_id INTO v_space_id;

    INSERT INTO knowledge.chunk_embeddings (chunk_id, embedding_space_id, embedding)
    VALUES (v_chunk_id, v_space_id, '[1,0,0]'::VECTOR);

    -- Positive controls: all valid data is visible through only the safe views.
    SELECT COUNT(*) INTO v_count FROM knowledge.production_destinations
     WHERE destination_id = v_destination_id;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Verified destination did not enter production view'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_destination_sources
     WHERE destination_id = v_destination_id AND source_id = v_source_id;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Verified provenance link did not enter production view'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_destination_categories
     WHERE category_id = v_category_id;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Active mapped category did not enter production view'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_destination_category_map
     WHERE destination_id = v_destination_id AND category_id = v_category_id;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Verified destination/category mapping did not enter production view'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_destination_tags
     WHERE destination_id = v_destination_id AND tag = 'temp_publication_gate_control';
    IF v_count <> 1 THEN RAISE EXCEPTION 'Verified destination tag did not enter production view'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_retrieval_documents
     WHERE document_id = v_document_id;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Processed verified document did not enter retrieval view'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_retrieval_chunks
     WHERE chunk_id = v_chunk_id;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Chunk from verified document did not enter retrieval view'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.active_embedding_spaces
     WHERE embedding_space_id = v_space_id;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Active embedding space did not enter configuration view'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_chunk_embeddings
     WHERE chunk_id = v_chunk_id AND embedding_space_id = v_space_id;
    IF v_count <> 1 THEN RAISE EXCEPTION 'Embedding for eligible chunk/space did not enter retrieval view'; END IF;

    -- Negative controls: source revocation immediately removes evidence-backed
    -- documents/chunks/embeddings and destination provenance from safe views.
    UPDATE knowledge.knowledge_sources
       SET verification_status = 'pending'
     WHERE source_id = v_source_id;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_destination_sources
     WHERE destination_id = v_destination_id;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Unverified source remains visible as destination evidence'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_destinations
     WHERE destination_id = v_destination_id;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Destination without any verified provenance remains published'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_retrieval_documents
     WHERE document_id = v_document_id;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Document with unverified source remains retrievable'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_retrieval_chunks
     WHERE chunk_id = v_chunk_id;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Chunk with unverified source remains retrievable'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_chunk_embeddings
     WHERE chunk_id = v_chunk_id;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Embedding with unverified source remains retrievable'; END IF;

    -- A valid source cannot compensate for an unpublished destination.
    UPDATE knowledge.knowledge_sources
       SET verification_status = 'verified'
     WHERE source_id = v_source_id;
    UPDATE knowledge.destinations
       SET status = 'needs_review'
     WHERE destination_id = v_destination_id;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_destinations
     WHERE destination_id = v_destination_id;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Destination in needs_review state remains published'; END IF;
    SELECT COUNT(*) INTO v_count FROM knowledge.production_retrieval_documents
     WHERE document_id = v_document_id;
    IF v_count <> 0 THEN RAISE EXCEPTION 'Document linked to unpublished destination remains retrievable'; END IF;

    RAISE NOTICE 'PASS: positive and negative publication/retrieval paths, taxonomy, provenance and active embedding views.';
END $$;

-- The positive-control dataset and vectors must never persist.
ROLLBACK;
