from __future__ import annotations

import hmac
import re
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.auth import get_auth_service
from app.core.config import Settings, get_settings
from app.main import app
from app.modules.identity.auth_service import AuthenticationService
from app.modules.identity.authorization import AuthorizationDenied, Principal, require_capability, require_owner
from app.modules.identity.phone import InvalidPhoneNumber, normalize_iranian_mobile
from app.modules.identity.sms import FakeSmsAdapter


def auth_settings(**overrides) -> Settings:
    values = {
        "_env_file": None, "database_password": "test-only", "auth_enabled": True,
        "auth_sms_adapter": "fake", "auth_cookie_secure": True,
        "auth_otp_hmac_secret": "otp-test-secret-0123456789-0123456789",
        "auth_csrf_secret": "csrf-test-secret-0123456789-0123456789",
        "auth_rate_limit_secret": "rate-test-secret-0123456789-0123456789",
        "auth_session_idle_seconds": 1800, "auth_session_absolute_seconds": 43200,
        "auth_allowed_origins": "https://testserver",
    }
    values.update(overrides)
    return Settings(**values)


class MemoryAuthRepository:
    """Deterministic service seam; PostgreSQL semantics are covered separately."""

    def __init__(self):
        self.challenges = {}
        self.sessions = {}
        self.csrf = {}
        self.users = {}

    def create_challenge(self, **kwargs):
        self.challenges[kwargs["challenge_id"]] = {**kwargs, "delivery_status": "queued", "failed": 0}
        return True

    def challenge_phone(self, challenge_id):
        row = self.challenges.get(challenge_id)
        return row["phone"] if row else None

    def allow_verification_attempt(self, limits, now, window_seconds):
        return True

    def mark_delivery_sent(self, challenge_id):
        self.challenges[challenge_id]["delivery_status"] = "sent"

    def mark_delivery_failed(self, challenge_id):
        self.challenges[challenge_id]["delivery_status"] = "failed"

    def verify_and_create_session(self, **kwargs):
        row = self.challenges.get(kwargs["challenge_id"])
        if not row or row["delivery_status"] != "sent" or row.get("consumed"):
            return None
        if datetime.now(UTC) >= row["expires_at"]:
            return None
        if not hmac.compare_digest(row["verifier"], kwargs["candidate_verifier"]):
            row["failed"] += 1
            return None
        row["consumed"] = True
        user_id = uuid4()
        self.users[user_id] = row["phone"]
        self.sessions[kwargs["token_hash"]] = user_id
        self.csrf[user_id] = kwargs["csrf_hash"]
        return {"user_id": user_id, "phone_e164": row["phone"], "session_id": user_id}

    def resolve_session(self, token_hash, now, idle_seconds):
        user_id = self.sessions.get(token_hash)
        if user_id is None:
            return None
        return {"user_id": user_id, "phone_e164": self.users[user_id], "session_id": user_id}

    def validate_csrf(self, session_id, csrf_hash):
        return self.csrf.get(session_id) == csrf_hash

    def revoke_session(self, token_hash, now):
        self.sessions.pop(token_hash, None)


def test_phone_normalization_accepts_iranian_formats_and_localized_digits():
    expected = "+989121234567"
    for value in ("09121234567", "+989121234567", "00989121234567", "۰۹۱۲۱۲۳۴۵۶۷", "+٩٨ ٩١٢ ١٢٣ ٤٥٦٧"):
        assert normalize_iranian_mobile(value) == expected


@pytest.mark.parametrize("value", ["9121234567", "+12025550123", "0912123456", "091212345678", "09ABC1234567", "0098912123456x"])
def test_phone_normalization_rejects_ambiguous_or_unsupported_values(value):
    with pytest.raises(InvalidPhoneNumber):
        normalize_iranian_mobile(value)


def test_settings_require_explicit_auth_security_configuration():
    with pytest.raises(ValueError):
        Settings(_env_file=None, database_password="test", auth_enabled=True)
    with pytest.raises(ValueError):
        auth_settings(app_env="production", auth_enabled=True)


def test_phone_otp_flow_never_returns_code_or_raw_session_in_json(caplog):
    settings = auth_settings()
    sms = FakeSmsAdapter()
    repository = MemoryAuthRepository()
    service = AuthenticationService(settings, sms, repository)  # type: ignore[arg-type]
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        with TestClient(app, base_url="https://testserver") as client:
            issue = client.post("/api/v1/auth/otp/challenges", json={"phone_number": "۰۹۱۲۱۲۳۴۵۶۷", "locale": "fa-IR"})
            assert issue.status_code == 202
            challenge = issue.json()["challenge_id"]
            message = sms.take_messages()[0]
            code = re.search(r"\d{6}", message.body).group()
            assert message.recipient == "+989121234567"
            assert code not in issue.text
            assert "OTP" not in issue.text

            verified = client.post("/api/v1/auth/otp/verify", json={"challenge_id": challenge, "code": code})
            assert verified.status_code == 200
            assert verified.json()["user"]["phone_verified"] is True
            assert "csrf_token" in verified.json()
            assert "session" not in verified.text.lower()
            cookie = verified.headers["set-cookie"]
            assert "__Host-rahgard_session=" in cookie
            assert "httponly" in cookie.lower() and "secure" in cookie.lower() and "samesite=lax" in cookie.lower()
            raw_cookie = cookie.split(";", 1)[0].split("=", 1)[1]
            assert code not in caplog.text
            assert raw_cookie not in caplog.text

            restored = client.get("/api/v1/auth/me")
            assert restored.status_code == 200
            assert restored.json()["user"]["user_id"] == verified.json()["user"]["user_id"]
            csrf = restored.json()["csrf_token"]
            assert client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf, "Origin": "https://testserver"}).status_code == 204
            assert client.get("/api/v1/auth/me").status_code == 401
            replay = client.post("/api/v1/auth/otp/verify", json={"challenge_id": challenge, "code": code})
            assert replay.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_csrf_and_expired_sessions_fail_closed():
    settings = auth_settings()
    sms = FakeSmsAdapter()
    repository = MemoryAuthRepository()
    service = AuthenticationService(settings, sms, repository)  # type: ignore[arg-type]
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        with TestClient(app, base_url="https://testserver") as client:
            response = client.post("/api/v1/auth/otp/challenges", json={"phone_number": "09121234567"})
            challenge = response.json()["challenge_id"]
            code = re.search(r"\d{6}", sms.take_messages()[0].body).group()
            login = client.post("/api/v1/auth/otp/verify", json={"challenge_id": challenge, "code": code})
            rejected = client.post("/api/v1/auth/logout", headers={"Origin": "https://evil.example", "X-CSRF-Token": login.json()["csrf_token"]})
            assert rejected.status_code == 403
            assert client.get("/api/v1/auth/me").status_code == 200
    finally:
        app.dependency_overrides.clear()


def test_authorization_is_server_scoped_and_provider_admin_fails_closed():
    user_id, another_id = uuid4(), uuid4()
    principal = Principal(user_id=user_id)
    require_owner(principal, user_id)
    with pytest.raises(AuthorizationDenied):
        require_owner(principal, another_id)
    with pytest.raises(AuthorizationDenied):
        require_capability(principal, "ai_provider:admin")
    response = TestClient(app).get("/api/v1/admin/providers")
    assert response.status_code == 404


def test_authenticated_client_cannot_submit_identity_or_capability_fields():
    from app.api.auth import ChallengeRequest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ChallengeRequest(phone_number="09121234567", user_id=str(uuid4()), is_admin=True)


def test_authentication_disabled_fails_closed():
    settings = auth_settings(auth_enabled=False)
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = TestClient(app).post(
            "/api/v1/auth/otp/challenges", json={"phone_number": "09121234567"}
        )
        assert response.status_code == 503
        assert response.json() == {"error": {"code": "authentication_unavailable"}}
    finally:
        app.dependency_overrides.clear()
