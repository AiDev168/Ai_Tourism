from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
import pytest

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
        self.validation_records = []

    def has_admin_grant(self, _user_id):
        return self.granted

    def get_admin_mfa(self, _user_id):
        return {"enabled_at": datetime.now(UTC), "secret_ref": "test-secret"} if self.fresh else {}

    def step_up_expires_at(self, _user_id, _session_id):
        return datetime.now(UTC) + timedelta(minutes=3) if self.fresh else None

    def has_fresh_step_up(self, _user_id, _session_id):
        return self.fresh

    def list_profiles(self):
        return [self.profile]

    def get_profile(self, _profile_id):
        return self.profile

    def latest_revision(self, _profile_id):
        return {**self.revision, "secret_configured": True}

    def list_revisions(self, _profile_id):
        return []

    def capability_validation(self, *_args, **_kwargs):
        return None

    def get_fallback(self, _capability):
        return {"enabled": False, "ordered_revision_ids": []}

    def record_validation(self, revision_id, *, outcome, safe_details, actor_id):
        self.validation_records.append((revision_id, outcome, safe_details, actor_id))
        return {"outcome": outcome}

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


def test_totp_step_up_has_persisted_per_admin_attempt_limit(monkeypatch):
    client, _ = _client(monkeypatch)

    class RateLimitedRepository:
        attempts = 0

        def __init__(self, _settings):
            pass

        def allow_verification_attempt(self, limits, _now, window_seconds):
            type(self).attempts += 1
            assert limits[0][0] == "verify_challenge"
            assert len(limits[0][1]) == 32
            assert limits[0][2] == 5
            assert window_seconds == 600
            return type(self).attempts <= 5

    class FakeVault:
        def get(self, _reference):
            return b"test-only-totp-secret"

    monkeypatch.setattr(provider_admin, "AuthRepository", RateLimitedRepository)
    monkeypatch.setattr(provider_admin, "_vault", lambda _settings: FakeVault())
    monkeypatch.setattr(provider_admin, "_totp_counter", lambda *_args: None)

    statuses = [
        client.post("/api/v1/admin/ai-providers/mfa/step-up", json={"code": "000000"}).status_code
        for _ in range(6)
    ]
    assert statuses == [401, 401, 401, 401, 401, 429]


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
    assert response.json() == {"policies": [
        {"capability": capability, "enabled": False, "ordered_revision_ids": []}
        for capability in ("chat", "embedding", "reranking", "vision")
    ]}


def test_fallback_write_requires_fresh_session_step_up(monkeypatch):
    client, _ = _client(monkeypatch, fresh=False)
    response = client.put("/api/v1/admin/ai-providers/fallback/vision", json={
        "enabled": True, "ordered_revision_ids": [str(uuid4())]
    })
    assert response.status_code == 403


def test_fallback_write_accepts_capability_specific_policy(monkeypatch):
    client, _ = _client(monkeypatch)
    response = client.put("/api/v1/admin/ai-providers/fallback/vision", json={
        "enabled": False, "ordered_revision_ids": []
    })
    assert response.status_code == 200
    assert response.json()["capability"] == "vision"
    assert response.json()["enabled"] is False


def test_unknown_fallback_capability_is_rejected(monkeypatch):
    client, _ = _client(monkeypatch)
    response = client.put("/api/v1/admin/ai-providers/fallback/tools", json={
        "enabled": False, "ordered_revision_ids": []
    })
    assert response.status_code == 422


def test_profile_contract_allows_local_independent_models_but_not_unverified_remote_caps():
    local = provider_admin.ProfileWrite.model_validate({
        "name": "Local multimodal", "provider_kind": "lm_studio",
        "base_url": "http://127.0.0.1:1234/v1", "auth_mode": "none",
        "capabilities": {
            "chat": {"model_id": "chat-model"},
            "vision": {"model_id": "vision-model"},
            "embedding": {"model_id": "embed-model"},
            "reranking": {"model_id": "rerank-model"},
        },
    })
    assert set(local.capabilities) == {"chat", "vision", "embedding", "reranking"}
    with pytest.raises(ValueError, match="verified account support"):
        provider_admin.ProfileWrite.model_validate({
            "name": "Remote", "provider_kind": "openai_compatible",
            "base_url": "https://api.gapgpt.app/v1", "auth_mode": "bearer",
            "api_key": "test-key",
            "capabilities": {"chat": {"model_id": "model"},
                             "embedding": {"model_id": "embed"}},
        })


def test_model_discovery_returns_actual_per_capability_support(monkeypatch):
    client, _registry = _client(monkeypatch)

    class Adapter:
        async def discover_models(self):
            return ("loaded-chat", "loaded-embed")

        def capability_support(self):
            return {"chat": "supported", "vision": "supported",
                    "embedding": "supported", "reranking": "unknown"}

    monkeypatch.setattr(provider_admin, "_provider_adapter", lambda *_args, **_kwargs: Adapter())
    response = client.post(
        f"/api/v1/admin/ai-providers/profiles/{_registry.profile_id}/discover-models",
        headers={"X-CSRF-Token": "ok"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "models": ["loaded-chat", "loaded-embed"],
        "status": "reachable",
        "capability_support": {"chat": "supported", "vision": "supported",
                               "embedding": "supported", "reranking": "unknown"},
    }


def test_explicit_inference_test_persists_capability_specific_success(monkeypatch):
    client, registry = _client(monkeypatch)

    class Adapter:
        async def test_capability(self, capability, model_id, *, test_kind, max_output_tokens):
            return {"success": True, "status": "inference_passed", "latency_ms": 19,
                    "capability": capability, "model_id": model_id, "test_kind": test_kind,
                    "models_catalog_reachable": True, "model_selected": True,
                    "capability_verified": True, "actual_inference_passed": True}

    monkeypatch.setattr(provider_admin, "_provider_adapter", lambda *_args, **_kwargs: Adapter())
    response = client.post(
        f"/api/v1/admin/ai-providers/profiles/{registry.profile_id}/test",
        headers={"X-CSRF-Token": "ok"},
        json={"capability": "chat", "model_id": "test-model",
              "test_kind": "inference", "max_output_tokens": 16},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["actual_inference_passed"] is True
    assert body["capability_verified"] is True
    assert registry.validation_records[-1][2]["capability"] == "chat"
    assert registry.validation_records[-1][2]["test_kind"] == "inference"
    assert registry.validation_records[-1][1] == "valid"


def test_test_api_rejects_output_budget_over_64_tokens(monkeypatch):
    client, registry = _client(monkeypatch)
    response = client.post(
        f"/api/v1/admin/ai-providers/profiles/{registry.profile_id}/test",
        headers={"X-CSRF-Token": "ok"},
        json={"capability": "chat", "model_id": "test-model",
              "test_kind": "inference", "max_output_tokens": 65},
    )
    assert response.status_code == 422


def test_inference_test_requires_binding_for_requested_capability(monkeypatch):
    client, registry = _client(monkeypatch)
    monkeypatch.setattr(
        provider_admin, "_provider_adapter",
        lambda *_args, **_kwargs: pytest.fail("unconfigured capability must not reach transport"),
    )
    response = client.post(
        f"/api/v1/admin/ai-providers/profiles/{registry.profile_id}/test",
        headers={"X-CSRF-Token": "ok"},
        json={"capability": "embedding", "model_id": "embed-model",
              "test_kind": "inference", "max_output_tokens": 16},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "capability_not_configured"
