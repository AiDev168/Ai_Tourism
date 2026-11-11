from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api import auth, provider_admin
from app.core.config import Settings, get_settings
from app.modules.identity.auth_service import AuthenticatedUser


class FakeRegistry:
    def __init__(self, granted=True, fresh=True):
        self.granted = granted
        self.fresh = fresh
        self.profile_id = uuid4()
        self.revision_id = uuid4()
        self.profile = {"profile_id": self.profile_id, "name": "Private", "provider_kind": "lm_studio",
                        "enabled": True, "version": 2}
        self.revision = {"revision_id": self.revision_id, "profile_id": self.profile_id,
                         "config": {"provider_kind": "lm_studio", "base_url": "http://127.0.0.1:1234/v1",
                                    "auth_mode": "none", "timeout_seconds": 10, "concurrency_limit": 1,
                                    "capabilities": {"chat": {"model_id": "test-model", "max_tokens": 32}}},
                         "secret_ref": "opaque-secret-reference"}

    def has_admin_grant(self, _user_id):
        return self.granted

    def get_admin_mfa(self, _user_id):
        return {"enabled_at": datetime.now(UTC)} if self.fresh else {}

    def step_up_expires_at(self, _user_id, _session_id):
        return datetime.now(UTC) + timedelta(minutes=3) if self.fresh else None

    def has_fresh_step_up(self, _user_id, _session_id):
        return self.fresh

    def list_profiles(self):
        return [self.profile]

    def latest_revision(self, _profile_id):
        return {**self.revision, "secret_configured": True}

    def list_revisions(self, _profile_id):
        return []

    def get_fallback(self, _capability):
        return {"enabled": False, "ordered_revision_ids": []}

    def set_fallback(self, _capability, enabled, ordered_revision_ids, *, actor_id):
        self.fallback = (enabled, ordered_revision_ids, actor_id)
        return {"enabled": enabled, "ordered_revision_ids": ordered_revision_ids}


def _settings():
    return Settings(
        app_env="local_pilot", database_password=SecretStr("test-only-not-a-secret"),
        auth_enabled=True, auth_local_owner_enabled=True, auth_cookie_secure=True,
        auth_allowed_origins="https://localhost:8443", auth_sms_adapter="disabled",
        auth_otp_hmac_secret=SecretStr("a" * 32), auth_csrf_secret=SecretStr("b" * 32),
        auth_rate_limit_secret=SecretStr("c" * 32), auth_session_idle_seconds=1800,
        auth_session_absolute_seconds=28800, ai_provider_admin_enabled=True,
        ai_provider_vault_dir="C:/local-pilot-secret-vault",
        ai_provider_admin_recovery_pepper=SecretStr("d" * 32),
    )


def _client(monkeypatch, *, auth_method="local_owner", granted=True, fresh=True):
    registry = FakeRegistry(granted=granted, fresh=fresh)
    user = AuthenticatedUser(uuid4(), None, uuid4(), auth_method)
    app = FastAPI()
    app.include_router(provider_admin.router)
    app.dependency_overrides[auth.authenticated_user] = lambda: user
    app.dependency_overrides[auth.require_authenticated_csrf] = lambda: None
    app.dependency_overrides[get_settings] = _settings
    monkeypatch.setattr(provider_admin, "_registry", lambda _settings: registry)
    return TestClient(app), registry


def test_traveler_otp_does_not_grant_provider_admin(monkeypatch):
    client, _ = _client(monkeypatch, auth_method="otp", granted=True)
    response = client.get("/api/v1/admin/ai-providers/me")
    assert response.status_code == 403


def test_local_owner_without_independent_admin_grant_is_denied(monkeypatch):
    client, _ = _client(monkeypatch, granted=False)
    response = client.get("/api/v1/admin/ai-providers/profiles")
    assert response.status_code == 403


def test_sensitive_profile_mutation_requires_fresh_totp_step_up(monkeypatch):
    client, _ = _client(monkeypatch, fresh=False)
    response = client.post("/api/v1/admin/ai-providers/profiles", json={
        "name": "local", "provider_kind": "lm_studio", "base_url": "http://127.0.0.1:1234/v1",
        "auth_mode": "none", "capabilities": {"chat": {"model_id": "local-model"}},
    })
    assert response.status_code == 403


def test_profile_read_contains_no_vault_reference_or_secret(monkeypatch):
    client, _ = _client(monkeypatch)
    response = client.get("/api/v1/admin/ai-providers/profiles")
    assert response.status_code == 200
    body = response.json()
    assert body["profiles"][0]["secret_configured"] is True
    assert "opaque-secret-reference" not in response.text
    assert "api_key" not in response.text
    assert body["profiles"][0]["base_url"] == "http://127.0.0.1:1234/v1"


def test_fallback_read_reports_disabled_default_without_secret_data(monkeypatch):
    client, _ = _client(monkeypatch)
    response = client.get("/api/v1/admin/ai-providers/fallback")
    assert response.status_code == 200
    assert response.json() == {"capability": "chat", "enabled": False, "ordered_revision_ids": []}


def test_fallback_write_requires_fresh_session_step_up(monkeypatch):
    client, _ = _client(monkeypatch, fresh=False)
    response = client.put("/api/v1/admin/ai-providers/fallback", json={
        "capability": "chat", "enabled": True, "ordered_revision_ids": [str(uuid4())]
    })
    assert response.status_code == 403


def test_fallback_write_rejects_unimplemented_capability(monkeypatch):
    client, _ = _client(monkeypatch)
    response = client.put("/api/v1/admin/ai-providers/fallback", json={
        "capability": "vision", "enabled": True, "ordered_revision_ids": [str(uuid4())]
    })
    assert response.status_code == 422
