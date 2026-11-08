\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_batch UUID;
    v_destination BIGINT;
    v_proposal UUID := gen_random_uuid();
    v_item UUID := gen_random_uuid();
    v_spatial_count BIGINT;
    v_culinary_count BIGINT;
    v_keys TEXT[] := ARRAY[
        'shiraz-delgosha-garden-v1',
        'shiraz-afifabad-garden-v1',
        'shiraz-shah-cheragh-v1',
        'shiraz-naqsh-e-rostam-v1'
    ];
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM system.schema_migrations
        WHERE migration_id='0010_task31_content_privacy_full_itinerary'
    ) THEN
        RAISE EXCEPTION 'Migration 0010 must provide the review-only proposal tables';
    END IF;

    IF (SELECT COUNT(*) FROM knowledge.destinations WHERE destination_key = ANY(v_keys)) <> 4
       OR EXISTS (
           SELECT destination_key FROM knowledge.destinations
           WHERE destination_key = ANY(v_keys)
           GROUP BY destination_key HAVING COUNT(*) <> 1
       ) THEN
        RAISE EXCEPTION 'The four addendum identities must each resolve to one exact canonical row';
    END IF;

    SELECT dataset_import_batch_id INTO v_batch
    FROM operations.dataset_import_batches ORDER BY imported_at LIMIT 1;
    SELECT destination_id INTO v_destination FROM knowledge.destinations
    WHERE destination_key='shiraz-delgosha-garden-v1';
    IF v_batch IS NULL OR v_destination IS NULL THEN
        RAISE EXCEPTION 'A pre-existing import batch and exact target identity are required';
    END IF;

    SELECT COUNT(*) INTO v_spatial_count FROM knowledge.production_destinations;
    SELECT COUNT(*) INTO v_culinary_count FROM knowledge.production_culinary_knowledge;

    INSERT INTO knowledge.destination_enrichment_proposals (
        proposal_id, proposal_key, dataset_import_batch_id, target_destination_id,
        target_destination_key, record_action, payload, payload_sha256,
        review_status, verification_status, is_synthetic, approval_confidence, publishable
    ) VALUES (
        v_proposal, 'sql-test:task32-addendum:delgosha', v_batch, v_destination,
        'shiraz-delgosha-garden-v1', 'stage_existing_record_enrichment_review',
        '{"review_fixture":true,"locale_contract":{"locales":["fa-IR","en-US","ar"],"translation_status":"draft_human_review_required"}}'::JSONB,
        repeat('a',64), 'needs_review', 'pending', FALSE, 0, FALSE
    );

    INSERT INTO knowledge.culinary_knowledge_items (
        item_id,item_key,record_key,dataset_import_batch_id,record_action,legacy_destination_id,
        category,names_by_locale,descriptions_by_locale,claims,payload,payload_sha256,
        review_status,verification_status,is_synthetic,approval_confidence,publishable
    ) VALUES (
        v_item,'sql-test:task32-pending-food','sql-test-pending-food',v_batch,
        'stage_new_non_spatial_candidate_review',NULL,'dish',
        '{"fa-IR":"غذای آزمایشی","en-US":"Test food","ar":"طعام تجريبي"}'::JSONB,
        '{"fa-IR":"پیش‌نویس","en-US":"Draft","ar":"مسودة"}'::JSONB,
        '[{"claim_id":"pending-claim","text_by_locale":{"fa-IR":"پیش‌نویس","en-US":"Draft","ar":"مسودة"}}]'::JSONB,
        '{"review_fixture":true}'::JSONB,repeat('b',64),
        'pending_review','pending',FALSE,0,FALSE
    );

    IF EXISTS (
        SELECT 1 FROM knowledge.destination_enrichment_proposals
        WHERE proposal_id=v_proposal AND
          (review_status <> 'needs_review' OR verification_status <> 'pending'
           OR publishable IS DISTINCT FROM FALSE OR approval_confidence <> 0 OR is_synthetic)
    ) THEN
        RAISE EXCEPTION 'Spatial addendum proposal escaped its review-only defaults';
    END IF;

    BEGIN
        UPDATE knowledge.destination_enrichment_proposals SET publishable=TRUE WHERE proposal_id=v_proposal;
        RAISE EXCEPTION 'Spatial proposal unexpectedly became publishable';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        UPDATE knowledge.destination_enrichment_proposals SET approval_confidence=0.1 WHERE proposal_id=v_proposal;
        RAISE EXCEPTION 'Spatial proposal unexpectedly gained approval confidence';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        UPDATE knowledge.destination_enrichment_proposals SET review_status='approved' WHERE proposal_id=v_proposal;
        RAISE EXCEPTION 'Spatial proposal unexpectedly left needs_review';
    EXCEPTION WHEN check_violation THEN NULL;
    END;

    IF EXISTS (
        SELECT 1 FROM knowledge.culinary_knowledge_items
        WHERE item_id=v_item AND
          (review_status <> 'pending_review' OR verification_status <> 'pending'
           OR publishable IS DISTINCT FROM FALSE OR approval_confidence <> 0 OR is_synthetic)
    ) THEN
        RAISE EXCEPTION 'Culinary proposal escaped its review-only defaults';
    END IF;
    IF EXISTS (
        SELECT 1 FROM knowledge.production_culinary_knowledge
        WHERE item_id=v_item
    ) OR (SELECT COUNT(*) FROM knowledge.production_culinary_knowledge) <> v_culinary_count THEN
        RAISE EXCEPTION 'Pending culinary addendum content entered the approved production view';
    END IF;
    IF (SELECT COUNT(*) FROM knowledge.production_destinations) <> v_spatial_count THEN
        RAISE EXCEPTION 'Staging proposal changed the canonical production destination view';
    END IF;

    RAISE NOTICE 'PASS: exact addendum identities, review-only spatial proposal constraints, and pending culinary production-view exclusion.';
END $$;

ROLLBACK;
