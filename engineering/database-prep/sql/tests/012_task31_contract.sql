\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_challenge UUID := gen_random_uuid();
    v_other_challenge UUID := gen_random_uuid();
    v_active_challenge UUID := gen_random_uuid();
    v_user UUID := gen_random_uuid();
    v_other_user UUID := gen_random_uuid();
    v_batch UUID;
    v_deleted INTEGER;
    v_trip UUID := gen_random_uuid();
    v_long_trip UUID := gen_random_uuid();
    v_itinerary UUID := gen_random_uuid();
    v_empty_itinerary UUID := gen_random_uuid();
    v_full_itinerary UUID := gen_random_uuid();
    v_destination BIGINT;
    v_definition TEXT;
BEGIN
    IF NOT EXISTS (SELECT 1 FROM system.schema_migrations
                   WHERE migration_id='0010_task31_content_privacy_full_itinerary') THEN
        RAISE EXCEPTION 'Migration 0010 ledger entry is required';
    END IF;
    IF (SELECT COUNT(*) FROM pg_catalog.pg_tables WHERE schemaname IN
        ('identity','conversation','travel','knowledge','recommendation','integration','operations','system')) <> 38 THEN
        RAISE EXCEPTION 'Expected 38 project-owned tables after Migration 0010';
    END IF;
    IF has_table_privilege('ai_tourism_app','knowledge.destination_enrichment_proposals','SELECT')
       OR has_table_privilege('ai_tourism_app','knowledge.destination_enrichment_proposal_sources','SELECT')
       OR has_table_privilege('ai_tourism_app','knowledge.culinary_knowledge_items','SELECT')
       OR has_table_privilege('ai_tourism_app','knowledge.culinary_item_sources','SELECT')
       OR NOT has_table_privilege('ai_tourism_app','knowledge.production_culinary_knowledge','SELECT') THEN
        RAISE EXCEPTION 'Application-role raw/proposal access or approved-view access is incorrect';
    END IF;
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema='knowledge' AND table_name='production_culinary_knowledge'
                 AND column_name IN ('destination_id','location','latitude','longitude')) THEN
        RAISE EXCEPTION 'Non-spatial culinary view exposes spatial destination fields';
    END IF;
    SELECT lower(pg_get_viewdef('knowledge.production_culinary_knowledge'::regclass, true)) INTO v_definition;
    IF position('knowledge.destinations' IN v_definition) > 0 THEN
        RAISE EXCEPTION 'Culinary production view must not join legacy spatial identities';
    END IF;
    IF (SELECT COUNT(*) FROM knowledge.production_culinary_knowledge) <> 0 THEN
        RAISE EXCEPTION 'Fresh lifecycle must not publish candidate culinary records';
    END IF;
    IF EXISTS (
        SELECT 1 FROM knowledge.destination_enrichment_proposals
        WHERE review_status <> 'needs_review' OR publishable IS DISTINCT FROM FALSE
           OR is_synthetic IS DISTINCT FROM FALSE OR approval_confidence <> 0
    ) OR EXISTS (
        SELECT 1 FROM knowledge.culinary_knowledge_items
        WHERE review_status <> 'pending_review' OR publishable IS DISTINCT FROM FALSE
           OR is_synthetic IS DISTINCT FROM FALSE OR approval_confidence <> 0
    ) THEN
        RAISE EXCEPTION 'Staged content proposals must remain non-publishable and zero-confidence';
    END IF;

    IF (SELECT is_nullable FROM information_schema.columns WHERE table_schema='identity'
        AND table_name='verified_phones' AND column_name='challenge_id') <> 'YES'
       OR NOT EXISTS (
           SELECT 1 FROM information_schema.referential_constraints rc
           JOIN information_schema.key_column_usage kcu USING (constraint_catalog,constraint_schema,constraint_name)
           WHERE kcu.table_schema='identity' AND kcu.table_name='verified_phones'
             AND kcu.column_name='challenge_id' AND rc.delete_rule='SET NULL'
       ) THEN
        RAISE EXCEPTION 'Verified phone challenge history must support safe challenge cleanup';
    END IF;
    IF NOT has_function_privilege('ai_tourism_app',
          'identity.purge_terminal_otp_challenges(timestamp with time zone,integer)','EXECUTE') THEN
        RAISE EXCEPTION 'Application role lacks bounded OTP cleanup execution privilege';
    END IF;

    INSERT INTO identity.users (user_id, phone_e164, account_status, is_synthetic)
    VALUES (v_user, '+989000000101', 'active', TRUE),
           (v_other_user, '+989000000102', 'active', TRUE);
    INSERT INTO identity.otp_challenges (
        challenge_id, phone_e164, purpose, verifier_hmac, key_version,
        delivery_status, created_at, expires_at, resend_after
    ) VALUES
        (v_challenge, '+989000000101', 'login', decode(repeat('01',32),'hex'), 'test',
         'sent', NOW()-interval '3 hours', NOW()-interval '2 hours', NOW()-interval '179 minutes'),
        (v_other_challenge, '+989000000102', 'login', decode(repeat('02',32),'hex'), 'test',
         'sent', NOW()-interval '2 hours', NOW()-interval '1 hour', NOW()-interval '119 minutes'),
        (v_active_challenge, '+989000000101', 'login', decode(repeat('03',32),'hex'), 'test',
         'sent', NOW()-interval '2 minutes', NOW()+interval '3 minutes', NOW()-interval '1 minute');
    INSERT INTO identity.verified_phones (phone_e164,user_id,verified_at,challenge_id)
    VALUES ('+989000000101',v_user,NOW(),v_challenge);

    v_deleted := identity.purge_terminal_otp_challenges(NOW()-interval '1 hour', 1);
    IF v_deleted <> 1 THEN RAISE EXCEPTION 'Cleanup must respect bounded batch size; deleted %', v_deleted; END IF;
    IF EXISTS (SELECT 1 FROM identity.otp_challenges WHERE challenge_id=v_active_challenge)
       IS FALSE THEN RAISE EXCEPTION 'Active unexpired sent challenge was removed'; END IF;
    IF EXISTS (SELECT 1 FROM identity.otp_challenges WHERE challenge_id=v_challenge)
       OR NOT EXISTS (SELECT 1 FROM identity.otp_challenges WHERE challenge_id=v_other_challenge) THEN
        RAISE EXCEPTION 'Bounded cleanup removed the wrong terminal challenge';
    END IF;
    IF (SELECT challenge_id FROM identity.verified_phones WHERE user_id=v_user) IS NOT NULL THEN
        RAISE EXCEPTION 'Verified phone challenge reference was not set NULL by cleanup';
    END IF;
    v_deleted := identity.purge_terminal_otp_challenges(NOW()-interval '1 hour', 10);
    IF v_deleted <> 1 THEN
        RAISE EXCEPTION 'Subsequent cleanup expected one expired terminal row; deleted %', v_deleted;
    END IF;
    IF EXISTS (SELECT 1 FROM identity.otp_challenges WHERE challenge_id=v_other_challenge) THEN
        RAISE EXCEPTION 'Subsequent cleanup left the remaining expired terminal row';
    END IF;
    BEGIN
        PERFORM identity.purge_terminal_otp_challenges(NOW(), 1001);
        RAISE EXCEPTION 'Cleanup batch size above 1000 unexpectedly succeeded';
    EXCEPTION WHEN raise_exception THEN
        IF SQLERRM = 'Cleanup batch size above 1000 unexpectedly succeeded' THEN RAISE; END IF;
    END;

    SELECT dataset_import_batch_id INTO v_batch
    FROM operations.dataset_import_batches ORDER BY imported_at LIMIT 1;
    INSERT INTO knowledge.culinary_knowledge_items (
        item_key, record_key, dataset_import_batch_id, record_action, category,
        names_by_locale, descriptions_by_locale, claims, payload, payload_sha256
    ) VALUES (
        'task31-sql-pending-food', 'task31-sql-pending-food', v_batch,
        'stage_new_non_spatial_candidate_review', 'dish',
        '{"fa-IR":"نمونه","en-US":"Sample","ar":"نموذج"}'::jsonb,
        '{"fa-IR":"شرح","en-US":"Description","ar":"وصف"}'::jsonb,
        '[{"claim_id":"overview","text_by_locale":{"fa-IR":"متن","en-US":"Text","ar":"نص"}}]'::jsonb,
        '{"source":"rollback-only"}'::jsonb, repeat('a',64)
    );
    IF (SELECT review_status FROM knowledge.culinary_knowledge_items
        WHERE item_key='task31-sql-pending-food') <> 'pending_review'
       OR (SELECT approval_confidence FROM knowledge.culinary_knowledge_items
        WHERE item_key='task31-sql-pending-food') <> 0
       OR (SELECT publishable FROM knowledge.culinary_knowledge_items
        WHERE item_key='task31-sql-pending-food') IS DISTINCT FROM FALSE
       OR EXISTS (SELECT 1 FROM knowledge.production_culinary_knowledge
                  WHERE item_key='task31-sql-pending-food') THEN
        RAISE EXCEPTION 'Candidate culinary data is not safely pending/non-publishable';
    END IF;

    SELECT destination_id INTO v_destination FROM knowledge.destinations
    WHERE is_synthetic=TRUE ORDER BY destination_id LIMIT 1;
    INSERT INTO travel.trips (trip_id,user_id,origin_text,duration_days,is_synthetic)
    VALUES (v_trip,v_user,NULL,10,TRUE);
    INSERT INTO travel.trips (trip_id,user_id,origin_text,duration_days,is_synthetic)
    VALUES (v_long_trip,v_user,NULL,365,TRUE);
    INSERT INTO travel.itineraries (itinerary_id,trip_id,title,day_count,is_synthetic)
    VALUES (v_empty_itinerary,v_long_trip,'Rollback-only empty 365 day draft',365,TRUE);
    INSERT INTO travel.itineraries (itinerary_id,trip_id,title,day_count,version,is_synthetic)
    VALUES (v_full_itinerary,v_long_trip,'Rollback-only 1000-stop bound test',365,2,TRUE);
    INSERT INTO travel.itineraries (itinerary_id,trip_id,title,day_count,is_synthetic)
    VALUES (v_itinerary,v_trip,'Rollback-only 10 day draft',10,TRUE);
    INSERT INTO travel.itinerary_stops (itinerary_id,destination_id,day_number,stop_order,is_synthetic)
    VALUES (v_itinerary,v_destination,10,50,TRUE);
    INSERT INTO travel.itinerary_stops (itinerary_id,destination_id,day_number,stop_order,is_synthetic)
    SELECT v_full_itinerary, v_destination,
           ((g - 1) / 50 + 1)::SMALLINT, ((g - 1) % 50 + 1)::SMALLINT, TRUE
    FROM generate_series(1,1000) AS g;
    IF (SELECT COUNT(*) FROM travel.itinerary_stops WHERE itinerary_id=v_full_itinerary) <> 1000 THEN
        RAISE EXCEPTION 'The itinerary must accept the technical 1000-stop bound';
    END IF;
    BEGIN
        INSERT INTO travel.itinerary_stops (itinerary_id,destination_id,day_number,stop_order,is_synthetic)
        VALUES (v_full_itinerary,v_destination,21,1,TRUE);
        RAISE EXCEPTION 'The 1001st itinerary stop unexpectedly succeeded';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO travel.itinerary_stops (itinerary_id,destination_id,day_number,stop_order,is_synthetic)
        VALUES (v_itinerary,v_destination,10,51,TRUE);
        RAISE EXCEPTION '51st stop in one day unexpectedly succeeded';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO travel.itinerary_stops (itinerary_id,destination_id,day_number,stop_order,is_synthetic)
        VALUES (v_itinerary,v_destination,11,1,TRUE);
        RAISE EXCEPTION 'Stop beyond confirmed 10-day trip unexpectedly succeeded';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO travel.itineraries (trip_id,title,day_count,is_synthetic)
        VALUES (v_trip,'Beyond confirmed trip duration',11,TRUE);
        RAISE EXCEPTION 'Itinerary beyond confirmed trip duration unexpectedly succeeded';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO travel.itineraries (trip_id,title,day_count,is_synthetic)
        VALUES (v_trip,'Beyond hard day-count ceiling',366,TRUE);
        RAISE EXCEPTION 'Itinerary day_count above 365 unexpectedly succeeded';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        UPDATE travel.trips SET duration_days=364 WHERE trip_id=v_long_trip;
        RAISE EXCEPTION 'Trip duration edit conflicting with existing itinerary unexpectedly succeeded';
    EXCEPTION WHEN check_violation THEN NULL;
    END;

    RAISE NOTICE 'PASS: Task 3.1 privacy cleanup, pending culinary publication boundary, app-role grants and full-duration itinerary limits.';
END $$;

ROLLBACK;
