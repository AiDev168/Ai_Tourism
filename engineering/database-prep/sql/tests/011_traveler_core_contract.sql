\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_user UUID := gen_random_uuid();
    v_conversation UUID := gen_random_uuid();
    v_trip UUID := gen_random_uuid();
    v_message UUID := gen_random_uuid();
    v_feedback UUID := gen_random_uuid();
    v_itinerary UUID := gen_random_uuid();
    v_second_conversation UUID := gen_random_uuid();
    v_second_trip UUID := gen_random_uuid();
    v_second_message UUID := gen_random_uuid();
    v_locale_notes JSONB := '{"fa-IR":"یادداشت کاربر","en-US":"User note","ar":"ملاحظة المستخدم"}'::JSONB;
    v_budget NUMERIC(20,4);
BEGIN
    IF NOT EXISTS (SELECT 1 FROM system.schema_migrations WHERE migration_id='0009_traveler_core') THEN
        RAISE EXCEPTION 'Migration 0009 is not recorded';
    END IF;
    IF to_regclass('travel.trips') IS NULL
       OR NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='travel' AND table_name='trips' AND column_name='confirmed_requirements')
       OR NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='conversation' AND table_name='messages' AND column_name='trip_id')
       OR NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='recommendation' AND table_name='recommendations' AND column_name='evidence')
       OR NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='travel' AND table_name='itinerary_stops' AND column_name='notes_by_locale') THEN
        RAISE EXCEPTION 'Migration 0009 traveler contract columns are incomplete';
    END IF;

    IF has_table_privilege('ai_tourism_app', 'knowledge.destinations', 'SELECT')
       OR NOT has_table_privilege('ai_tourism_app', 'knowledge.production_destinations', 'SELECT')
       OR NOT has_table_privilege('ai_tourism_app', 'knowledge.production_destination_sources', 'SELECT') THEN
        RAISE EXCEPTION 'Migration 0009 changed the least-privilege production catalogue boundary';
    END IF;
    IF (SELECT COUNT(*) FROM knowledge.production_destinations) <> 0 THEN
        RAISE EXCEPTION 'Unpublished or test rows unexpectedly entered the production catalogue';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname='conversation' AND indexname='uq_conversations_owner_create_key')
       OR NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname='travel' AND indexname='uq_trips_owner_create_key') THEN
        RAISE EXCEPTION 'Owner-scoped create idempotency indexes are missing';
    END IF;

    INSERT INTO identity.users (user_id, phone_e164, account_status, is_synthetic)
    VALUES (v_user, '+989000000001', 'active', TRUE);
    INSERT INTO conversation.conversations (conversation_id, user_id, language_code, is_synthetic)
    VALUES (v_conversation, v_user, 'fa-IR', TRUE);
    INSERT INTO travel.trips (
        trip_id, user_id, conversation_id, origin_text, duration_days, traveler_count,
        budget_amount_original, budget_currency_iso, budget_unit, budget_raw_text,
        confirmed_requirements, is_synthetic
    ) VALUES (
        v_trip, v_user, v_conversation, NULL, 365, NULL,
        20000000.2500, 'IRR', 'toman', '۲۰٬۰۰۰٬۰۰۰٫۲۵ تومان',
        '{"destination":{"value":"شیراز","status":"user_confirmed"}}'::JSONB, TRUE
    );
    INSERT INTO conversation.messages (message_id, conversation_id, trip_id, role, content, is_synthetic)
    VALUES (v_message, v_conversation, v_trip, 'user', 'synthetic rollback-only privacy content', TRUE);
    INSERT INTO operations.feedback (feedback_id, user_id, trip_id, feedback_type, comment, is_synthetic)
    VALUES (v_feedback, v_user, v_trip, 'other', 'synthetic rollback-only personal comment', TRUE);

    SELECT budget_amount_original INTO v_budget FROM travel.trips WHERE trip_id=v_trip;
    IF v_budget <> 20000000.2500
       OR (SELECT budget_unit FROM travel.trips WHERE trip_id=v_trip) <> 'toman'
       OR (SELECT budget_raw_text FROM travel.trips WHERE trip_id=v_trip) <> '۲۰٬۰۰۰٬۰۰۰٫۲۵ تومان' THEN
        RAISE EXCEPTION 'Original budget amount, unit or display text was changed';
    END IF;

    -- Reject an out-of-range duration and every incomplete budget tuple.
    BEGIN
        INSERT INTO travel.trips (user_id, origin_text, duration_days, is_synthetic)
        VALUES (v_user, NULL, 366, TRUE);
        RAISE EXCEPTION 'Duration 366 unexpectedly passed the 365-day cap';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO travel.trips (user_id, budget_amount_original, is_synthetic)
        VALUES (v_user, 10, TRUE);
        RAISE EXCEPTION 'Incomplete budget tuple unexpectedly passed';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO travel.trips (user_id, budget_amount_original, budget_unit, budget_raw_text, is_synthetic)
        VALUES (v_user, 10, 'rial', '10 rial', TRUE);
        RAISE EXCEPTION 'Budget tuple with missing currency unexpectedly passed';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO travel.trips (user_id, budget_amount_original, budget_currency_iso, budget_raw_text, is_synthetic)
        VALUES (v_user, 10, 'IRR', '10 rial', TRUE);
        RAISE EXCEPTION 'Budget tuple with missing unit unexpectedly passed';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO travel.trips (user_id, budget_currency_iso, budget_unit, budget_raw_text, is_synthetic)
        VALUES (v_user, 'IRR', 'toman', '10 toman', TRUE);
        RAISE EXCEPTION 'Budget tuple with missing amount unexpectedly passed';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO travel.trips (user_id, budget_amount_original, budget_currency_iso, budget_unit, is_synthetic)
        VALUES (v_user, 10, 'IRR', 'rial', TRUE);
        RAISE EXCEPTION 'Budget tuple with missing original text unexpectedly passed';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO travel.trips (user_id, budget_amount_original, budget_currency_iso, budget_unit, budget_raw_text, is_synthetic)
        VALUES (v_user, 10, 'USD', 'rial', '10 USD', TRUE);
        RAISE EXCEPTION 'Unsupported non-IRR domestic budget currency unexpectedly passed';
    EXCEPTION WHEN check_violation THEN NULL;
    END;
    BEGIN
        INSERT INTO travel.trips (user_id, budget_amount_original, budget_currency_iso, budget_unit, budget_raw_text, is_synthetic)
        VALUES (v_user, 10000000000000000.0000, 'IRR', 'rial', 'overflow', TRUE);
        RAISE EXCEPTION 'Out-of-range numeric budget unexpectedly passed';
    EXCEPTION WHEN numeric_value_out_of_range THEN NULL;
    END;

    INSERT INTO travel.itineraries (itinerary_id, trip_id, title, title_by_locale, day_count, is_synthetic)
    VALUES (v_itinerary, v_trip, 'نمونه آزمایشی', '{"fa-IR":"برنامه","en-US":"Plan","ar":"الخطة"}'::JSONB, 1, TRUE);
    INSERT INTO travel.itinerary_stops (itinerary_id, destination_id, day_number, stop_order, notes_by_locale, is_synthetic)
    SELECT v_itinerary, destination_id, 1, 1, v_locale_notes, TRUE
    FROM knowledge.destinations WHERE is_synthetic=TRUE ORDER BY destination_id LIMIT 1;
    IF (SELECT title_by_locale->>'fa-IR' FROM travel.itineraries WHERE itinerary_id=v_itinerary) <> 'برنامه'
       OR (SELECT title_by_locale->>'en-US' FROM travel.itineraries WHERE itinerary_id=v_itinerary) <> 'Plan'
       OR (SELECT notes_by_locale->>'ar' FROM travel.itinerary_stops WHERE itinerary_id=v_itinerary) <> 'ملاحظة المستخدم' THEN
        RAISE EXCEPTION 'Locale fields did not retain independently authored strings';
    END IF;

    -- A trip deletion must purge its messages and text-bearing feedback, while
    -- retaining the conversation so another trip draft can remain in it.
    DELETE FROM travel.trips WHERE trip_id=v_trip;
    IF EXISTS (SELECT 1 FROM conversation.messages WHERE message_id=v_message)
       OR EXISTS (SELECT 1 FROM operations.feedback WHERE feedback_id=v_feedback)
       OR NOT EXISTS (SELECT 1 FROM conversation.conversations WHERE conversation_id=v_conversation) THEN
        RAISE EXCEPTION 'Trip deletion did not remove only its associated personal content';
    END IF;

    INSERT INTO travel.trips (trip_id, user_id, conversation_id, origin_text, is_synthetic)
    VALUES (v_second_trip, v_user, v_conversation, NULL, TRUE);
    INSERT INTO conversation.messages (message_id, conversation_id, trip_id, role, content, is_synthetic)
    VALUES (v_second_message, v_conversation, v_second_trip, 'user', 'rollback-only second trip message', TRUE);
    INSERT INTO conversation.conversations (conversation_id, user_id, language_code, is_synthetic)
    VALUES (v_second_conversation, v_user, 'ar', TRUE);
    INSERT INTO travel.trips (user_id, conversation_id, origin_text, is_synthetic)
    VALUES (v_user, v_second_conversation, NULL, TRUE);

    DELETE FROM conversation.conversations WHERE conversation_id=v_conversation;
    IF EXISTS (SELECT 1 FROM travel.trips WHERE trip_id=v_second_trip)
       OR EXISTS (SELECT 1 FROM conversation.messages WHERE message_id=v_second_message) THEN
        RAISE EXCEPTION 'Conversation deletion did not cascade to trip and message content';
    END IF;

    DELETE FROM identity.users WHERE user_id=v_user;
    IF EXISTS (SELECT 1 FROM conversation.conversations WHERE user_id=v_user)
       OR EXISTS (SELECT 1 FROM travel.trips WHERE user_id=v_user)
       OR EXISTS (SELECT 1 FROM conversation.messages WHERE message_id=v_second_message) THEN
        RAISE EXCEPTION 'Account deletion left user-owned travel content';
    END IF;
END $$;

ROLLBACK;

DO $$
BEGIN
    RAISE NOTICE 'PASS: traveler schema limits, exact budget units, localization, owner-scoped idempotency, deletion cascades, and unchanged publication/app-role boundaries.';
END $$;
