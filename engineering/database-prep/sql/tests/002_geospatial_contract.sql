\set ON_ERROR_STOP on

DO $$
DECLARE
    v_distance DOUBLE PRECISION;
    v_index_count INTEGER;
    v_neighbor_count INTEGER;
    v_alias_index_count INTEGER;
BEGIN
    SELECT ST_Distance(a.location, b.location)
      INTO v_distance
      FROM knowledge.destinations a
      JOIN knowledge.destinations b ON b.destination_key = 'qa-mountain-02'
     WHERE a.destination_key = 'qa-forest-01';

    IF v_distance IS NULL OR v_distance < 1000 OR v_distance > 1200 THEN
        RAISE EXCEPTION 'Unexpected PostGIS distance between synthetic coordinates: % meters', v_distance;
    END IF;

    SELECT COUNT(*) INTO v_index_count
      FROM pg_indexes
     WHERE schemaname = 'knowledge'
       AND tablename = 'destinations'
       AND indexname = 'idx_destinations_location_gist'
       AND indexdef ILIKE '%USING gist%';

    IF v_index_count <> 1 THEN
        RAISE EXCEPTION 'Expected GiST index idx_destinations_location_gist';
    END IF;

    SELECT COUNT(*) INTO v_alias_index_count
      FROM pg_indexes
     WHERE schemaname = 'knowledge'
       AND tablename = 'destinations'
       AND indexname = 'idx_destinations_aliases_gin'
       AND indexdef ILIKE '%USING gin%';

    IF v_alias_index_count <> 1 THEN
        RAISE EXCEPTION 'Expected GIN index idx_destinations_aliases_gin';
    END IF;

    IF EXISTS (SELECT 1 FROM knowledge.destinations WHERE destination_key LIKE 'qa-%' AND coordinate_role <> 'test_fixture') THEN
        RAISE EXCEPTION 'Every synthetic coordinate must be explicitly marked test_fixture';
    END IF;
    IF EXISTS (SELECT 1 FROM knowledge.destinations WHERE record_origin = 'user_supplied_unverified' AND (latitude IS NOT NULL OR longitude IS NOT NULL OR coordinate_role <> 'unknown')) THEN
        RAISE EXCEPTION 'Unenriched legacy unverified records must not gain invented coordinates';
    END IF;

    SELECT COUNT(*) INTO v_neighbor_count
      FROM knowledge.destinations d
     WHERE d.destination_key LIKE 'qa-%'
       AND ST_DWithin(
            d.location,
            (SELECT location FROM knowledge.destinations WHERE destination_key = 'qa-forest-01'),
            1200
       );

    IF v_neighbor_count < 3 THEN
        RAISE EXCEPTION 'Expected at least 3 synthetic points within 1.2 km of QA origin; found %', v_neighbor_count;
    END IF;

    RAISE NOTICE 'PASS: PostGIS geography, distance calculation, ST_DWithin, GiST spatial index and GIN alias index.';
END $$;
