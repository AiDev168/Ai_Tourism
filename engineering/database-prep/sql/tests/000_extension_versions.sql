\set ON_ERROR_STOP on

DO $$
DECLARE
    v_server_major INTEGER;
    v_vector_version TEXT;
    v_postgis_version TEXT;
BEGIN
    v_server_major := current_setting('server_version_num')::INTEGER / 10000;
    IF v_server_major <> 17 THEN
        RAISE EXCEPTION 'Expected PostgreSQL 17, got major version %', v_server_major;
    END IF;

    SELECT extversion INTO v_vector_version
      FROM pg_extension WHERE extname = 'vector';
    IF v_vector_version IS DISTINCT FROM '0.8.7' THEN
        RAISE EXCEPTION 'Expected pgvector 0.8.7, got %', v_vector_version;
    END IF;

    SELECT PostGIS_Lib_Version() INTO v_postgis_version;
    IF v_postgis_version NOT LIKE '3.6.%' THEN
        RAISE EXCEPTION 'Expected PostGIS 3.6.x, got %', v_postgis_version;
    END IF;

    RAISE NOTICE 'PASS: PostgreSQL %, PostGIS %, pgvector %.',
        v_server_major, v_postgis_version, v_vector_version;
END $$;
