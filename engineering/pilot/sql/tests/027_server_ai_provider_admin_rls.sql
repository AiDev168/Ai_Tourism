\set ON_ERROR_STOP on
-- Run only in a disposable PG17 database initialized through migration 0027.
-- All synthetic rows are rolled back at the end of this file.
BEGIN;
INSERT INTO identity.users(user_id,auth_subject,display_name,is_synthetic)
VALUES
 ('02700000-0000-4000-8000-000000000001','issue27-migration-test-admin','migration test admin',TRUE),
 ('02700000-0000-4000-8000-000000000002','issue27-migration-test-traveler','migration test traveler',TRUE);
INSERT INTO identity.web_sessions(session_id,token_hash,user_id,csrf_hash,created_at,last_seen_at,
    idle_expires_at,absolute_expires_at)
VALUES ('02700000-0000-4000-8000-000000000003',decode(repeat('01',32),'hex'),
        '02700000-0000-4000-8000-000000000001',decode(repeat('02',32),'hex'),now(),now(),
        now()+interval '1 hour',now()+interval '2 hours');
INSERT INTO identity.ai_provider_admin_grants(user_id,granted_by,grant_reason)
VALUES ('02700000-0000-4000-8000-000000000001','02700000-0000-4000-8000-000000000002',
        'isolated migration policy test grant');
INSERT INTO partner.platform_grants(user_id,capability,granted_by,reason)
VALUES ('02700000-0000-4000-8000-000000000001','organization_review',
        '02700000-0000-4000-8000-000000000002','isolated platform administrator test grant');
INSERT INTO identity.platform_admin_mfa(user_id,secret_ciphertext,enabled_at)
VALUES ('02700000-0000-4000-8000-000000000001',decode(repeat('aa',49),'hex'),now());
INSERT INTO identity.platform_admin_step_up(user_id,session_id,verified_at,expires_at)
VALUES ('02700000-0000-4000-8000-000000000001','02700000-0000-4000-8000-000000000003',
        now(),now()+interval '4 minutes');

INSERT INTO ai_provider.profiles(profile_id,name,provider_kind,created_by)
VALUES ('02700000-0000-4000-8000-000000000004','isolated seed','lm_studio',
        '02700000-0000-4000-8000-000000000001');

SET LOCAL ROLE ai_tourism_app;
SELECT set_config('app.actor_id','02700000-0000-4000-8000-000000000002',true);
SELECT set_config('app.session_id','02700000-0000-4000-8000-000000000005',true);
DO $$ BEGIN
  IF (SELECT count(*) FROM ai_provider.profiles) <> 0 THEN
    RAISE EXCEPTION 'ungranted user read provider profiles';
  END IF;
  BEGIN
    INSERT INTO ai_provider.profiles(name,provider_kind,created_by)
    VALUES ('unauthorized','lm_studio','02700000-0000-4000-8000-000000000002');
    RAISE EXCEPTION 'ungranted user wrote provider profile';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END $$;

RESET ROLE;
SELECT set_config('app.actor_id','02700000-0000-4000-8000-000000000001',true);
SELECT set_config('app.session_id','02700000-0000-4000-8000-000000000005',true);
SET LOCAL ROLE ai_tourism_app;
DO $$ BEGIN
  IF (SELECT count(*) FROM ai_provider.profiles) <> 1 THEN
    RAISE EXCEPTION 'provider administrator cannot read registry';
  END IF;
  BEGIN
    INSERT INTO ai_provider.profiles(name,provider_kind,created_by)
    VALUES ('no-step-up','lm_studio','02700000-0000-4000-8000-000000000001');
    RAISE EXCEPTION 'provider write passed without matching step-up';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END $$;

RESET ROLE;
DELETE FROM identity.platform_admin_step_up;
INSERT INTO identity.platform_admin_step_up(user_id,session_id,verified_at,expires_at)
VALUES ('02700000-0000-4000-8000-000000000001','02700000-0000-4000-8000-000000000003',
        now(),now()+interval '4 minutes');
SELECT set_config('app.session_id','02700000-0000-4000-8000-000000000003',true);
SET LOCAL ROLE ai_tourism_app;
INSERT INTO ai_provider.profiles(name,provider_kind,created_by)
VALUES ('authorized','lm_studio','02700000-0000-4000-8000-000000000001');

RESET ROLE;
SELECT set_config('app.actor_id','',true);
SELECT set_config('app.session_id','',true);
SELECT set_config('app.provider_runtime','true',true);
SET LOCAL ROLE ai_tourism_app;
DO $$ BEGIN
  IF (SELECT count(*) FROM ai_provider.profiles) <> 2 THEN
    RAISE EXCEPTION 'trusted runtime cannot read active registry data';
  END IF;
END $$;
INSERT INTO ai_provider.usage_events(capability,outcome,latency_ms)
VALUES ('chat','success',1);
DO $$ BEGIN
  BEGIN
    INSERT INTO ai_provider.profiles(name,provider_kind,created_by)
    VALUES ('runtime-mutation','lm_studio','02700000-0000-4000-8000-000000000001');
    RAISE EXCEPTION 'runtime route wrote provider configuration';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END $$;
ROLLBACK;
SELECT 'PASS: provider registry RLS and session-bound step-up' AS result;
