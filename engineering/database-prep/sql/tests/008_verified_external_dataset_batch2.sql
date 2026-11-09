\set ON_ERROR_STOP on

DO $$
DECLARE
    n BIGINT;
BEGIN
    -- Seven exact destination keys from the second curated batch.
    SELECT COUNT(*) INTO n
    FROM knowledge.destinations
    WHERE destination_key IN (
        'unesco-takht-e-soleyman-v2',
        'unesco-tchogha-zanbil-v2',
        'unesco-sheikh-safi-ardabil-v2',
        'unesco-masjed-jame-isfahan-v2',
        'unesco-shahr-i-sokhta-v2',
        'unesco-maymand-v2',
        'unesco-hegmataneh-v2'
    );
    IF n <> 7 THEN
        RAISE EXCEPTION 'Expected seven second-batch UNESCO destinations; found %', n;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM knowledge.destinations
        WHERE destination_key IN (
            'unesco-takht-e-soleyman-v2',
            'unesco-tchogha-zanbil-v2',
            'unesco-sheikh-safi-ardabil-v2',
            'unesco-masjed-jame-isfahan-v2',
            'unesco-shahr-i-sokhta-v2',
            'unesco-maymand-v2',
            'unesco-hegmataneh-v2'
        )
        AND (
            record_origin <> 'verified_external'
            OR verification_status <> 'verified'
            OR status <> 'needs_review'
            OR is_synthetic
            OR coordinate_role <> 'property_reference'
            OR location IS NULL
            OR data_confidence <> 0
        )
    ) THEN
        RAISE EXCEPTION 'Second-batch factual destinations must remain source-verified, non-synthetic, needs_review and property-reference only';
    END IF;

    -- All seven names must be linked to one description and one official map source.
    SELECT COUNT(*) INTO n
    FROM knowledge.destination_sources ds
    JOIN knowledge.destinations d ON d.destination_id=ds.destination_id
    JOIN knowledge.knowledge_sources s ON s.source_id=ds.source_id
    WHERE d.destination_key IN (
        'unesco-takht-e-soleyman-v2',
        'unesco-tchogha-zanbil-v2',
        'unesco-sheikh-safi-ardabil-v2',
        'unesco-masjed-jame-isfahan-v2',
        'unesco-shahr-i-sokhta-v2',
        'unesco-maymand-v2',
        'unesco-hegmataneh-v2'
    )
    AND s.source_name LIKE 'UNESCO WHC %'
    AND s.url LIKE 'https://whc.unesco.org/en/list/%';
    IF n <> 14 THEN
        RAISE EXCEPTION 'Expected 14 direct UNESCO property-description/map links; found %', n;
    END IF;

    SELECT COUNT(*) INTO n
    FROM knowledge.destination_sources ds
    JOIN knowledge.destinations d ON d.destination_id=ds.destination_id
    JOIN knowledge.knowledge_sources s ON s.source_id=ds.source_id
    WHERE d.destination_key IN ('unesco-shahr-i-sokhta-v2','unesco-maymand-v2')
      AND s.source_name IN (
        'UNESCO WHC Nomination 1456: Shahr-i Sokhta — administrative location',
        'UNESCO ICOMOS Evaluation 1423rev: Maymand — administrative location'
      );
    IF n <> 2 THEN
        RAISE EXCEPTION 'Expected two supplemental official administrative-location references; found %', n;
    END IF;

    SELECT COUNT(*) INTO n
    FROM knowledge.knowledge_sources
    WHERE source_name IN (
        'UNESCO WHC 1077: Takht-e Soleyman — description',
        'UNESCO WHC 1077: Takht-e Soleyman — mapped property point',
        'UNESCO WHC 113: Tchogha Zanbil — description',
        'UNESCO WHC 113: Tchogha Zanbil — mapped property point',
        'UNESCO WHC 1345: Sheikh Safi al-din Khānegāh and Shrine Ensemble in Ardabil — description',
        'UNESCO WHC 1345: Sheikh Safi al-din Khānegāh and Shrine Ensemble in Ardabil — mapped property point',
        'UNESCO WHC 1397: Masjed-e Jāmé of Isfahan — description',
        'UNESCO WHC 1397: Masjed-e Jāmé of Isfahan — mapped property point',
        'UNESCO WHC 1456: Shahr-i Sokhta — description',
        'UNESCO WHC 1456: Shahr-i Sokhta — mapped property point',
        'UNESCO WHC 1423: Cultural Landscape of Maymand — description',
        'UNESCO WHC 1423: Cultural Landscape of Maymand — mapped property point',
        'UNESCO WHC 1716: Hegmataneh — description',
        'UNESCO WHC 1716: Hegmataneh — mapped property point',
        'UNESCO WHC Nomination 1456: Shahr-i Sokhta — administrative location',
        'UNESCO ICOMOS Evaluation 1423rev: Maymand — administrative location'
    )
    AND verification_status='verified' AND is_synthetic=FALSE
    AND reliability_score IS NULL AND url LIKE 'https://%';
    IF n <> 16 THEN
        RAISE EXCEPTION 'Expected 16 verified, non-synthetic, explicit external source records; found %', n;
    END IF;

    -- Exact property/reference coordinate checks. These are not visitor entrances.
    IF EXISTS (
        SELECT 1
        FROM (VALUES
            ('unesco-takht-e-soleyman-v2', 36.6038889::DOUBLE PRECISION, 47.2350000::DOUBLE PRECISION),
            ('unesco-tchogha-zanbil-v2', 32.0085700, 48.5221181),
            ('unesco-sheikh-safi-ardabil-v2', 38.2486111, 48.2913889),
            ('unesco-masjed-jame-isfahan-v2', 32.6697222, 51.6852778),
            ('unesco-shahr-i-sokhta-v2', 30.5938889, 61.3277778),
            ('unesco-maymand-v2', 30.1680556, 55.3755556),
            ('unesco-hegmataneh-v2', 34.8035556, 48.5183333)
        ) AS expected(destination_key, latitude, longitude)
        LEFT JOIN knowledge.destinations d ON d.destination_key=expected.destination_key
        WHERE d.destination_id IS NULL
           OR ABS(d.latitude-expected.latitude) > 0.000001
           OR ABS(d.longitude-expected.longitude) > 0.000001
           OR ABS(ST_Y(d.location::geometry)-expected.latitude) > 0.000001
           OR ABS(ST_X(d.location::geometry)-expected.longitude) > 0.000001
    ) THEN
        RAISE EXCEPTION 'A second-batch destination coordinate differs from the UNESCO map reference or geography column';
    END IF;

    SELECT COUNT(*) INTO n
    FROM knowledge.destination_category_map m
    JOIN knowledge.destinations d ON d.destination_id=m.destination_id
    JOIN knowledge.destination_categories c ON c.category_id=m.category_id
    WHERE d.destination_key IN (
        'unesco-takht-e-soleyman-v2',
        'unesco-tchogha-zanbil-v2',
        'unesco-sheikh-safi-ardabil-v2',
        'unesco-masjed-jame-isfahan-v2',
        'unesco-shahr-i-sokhta-v2',
        'unesco-maymand-v2',
        'unesco-hegmataneh-v2'
    )
      AND c.category_key='historical'
      AND m.mapping_source='verified_external_curated'
      AND m.is_synthetic=FALSE;
    IF n <> 7 THEN
        RAISE EXCEPTION 'Expected seven curated historical-category mappings; found %', n;
    END IF;

    SELECT COUNT(*) INTO n
    FROM knowledge.destination_tags t
    JOIN knowledge.destinations d ON d.destination_id=t.destination_id
    WHERE d.destination_key IN (
        'unesco-takht-e-soleyman-v2',
        'unesco-tchogha-zanbil-v2',
        'unesco-sheikh-safi-ardabil-v2',
        'unesco-masjed-jame-isfahan-v2',
        'unesco-shahr-i-sokhta-v2',
        'unesco-maymand-v2',
        'unesco-hegmataneh-v2'
    )
      AND (t.tag='unesco_world_heritage'
           OR t.tag LIKE 'province:%'
           OR t.tag LIKE 'unesco_dossier:%');
    IF n <> 21 THEN
        RAISE EXCEPTION 'Expected 21 source-backed UNESCO/province/dossier tags; found %', n;
    END IF;

    SELECT COUNT(*) INTO n
    FROM knowledge.knowledge_documents d
    JOIN knowledge.destinations x ON x.destination_id=d.destination_id
    JOIN knowledge.knowledge_sources s ON s.source_id=d.source_id
    WHERE x.destination_key IN (
        'unesco-takht-e-soleyman-v2',
        'unesco-tchogha-zanbil-v2',
        'unesco-sheikh-safi-ardabil-v2',
        'unesco-masjed-jame-isfahan-v2',
        'unesco-shahr-i-sokhta-v2',
        'unesco-maymand-v2',
        'unesco-hegmataneh-v2'
    )
      AND d.record_origin='verified_external'
      AND d.is_synthetic=FALSE
      AND d.ingestion_status='processed'
      AND d.language_code='fa'
      AND d.canonical_url=s.url;
    IF n <> 7 THEN
        RAISE EXCEPTION 'Expected seven Persian factual documents linked to their exact official description sources; found %', n;
    END IF;

    SELECT COUNT(*) INTO n
    FROM knowledge.knowledge_chunks c
    JOIN knowledge.knowledge_documents d ON d.document_id=c.document_id
    JOIN knowledge.destinations x ON x.destination_id=d.destination_id
    WHERE x.destination_key IN (
        'unesco-takht-e-soleyman-v2',
        'unesco-tchogha-zanbil-v2',
        'unesco-sheikh-safi-ardabil-v2',
        'unesco-masjed-jame-isfahan-v2',
        'unesco-shahr-i-sokhta-v2',
        'unesco-maymand-v2',
        'unesco-hegmataneh-v2'
    )
      AND c.is_synthetic=FALSE;
    IF n <> 14 THEN
        RAISE EXCEPTION 'Expected 14 non-synthetic chunks across seven factual documents; found %', n;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM knowledge.knowledge_documents d
        JOIN knowledge.destinations x ON x.destination_id=d.destination_id
        LEFT JOIN knowledge.knowledge_chunks c ON c.document_id=d.document_id
        WHERE x.destination_key IN (
            'unesco-takht-e-soleyman-v2',
            'unesco-tchogha-zanbil-v2',
            'unesco-sheikh-safi-ardabil-v2',
            'unesco-masjed-jame-isfahan-v2',
            'unesco-shahr-i-sokhta-v2',
            'unesco-maymand-v2',
            'unesco-hegmataneh-v2'
        )
        GROUP BY d.document_id
        HAVING COUNT(c.chunk_id) <> 2
    ) THEN
        RAISE EXCEPTION 'Each second-batch factual document must have exactly two chunks';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM knowledge.knowledge_documents d
        JOIN knowledge.destinations x ON x.destination_id=d.destination_id
        WHERE x.destination_key IN (
            'unesco-takht-e-soleyman-v2',
            'unesco-tchogha-zanbil-v2',
            'unesco-sheikh-safi-ardabil-v2',
            'unesco-masjed-jame-isfahan-v2',
            'unesco-shahr-i-sokhta-v2',
            'unesco-maymand-v2',
            'unesco-hegmataneh-v2'
        )
        AND d.content_sha256 <> encode(sha256(convert_to(d.raw_content,'UTF8')),'hex')
    ) THEN
        RAISE EXCEPTION 'A second-batch factual document SHA-256 does not match stored Persian text';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM knowledge.knowledge_chunks c
        JOIN knowledge.knowledge_documents d ON d.document_id=c.document_id
        JOIN knowledge.destinations x ON x.destination_id=d.destination_id
        WHERE x.destination_key IN (
            'unesco-takht-e-soleyman-v2',
            'unesco-tchogha-zanbil-v2',
            'unesco-sheikh-safi-ardabil-v2',
            'unesco-masjed-jame-isfahan-v2',
            'unesco-shahr-i-sokhta-v2',
            'unesco-maymand-v2',
            'unesco-hegmataneh-v2'
        )
          AND (c.char_count <> CHAR_LENGTH(c.content)
            OR c.content_sha256 <> encode(sha256(convert_to(c.content,'UTF8')),'hex'))
    ) THEN
        RAISE EXCEPTION 'A second-batch factual chunk character count or SHA-256 is invalid';
    END IF;

    SELECT COUNT(*) INTO n
    FROM operations.dataset_import_batches
    WHERE batch_key='verified-unesco-iran-sites-v2'
      AND data_class='verified_external'
      AND record_counts->>'destinations'='7'
      AND record_counts->>'sources'='16'
      AND record_counts->>'destination_source_links'='16'
      AND record_counts->>'category_mappings'='7'
      AND record_counts->>'documents'='7'
      AND record_counts->>'chunks'='14';
    IF n <> 1 THEN
        RAISE EXCEPTION 'Second-batch import manifest does not match the expected record counts';
    END IF;

    SELECT COUNT(*) INTO n FROM system.schema_migrations
    WHERE migration_id='0006_verified_unesco_destination_seed_batch2';
    IF n <> 1 THEN
        RAISE EXCEPTION 'Second-batch migration ledger entry is missing';
    END IF;

    -- Source verification is not an editorial publication decision.
    SELECT COUNT(*) INTO n FROM knowledge.production_destinations;
    IF n <> 0 THEN
        RAISE EXCEPTION 'No second-batch site may publish before explicit editorial approval';
    END IF;
    SELECT COUNT(*) INTO n FROM knowledge.production_retrieval_documents;
    IF n <> 0 THEN
        RAISE EXCEPTION 'Second-batch documents must remain outside production RAG before editorial approval';
    END IF;

    RAISE NOTICE 'PASS: seven additional UNESCO properties, 16 provenance records/links, exact map points, categories, tags, seven Persian docs, 14 chunks, hashes and non-publication gate.';
END $$;
