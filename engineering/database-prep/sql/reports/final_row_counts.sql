\set ON_ERROR_STOP on

WITH actual(table_name, actual_count) AS (
    SELECT 'identity.users', COUNT(*)::BIGINT FROM identity.users
    UNION ALL SELECT 'identity.user_consents', COUNT(*) FROM identity.user_consents
    UNION ALL SELECT 'identity.user_preferences', COUNT(*) FROM identity.user_preferences
    UNION ALL SELECT 'conversation.conversations', COUNT(*) FROM conversation.conversations
    UNION ALL SELECT 'conversation.messages', COUNT(*) FROM conversation.messages
    UNION ALL SELECT 'travel.trips', COUNT(*) FROM travel.trips
    UNION ALL SELECT 'travel.trip_constraints', COUNT(*) FROM travel.trip_constraints
    UNION ALL SELECT 'travel.trip_interests', COUNT(*) FROM travel.trip_interests
    UNION ALL SELECT 'travel.itineraries', COUNT(*) FROM travel.itineraries
    UNION ALL SELECT 'travel.itinerary_stops', COUNT(*) FROM travel.itinerary_stops
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
    UNION ALL SELECT 'recommendation.recommendation_requests', COUNT(*) FROM recommendation.recommendation_requests
    UNION ALL SELECT 'recommendation.recommendations', COUNT(*) FROM recommendation.recommendations
    UNION ALL SELECT 'recommendation.recommendation_score_components', COUNT(*) FROM recommendation.recommendation_score_components
    UNION ALL SELECT 'integration.external_links', COUNT(*) FROM integration.external_links
    UNION ALL SELECT 'integration.outbound_clicks', COUNT(*) FROM integration.outbound_clicks
    UNION ALL SELECT 'operations.feedback', COUNT(*) FROM operations.feedback
    UNION ALL SELECT 'operations.ai_model_calls', COUNT(*) FROM operations.ai_model_calls
    UNION ALL SELECT 'operations.audit_events', COUNT(*) FROM operations.audit_events
    UNION ALL SELECT 'operations.dataset_import_batches', COUNT(*) FROM operations.dataset_import_batches
    UNION ALL SELECT 'system.schema_migrations', COUNT(*) FROM system.schema_migrations
), expected(table_name, expected_count) AS (
    VALUES
    ('identity.users', 1::BIGINT),
    ('identity.user_consents', 1),
    ('identity.user_preferences', 3),
    ('conversation.conversations', 1),
    ('conversation.messages', 4),
    ('travel.trips', 1),
    ('travel.trip_constraints', 3),
    ('travel.trip_interests', 3),
    ('travel.itineraries', 1),
    ('travel.itinerary_stops', 6),
    ('knowledge.knowledge_sources', 40),
    ('knowledge.destinations', 44),
    ('knowledge.destination_sources', 65),
    ('knowledge.destination_tags', 88),
    ('knowledge.destination_categories', 12),
    ('knowledge.destination_category_map', 30),
    ('knowledge.knowledge_documents', 29),
    ('knowledge.knowledge_chunks', 58),
    ('knowledge.embedding_spaces', 0),
    ('knowledge.chunk_embeddings', 0),
    ('recommendation.recommendation_requests', 1),
    ('recommendation.recommendations', 3),
    ('recommendation.recommendation_score_components', 9),
    ('integration.external_links', 3),
    ('integration.outbound_clicks', 0),
    ('operations.feedback', 1),
    ('operations.ai_model_calls', 0),
    ('operations.audit_events', 0),
    ('operations.dataset_import_batches', 5),
    ('system.schema_migrations', 7)
)
SELECT e.table_name,
       a.actual_count,
       e.expected_count,
       CASE WHEN a.actual_count = e.expected_count THEN 'PASS' ELSE 'FAIL' END AS result
FROM expected e
JOIN actual a USING (table_name)

UNION ALL

SELECT 'TOTAL', SUM(a.actual_count), SUM(e.expected_count),
       CASE WHEN SUM(a.actual_count) = SUM(e.expected_count) THEN 'PASS' ELSE 'FAIL' END
FROM expected e
JOIN actual a USING (table_name)
ORDER BY 1;


-- The report above is also a release gate: fail the psql process on any
-- per-table mismatch or missing table, not merely print a FAIL label.
DO $$
DECLARE
    item RECORD;
    actual_rows BIGINT;
    total_actual BIGINT := 0;
    total_expected BIGINT := 0;
BEGIN
    FOR item IN
        SELECT * FROM (VALUES
            ('identity','users',1::BIGINT),
            ('identity','user_consents',1),
            ('identity','user_preferences',3),
            ('conversation','conversations',1),
            ('conversation','messages',4),
            ('travel','trips',1),
            ('travel','trip_constraints',3),
            ('travel','trip_interests',3),
            ('travel','itineraries',1),
            ('travel','itinerary_stops',6),
            ('knowledge','knowledge_sources',40),
            ('knowledge','destinations',44),
            ('knowledge','destination_sources',65),
            ('knowledge','destination_tags',88),
            ('knowledge','destination_categories',12),
            ('knowledge','destination_category_map',30),
            ('knowledge','knowledge_documents',29),
            ('knowledge','knowledge_chunks',58),
            ('knowledge','embedding_spaces',0),
            ('knowledge','chunk_embeddings',0),
            ('recommendation','recommendation_requests',1),
            ('recommendation','recommendations',3),
            ('recommendation','recommendation_score_components',9),
            ('integration','external_links',3),
            ('integration','outbound_clicks',0),
            ('operations','feedback',1),
            ('operations','ai_model_calls',0),
            ('operations','audit_events',0),
            ('operations','dataset_import_batches',5),
            ('system','schema_migrations',7)
        ) AS x(schema_name, table_name, expected_count)
    LOOP
        IF to_regclass(format('%I.%I', item.schema_name, item.table_name)) IS NULL THEN
            RAISE EXCEPTION 'Expected table %.% is missing', item.schema_name, item.table_name;
        END IF;
        EXECUTE format('SELECT COUNT(*) FROM %I.%I', item.schema_name, item.table_name)
            INTO actual_rows;
        total_actual := total_actual + actual_rows;
        total_expected := total_expected + item.expected_count;
        IF actual_rows <> item.expected_count THEN
            RAISE EXCEPTION 'Row-count mismatch for %.%: expected %, found %',
                item.schema_name, item.table_name, item.expected_count, actual_rows;
        END IF;
    END LOOP;

    IF total_actual <> 419 OR total_expected <> 419 THEN
        RAISE EXCEPTION 'Total row-count mismatch: expected 419, found % (manifest total %)',
            total_actual, total_expected;
    END IF;

    RAISE NOTICE 'PASS: all 30 expected tables have exact per-table counts; total rows = 419.';
END $$;
