from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api import auth
from app.core.config import Settings, get_settings
from app.main import app
from app.modules.identity.auth_service import AuthenticatedUser


def local_settings() -> Settings:
    return Settings(
        app_env="local_pilot", app_host="127.0.0.1", database_host="127.0.0.1",
        database_port=55441, database_name="rahgard_pilot_local", database_user="ai_tourism_app",
        database_password=SecretStr("local-test-db-password"), auth_enabled=True,
        auth_local_owner_enabled=True, auth_sms_adapter="disabled", auth_cookie_secure=True,
        auth_allowed_origins="https://localhost:8443", auth_otp_hmac_secret=SecretStr("a" * 32),
        auth_csrf_secret=SecretStr("b" * 32), auth_rate_limit_secret=SecretStr("c" * 32),
        auth_session_idle_seconds=3600, auth_session_absolute_seconds=86400,
    )


class FakeRepository:
    def load_local_owner_credential(self, login_name):
        assert login_name == "owner"
        return {"owner_id": uuid4(), "salt": b"a" * 32, "verifier": b"b" * 32, "iterations": 600_000}


class FakeService:
    repository = FakeRepository()

    def issue_local_owner_session(self, owner_id, _salt=None, _verifier=None, _iterations=None):
        return (AuthenticatedUser(owner_id, None, uuid4(), "local_owner"), "opaque-session", "csrf-memory")


def test_local_owner_login_returns_only_normal_secure_session(monkeypatch):
    settings = local_settings()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[auth.get_auth_service] = lambda: FakeService()
    called = {}

    def verifier(credential, password, **kwargs):
        called.update(credential=credential, password=password, kwargs=kwargs)
        return FakeService().issue_local_owner_session(credential.owner_id)

    monkeypatch.setattr(auth, "verify_and_issue", verifier)
    try:
        with TestClient(app, base_url="https://localhost:8443") as client:
            response = client.post("/api/v1/auth/local-owner/login", json={
                "login_name": "owner", "password": "correct horse battery 912!",
            }, headers={"Origin": "https://localhost:8443"})
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["user"]["auth_method"] == "local_owner"
        assert payload["user"]["phone_e164"] is None
        assert payload["user"]["phone_verified"] is None
        assert payload["csrf_token"] == "csrf-memory"
        cookie = response.headers["set-cookie"]
        assert "__Host-rahgard_session=opaque-session" in cookie
        assert "Secure" in cookie and "HttpOnly" in cookie and "SameSite=lax" in cookie
        assert "correct horse" not in response.text
        assert called["credential"].owner_id
        assert called["kwargs"]["request_peer"] == "testclient"
        assert called["kwargs"]["origin"] == "https://localhost:8443"
    finally:
        app.dependency_overrides.clear()


def test_local_owner_login_rejects_forwarded_client_identity_before_verifier(monkeypatch):
    settings = local_settings()
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[auth.get_auth_service] = lambda: FakeService()
    monkeypatch.setattr(auth, "verify_and_issue", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("must reject first")))
    try:
        with TestClient(app, base_url="https://localhost:8443") as client:
            response = client.post("/api/v1/auth/local-owner/login",
                                   headers={"Origin": "https://localhost:8443", "X-Forwarded-For": "127.0.0.1"},
                                   json={"login_name": "owner", "password": "any password"})
        assert response.status_code == 401, response.text
        assert response.json() == {"error": {"code": "unauthenticated"}}
        assert "set-cookie" not in response.headers
    finally:
        app.dependency_overrides.clear()


def test_auth_method_reports_only_public_local_mode():
    settings = local_settings()
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app, base_url="https://localhost:8443") as client:
            response = client.get("/api/v1/auth/method")
        assert response.status_code == 200
        assert response.json() == {"method": "local_owner"}
        assert response.headers["cache-control"] == "no-store"
    finally:
        app.dependency_overrides.clear()
