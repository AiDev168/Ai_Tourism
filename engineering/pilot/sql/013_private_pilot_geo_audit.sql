\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0012_hash RAHGARD_PILOT_MIGRATION_0012_SHA256
-- Owner-operated, private-pilot migration. The execution role must be the
-- non-superuser owner of the relevant objects; the caller supplies the exact
-- file hash as :migration_hash. This file does not create or grant roles.
BEGIN;
SELECT 1 / CASE WHEN current_database() ~ '^rahgard_pilot_[a-z0-9_]{3,40}$'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND inet_server_port() <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker) = 1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) = :'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_0012_hash' ~ '^[a-f0-9]{64}$'
    AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles r WHERE r.rolname=current_user
                    AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole
                         OR r.rolreplication OR r.rolbypassrls))
    AND EXISTS (SELECT 1 FROM pg_catalog.pg_roles r WHERE r.rolname='rahgard_pilot_geo_executor'
                AND NOT r.rolcanlogin AND NOT r.rolsuper AND NOT r.rolcreatedb
                AND NOT r.rolcreaterole AND NOT r.rolreplication AND NOT r.rolbypassrls)
    AND EXISTS (SELECT 1 FROM system.schema_migrations
                WHERE migration_id='0012_task5_published_claim_evidence'
                  AND sha256=:'migration_0012_hash')
    AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles r
                    WHERE pg_has_role(current_user, r.oid, 'MEMBER')
                      AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole
                           OR r.rolreplication OR r.rolbypassrls))
    THEN 1 ELSE 0 END;

-- Only the owner, never the publisher or application, may provision these
-- exact, time-bounded records after receiving the owner's geographic decision.
CREATE TABLE operations.private_pilot_geo_authorizations (
    authorization_id UUID PRIMARY KEY DEFAULT pg_catalog.gen_random_uuid(),
    destination_key TEXT NOT NULL REFERENCES knowledge.destinations(destination_key),
    decision_sha256 CHAR(64) NOT NULL CHECK (decision_sha256 ~ '^[a-f0-9]{64}$'),
    marker_sha256 CHAR(64) NOT NULL CHECK (marker_sha256 ~ '^[a-f0-9]{64}$'),
    canonical_name TEXT NOT NULL,
    destination_type TEXT NOT NULL,
    province_name TEXT NOT NULL,
    city_name TEXT,
    latitude DOUBLE PRECISION NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE PRECISION NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    coordinate_role TEXT NOT NULL,
    source_url TEXT NOT NULL,
    reviewer TEXT NOT NULL CHECK (length(btrim(reviewer)) BETWEEN 1 AND 240),
    approval_reference TEXT NOT NULL CHECK (length(btrim(approval_reference)) BETWEEN 1 AND 240),
    reviewed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    expires_at TIMESTAMPTZ NOT NULL,
    UNIQUE (destination_key, decision_sha256, marker_sha256),
    CHECK (reviewed_at <= created_at AND expires_at > created_at
           AND expires_at <= created_at + INTERVAL '1 hour'),
    CHECK ((destination_key='shiraz-hafezieh-v1' AND coordinate_role='representative_point'
             AND source_url='https://en.wikipedia.org/wiki/Tomb_of_Hafez')
        OR (destination_key='shiraz-eram-garden-v1' AND coordinate_role='representative_point'
             AND source_url='https://en.wikipedia.org/wiki/Eram_Garden')
        OR (destination_key='shiraz-vakil-bazaar-v1' AND coordinate_role='representative_point'
             AND source_url='https://en.wikipedia.org/wiki/Vakil_Bazaar')
        OR (destination_key='unesco-persepolis-v1' AND coordinate_role='property_reference'
             AND source_url='https://whc.unesco.org/en/list/114/maps/'))
);

-- This append-only row simultaneously records and consumes an authorization.
CREATE TABLE operations.private_pilot_geo_approvals (
    authorization_id UUID PRIMARY KEY REFERENCES operations.private_pilot_geo_authorizations(authorization_id),
    destination_key TEXT NOT NULL REFERENCES knowledge.destinations(destination_key),
    decision_sha256 CHAR(64) NOT NULL CHECK (decision_sha256 ~ '^[a-f0-9]{64}$'),
    marker_sha256 CHAR(64) NOT NULL CHECK (marker_sha256 ~ '^[a-f0-9]{64}$'),
    reviewer TEXT NOT NULL,
    approval_reference TEXT NOT NULL,
    reviewed_at TIMESTAMPTZ NOT NULL,
    coordinate_role TEXT NOT NULL CHECK (coordinate_role IN ('representative_point', 'property_reference')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT pg_catalog.now(),
    UNIQUE(destination_key, decision_sha256, marker_sha256)
);
REVOKE ALL ON operations.private_pilot_geo_authorizations, operations.private_pilot_geo_approvals FROM PUBLIC;

CREATE FUNCTION operations.apply_private_geo_approval(
    p_destination_key TEXT, p_decision_sha256 TEXT, p_marker_sha256 TEXT,
    p_reviewer TEXT, p_approval_reference TEXT, p_reviewed_at TIMESTAMPTZ
) RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog
AS $function$
DECLARE
    v_authorization operations.private_pilot_geo_authorizations%ROWTYPE;
    destination knowledge.destinations%ROWTYPE;
    marker_count BIGINT;
    actual_marker_hash TEXT;
    source_count BIGINT;
    consumed BOOLEAN;
    changed BOOLEAN := FALSE;
BEGIN
    IF session_user <> 'rahgard_pilot_geo_publisher'
       OR current_database() !~ '^rahgard_pilot_[a-z0-9_]{3,40}$'
       OR EXISTS (SELECT 1 FROM pg_catalog.pg_roles r WHERE r.rolname=session_user
                  AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls))
       OR p_destination_key NOT IN ('shiraz-hafezieh-v1', 'shiraz-eram-garden-v1',
                                    'shiraz-vakil-bazaar-v1', 'unesco-persepolis-v1')
       OR p_decision_sha256 !~ '^[a-f0-9]{64}$' OR p_marker_sha256 !~ '^[a-f0-9]{64}$'
       OR EXISTS (SELECT 1 FROM pg_catalog.pg_roles r WHERE pg_has_role(session_user, r.oid, 'MEMBER')
                  AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls))
       OR has_database_privilege(session_user, current_database(), 'CREATE')
       OR has_schema_privilege(session_user, 'operations', 'CREATE')
       OR has_schema_privilege(session_user, 'knowledge', 'CREATE')
       OR has_schema_privilege(session_user, 'public', 'CREATE')
       OR has_table_privilege(session_user, 'knowledge.destinations', 'INSERT,UPDATE,DELETE,TRUNCATE')
       OR has_any_column_privilege(session_user, 'knowledge.destinations', 'INSERT,UPDATE')
       OR has_table_privilege(session_user, 'operations.private_pilot_geo_authorizations', 'INSERT,UPDATE,DELETE,TRUNCATE')
       OR has_any_column_privilege(session_user, 'operations.private_pilot_geo_authorizations', 'INSERT,UPDATE')
       OR has_table_privilege(session_user, 'operations.private_pilot_geo_approvals', 'INSERT,UPDATE,DELETE,TRUNCATE')
       OR has_any_column_privilege(session_user, 'operations.private_pilot_geo_approvals', 'INSERT,UPDATE')
       OR has_table_privilege(session_user, 'public.rahgard_private_pilot_marker', 'INSERT,UPDATE,DELETE,TRUNCATE')
       OR has_any_column_privilege(session_user, 'public.rahgard_private_pilot_marker', 'INSERT,UPDATE')
    THEN
        RAISE EXCEPTION 'private pilot publisher role or scope is unsafe';
    END IF;

    SELECT count(*), min(pg_catalog.encode(pg_catalog.sha256(pg_catalog.convert_to(marker_value, 'UTF8')), 'hex'))
      INTO marker_count, actual_marker_hash FROM public.rahgard_private_pilot_marker;
    IF marker_count <> 1 OR actual_marker_hash IS DISTINCT FROM p_marker_sha256 THEN
        RAISE EXCEPTION 'private pilot marker mismatch';
    END IF;

    SELECT * INTO v_authorization FROM operations.private_pilot_geo_authorizations
      WHERE destination_key=p_destination_key AND decision_sha256=p_decision_sha256
        AND marker_sha256=p_marker_sha256;
    IF NOT FOUND OR v_authorization.expires_at <= pg_catalog.clock_timestamp()
       OR v_authorization.reviewer IS DISTINCT FROM p_reviewer
       OR v_authorization.approval_reference IS DISTINCT FROM p_approval_reference
       OR v_authorization.reviewed_at IS DISTINCT FROM p_reviewed_at THEN
        RAISE EXCEPTION 'owner geographic authorization missing or expired';
    END IF;
    SELECT * INTO destination FROM knowledge.destinations
      WHERE destination_key=p_destination_key FOR UPDATE;
    IF NOT FOUND OR destination.canonical_name IS DISTINCT FROM v_authorization.canonical_name
       OR destination.destination_type IS DISTINCT FROM v_authorization.destination_type
       OR destination.province_name IS DISTINCT FROM v_authorization.province_name
       OR destination.city_name IS DISTINCT FROM v_authorization.city_name
       OR destination.latitude IS NULL OR destination.longitude IS NULL OR destination.location IS NULL
       OR abs(destination.latitude - v_authorization.latitude) > 0.0000001
       OR abs(destination.longitude - v_authorization.longitude) > 0.0000001
       OR abs(public.ST_Y(destination.location::public.geometry) - v_authorization.latitude) > 0.0000001
       OR abs(public.ST_X(destination.location::public.geometry) - v_authorization.longitude) > 0.0000001
       OR destination.coordinate_role IS DISTINCT FROM v_authorization.coordinate_role
       OR destination.record_origin <> 'verified_external' OR destination.verification_status <> 'verified'
       OR destination.is_synthetic IS DISTINCT FROM FALSE OR destination.status NOT IN ('needs_review', 'active')
    THEN
        RAISE EXCEPTION 'reviewed canonical geographic identity differs';
    END IF;
    SELECT count(*) INTO source_count FROM knowledge.destination_sources ds
      JOIN knowledge.knowledge_sources s ON s.source_id=ds.source_id
      WHERE ds.destination_id=destination.destination_id AND s.url=v_authorization.source_url
        AND s.verification_status='verified' AND s.is_synthetic=FALSE
        AND (ds.valid_from IS NULL OR ds.valid_from <= pg_catalog.now())
        AND (ds.valid_until IS NULL OR ds.valid_until >= pg_catalog.now());
    IF source_count <> 1 THEN RAISE EXCEPTION 'verified geographic source unavailable'; END IF;

    SELECT EXISTS (SELECT 1 FROM operations.private_pilot_geo_approvals
                   WHERE authorization_id=v_authorization.authorization_id) INTO consumed;
    IF destination.status <> 'active' AND EXISTS (
        SELECT 1 FROM operations.private_pilot_geo_approvals WHERE destination_key=p_destination_key
    ) THEN
        RAISE EXCEPTION 'a previously activated point requires a separate reauthorization procedure';
    END IF;
    IF consumed THEN
        IF destination.status <> 'active' THEN RAISE EXCEPTION 'authorization already consumed'; END IF;
        RETURN FALSE;
    END IF;
    IF v_authorization.expires_at <= pg_catalog.clock_timestamp() THEN
        RAISE EXCEPTION 'owner geographic authorization expired';
    END IF;
    IF destination.status = 'needs_review' THEN
        UPDATE knowledge.destinations SET status='active', updated_at=pg_catalog.now()
          WHERE destination_id=destination.destination_id;
        changed := TRUE;
    END IF;
    INSERT INTO operations.private_pilot_geo_approvals
        (authorization_id, destination_key, decision_sha256, marker_sha256, reviewer,
         approval_reference, reviewed_at, coordinate_role)
      VALUES (v_authorization.authorization_id, v_authorization.destination_key,
              v_authorization.decision_sha256, v_authorization.marker_sha256,
              v_authorization.reviewer, v_authorization.approval_reference,
              v_authorization.reviewed_at, v_authorization.coordinate_role);
    RETURN changed;
END;
$function$;
REVOKE ALL ON FUNCTION operations.apply_private_geo_approval(TEXT, TEXT, TEXT, TEXT, TEXT, TIMESTAMPTZ) FROM PUBLIC;
-- The executor's minimal privileges on existing canonical tables/schemas must
-- be provisioned by their owner before migration; this migration owns only
-- the two new audit tables and grants access to those new objects.
GRANT SELECT ON operations.private_pilot_geo_authorizations,
    operations.private_pilot_geo_approvals TO rahgard_pilot_geo_executor;
GRANT INSERT ON operations.private_pilot_geo_approvals TO rahgard_pilot_geo_executor;
ALTER FUNCTION operations.apply_private_geo_approval(TEXT, TEXT, TEXT, TEXT, TEXT, TIMESTAMPTZ)
    OWNER TO rahgard_pilot_geo_executor;

-- Owner provisioning, after review (not executed by this migration):
-- GRANT USAGE ON SCHEMA operations TO rahgard_pilot_geo_publisher;
-- GRANT EXECUTE ON FUNCTION operations.apply_private_geo_approval(TEXT,TEXT,TEXT,TEXT,TEXT,TIMESTAMPTZ)
--   TO rahgard_pilot_geo_publisher;
-- Do not grant the publisher direct writes to the underlying tables.
INSERT INTO system.schema_migrations (migration_id, sha256)
VALUES ('0013_private_pilot_geo_audit', :'migration_hash');
COMMIT;
