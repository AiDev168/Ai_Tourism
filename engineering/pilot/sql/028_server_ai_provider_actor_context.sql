\set ON_ERROR_STOP on
\getenv pilot_marker RAHGARD_PILOT_DATABASE_MARKER
\getenv migration_0027_hash RAHGARD_PILOT_MIGRATION_0027_SHA256
\getenv migration_hash RAHGARD_PILOT_MIGRATION_0028_SHA256

-- The 0027 server-only capability SECURITY DEFINER functions call
-- partner.current_actor_id() and identity.has_platform_admin_capability().
-- These functions are intentionally not executable by PUBLIC; 0019/0026 grant
-- them to the application role. Grant the narrow execution rights to the exact
-- restricted owner of the 0027 functions so its authorization check can read
-- the transaction-local actor and evaluate platform capability. No application
-- role, PUBLIC grant, table access, or RLS policy is changed.
BEGIN;
SELECT 1 / CASE WHEN current_database()='rahgard_pilot_vps_staging'
    AND current_setting('server_version_num')::integer BETWEEN 170000 AND 179999
    AND COALESCE(inet_server_port(),0) <> 55433
    AND (SELECT count(*) FROM public.rahgard_private_pilot_marker)=1
    AND (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker)=:'pilot_marker'
    AND :'pilot_marker' ~ '^[a-fA-F0-9]{32,128}$'
    AND :'migration_0027_hash' ~ '^[a-f0-9]{64}$'
    AND :'migration_hash' ~ '^[a-f0-9]{64}$'
    AND EXISTS(SELECT 1 FROM system.schema_migrations
               WHERE migration_id='0027_server_ai_provider_admin' AND sha256=:'migration_0027_hash')
    AND (SELECT count(*) FROM system.schema_migrations)=26
    AND (SELECT max(migration_id) FROM system.schema_migrations)='0027_server_ai_provider_admin'
    AND NOT EXISTS(SELECT 1 FROM system.schema_migrations WHERE migration_id IN (
      '0014_local_owner_login','0015_ai_provider_admin'))
    AND NOT EXISTS(SELECT 1 FROM system.schema_migrations WHERE migration_id NOT IN (
      '0000_legacy_tourism_points_baseline','0001_core_schema','0002_synthetic_knowledge_seed',
      '0003_synthetic_e2e_seed','0004_app_role_grants','0005_verified_unesco_destination_seed',
      '0006_verified_unesco_destination_seed_batch2','0007_shiraz_dalahoo_wikipedia_dataset_v1',
      '0008_authentication_foundation','0009_traveler_core','0010_task31_content_privacy_full_itinerary',
      '0011_internal_chat_turns','0012_task5_published_claim_evidence','0013_private_pilot_geo_audit',
      '0016_staging_invitation_auth','0017_provisional_itineraries','0018_national_catalogue_ingestion',
      '0019_partner_workspace','0020_archive_candidate_publication','0021_postgis_security_definer_publication',
      '0022_traveler_company_requests','0023_partner_trip_responses','0024_partner_review_audit_actions',
      '0025_owner_control_center','0026_platform_reviewer_mfa','0027_server_ai_provider_admin'))
    AND NOT EXISTS(SELECT 1 FROM system.schema_migrations
                   WHERE migration_id='0028_server_ai_provider_actor_context')
    AND to_regprocedure('partner.current_actor_id()') IS NOT NULL
    AND to_regprocedure('identity.has_ai_provider_admin_capability(uuid)') IS NOT NULL
    AND to_regprocedure('identity.has_ai_provider_admin_step_up()') IS NOT NULL
    AND to_regprocedure('identity.has_privileged_admin_step_up()') IS NOT NULL
    AND to_regprocedure('identity.has_platform_admin_capability(uuid)') IS NOT NULL
    THEN 1 ELSE 0 END;

DO $migration$
DECLARE
  function_owner oid;
  target_role name;
BEGIN
  SELECT p.proowner, r.rolname
    INTO function_owner, target_role
  FROM pg_catalog.pg_proc p
  JOIN pg_catalog.pg_roles r ON r.oid=p.proowner
  WHERE p.oid IN (
    'identity.has_ai_provider_admin_capability(uuid)'::regprocedure,
    'identity.has_ai_provider_admin_step_up()'::regprocedure,
    'identity.has_privileged_admin_step_up()'::regprocedure
  )
  GROUP BY p.proowner,r.rolname
  HAVING count(*)=3
     AND bool_and(NOT r.rolsuper AND NOT r.rolcreatedb AND NOT r.rolcreaterole
                  AND NOT r.rolreplication AND NOT r.rolbypassrls);

  IF function_owner IS NULL OR target_role IS NULL OR target_role='ai_tourism_app' THEN
    RAISE EXCEPTION '0027 capability functions must share one restricted non-application owner';
  END IF;

  EXECUTE format('GRANT EXECUTE ON FUNCTION partner.current_actor_id() TO %I', target_role);
  EXECUTE format('GRANT EXECUTE ON FUNCTION identity.has_platform_admin_capability(uuid) TO %I', target_role);
END
$migration$;

-- Verify the access path is narrow and the capability function now evaluates
-- for the application role. Its false result for a non-existent actor is
-- expected; a permission error is not.
DO $verify$
DECLARE
  target_role name;
  is_public_executable boolean;
BEGIN
  SELECT r.rolname INTO target_role
  FROM pg_catalog.pg_proc p
  JOIN pg_catalog.pg_roles r ON r.oid=p.proowner
  WHERE p.oid='identity.has_ai_provider_admin_capability(uuid)'::regprocedure;

  IF NOT has_function_privilege(target_role,'partner.current_actor_id()','EXECUTE')
     OR NOT has_function_privilege(target_role,'identity.has_platform_admin_capability(uuid)','EXECUTE')
     OR NOT has_function_privilege('ai_tourism_app','partner.current_actor_id()','EXECUTE') THEN
    RAISE EXCEPTION 'capability dependencies are not executable by required roles';
  END IF;

  SELECT EXISTS(
    SELECT 1 FROM pg_catalog.pg_proc p,
      LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) acl
    WHERE p.oid='partner.current_actor_id()'::regprocedure
      AND acl.grantee=0 AND acl.privilege_type='EXECUTE'
  ) INTO is_public_executable;

  IF is_public_executable THEN
    RAISE EXCEPTION 'actor-context function must not be executable by PUBLIC';
  END IF;

  SELECT EXISTS(
    SELECT 1 FROM pg_catalog.pg_proc p,
      LATERAL aclexplode(COALESCE(p.proacl,acldefault('f',p.proowner))) acl
    WHERE p.oid='identity.has_platform_admin_capability(uuid)'::regprocedure
      AND acl.grantee=0 AND acl.privilege_type='EXECUTE'
  ) INTO is_public_executable;
  IF is_public_executable THEN
    RAISE EXCEPTION 'platform capability function must not be executable by PUBLIC';
  END IF;
END
$verify$;

INSERT INTO system.schema_migrations(migration_id,sha256)
VALUES('0028_server_ai_provider_actor_context',:'migration_hash');
COMMIT;
