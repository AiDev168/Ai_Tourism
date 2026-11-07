"""Disposable PostgreSQL integration tests. Set AUTH_INTEGRATION_TESTS=1 explicitly."""

from __future__ import annotations

import hashlib
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import psycopg
from psycopg.rows import dict_row
import pytest

from app.core.config import Settings
from app.core.config import get_settings
from app.main import app
from app.modules.identity.auth_service import AuthenticationService
from app.modules.identity.auth_repository import AuthRepository
from app.modules.identity.sms import FakeSmsAdapter

pytestmark = pytest.mark.skipif(
    os.environ.get("AUTH_INTEGRATION_TESTS") != "1",
    reason="requires the explicitly selected disposable PostgreSQL integration database",
)


def make_settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        database_host=os.environ["AUTH_TEST_DATABASE_HOST"],
        database_port=int(os.environ["AUTH_TEST_DATABASE_PORT"]),
        database_name="ai_tourism_dev",
        database_user="ai_tourism_app",
        database_password=os.environ["AUTH_TEST_DATABASE_PASSWORD"],
        auth_enabled=True,
        auth_sms_adapter="fake",
        auth_otp_hmac_secret="integration-otp-key-only-test-000000000001",
        auth_csrf_secret="integration-csrf-key-only-test-000000000001",
        auth_rate_limit_secret="integration-rate-key-only-test-000000000001",
        auth_session_idle_seconds=1800,
        auth_session_absolute_seconds=43200,
        auth_allowed_origins="https://testserver",
        auth_rate_window_seconds=600,
        auth_phone_issue_limit=20,
        auth_ip_issue_limit=100,
        auth_global_issue_limit=1000,
        auth_phone_verify_limit=100,
        auth_ip_verify_limit=100,
    )


def connect(settings: Settings):
    return psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password.get_secret_value(),
        row_factory=dict_row,
    )


def test_postgres_otp_session_atomicity_and_revocation():
    settings = make_settings()
    sms = FakeSmsAdapter()
    repository = AuthRepository(settings)
    service = AuthenticationService(settings, sms, repository)

    # One successful OTP establishes verification evidence and a hashed-only session.
    issued = service.issue("09120000011", "integration-ip-a", "en-US")
    assert issued.challenge_id is not None
    code = re.search(r"[0-9]{6}", sms.take_messages()[0].body).group()
    verified = service.verify(issued.challenge_id, code, "integration-ip-a")
    assert verified is not None
    user, raw_session, _csrf = verified
    assert service.authenticate(raw_session) is not None

    with connect(settings) as conn:
        challenge = conn.execute(
            "SELECT verifier_hmac, phone_e164, consumed_at FROM identity.otp_challenges WHERE challenge_id=%s",
            (issued.challenge_id,),
        ).fetchone()
        stored_session = conn.execute(
            "SELECT token_hash, csrf_hash FROM identity.web_sessions WHERE user_id=%s AND token_hash=%s",
            (user.user_id, hashlib.sha256(raw_session.encode()).digest()),
        ).fetchone()
        evidence = conn.execute(
            "SELECT phone_e164, user_id FROM identity.verified_phones WHERE user_id=%s",
            (user.user_id,),
        ).fetchone()
        assert challenge["consumed_at"] is not None
        assert code not in bytes(challenge["verifier_hmac"]).hex()
        assert stored_session["token_hash"] == hashlib.sha256(raw_session.encode()).digest()
        assert raw_session.encode() not in bytes(stored_session["token_hash"])
        assert evidence["phone_e164"] == "+989120000011"
        assert evidence["user_id"] == user.user_id

    # A challenge can be consumed only once even under concurrent valid requests.
    concurrent = service.issue("09120000012", "integration-ip-b", "fa-IR")
    concurrent_code = re.search(r"[0-9]{6}", sms.take_messages()[0].body).group()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda _: service.verify(concurrent.challenge_id, concurrent_code, "integration-ip-b"),
            range(2),
        ))
    assert sum(result is not None for result in results) == 1

    # Server-side expiration and account disablement invalidate sessions; the DB trigger revokes.
    with connect(settings) as conn:
        conn.execute(
            "UPDATE identity.web_sessions SET idle_expires_at=%s WHERE user_id=%s",
            (datetime.now(UTC) - timedelta(seconds=1), user.user_id),
        )
    assert service.authenticate(raw_session) is None
    with connect(settings) as conn:
        conn.execute("UPDATE identity.users SET account_status='disabled' WHERE user_id=%s", (user.user_id,))
        revoked = conn.execute(
            "SELECT revoked_at, revoked_reason FROM identity.web_sessions WHERE user_id=%s",
            (user.user_id,),
        ).fetchone()
        assert revoked["revoked_at"] is not None
        assert revoked["revoked_reason"] == "account_disabled"

    # Invalid codes consume a bounded attempt and cannot create identity evidence.
    invalid = service.issue("09120000013", "integration-ip-c", "ar")
    assert invalid.challenge_id is not None
    valid_code = re.search(r"[0-9]{6}", sms.take_messages()[0].body).group()
    invalid_code = "000000" if valid_code != "000000" else "000001"
    for _ in range(settings.auth_otp_max_attempts):
        assert service.verify(invalid.challenge_id, invalid_code, "integration-ip-c") is None
    with connect(settings) as conn:
        failed = conn.execute(
            "SELECT failed_attempts, locked_at FROM identity.otp_challenges WHERE challenge_id=%s",
            (invalid.challenge_id,),
        ).fetchone()
        evidence_count = conn.execute(
            "SELECT COUNT(*) FROM identity.verified_phones WHERE phone_e164='+989120000013'"
        ).fetchone()["count"]
        assert failed["failed_attempts"] == settings.auth_otp_max_attempts
        assert failed["locked_at"] is not None
        assert evidence_count == 0


def test_actual_fastapi_flow_uses_app_role_and_secure_cookie():
    from fastapi.testclient import TestClient

    settings = make_settings()
    sms = FakeSmsAdapter()
    old_adapter = app.state.sms_adapter
    app.state.sms_adapter = sms
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app, base_url="https://testserver") as client:
            requested = client.post(
                "/api/v1/auth/otp/challenges",
                json={"phone_number": "09120000014", "locale": "ar"},
            )
            assert requested.status_code == 202
            code = re.search(r"[0-9]{6}", sms.take_messages()[0].body).group()
            verified = client.post(
                "/api/v1/auth/otp/verify",
                json={"challenge_id": requested.json()["challenge_id"], "code": code},
            )
            assert verified.status_code == 200
            cookie = verified.headers["set-cookie"].lower()
            assert "__host-rahgard_session=" in cookie
            assert "secure" in cookie and "httponly" in cookie and "samesite=lax" in cookie
            assert "domain=" not in cookie
            assert code not in verified.text
            current = client.get("/api/v1/auth/me")
            assert current.status_code == 200
            csrf = current.json()["csrf_token"]
            assert client.post(
                "/api/v1/auth/logout",
                headers={"Origin": "https://testserver", "X-CSRF-Token": csrf},
            ).status_code == 204
            assert client.get("/api/v1/auth/me").status_code == 401
    finally:
        app.dependency_overrides.clear()
        app.state.sms_adapter = old_adapter
