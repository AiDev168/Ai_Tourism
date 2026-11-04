\set ON_ERROR_STOP on

DO $$
DECLARE
    v_orphans BIGINT;
BEGIN
    SELECT COUNT(*) INTO v_orphans
      FROM knowledge.destination_sources ds
      LEFT JOIN knowledge.destinations d ON d.destination_id = ds.destination_id
      LEFT JOIN knowledge.knowledge_sources s ON s.source_id = ds.source_id
     WHERE d.destination_id IS NULL OR s.source_id IS NULL;
    IF v_orphans <> 0 THEN RAISE EXCEPTION 'Found % orphan destination-source links', v_orphans; END IF;

    SELECT COUNT(*) INTO v_orphans
      FROM knowledge.knowledge_chunks c
      LEFT JOIN knowledge.knowledge_documents d ON d.document_id = c.document_id
     WHERE d.document_id IS NULL;
    IF v_orphans <> 0 THEN RAISE EXCEPTION 'Found % orphan knowledge chunks', v_orphans; END IF;

    SELECT COUNT(*) INTO v_orphans
      FROM recommendation.recommendations r
      LEFT JOIN knowledge.destinations d ON d.destination_id = r.destination_id
      LEFT JOIN recommendation.recommendation_requests q ON q.recommendation_request_id = r.recommendation_request_id
     WHERE d.destination_id IS NULL OR q.recommendation_request_id IS NULL;
    IF v_orphans <> 0 THEN RAISE EXCEPTION 'Found % orphan recommendation rows', v_orphans; END IF;

    SELECT COUNT(*) INTO v_orphans
      FROM travel.itinerary_stops s
      LEFT JOIN travel.itineraries i ON i.itinerary_id = s.itinerary_id
      LEFT JOIN knowledge.destinations d ON d.destination_id = s.destination_id
     WHERE i.itinerary_id IS NULL OR d.destination_id IS NULL;
    IF v_orphans <> 0 THEN RAISE EXCEPTION 'Found % orphan itinerary stops', v_orphans; END IF;

    -- Scores are traceable: exactly three persisted score components per QA recommendation.
    IF EXISTS (
        SELECT r.recommendation_id
          FROM recommendation.recommendations r
          LEFT JOIN recommendation.recommendation_score_components s
            ON s.recommendation_id = r.recommendation_id
         GROUP BY r.recommendation_id
        HAVING COUNT(s.score_component_id) <> 3
    ) THEN RAISE EXCEPTION 'Each synthetic recommendation must have exactly 3 score components'; END IF;

    IF EXISTS (
        SELECT r.recommendation_id
          FROM recommendation.recommendations r
          JOIN recommendation.recommendation_score_components s
            ON s.recommendation_id = r.recommendation_id
         GROUP BY r.recommendation_id, r.final_score
        HAVING ABS(SUM(s.weighted_score) - r.final_score) > 0.000001
    ) THEN RAISE EXCEPTION 'Recommendation final_score does not equal the sum of its weighted score components'; END IF;

    IF EXISTS (
        SELECT i.itinerary_id
          FROM travel.itineraries i
          JOIN travel.itinerary_stops s ON s.itinerary_id = i.itinerary_id
         GROUP BY i.itinerary_id, i.day_count
        HAVING MIN(s.day_number) <> 1 OR MAX(s.day_number) <> i.day_count
    ) THEN RAISE EXCEPTION 'Itinerary stops do not span the declared day_count'; END IF;

    RAISE NOTICE 'PASS: no orphan records; recommendation scores reconcile; itinerary day coverage is consistent.';
END $$;
