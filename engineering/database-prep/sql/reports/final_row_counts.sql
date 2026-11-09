\set ON_ERROR_STOP on

WITH actual(table_name, actual_count) AS (
    SELECT 'identity.users (synthetic seed)', COUNT(*)::BIGINT FROM identity.users WHERE is_synthetic=TRUE
    UNION ALL SELECT 'identity.user_consents (synthetic seed)', COUNT(*) FROM identity.user_consents WHERE is_synthetic=TRUE
    UNION ALL SELECT 'identity.user_preferences (synthetic seed)', COUNT(*) FROM identity.user_preferences WHERE is_synthetic=TRUE
    UNION ALL SELECT 'conversation.conversations (synthetic seed)', COUNT(*) FROM conversation.conversations WHERE is_synthetic=TRUE
    UNION ALL SELECT 'conversation.messages (synthetic seed)', COUNT(*) FROM conversation.messages WHERE is_synthetic=TRUE
    UNION ALL SELECT 'travel.trips (synthetic seed)', COUNT(*) FROM travel.trips WHERE is_synthetic=TRUE
    UNION ALL SELECT 'travel.trip_constraints (synthetic seed)', COUNT(*) FROM travel.trip_constraints WHERE is_synthetic=TRUE
    UNION ALL SELECT 'travel.trip_interests (synthetic seed)', COUNT(*) FROM travel.trip_interests WHERE is_synthetic=TRUE
    UNION ALL SELECT 'travel.itineraries (synthetic seed)', COUNT(*) FROM travel.itineraries WHERE is_synthetic=TRUE
    UNION ALL SELECT 'travel.itinerary_stops (synthetic seed)', COUNT(*) FROM travel.itinerary_stops WHERE is_synthetic=TRUE
    UNION ALL SELECT 'knowledge.knowledge_sources', COUNT(*) FROM knowledge.knowledge_sources
    UNION ALL SELECT 'knowledge.destinations', COUNT(*) FROM knowledge.destinations
    UNION ALL SELECT 'knowledge.destination_sources', COUNT(*) FROM knowledge.destination_sources
    UNION ALL SELECT 'knowledge.destination_tags', COUNT(*) FROM knowledge.destination_tags
    UNION ALL SELECT 'knowledge.destination_categories', COUNT(*) FROM knowledge.destination_categories
    UNION ALL SELECT 'knowledge.destination_category_map', COUNT(*) FROM knowledge.destination_category_map
    UNION ALL SELECT 'knowledge.knowledge_documents', COUNT(*) FROM knowledge.knowledge_documents
    UNION ALL SELECT 'knowledge.knowledge_chunks', COUNT(*) FROM knowledge.knowledge_chunks
    UNION ALL SELECT 'knowledge.embedding_spaces', COUNT(*) FROM knowledge.embedding_spaces
    UNION ALL SELECT 'knowledge.chunk_embeddings', COUNT(*) FROM knowledge.chunk_embeddings
    UNION ALL SELECT 'recommendation.recommendation_requests (synthetic seed)', COUNT(*) FROM recommendation.recommendation_requests WHERE is_synthetic=TRUE
    UNION ALL SELECT 'recommendation.recommendations (synthetic seed)', COUNT(*) FROM recommendation.recommendations WHERE is_synthetic=TRUE
    UNION ALL SELECT 'recommendation.recommendation_score_components (synthetic seed)', COUNT(*) FROM recommendation.recommendation_score_components WHERE is_synthetic=TRUE
    UNION ALL SELECT 'integration.external_links', COUNT(*) FROM integration.external_links
    UNION ALL SELECT 'integration.outbound_clicks (synthetic seed)', COUNT(*) FROM integration.outbound_clicks WHERE is_synthetic=TRUE
    UNION ALL SELECT 'operations.feedback (synthetic seed)', COUNT(*) FROM operations.feedback WHERE is_synthetic=TRUE
    UNION ALL SELECT 'operations.dataset_import_batches', COUNT(*) FROM operations.dataset_import_batches
    UNION ALL SELECT 'system.schema_migrations', COUNT(*) FROM system.schema_migrations
), state AS (
    SELECT EXISTS (
        SELECT 1 FROM system.schema_migrations
        WHERE migration_id = '0007_shiraz_dalahoo_wikipedia_dataset_v1'
    ) AS shiraz_applied,
    EXISTS (SELECT 1 FROM system.schema_migrations
            WHERE migration_id = '0008_authentication_foundation') AS auth_applied,
    EXISTS (SELECT 1 FROM system.schema_migrations
            WHERE migration_id = '0009_traveler_core') AS traveler_applied,
    EXISTS (SELECT 1 FROM system.schema_migrations
            WHERE migration_id = '0010_task31_content_privacy_full_itinerary') AS task31_applied
), expected(table_name, expected_0006, expected_0007) AS (
    VALUES
    ('identity.users (synthetic seed)', 1::BIGINT, 1::BIGINT),
    ('identity.user_consents (synthetic seed)', 1, 1),
    ('identity.user_preferences (synthetic seed)', 3, 3),
    ('conversation.conversations (synthetic seed)', 1, 1),
    ('conversation.messages (synthetic seed)', 4, 4),
    ('travel.trips (synthetic seed)', 1, 1),
    ('travel.trip_constraints (synthetic seed)', 3, 3),
    ('travel.trip_interests (synthetic seed)', 3, 3),
    ('travel.itineraries (synthetic seed)', 1, 1),
    ('travel.itinerary_stops (synthetic seed)', 6, 6),
    ('knowledge.knowledge_sources', 40, 58),
    ('knowledge.destinations', 44, 66),
    ('knowledge.destination_sources', 65, 116),
    ('knowledge.destination_tags', 88, 208),
    ('knowledge.destination_categories', 12, 12),
    ('knowledge.destination_category_map', 30, 47),
    ('knowledge.knowledge_documents', 29, 52),
    ('knowledge.knowledge_chunks', 58, 81),
    ('knowledge.embedding_spaces', 0, 0),
    ('knowledge.chunk_embeddings', 0, 0),
    ('recommendation.recommendation_requests (synthetic seed)', 1, 1),
    ('recommendation.recommendations (synthetic seed)', 3, 3),
    ('recommendation.recommendation_score_components (synthetic seed)', 9, 9),
    ('integration.external_links', 3, 3),
    ('integration.outbound_clicks (synthetic seed)', 0, 0),
    ('operations.feedback (synthetic seed)', 1, 1),
    ('operations.dataset_import_batches', 5, 6),
    ('system.schema_migrations', 7, 8)
), expected_for_state AS (
    SELECT table_name,
           CASE WHEN state.auth_applied AND table_name='system.schema_migrations'
                THEN CASE WHEN state.shiraz_applied THEN expected_0007 + 1 ELSE expected_0006 + 1 END
                WHEN state.shiraz_applied THEN expected_0007 ELSE expected_0006 END
               + CASE WHEN state.traveler_applied AND table_name='system.schema_migrations' THEN 1 ELSE 0 END
               + CASE WHEN state.task31_applied AND table_name='system.schema_migrations' THEN 1 ELSE 0 END AS expected_count,
           state.shiraz_applied
    FROM expected CROSS JOIN state
)
SELECT e.table_name,
       a.actual_count,
       e.expected_count,
       CASE WHEN a.actual_count = e.expected_count THEN 'PASS' ELSE 'FAIL' END AS result
FROM expected_for_state e
JOIN actual a USING (table_name)

UNION ALL

SELECT 'IMMUTABLE_TOTAL', SUM(a.actual_count), SUM(e.expected_count),
       CASE WHEN SUM(a.actual_count) = SUM(e.expected_count) THEN 'PASS' ELSE 'FAIL' END
FROM expected_for_state e
JOIN actual a USING (table_name)
ORDER BY 1;


-- Runtime identity/auth rows are reported, not compared with seed counts.
DO $$
DECLARE
    runtime_count BIGINT;
    has_auth BOOLEAN;
BEGIN
    SELECT COUNT(*) INTO runtime_count FROM identity.users WHERE is_synthetic=FALSE;
    RAISE NOTICE 'RUNTIME rows (not seed assertions): non-synthetic identity.users=%', runtime_count;
    SELECT COUNT(*) INTO runtime_count FROM conversation.conversations WHERE is_synthetic=FALSE;
    RAISE NOTICE 'RUNTIME rows: non-synthetic conversations=%', runtime_count;
    SELECT COUNT(*) INTO runtime_count FROM conversation.messages WHERE is_synthetic=FALSE;
    RAISE NOTICE 'RUNTIME rows: non-synthetic messages=%', runtime_count;
    SELECT COUNT(*) INTO runtime_count FROM travel.trips WHERE is_synthetic=FALSE;
    RAISE NOTICE 'RUNTIME rows: non-synthetic trips=%', runtime_count;
    SELECT COUNT(*) INTO runtime_count FROM travel.itineraries WHERE is_synthetic=FALSE;
    RAISE NOTICE 'RUNTIME rows: non-synthetic itineraries=%', runtime_count;
    SELECT COUNT(*) INTO runtime_count FROM travel.itinerary_stops WHERE is_synthetic=FALSE;
    RAISE NOTICE 'RUNTIME rows: non-synthetic itinerary stops=%', runtime_count;
    SELECT COUNT(*) INTO runtime_count FROM recommendation.recommendations WHERE is_synthetic=FALSE;
    RAISE NOTICE 'RUNTIME rows: non-synthetic recommendations=%', runtime_count;
    SELECT COUNT(*) INTO runtime_count FROM integration.outbound_clicks WHERE is_synthetic=FALSE;
    RAISE NOTICE 'RUNTIME rows: non-synthetic outbound clicks=%', runtime_count;
    SELECT COUNT(*) INTO runtime_count FROM operations.feedback WHERE is_synthetic=FALSE;
    RAISE NOTICE 'RUNTIME rows: non-synthetic feedback=%', runtime_count;
    SELECT COUNT(*) INTO runtime_count FROM operations.ai_model_calls;
    RAISE NOTICE 'RUNTIME rows: model calls=%', runtime_count;
    SELECT COUNT(*) INTO runtime_count FROM operations.audit_events;
    RAISE NOTICE 'RUNTIME rows: audit events=%', runtime_count;
    SELECT EXISTS (SELECT 1 FROM system.schema_migrations
                   WHERE migration_id='0008_authentication_foundation') INTO has_auth;
    IF has_auth THEN
        EXECUTE 'SELECT COUNT(*) FROM identity.otp_challenges' INTO runtime_count;
        RAISE NOTICE 'RUNTIME rows: identity.otp_challenges=%', runtime_count;
        EXECUTE 'SELECT COUNT(*) FROM identity.verified_phones' INTO runtime_count;
        RAISE NOTICE 'RUNTIME rows: identity.verified_phones=%', runtime_count;
        EXECUTE 'SELECT COUNT(*) FROM identity.web_sessions' INTO runtime_count;
        RAISE NOTICE 'RUNTIME rows: identity.web_sessions=%', runtime_count;
        EXECUTE 'SELECT COUNT(*) FROM identity.auth_rate_limits' INTO runtime_count;
        RAISE NOTICE 'RUNTIME rows: identity.auth_rate_limits=%', runtime_count;
    END IF;
END $$;

-- The report above is also a release gate: fail the psql process on any
-- per-table mismatch or missing table, not merely print a FAIL label.
DO $$
DECLARE
    item RECORD;
    actual_rows BIGINT;
    total_actual BIGINT := 0;
    total_expected BIGINT := 0;
    has_shiraz BOOLEAN;
    has_auth BOOLEAN;
    has_traveler_core BOOLEAN;
    has_task31 BOOLEAN;
    required_total BIGINT;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM system.schema_migrations
        WHERE migration_id = '0007_shiraz_dalahoo_wikipedia_dataset_v1'
    ) INTO has_shiraz;
    SELECT EXISTS (SELECT 1 FROM system.schema_migrations
                   WHERE migration_id = '0008_authentication_foundation') INTO has_auth;
    SELECT EXISTS (SELECT 1 FROM system.schema_migrations
                   WHERE migration_id = '0009_traveler_core') INTO has_traveler_core;
    SELECT EXISTS (SELECT 1 FROM system.schema_migrations
                   WHERE migration_id = '0010_task31_content_privacy_full_itinerary') INTO has_task31;
    -- Counts only the immutable synthetic identity seed; real users and
    -- authentication activity are reported separately below.
    required_total := CASE WHEN has_shiraz THEN 695 ELSE 419 END
        + CASE WHEN has_auth THEN 1 ELSE 0 END
        + CASE WHEN has_traveler_core THEN 1 ELSE 0 END
        + CASE WHEN has_task31 THEN 1 ELSE 0 END;

    FOR item IN
        SELECT schema_name, table_name,
               CASE WHEN schema_name='system' AND table_name='schema_migrations'
                    THEN CASE WHEN has_shiraz THEN expected_0007 ELSE expected_0006 END
                         + CASE WHEN has_auth THEN 1 ELSE 0 END
                         + CASE WHEN has_traveler_core THEN 1 ELSE 0 END
                         + CASE WHEN has_task31 THEN 1 ELSE 0 END
                    WHEN has_shiraz THEN expected_0007 ELSE expected_0006 END AS expected_count
        FROM (VALUES
            ('identity','users',1::BIGINT,1::BIGINT),
            ('identity','user_consents',1,1),
            ('identity','user_preferences',3,3),
            ('conversation','conversations',1,1),
            ('conversation','messages',4,4),
            ('travel','trips',1,1),
            ('travel','trip_constraints',3,3),
            ('travel','trip_interests',3,3),
            ('travel','itineraries',1,1),
            ('travel','itinerary_stops',6,6),
            ('knowledge','knowledge_sources',40,58),
            ('knowledge','destinations',44,66),
            ('knowledge','destination_sources',65,116),
            ('knowledge','destination_tags',88,208),
            ('knowledge','destination_categories',12,12),
            ('knowledge','destination_category_map',30,47),
            ('knowledge','knowledge_documents',29,52),
            ('knowledge','knowledge_chunks',58,81),
            ('knowledge','embedding_spaces',0,0),
            ('knowledge','chunk_embeddings',0,0),
            ('recommendation','recommendation_requests',1,1),
            ('recommendation','recommendations',3,3),
            ('recommendation','recommendation_score_components',9,9),
            ('integration','external_links',3,3),
            ('integration','outbound_clicks',0,0),
            ('operations','feedback',1,1),
            ('operations','dataset_import_batches',5,6),
            ('system','schema_migrations',7,8)
        ) AS x(schema_name, table_name, expected_0006, expected_0007)
    LOOP
        IF to_regclass(format('%I.%I', item.schema_name, item.table_name)) IS NULL THEN
            RAISE EXCEPTION 'Expected table %.% is missing', item.schema_name, item.table_name;
        END IF;
        IF item.schema_name IN ('identity','conversation','travel','recommendation')
           AND item.table_name <> 'auth_rate_limits' THEN
            EXECUTE format('SELECT COUNT(*) FROM %I.%I WHERE is_synthetic=TRUE', item.schema_name, item.table_name)
                INTO actual_rows;
        ELSIF item.schema_name='integration' AND item.table_name='outbound_clicks' THEN
            SELECT COUNT(*) INTO actual_rows FROM integration.outbound_clicks WHERE is_synthetic=TRUE;
        ELSIF item.schema_name='operations' AND item.table_name='feedback' THEN
            SELECT COUNT(*) INTO actual_rows FROM operations.feedback WHERE is_synthetic=TRUE;
        ELSE
            EXECUTE format('SELECT COUNT(*) FROM %I.%I', item.schema_name, item.table_name)
                INTO actual_rows;
        END IF;
        total_actual := total_actual + actual_rows;
        total_expected := total_expected + item.expected_count;
        IF actual_rows <> item.expected_count THEN
            RAISE EXCEPTION 'Row-count mismatch for %.%: expected %, found %',
                item.schema_name, item.table_name, item.expected_count, actual_rows;
        END IF;
    END LOOP;

    IF total_actual <> required_total OR total_expected <> required_total THEN
        RAISE EXCEPTION 'Migration ledger state requires exactly % rows, found % (manifest total %)',
            required_total, total_actual, total_expected;
    END IF;

    IF has_auth AND (to_regclass('identity.otp_challenges') IS NULL
        OR to_regclass('identity.verified_phones') IS NULL
        OR to_regclass('identity.web_sessions') IS NULL
        OR to_regclass('identity.auth_rate_limits') IS NULL) THEN
        RAISE EXCEPTION 'Migration 0008 is recorded but authentication tables are incomplete';
    ELSIF NOT has_auth AND (to_regclass('identity.otp_challenges') IS NOT NULL
        OR to_regclass('identity.verified_phones') IS NOT NULL
        OR to_regclass('identity.web_sessions') IS NOT NULL
        OR to_regclass('identity.auth_rate_limits') IS NOT NULL) THEN
        RAISE EXCEPTION 'Authentication tables exist without Migration 0008 ledger entry';
    END IF;

    IF has_task31 THEN
        IF to_regclass('knowledge.destination_enrichment_proposals') IS NULL
           OR to_regclass('knowledge.destination_enrichment_proposal_sources') IS NULL
           OR to_regclass('knowledge.culinary_knowledge_items') IS NULL
           OR to_regclass('knowledge.culinary_item_sources') IS NULL
           OR to_regclass('knowledge.production_culinary_knowledge') IS NULL THEN
            RAISE EXCEPTION 'Migration 0010 is recorded but Task 3.1 objects are incomplete';
        END IF;
        RAISE NOTICE 'RUNTIME/review rows (not immutable seed assertions): spatial proposals=%, spatial provenance edges=%, culinary proposals=%, culinary source edges=%',
            (SELECT COUNT(*) FROM knowledge.destination_enrichment_proposals),
            (SELECT COUNT(*) FROM knowledge.destination_enrichment_proposal_sources),
            (SELECT COUNT(*) FROM knowledge.culinary_knowledge_items),
            (SELECT COUNT(*) FROM knowledge.culinary_item_sources);
    ELSIF to_regclass('knowledge.culinary_knowledge_items') IS NOT NULL THEN
        RAISE EXCEPTION 'Task 3.1 proposal tables exist without Migration 0010 ledger entry';
    END IF;

    RAISE NOTICE 'PASS: immutable seed and migration row-count manifest; total = % (runtime identities, auth rows and proposals excluded).', total_actual;
END $$;
