\set ON_ERROR_STOP on

DO $$
DECLARE
    n BIGINT;
BEGIN
    SELECT COUNT(*) INTO n
      FROM knowledge.destinations
     WHERE destination_key LIKE 'unesco-%-v1'
       AND record_origin='verified_external'
       AND verification_status='verified'
       AND status='needs_review'
       AND is_synthetic=FALSE
       AND coordinate_role='property_reference'
       AND location IS NOT NULL;
    IF n <> 10 THEN RAISE EXCEPTION 'Expected 10 externally sourced UNESCO destinations held for editorial review; found %', n; END IF;

    -- Keep this first-batch assertion scoped to its ten destinations.
    -- Later UNESCO batches add sources to the same global source table.
    SELECT COUNT(DISTINCT s.source_id) INTO n
      FROM knowledge.knowledge_sources s
      JOIN knowledge.destination_sources ds ON ds.source_id=s.source_id
      JOIN knowledge.destinations d ON d.destination_id=ds.destination_id
     WHERE d.destination_key LIKE 'unesco-%-v1'
       AND s.source_name LIKE 'UNESCO WHC %'
       AND s.verification_status='verified' AND s.is_synthetic=FALSE
       AND s.url LIKE 'https://whc.unesco.org/%';
    IF n <> 20 THEN RAISE EXCEPTION 'Expected 20 official UNESCO property/map sources for the first batch; found %', n; END IF;

    SELECT COUNT(*) INTO n
      FROM knowledge.destination_sources ds
      JOIN knowledge.destinations d ON d.destination_id=ds.destination_id
     WHERE d.destination_key LIKE 'unesco-%-v1';
    IF n <> 22 THEN RAISE EXCEPTION 'Expected 22 source links for the 10 UNESCO sites; found %', n; END IF;

    SELECT COUNT(*) INTO n
      FROM knowledge.destination_sources ds
      JOIN knowledge.destinations d ON d.destination_id=ds.destination_id
      JOIN knowledge.knowledge_sources s ON s.source_id=ds.source_id
     WHERE d.destination_key LIKE 'unesco-%-v1'
       AND s.source_name LIKE 'UNESCO WHC %'
       AND s.url LIKE 'https://whc.unesco.org/%';
    IF n <> 20 THEN RAISE EXCEPTION 'Expected 20 direct UNESCO property/map provenance links; found %', n; END IF;

    SELECT COUNT(*) INTO n
      FROM knowledge.destination_sources ds
      JOIN knowledge.destinations d ON d.destination_id=ds.destination_id
      JOIN knowledge.knowledge_sources s ON s.source_id=ds.source_id
     WHERE d.destination_key LIKE 'unesco-%-v1'
       AND s.source_name IN (
         'ICID World Heritage Irrigation Structures: Shushtar — location',
         'UNESCO ICOMOS evaluation: Gonbad-e Qābus — location'
       );
    IF n <> 2 THEN RAISE EXCEPTION 'Expected two supplemental administrative-location references; found %', n; END IF;

    SELECT COUNT(*) INTO n
      FROM knowledge.knowledge_documents d
      JOIN knowledge.destinations x ON x.destination_id=d.destination_id
     WHERE x.destination_key LIKE 'unesco-%-v1'
       AND d.record_origin='verified_external' AND d.is_synthetic=FALSE
       AND d.ingestion_status='processed' AND d.language_code='fa';
    IF n <> 10 THEN RAISE EXCEPTION 'Expected 10 processed Persian factual documents; found %', n; END IF;

    SELECT COUNT(*) INTO n
      FROM knowledge.knowledge_chunks c
      JOIN knowledge.knowledge_documents d ON d.document_id=c.document_id
     WHERE d.document_key LIKE 'unesco-%-v1-doc' AND c.is_synthetic=FALSE;
    IF n <> 20 THEN RAISE EXCEPTION 'Expected 20 non-synthetic chunks attached to UNESCO factual docs; found %', n; END IF;

    IF EXISTS (
        SELECT 1
          FROM knowledge.destinations d
         WHERE d.destination_key LIKE 'unesco-%-v1'
           AND (
             d.latitude NOT BETWEEN 24 AND 40
             OR d.longitude NOT BETWEEN 43 AND 64
             OR d.coordinate_role <> 'property_reference'
             OR ST_IsEmpty(d.location::geometry)
             OR ABS(ST_Y(d.location::geometry)-d.latitude) > 0.000001
             OR ABS(ST_X(d.location::geometry)-d.longitude) > 0.000001
           )
    ) THEN RAISE EXCEPTION 'A factual destination has an invalid Iran-range/reference coordinate or geography mismatch'; END IF;

    IF EXISTS (
        SELECT 1
          FROM (VALUES
            ('unesco-persepolis-v1', 29.9344400::DOUBLE PRECISION, 52.8902800::DOUBLE PRECISION),
            ('unesco-golestan-palace-v1', 35.6803667, 51.4205111),
            ('unesco-meidan-emam-v1', 32.6574500, 51.6777778),
            ('unesco-tabriz-bazaar-v1', 38.0813889, 46.2930556),
            ('unesco-shushtar-hydraulic-v1', 32.0186111, 48.8358333),
            ('unesco-bam-cultural-landscape-v1', 29.1168300, 58.3666667),
            ('unesco-soltaniyeh-v1', 36.4339722, 48.7960278),
            ('unesco-bisotun-v1', 34.3883333, 47.4366667),
            ('unesco-pasargadae-v1', 30.1938300, 53.1672900),
            ('unesco-gonbad-e-qabus-v1', 37.2580278, 55.1690000)
          ) AS expected(destination_key, latitude, longitude)
          LEFT JOIN knowledge.destinations d ON d.destination_key=expected.destination_key
         WHERE d.destination_id IS NULL
            OR ABS(d.latitude-expected.latitude) > 0.000001
            OR ABS(d.longitude-expected.longitude) > 0.000001
    ) THEN RAISE EXCEPTION 'One or more UNESCO reference coordinates differ from the curated source values'; END IF;

    IF EXISTS (
        SELECT 1
          FROM knowledge.destinations d
         WHERE d.destination_key LIKE 'unesco-%-v1'
           AND d.status <> 'needs_review'
    ) THEN RAISE EXCEPTION 'Source verification must not auto-publish a destination; all first-batch rows must remain needs_review'; END IF;

    SELECT COUNT(*) INTO n FROM knowledge.production_destinations;
    IF n <> 0 THEN RAISE EXCEPTION 'No first-batch UNESCO destination may publish before explicit editorial approval'; END IF;
    SELECT COUNT(*) INTO n FROM knowledge.production_retrieval_documents;
    IF n <> 0 THEN RAISE EXCEPTION 'First-batch documents attached to needs_review sites must not enter production RAG'; END IF;

    IF EXISTS (
        SELECT 1
          FROM knowledge.knowledge_documents d
          JOIN knowledge.knowledge_sources s ON s.source_id=d.source_id
         WHERE d.document_key LIKE 'unesco-%-v1-doc'
           AND (s.verification_status <> 'verified' OR s.is_synthetic
             OR s.url <> d.canonical_url OR s.source_type <> 'world_heritage_description')
    ) THEN RAISE EXCEPTION 'A factual document is not linked to its exact verified primary description source'; END IF;

    IF EXISTS (
        SELECT 1
          FROM knowledge.knowledge_documents d
         WHERE d.document_key LIKE 'unesco-%-v1-doc'
           AND d.content_sha256 <> encode(sha256(convert_to(d.raw_content,'UTF8')),'hex')
    ) THEN RAISE EXCEPTION 'A stored factual document content hash is invalid'; END IF;

    IF EXISTS (
        SELECT 1
          FROM knowledge.knowledge_chunks c
          JOIN knowledge.knowledge_documents d ON d.document_id=c.document_id
         WHERE d.document_key LIKE 'unesco-%-v1-doc'
           AND (c.char_count <> CHAR_LENGTH(c.content)
             OR c.content_sha256 <> encode(sha256(convert_to(c.content,'UTF8')),'hex'))
    ) THEN RAISE EXCEPTION 'A stored factual chunk character count or hash is invalid'; END IF;

    RAISE NOTICE 'PASS: 10 UNESCO factual records, 20 official and 2 supplemental provenance links, exact source/document links, coordinates, 10 docs, 20 chunks, hashes and editorial publication gate.';
END $$;
