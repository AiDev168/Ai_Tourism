from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api import auth as auth_api
from app.api.auth import (
    StagingEmailRegistrationRequest,
    StagingInviteRedeemRequest,
    get_auth_service,
)
from app.core.config import Settings, get_settings
from app.api.auth import router as auth_router
from app.modules.identity.auth_service import AuthenticationService
from app.modules.identity.sms import DisabledSmsAdapter
from app.modules.identity.staging_auth import derive_password, hash_invite, normalize_login, password_bytes, password_material

api_test_app = FastAPI()
api_test_app.include_router(auth_router)


def staging_settings(**overrides):
    values = {
        "_env_file": None, "database_password": "test-only", "app_env": "staging",
        "auth_enabled": True, "auth_sms_adapter": "disabled", "staging_auth_enabled": True,
        "staging_public_host": "rahgard-staging.example.test", "auth_cookie_secure": True,
        "auth_allowed_origins": "https://rahgard-staging.example.test",
        "staging_email_signup_enabled": False,
        "auth_otp_hmac_secret": SecretStr("a" * 32), "auth_csrf_secret": SecretStr("b" * 32),
        "auth_rate_limit_secret": SecretStr("c" * 32), "auth_session_idle_seconds": 1800,
        "auth_session_absolute_seconds": 43200,
    }
    values.update(overrides)
    return Settings(**values)


class MemoryStagingRepository:
    def __init__(self, login_name: str, password: str):
        self.user_id = uuid4()
        self.salt, self.verifier = password_material(password)
        self.login_name = login_name

    def allow_attempt(self, **_kwargs):
        return True

    def load_credential(self, login_name):
        if login_name != self.login_name:
            return None
        return {"user_id": self.user_id, "salt": self.salt, "verifier": self.verifier,
                "iterations": 600_000, "account_status": "active", "is_synthetic": False}

    def create_session(self, **kwargs):
        assert kwargs["user_id"] == self.user_id
        assert kwargs["expected_verifier"] == self.verifier
        assert len(kwargs["token_hash"]) == len(kwargs["csrf_hash"]) == 32
        return {"user_id": self.user_id, "email": self.login_name, "session_id": uuid4()}

    def register_email_account(self, **kwargs):
        if kwargs["login_name"] == self.login_name:
            return None
        self.user_id = uuid4()
        self.login_name = kwargs["login_name"]
        self.salt = kwargs["salt"]
        self.verifier = kwargs["verifier"]
        assert kwargs["maximum_accounts"] >= 1
        return {"user_id": self.user_id, "email": self.login_name, "session_id": uuid4()}

    def redeem_invite(self, **kwargs):
        if kwargs["token_digest"] != hash_invite("valid-invite-code-0123456789012345678901234"):
            return None
        return {"user_id": self.user_id, "email": kwargs["login_name"], "session_id": uuid4()}


def test_staging_passwords_preserve_unicode_and_bound_inputs():
    login = normalize_login("  Traveler@Example.Test ")
    password = "\u0633\u0641\u0631 \u0627\u0645\u0646 \u0648 \u062f\u0644\u0646\u0634\u06cc\u0646 Rahgard \u06f2\u06f0\u06f2\u06f6"
    salt, verifier = password_material(password)
    assert login == "traveler@example.test"
    assert len(salt) == len(verifier) == 32
    assert derive_password(password, salt) == verifier
    assert hash_invite("valid-invite-code-0123456789012345678901234") != hash_invite("other-invite-code-0123456789012345678901234")
    for value in ("bad", "x" * 257, "a\0" + "b" * 20):
        with pytest.raises(ValueError):
            password_material(value)


def test_regular_user_password_boundaries_are_8_to_256_unicode_characters():
    for length in (8, 24, 25, 256):
        value = "旅" * length
        assert len(password_bytes(value)) > length
        salt, verifier = password_material(value)
        assert derive_password(value, salt) == verifier
        registration = StagingEmailRegistrationRequest.model_validate(
            {"email": "new@example.test", "password": value}
        )
        redemption = StagingInviteRedeemRequest.model_validate(
            {"invite_code": "A" * 32, "email": "new@example.test", "password": value}
        )
        assert registration.password == redemption.password == value
    for length in (7, 257):
        value = "旅" * length
        with pytest.raises(ValueError):
            password_bytes(value)
        with pytest.raises(ValueError):
            StagingEmailRegistrationRequest.model_validate(
                {"email": "new@example.test", "password": value}
            )
        with pytest.raises(ValueError):
            StagingInviteRedeemRequest.model_validate(
                {"invite_code": "A" * 32, "email": "new@example.test", "password": value}
            )


def test_staging_login_uses_exact_origin_secure_cookie_and_one_time_invite(monkeypatch):
    settings = staging_settings()
    correct_password = "\u0633\u0641\u0631 \u0627\u0645\u0646 \u0648 \u062f\u0644\u0646\u0634\u06cc\u0646 Rahgard \u06f2\u06f0\u06f2\u06f6"
    repository = MemoryStagingRepository("traveler@example.test", correct_password)
    monkeypatch.setattr(auth_api, "StagingAuthRepository", lambda _settings: repository)
    service = AuthenticationService(settings, DisabledSmsAdapter())
    api_test_app.dependency_overrides[get_settings] = lambda: settings
    api_test_app.dependency_overrides[get_auth_service] = lambda: service
    headers = {"Origin": "https://rahgard-staging.example.test", "Host": "rahgard-staging.example.test",
               "X-Forwarded-Proto": "https"}
    try:
        with TestClient(api_test_app, base_url="https://rahgard-staging.example.test") as client:
            signed_in = client.post("/api/v1/auth/staging/login", headers=headers,
                                    json={"email": "TRAVELER@example.test", "password": correct_password})
            assert signed_in.status_code == 200
            assert signed_in.json()["user"]["auth_method"] == "staging_invite"
            assert signed_in.headers["set-cookie"].startswith("__Host-rahgard_session=")
            assert "secure" in signed_in.headers["set-cookie"].lower()

            invite = client.post("/api/v1/auth/staging/redeem", headers=headers,
                                 json={"invite_code": "valid-invite-code-0123456789012345678901234",
                                       "email": "new@example.test", "password": correct_password})
            assert invite.status_code == 200
            assert invite.json()["user"]["auth_method"] == "staging_invite"

            denied = client.post("/api/v1/auth/staging/login",
                                 headers={**headers, "Origin": "https://attacker.example.test"},
                                 json={"email": "traveler@example.test", "password": correct_password})
            assert denied.status_code == 401
            forwarded_host = client.post("/api/v1/auth/staging/login",
                                         headers={**headers, "X-Forwarded-Host": "attacker.example.test"},
                                         json={"email": "traveler@example.test", "password": correct_password})
            assert forwarded_host.status_code == 401
    finally:
        api_test_app.dependency_overrides.clear()


def test_staging_email_registration_is_explicitly_gated_rate_limited_and_issues_secure_session(monkeypatch):
    password = "Pilot888"
    settings = staging_settings(staging_email_signup_enabled=True)
    repository = MemoryStagingRepository("existing@example.test", password)
    attempts = []

    def allow_attempt(**kwargs):
        attempts.append(kwargs)
        return True

    repository.allow_attempt = allow_attempt
    monkeypatch.setattr(auth_api, "StagingAuthRepository", lambda _settings: repository)
    service = AuthenticationService(settings, DisabledSmsAdapter())
    api_test_app.dependency_overrides[get_settings] = lambda: settings
    api_test_app.dependency_overrides[get_auth_service] = lambda: service
    headers = {"Origin": "https://rahgard-staging.example.test", "Host": "rahgard-staging.example.test",
               "X-Forwarded-Proto": "https"}
    try:
        with TestClient(api_test_app, base_url="https://rahgard-staging.example.test") as client:
            methods = client.get("/api/v1/auth/method").json()
            assert methods["staging_email_signup"] is True
            response = client.post("/api/v1/auth/staging/register", headers=headers,
                                   json={"email": " New.Traveler@example.test ", "password": password})
            assert response.status_code == 200
            assert response.json()["user"]["auth_method"] == "staging_invite"
            assert response.headers["set-cookie"].startswith("__Host-rahgard_session=")
            assert "secure" in response.headers["set-cookie"].lower()
            assert [item["dimension"] for item in attempts] == ["invite", "global"]
            assert repository.load_credential("new.traveler@example.test") is not None
            disabled = staging_settings(staging_email_signup_enabled=False)
            api_test_app.dependency_overrides[get_settings] = lambda: disabled
            rejected = client.post("/api/v1/auth/staging/register", headers=headers,
                                   json={"email": "other@example.test", "password": password})
            assert rejected.status_code == 401
    finally:
        api_test_app.dependency_overrides.clear()


def test_email_registration_cannot_be_enabled_outside_staging():
    with pytest.raises(ValueError, match="restricted to authenticated staging"):
        staging_settings(app_env="development", staging_auth_enabled=False,
                         auth_cookie_secure=False, staging_email_signup_enabled=True)
