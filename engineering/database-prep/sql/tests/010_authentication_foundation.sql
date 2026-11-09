\set ON_ERROR_STOP on

DO $$
DECLARE
    table_count INTEGER;
    migration_applied_at TIMESTAMPTZ;
BEGIN
    SELECT applied_at INTO migration_applied_at
      FROM system.schema_migrations WHERE migration_id='0008_authentication_foundation';
    IF migration_applied_at IS NULL THEN
        RAISE EXCEPTION 'Migration 0008 ledger entry is required';
    END IF;
    SELECT COUNT(*) INTO table_count FROM pg_catalog.pg_tables
     WHERE schemaname='identity' AND tablename IN
       ('otp_challenges','verified_phones','web_sessions','auth_rate_limits');
    IF table_count <> 4 THEN RAISE EXCEPTION 'Expected four auth tables, found %', table_count; END IF;
    IF NOT (has_table_privilege('ai_tourism_app','identity.otp_challenges','SELECT')
       AND has_table_privilege('ai_tourism_app','identity.otp_challenges','INSERT')
       AND has_table_privilege('ai_tourism_app','identity.otp_challenges','UPDATE')
       AND has_table_privilege('ai_tourism_app','identity.otp_challenges','DELETE')
       AND has_table_privilege('ai_tourism_app','identity.verified_phones','SELECT')
       AND has_table_privilege('ai_tourism_app','identity.verified_phones','INSERT')
       AND has_table_privilege('ai_tourism_app','identity.verified_phones','UPDATE')
       AND has_table_privilege('ai_tourism_app','identity.verified_phones','DELETE')
       AND has_table_privilege('ai_tourism_app','identity.web_sessions','SELECT')
       AND has_table_privilege('ai_tourism_app','identity.web_sessions','INSERT')
       AND has_table_privilege('ai_tourism_app','identity.web_sessions','UPDATE')
       AND has_table_privilege('ai_tourism_app','identity.web_sessions','DELETE')
       AND has_table_privilege('ai_tourism_app','identity.auth_rate_limits','SELECT')
       AND has_table_privilege('ai_tourism_app','identity.auth_rate_limits','INSERT')
       AND has_table_privilege('ai_tourism_app','identity.auth_rate_limits','UPDATE')
       AND has_table_privilege('ai_tourism_app','identity.auth_rate_limits','DELETE')) THEN
        RAISE EXCEPTION 'Application role lacks required auth repository privileges';
    END IF;
    -- Repeatable after login activity: any verification evidence must have
    -- been created after the migration, through the OTP flow. This proves the
    -- migration did not infer verification from pre-existing phone values.
    IF EXISTS (
        SELECT 1 FROM identity.verified_phones v
        JOIN identity.users u ON u.user_id=v.user_id
        WHERE v.verified_at < migration_applied_at OR u.is_synthetic=TRUE
    ) THEN
        RAISE EXCEPTION 'Verified-phone evidence predates Migration 0008 or belongs to a synthetic identity';
    END IF;
    IF EXISTS (
        SELECT 1 FROM identity.otp_challenges
        WHERE created_at < migration_applied_at
    ) OR EXISTS (
        SELECT 1 FROM identity.web_sessions
        WHERE created_at < migration_applied_at
    ) THEN
        RAISE EXCEPTION 'Authentication runtime records predate Migration 0008';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname='trg_revoke_disabled_user_sessions' AND NOT tgisinternal) THEN
        RAISE EXCEPTION 'Account-disable session revocation trigger is missing';
    END IF;
    IF has_table_privilege('ai_tourism_app','knowledge.destinations','SELECT') THEN
        RAISE EXCEPTION 'Application role unexpectedly has raw destination access';
    END IF;
    RAISE NOTICE 'PASS: authentication schema, app-role access, legacy verification boundary, and disable trigger.';
END $$;
