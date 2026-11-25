from uuid import UUID

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.api.admin_guards import privileged_admin_writes_available, require_privileged_admin_step_up
from app.core.config import Settings
from app.modules.identity.auth_service import AuthenticatedUser


def _user():
    return AuthenticatedUser(UUID(int=7), None, UUID(int=8), "staging_invite")


def _settings(environment: str, *, configured: bool = True):
    settings = Settings(
        _env_file=None, app_env="staging", auth_enabled=True, auth_cookie_secure=True,
        auth_rate_limit_secret=SecretStr("r" * 32), auth_otp_hmac_secret=SecretStr("o" * 32),
        auth_csrf_secret=SecretStr("c" * 32), auth_session_idle_seconds=1800,
        auth_session_absolute_seconds=43200, auth_sms_adapter="disabled",
        staging_auth_enabled=True, staging_public_host="staging.example.test",
        auth_allowed_origins="https://staging.example.test", database_password="test-only",
        database_user="ai_tourism_app",
        platform_admin_mfa_encryption_key_hex=SecretStr("a" * 64) if configured else None,
        platform_admin_recovery_pepper=SecretStr("p" * 32) if configured else None,
    )
    # Production currently deliberately disables public authentication. The
    # guard's fail-closed production branch can still be checked by switching
    # the already validated staging object without enabling that auth mode.
    settings.app_env = environment
    return settings


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_public_environments_require_configured_session_bound_platform_step_up(environment, monkeypatch):
    settings = _settings(environment)
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def execute(self, *_): return self
        def fetchone(self): return {"fresh": False}
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return Cursor()
    monkeypatch.setattr("app.api.admin_guards.psycopg.connect", lambda **_kwargs: Connection())
    assert privileged_admin_writes_available(environment) is False
    with pytest.raises(HTTPException) as error:
        require_privileged_admin_step_up(settings, _user())
    assert error.value.status_code == 403
    assert error.value.detail == "privileged_admin_step_up_required"


def test_public_writes_fail_closed_when_step_up_keys_are_not_provisioned():
    with pytest.raises(HTTPException) as error:
        require_privileged_admin_step_up(_settings("staging", configured=False), _user())
    assert error.value.status_code == 403
    assert error.value.detail == "privileged_admin_mfa_not_configured"


def test_valid_step_up_for_exact_user_and_session_allows_guarded_write(monkeypatch):
    class Cursor:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def execute(self, *_): return self
        def fetchone(self): return {"fresh": True}
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def cursor(self): return Cursor()
    monkeypatch.setattr("app.api.admin_guards.psycopg.connect", lambda **_kwargs: Connection())
    require_privileged_admin_step_up(_settings("staging"), _user())


@pytest.mark.parametrize("environment", ["development", "test", "local_pilot"])
def test_isolated_local_environments_keep_existing_capability_audited_workflows(environment):
    assert privileged_admin_writes_available(environment) is True
    require_privileged_admin_step_up(_settings(environment, configured=False), _user())


def test_environment_matching_is_case_and_whitespace_insensitive():
    assert privileged_admin_writes_available(" Production ") is False
