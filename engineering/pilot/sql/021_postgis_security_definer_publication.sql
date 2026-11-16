\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0020_hash RAHGARD_PILOT_MIGRATION_0020_SHA256
\getenv migration_hash RAHGARD_PILOT_MIGRATION_0021_SHA256

-- Fix destination publication under the SECURITY DEFINER function's restricted
-- search_path. The legacy destination trigger referenced PostGIS's geography
-- type unqualified; that lookup fails when the reviewed publication function
-- inserts a canonical destination. Fully qualify PostGIS objects instead of
-- broadening the SECURITY DEFINER search_path.
BEGIN;
SELECT 1 / CASE WHEN current_database() = 'rahgard_pilot_vps_staging'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND inet_server_port() <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker) = 1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) = :'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_0020_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND to_regtype('public.geography') IS NOT NULL
    AND EXISTS (SELECT 1 FROM system.schema_migrations
                WHERE migration_id='0020_archive_candidate_publication' AND sha256=:'migration_0020_hash')
    AND NOT EXISTS (SELECT 1 FROM system.schema_migrations
                    WHERE migration_id='0021_postgis_security_definer_publication')
    THEN 1 ELSE 0 END;

CREATE OR REPLACE FUNCTION knowledge.sync_destination_location()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.latitude IS NULL OR NEW.longitude IS NULL THEN
        NEW.location := NULL;
    ELSE
        NEW.location := public.ST_SetSRID(
            public.ST_MakePoint(NEW.longitude, NEW.latitude), 4326
        )::public.geography;
    END IF;
    RETURN NEW;
END;
$$;

INSERT INTO system.schema_migrations(migration_id,sha256)
VALUES('0021_postgis_security_definer_publication',:'migration_hash');
COMMIT;
