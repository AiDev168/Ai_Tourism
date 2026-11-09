\set ON_ERROR_STOP on

BEGIN;

CREATE TABLE IF NOT EXISTS identity.otp_challenges (
    challenge_id UUID PRIMARY KEY,
    phone_e164 TEXT NOT NULL CHECK (phone_e164 ~ '^\+989[0-9]{9}$'),
    purpose TEXT NOT NULL CHECK (purpose = 'login'),
    verifier_hmac BYTEA NOT NULL CHECK (octet_length(verifier_hmac) = 32),
    key_version TEXT NOT NULL,
    delivery_status TEXT NOT NULL DEFAULT 'queued'
        CHECK (delivery_status IN ('queued', 'sent', 'failed')),
    failed_attempts SMALLINT NOT NULL DEFAULT 0 CHECK (failed_attempts BETWEEN 0 AND 10),
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    resend_after TIMESTAMPTZ NOT NULL,
    consumed_at TIMESTAMPTZ,
    superseded_at TIMESTAMPTZ,
    locked_at TIMESTAMPTZ,
    CHECK (expires_at > created_at),
    CHECK (resend_after >= created_at)
);
CREATE INDEX IF NOT EXISTS idx_otp_challenges_phone_created
    ON identity.otp_challenges (phone_e164, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_otp_challenges_expiry
    ON identity.otp_challenges (expires_at)
    WHERE consumed_at IS NULL AND superseded_at IS NULL;

CREATE TABLE IF NOT EXISTS identity.verified_phones (
    phone_e164 TEXT PRIMARY KEY CHECK (phone_e164 ~ '^\+989[0-9]{9}$'),
    user_id UUID NOT NULL UNIQUE REFERENCES identity.users(user_id) ON DELETE CASCADE,
    verified_at TIMESTAMPTZ NOT NULL,
    challenge_id UUID NOT NULL UNIQUE REFERENCES identity.otp_challenges(challenge_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS identity.web_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_hash BYTEA NOT NULL UNIQUE CHECK (octet_length(token_hash) = 32),
    user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE CASCADE,
    csrf_hash BYTEA NOT NULL CHECK (octet_length(csrf_hash) = 32),
    created_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    idle_expires_at TIMESTAMPTZ NOT NULL,
    absolute_expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    revoked_reason TEXT,
    CHECK (idle_expires_at <= absolute_expires_at),
    CHECK (absolute_expires_at > created_at)
);
CREATE INDEX IF NOT EXISTS idx_web_sessions_user_active
    ON identity.web_sessions (user_id, absolute_expires_at)
    WHERE revoked_at IS NULL;

CREATE TABLE IF NOT EXISTS identity.auth_rate_limits (
    dimension TEXT NOT NULL CHECK (dimension IN (
        'phone', 'ip', 'global', 'verify_challenge', 'verify_phone', 'verify_ip'
    )),
    subject_digest BYTEA NOT NULL CHECK (octet_length(subject_digest) = 32),
    window_started_at TIMESTAMPTZ NOT NULL,
    hit_count INTEGER NOT NULL CHECK (hit_count > 0),
    PRIMARY KEY (dimension, subject_digest, window_started_at)
);
CREATE INDEX IF NOT EXISTS idx_auth_rate_limits_window
    ON identity.auth_rate_limits (window_started_at);

CREATE OR REPLACE FUNCTION identity.revoke_disabled_user_sessions()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.account_status <> 'active' AND OLD.account_status = 'active' THEN
        UPDATE identity.web_sessions
        SET revoked_at = COALESCE(revoked_at, NOW()),
            revoked_reason = COALESCE(revoked_reason, 'account_disabled')
        WHERE user_id = NEW.user_id AND revoked_at IS NULL;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_revoke_disabled_user_sessions ON identity.users;
CREATE TRIGGER trg_revoke_disabled_user_sessions
AFTER UPDATE OF account_status ON identity.users
FOR EACH ROW EXECUTE FUNCTION identity.revoke_disabled_user_sessions();

GRANT SELECT, INSERT, UPDATE, DELETE ON
    identity.otp_challenges, identity.verified_phones,
    identity.web_sessions, identity.auth_rate_limits TO ai_tourism_app;
GRANT EXECUTE ON FUNCTION identity.revoke_disabled_user_sessions() TO ai_tourism_app;

INSERT INTO system.schema_migrations (migration_id, sha256)
VALUES ('0008_authentication_foundation', :'migration_hash')
ON CONFLICT (migration_id) DO NOTHING;

COMMIT;
