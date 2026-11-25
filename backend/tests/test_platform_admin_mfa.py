from uuid import UUID
import base64
import time

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api.auth import authenticated_user, require_authenticated_csrf
from app.api.platform_admin_mfa import platform_mfa_status
from app.api.platform_admin_mfa import _runtime
from app.core.config import Settings, get_settings
from app.main import app
from app.modules.identity.auth_service import AuthenticatedUser
from app.modules.identity.platform_admin_mfa import (
    current_totp_counter,
    decrypt_totp_secret,
    encrypt_totp_secret,
    generate_recovery_codes,
    recovery_code_hash,
)
from app.modules.provider_admin.security import totp_code


def _settings(**overrides):
    values = {
        "_env_file": None,
        "app_env": "staging",
        "auth_enabled": True,
        "auth_cookie_secure": True,
        "auth_sms_adapter": "disabled",
        "staging_auth_enabled": True,
        "staging_public_host": "rahgard.example.test",
        "auth_allowed_origins": "https://rahgard.example.test",
        "auth_otp_hmac_secret": SecretStr("o" * 32),
        "auth_csrf_secret": SecretStr("c" * 32),
        "auth_rate_limit_secret": SecretStr("r" * 32),
        "auth_session_idle_seconds": 1800,
        "auth_session_absolute_seconds": 43200,
        "database_password": "test-only",
        "database_user": "ai_tourism_app",
        "platform_admin_mfa_encryption_key_hex": SecretStr("a" * 64),
        "platform_admin_recovery_pepper": SecretStr("p" * 32),
    }
    values.update(overrides)
    return Settings(**values)


def test_totp_secret_encryption_authenticates_owner_identity_and_ciphertext():
    actor = UUID(int=1)
    other = UUID(int=2)
    secret = bytes(range(20))
    key = bytes(range(32))
    ciphertext = encrypt_totp_secret(secret, key, actor)
    assert decrypt_totp_secret(ciphertext, key, actor) == secret
    with pytest.raises(Exception):
        decrypt_totp_secret(ciphertext, key, other)
    damaged = ciphertext[:-1] + bytes([ciphertext[-1] ^ 1])
    with pytest.raises(Exception):
        decrypt_totp_secret(damaged, key, actor)


def test_totp_verification_returns_monotonic_counter_and_rejects_bad_codes():
    secret = bytes(range(20))
    now = 1_800_000_000
    code = totp_code(secret, now)
    counter = current_totp_counter(secret, code, now)
    assert counter == now // 30
    assert current_totp_counter(secret, code, now + 30) == (now // 30)  # previous step allowed for clock skew
    assert current_totp_counter(secret, "۱۲۳۴۵۶", now) is None
    assert current_totp_counter(secret, "1234567", now) is None


def test_recovery_hashes_are_domain_separated_and_generated_codes_are_unique():
    codes = generate_recovery_codes(10)
    assert len(set(codes)) == 10
    assert all(recovery_code_hash(code, b"p" * 32) == recovery_code_hash(code.replace("-", " "), b"p" * 32) for code in codes)
    assert recovery_code_hash(codes[0], b"p" * 32) != recovery_code_hash(codes[0], b"q" * 32)


def test_platform_mfa_requires_staging_authentication_and_server_secrets():
    assert len(_runtime(_settings())[0]) == 32
    missing = _settings()
    missing.platform_admin_mfa_encryption_key_hex = None
    with pytest.raises(HTTPException) as disabled:
        _runtime(missing)
    assert disabled.value.status_code == 503
    insecure_settings = _settings()
    insecure_settings.auth_cookie_secure = False
    with pytest.raises(HTTPException) as insecure:
        _runtime(insecure_settings)
    assert insecure.value.status_code == 503
    local_settings = _settings()
    local_settings.app_env = "local_pilot"
    with pytest.raises(HTTPException) as local:
        _runtime(local_settings)
    assert local.value.status_code == 503


def test_mfa_endpoints_require_authenticated_identity_and_csrf():
    app.dependency_overrides.clear()
    def unauthenticated():
        raise HTTPException(status_code=401, detail="unauthenticated")
    app.dependency_overrides[authenticated_user] = unauthenticated
    try:
        with TestClient(app, base_url="https://rahgard.example.test") as client:
            assert client.post("/api/v1/admin/mfa/enroll").status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_real_api_flow_enrolls_steps_up_uses_recovery_once_and_resets(monkeypatch):
    from app.modules.identity.auth_repository import AuthRepository
    from app.modules.provider_admin.security import totp_code

    actor = AuthenticatedUser(UUID(int=71), None, UUID(int=72), "staging_invite")
    settings = _settings()
    store: dict[str, object] = {"recovery_hashes": []}

    class Cursor:
        row = None
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def execute(self, query, params=()):
            sql = " ".join(query.split())
            if "identity.has_platform_admin_capability" in sql:
                self.row = {"allowed": True}
            elif sql.startswith("INSERT INTO identity.platform_admin_mfa("):
                store["pending"] = params[1]
                self.row = {"user_id": actor.user_id}
            elif sql.startswith("SELECT pending_secret_ciphertext"):
                self.row = {"pending_secret_ciphertext": store.get("pending")}
            elif sql.startswith("UPDATE identity.platform_admin_mfa SET secret_ciphertext=pending_secret_ciphertext"):
                store["secret"] = store.pop("pending")
                store["enabled"] = params[0]
                store["last_counter"] = params[1]
                store["recovery_hashes"] = list(params[2])
                self.row = {"user_id": actor.user_id}
            elif sql.startswith("INSERT INTO identity.platform_admin_step_up"):
                store["step_up"] = params[3]
                self.row = None
            elif sql.startswith("SELECT secret_ciphertext,last_totp_counter"):
                self.row = {"secret_ciphertext": store.get("secret"), "last_totp_counter": store.get("last_counter", -1)}
            elif sql.startswith("UPDATE identity.platform_admin_mfa SET last_totp_counter"):
                store["last_counter"] = params[0]
                self.row = {"user_id": actor.user_id}
            elif sql.startswith("UPDATE identity.platform_admin_mfa SET recovery_hashes=array_remove"):
                hashes = store.get("recovery_hashes", [])
                if params[0] in hashes:
                    store["recovery_hashes"] = [value for value in hashes if value != params[0]]
                    self.row = {"user_id": actor.user_id}
                else:
                    self.row = None
            elif sql.startswith("SELECT EXISTS(SELECT 1 FROM identity.platform_admin_step_up"):
                self.row = {"fresh": bool(store.get("step_up"))}
            elif sql.startswith("SELECT m.enabled_at,"):
                self.row = {"enabled_at": store.get("enabled"), "step_up_expires_at": store.get("step_up")}
            elif sql.startswith("DELETE FROM identity.platform_admin_mfa"):
                store.clear()
                self.row = None
            elif "identity.record_platform_admin_mfa_event" in sql or "set_config('app.actor_id'" in sql:
                self.row = None
            else:
                raise AssertionError(f"unexpected SQL in MFA API test: {sql}")
            return self
        def fetchone(self): return self.row

    class Connection:
        def __init__(self): self.value = Cursor()
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def transaction(self): return self
        def cursor(self): return self.value

    app.dependency_overrides.clear()
    app.dependency_overrides[authenticated_user] = lambda: actor
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr("app.api.platform_admin_mfa._connection", lambda _settings: Connection())
    monkeypatch.setattr(AuthRepository, "allow_verification_attempt", lambda *_args, **_kwargs: True)
    try:
        with TestClient(app, base_url="https://rahgard.example.test") as client:
            enrolled = client.post("/api/v1/admin/mfa/enroll")
            assert enrolled.status_code == 200
            secret = base64.b32decode(enrolled.json()["secret"] + "=" * (-len(enrolled.json()["secret"]) % 8))
            now = int(time.time())
            code = totp_code(secret, now)
            verified = client.post("/api/v1/admin/mfa/verify", json={"code": code})
            assert verified.status_code == 200
            codes = verified.json()["recovery_codes"]
            assert len(codes) == 10 and len(set(codes)) == 10
            assert platform_mfa_status(settings, actor)["enrolled"] is True
            replay = client.post("/api/v1/admin/mfa/step-up", json={"code": code})
            assert replay.status_code == 401
            recovery = client.post("/api/v1/admin/mfa/recovery", json={"code": codes[0]})
            assert recovery.status_code == 200
            reused = client.post("/api/v1/admin/mfa/recovery", json={"code": codes[0]})
            assert reused.status_code == 401
            reset = client.post("/api/v1/admin/mfa/reset")
            assert reset.status_code == 200
            assert platform_mfa_status(settings, actor)["enrolled"] is False
    finally:
        app.dependency_overrides.clear()

    actor = AuthenticatedUser(UUID(int=17), None, UUID(int=18), "staging_invite")
    app.dependency_overrides[authenticated_user] = lambda: actor
    app.dependency_overrides[get_settings] = lambda: _settings()
    try:
        with TestClient(app, base_url="https://rahgard.example.test") as client:
            response = client.post("/api/v1/admin/mfa/enroll")
            assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
