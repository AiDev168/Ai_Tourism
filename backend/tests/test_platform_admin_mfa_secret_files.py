from pathlib import Path
import os

import pytest

from app.core.config import Settings


KEY = "a" * 64
PEPPER = "p" * 48


def _settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "app_env": "staging",
        "auth_enabled": True,
        "auth_otp_hmac_secret": "otp-test-only-" + "x" * 32,
        "auth_csrf_secret": "csrf-test-only-" + "x" * 32,
        "staging_auth_enabled": True,
        "staging_public_host": "pilot.example.invalid",
        "auth_allowed_origins": "https://pilot.example.invalid",
        "auth_cookie_secure": True,
        "auth_rate_limit_secret": "rate-limit-test-only-" + "x" * 32,
        "auth_session_idle_seconds": 1800,
        "auth_session_absolute_seconds": 43200,
        "database_user": "ai_tourism_app",
        "database_password": "test-only",
    }
    values.update(overrides)
    return Settings(**values)


def _private_file(path: Path, value: str) -> Path:
    path.write_text(value + "\n", encoding="utf-8")
    if path.stat().st_mode & 0o777:
        path.chmod(0o640)
    return path


def test_platform_mfa_secret_files_are_loaded_and_masked(tmp_path):
    key_file = _private_file(tmp_path / "key", KEY)
    pepper_file = _private_file(tmp_path / "pepper", PEPPER)
    settings = _settings(
        platform_admin_mfa_encryption_key_file=key_file,
        platform_admin_recovery_pepper_file=pepper_file,
    )
    assert settings.platform_admin_mfa_encryption_key_hex.get_secret_value() == KEY
    assert settings.platform_admin_recovery_pepper.get_secret_value() == PEPPER
    assert KEY not in repr(settings)
    assert PEPPER not in repr(settings)


def test_platform_mfa_file_permissions_and_path_are_fail_closed(tmp_path):
    if os.name == "nt":
        pytest.skip("POSIX mode-bit validation is exercised only on Linux")
    key_file = _private_file(tmp_path / "key", KEY)
    pepper_file = _private_file(tmp_path / "pepper", PEPPER)
    pepper_file.chmod(0o644)
    with pytest.raises(ValueError, match="secret file is unavailable or unsafe"):
        _settings(
            platform_admin_mfa_encryption_key_file=key_file,
            platform_admin_recovery_pepper_file=pepper_file,
        )


def test_platform_mfa_secret_file_rejects_direct_value_precedence(tmp_path):
    key_file = _private_file(tmp_path / "key", KEY)
    with pytest.raises(ValueError, match="either direct injection or a secret file"):
        _settings(
            platform_admin_mfa_encryption_key_hex=KEY,
            platform_admin_mfa_encryption_key_file=key_file,
            platform_admin_recovery_pepper=PEPPER,
        )


def test_platform_mfa_secret_file_content_still_obeys_exact_key_validation(tmp_path):
    key_file = _private_file(tmp_path / "key", "not-a-hex-key")
    pepper_file = _private_file(tmp_path / "pepper", PEPPER)
    with pytest.raises(ValueError, match="two valid server keys"):
        _settings(
            platform_admin_mfa_encryption_key_file=key_file,
            platform_admin_recovery_pepper_file=pepper_file,
        )
