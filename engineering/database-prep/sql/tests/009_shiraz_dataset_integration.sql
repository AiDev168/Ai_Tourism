\set ON_ERROR_STOP on

DO $$
DECLARE
    n BIGINT;
    v_city_id BIGINT;
BEGIN
    SELECT COUNT(*) INTO n FROM knowledge.destinations WHERE destination_key LIKE 'shiraz-%-v1';
    IF n <> 22 THEN RAISE EXCEPTION 'Expected 22 Shiraz pilot entities, found %', n; END IF;

    IF EXISTS (
        SELECT 1 FROM knowledge.destinations
        WHERE destination_key LIKE 'shiraz-%-v1'
          AND (record_origin <> 'verified_external' OR is_synthetic IS DISTINCT FROM FALSE
               OR verification_status <> 'verified' OR status <> 'needs_review' OR data_confidence <> 0)
    ) THEN RAISE EXCEPTION 'A Shiraz candidate has incorrect classification or publication status'; END IF;

    SELECT destination_id INTO v_city_id FROM knowledge.destinations WHERE destination_key='shiraz-city-v1';
    IF v_city_id IS NULL THEN RAISE EXCEPTION 'Shiraz parent destination was not imported'; END IF;
    SELECT COUNT(*) INTO n FROM knowledge.destinations
     WHERE destination_key LIKE 'shiraz-%-v1' AND parent_destination_id=v_city_id;
    IF n <> 20 THEN RAISE EXCEPTION 'Expected 20 in-city attractions/food children under Shiraz, found %', n; END IF;

    SELECT COUNT(*) INTO n FROM knowledge.destinations
     WHERE destination_key LIKE 'shiraz-%-v1' AND destination_type IN ('food_dish','local_sweet','local_drink')
       AND parent_destination_id=v_city_id AND latitude IS NULL AND longitude IS NULL AND coordinate_role='unknown';
    IF n <> 9 THEN RAISE EXCEPTION 'Expected nine food/product experiences with unknown coordinates, found %', n; END IF;

    SELECT COUNT(*) INTO n FROM knowledge.destinations
     WHERE destination_key='shiraz-naqsh-e-rostam-v1' AND province_name='فارس' AND city_name='مرودشت'
       AND parent_destination_id IS NULL AND coordinate_role='representative_point'
       AND status='needs_review' AND is_synthetic=FALSE;
    IF n <> 1 THEN RAISE EXCEPTION 'Naqsh-e Rostam must remain a separate nearby-trip entity in Marvdasht'; END IF;
    IF NOT EXISTS (
        SELECT 1 FROM knowledge.destination_tags t
        JOIN knowledge.destinations d USING(destination_id)
        WHERE d.destination_key='shiraz-naqsh-e-rostam-v1' AND t.tag='destination_scope:nearby_trip'
    ) THEN RAISE EXCEPTION 'Naqsh-e Rostam nearby-trip scope tag is missing'; END IF;

    SELECT COUNT(*) INTO n FROM knowledge.destinations
     WHERE canonical_name='رصدخانه مراغه' AND province_name='آذربایجان شرقی' AND city_name='مراغه';
    IF n <> 1 THEN RAISE EXCEPTION 'Maragheh Observatory identity was duplicated'; END IF;
    IF NOT EXISTS (
        SELECT 1 FROM knowledge.destinations
        WHERE canonical_name='رصدخانه مراغه' AND province_name='آذربایجان شرقی' AND city_name='مراغه'
          AND destination_type='historical_astronomical_site'
          AND record_origin='verified_external' AND is_synthetic=FALSE
          AND verification_status='verified' AND status='needs_review' AND data_confidence=0
          AND coordinate_role='representative_point'
          AND latitude=37.396111 AND longitude=46.209167
          AND difficulty IS NULL AND suitable_transport IS NULL AND local_language IS NULL
          AND local_food IS NULL AND local_souvenirs IS NULL AND best_travel_time IS NULL
    ) THEN RAISE EXCEPTION 'Maragheh Observatory enrichment/classification/unknown-value clearing is incorrect'; END IF;
    IF EXISTS (
        SELECT 1 FROM knowledge.destination_tags t
        JOIN knowledge.destinations d USING(destination_id)
        WHERE d.canonical_name='رصدخانه مراغه' AND d.province_name='آذربایجان شرقی' AND d.city_name='مراغه'
          AND t.tag IN ('آسان','transport:سواری')
    ) THEN RAISE EXCEPTION 'Unsupported legacy Maragheh tags remain'; END IF;

    -- Existing UNESCO entities must stay singular and retain their established points.
    IF (SELECT COUNT(*) FROM knowledge.destinations WHERE destination_key='unesco-persepolis-v1') <> 1
       OR (SELECT COUNT(*) FROM knowledge.destinations WHERE destination_key='unesco-pasargadae-v1') <> 1
    THEN RAISE EXCEPTION 'Shiraz import duplicated an existing UNESCO destination'; END IF;
    IF NOT EXISTS (SELECT 1 FROM knowledge.destinations WHERE destination_key='unesco-persepolis-v1'
                   AND latitude=29.93444 AND longitude=52.89028 AND coordinate_role='property_reference')
       OR NOT EXISTS (SELECT 1 FROM knowledge.destinations WHERE destination_key='unesco-pasargadae-v1'
                      AND latitude=30.19383 AND longitude=53.16729 AND coordinate_role='property_reference')
    THEN RAISE EXCEPTION 'Existing UNESCO reference points were changed'; END IF;

    SELECT COUNT(*) INTO n FROM knowledge.knowledge_sources
     WHERE source_name IN (
       'Dalahoo domestic destination index','Dalahoo Shiraz destination guide','Wikipedia — Shiraz',
       'Wikipedia — Tomb of Hafez','Wikipedia — Tomb of Saadi','Wikipedia — Arg of Karim Khan',
       'Wikipedia — Qavam House','Wikipedia — Eram Garden','Wikipedia — Delgosha Garden',
       'Wikipedia — Vakil Bathhouse','Wikipedia — Shah Cheragh','Wikipedia — Vakil Bazaar',
       'Wikipedia — Nasir-ol-Molk Mosque','Wikipedia — Afif-Abad Garden','Wikipedia — Naqsh-e Rostam',
       'Dalahoo Maragheh Observatory destination guide',
       'UNESCO Portal to the Heritage of Astronomy — Maragheh Observatory',
       'Mapcarta / OpenStreetMap — Maragheh Observatory'
     ) AND verification_status='verified' AND is_synthetic=FALSE;
    IF n <> 18 THEN RAISE EXCEPTION 'Expected 18 verified non-synthetic Shiraz dataset sources, found %', n; END IF;

    SELECT COUNT(*) INTO n FROM knowledge.destination_sources ds
      JOIN knowledge.knowledge_sources s USING(source_id)
     WHERE s.source_name IN (
       'Dalahoo domestic destination index','Dalahoo Shiraz destination guide','Wikipedia — Shiraz',
       'Wikipedia — Tomb of Hafez','Wikipedia — Tomb of Saadi','Wikipedia — Arg of Karim Khan',
       'Wikipedia — Qavam House','Wikipedia — Eram Garden','Wikipedia — Delgosha Garden',
       'Wikipedia — Vakil Bathhouse','Wikipedia — Shah Cheragh','Wikipedia — Vakil Bazaar',
       'Wikipedia — Nasir-ol-Molk Mosque','Wikipedia — Afif-Abad Garden','Wikipedia — Naqsh-e Rostam',
       'Dalahoo Maragheh Observatory destination guide',
       'UNESCO Portal to the Heritage of Astronomy — Maragheh Observatory',
       'Mapcarta / OpenStreetMap — Maragheh Observatory'
     );
    IF n <> 51 THEN RAISE EXCEPTION 'Expected 51 new destination/source relationships, found %', n; END IF;

    SELECT COUNT(*) INTO n FROM knowledge.destination_sources ds
      JOIN knowledge.knowledge_sources s USING(source_id)
      JOIN knowledge.destinations d USING(destination_id)
     WHERE s.source_name='Dalahoo domestic destination index'
       AND d.record_origin='user_supplied_unverified' AND d.verification_status='pending'
       AND d.status='needs_review';
    IF n <> 12 THEN RAISE EXCEPTION 'Expected 12 discovery-only links on legacy records excluding enriched Maragheh, found %', n; END IF;

    SELECT COUNT(*) INTO n FROM knowledge.destination_sources ds
      JOIN knowledge.knowledge_sources s USING(source_id)
     WHERE s.source_name='Dalahoo Shiraz destination guide'
       AND ds.destination_id IN (
           SELECT destination_id FROM knowledge.destinations
           WHERE destination_key IN ('unesco-persepolis-v1','unesco-pasargadae-v1')
       ) AND ds.source_role='discovery';
    IF n <> 2 THEN RAISE EXCEPTION 'Expected two discovery-only UNESCO nearby-trip relationships, found %', n; END IF;

    SELECT COUNT(*) INTO n FROM knowledge.knowledge_documents
     WHERE document_key LIKE 'shiraz-%-v1-doc' OR document_key='maragheh-observatory-v1-doc';
    IF n <> 23 THEN RAISE EXCEPTION 'Expected 23 Shiraz/Maragheh Persian documents, found %', n; END IF;
    IF EXISTS (
        SELECT 1 FROM knowledge.knowledge_documents d
        LEFT JOIN knowledge.knowledge_chunks c ON c.document_id=d.document_id
        WHERE (d.document_key LIKE 'shiraz-%-v1-doc' OR d.document_key='maragheh-observatory-v1-doc')
        GROUP BY d.document_id
        HAVING COUNT(c.chunk_id) <> 1 OR MIN(c.chunk_index) <> 0
    ) THEN RAISE EXCEPTION 'Each Shiraz/Maragheh document must have exactly one chunk at index zero'; END IF;
    IF EXISTS (
        SELECT 1 FROM knowledge.knowledge_documents d
        JOIN knowledge.knowledge_chunks c USING(document_id)
        WHERE (d.document_key LIKE 'shiraz-%-v1-doc' OR d.document_key='maragheh-observatory-v1-doc')
          AND (d.language_code <> 'fa' OR d.record_origin <> 'verified_external'
               OR d.is_synthetic IS DISTINCT FROM FALSE OR d.ingestion_status <> 'processed'
               OR d.content_sha256 <> encode(sha256(convert_to(d.raw_content,'UTF8')),'hex')
               OR c.is_synthetic IS DISTINCT FROM FALSE
               OR c.char_count <> CHAR_LENGTH(c.content)
               OR c.content_sha256 <> encode(sha256(convert_to(c.content,'UTF8')),'hex')
               OR c.content IS DISTINCT FROM d.raw_content)
    ) THEN RAISE EXCEPTION 'A Shiraz/Maragheh document or chunk has invalid markers/content/hash/count'; END IF;

    IF EXISTS (
        SELECT 1 FROM knowledge.destinations
        WHERE destination_key LIKE 'shiraz-%-v1'
          AND destination_key <> 'shiraz-city-v1'
          AND latitude IS NOT NULL AND coordinate_role <> 'representative_point'
    ) THEN RAISE EXCEPTION 'A Shiraz dataset coordinate is not marked as a representative point'; END IF;

    SELECT COUNT(*) INTO n FROM knowledge.production_destinations WHERE destination_key LIKE 'shiraz-%-v1';
    IF n <> 0 THEN RAISE EXCEPTION 'Shiraz candidates leaked into production destinations before editorial review'; END IF;
    SELECT COUNT(*) INTO n FROM knowledge.production_retrieval_documents
     WHERE document_key LIKE 'shiraz-%-v1-doc' OR document_key='maragheh-observatory-v1-doc';
    IF n <> 0 THEN RAISE EXCEPTION 'Shiraz/Maragheh documents leaked into production retrieval before editorial review'; END IF;
    SELECT COUNT(*) INTO n FROM knowledge.embedding_spaces;
    IF n <> 0 THEN RAISE EXCEPTION 'Dataset import must not create an embedding space'; END IF;
    SELECT COUNT(*) INTO n FROM knowledge.chunk_embeddings;
    IF n <> 0 THEN RAISE EXCEPTION 'Dataset import must not create embeddings'; END IF;

    IF (SELECT count(*) FROM operations.dataset_import_batches WHERE batch_key='shiraz-dalahoo-wikipedia-v1'
        AND source_checksum='16c42d6b34c012379712404b9699d15b971393f78980098c0be8520bcfa23e62'
        AND record_counts->>'catalogue_entities'='22'
        AND record_counts->>'knowledge_documents'='23'
        AND record_counts->>'knowledge_chunks'='23'
        AND record_counts->>'sources_in_package'='18') <> 1
    THEN RAISE EXCEPTION 'Shiraz dataset import batch ledger is missing or inconsistent'; END IF;

    RAISE NOTICE 'PASS: Shiraz catalogue hierarchy/scope, provenance, Maragheh enrichment, UNESCO preservation, 23 documents/chunks, no embeddings and publication isolation.';
END $$;
