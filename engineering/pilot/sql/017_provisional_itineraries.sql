\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0016_hash RAHGARD_PILOT_MIGRATION_0016_SHA256
\getenv migration_hash RAHGARD_PILOT_MIGRATION_0017_SHA256

-- Owner-scoped editable AI-assisted drafts. This is intentionally separate
-- from travel.itineraries and the approved production destination catalogue.
BEGIN;
SELECT 1 / CASE WHEN current_database() = 'rahgard_pilot_vps_staging'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND inet_server_port() <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker) = 1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) = :'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_0016_hash' ~ '^[a-f0-9]{64}$'
    AND EXISTS (SELECT 1 FROM system.schema_migrations
                WHERE migration_id='0016_staging_invitation_auth'
                  AND sha256=:'migration_0016_hash')
    AND NOT EXISTS (SELECT 1 FROM system.schema_migrations
                    WHERE migration_id='0017_provisional_itineraries')
    THEN 1 ELSE 0 END;

CREATE UNIQUE INDEX uq_trips_id_owner
    ON travel.trips(trip_id, user_id);

CREATE TABLE travel.provisional_itineraries (
    provisional_itinerary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trip_id UUID NOT NULL UNIQUE,
    user_id UUID NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
    day_count INTEGER NOT NULL CHECK (day_count BETWEEN 1 AND 365),
    locale TEXT NOT NULL CHECK (locale IN ('fa-IR', 'en-US', 'ar')),
    title_by_locale JSONB NOT NULL DEFAULT '{}'::JSONB
        CHECK (jsonb_typeof(title_by_locale) = 'object'),
    days JSONB NOT NULL CHECK (jsonb_typeof(days) = 'array'),
    status TEXT NOT NULL DEFAULT 'provisional_unverified'
        CHECK (status = 'provisional_unverified'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (trip_id, user_id)
        REFERENCES travel.trips(trip_id, user_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE
);

CREATE INDEX ix_provisional_itineraries_owner_updated
    ON travel.provisional_itineraries(user_id, updated_at DESC);

REVOKE ALL ON travel.provisional_itineraries FROM PUBLIC;
GRANT SELECT, INSERT, UPDATE, DELETE ON travel.provisional_itineraries TO ai_tourism_app;
INSERT INTO system.schema_migrations(migration_id, sha256)
VALUES ('0017_provisional_itineraries', :'migration_hash');
COMMIT;
