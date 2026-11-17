from datetime import UTC, datetime, timedelta

import pytest

from app.modules.provider_admin.security import (
    AI_PROVIDER_ADMIN,
    consume_recovery_code,
    generate_recovery_codes,
    hash_recovery_code,
    has_ai_provider_admin_capability,
    new_totp_secret,
    normalize_recovery_code,
    step_up_is_fresh,
    totp_code,
    totp_provisioning_uri,
    verify_totp,
)


PEPPER = b"recovery-pepper-for-tests-only-0000000000"


def test_admin_capability_is_explicit_and_independent_of_traveler_identity():
    assert has_ai_provider_admin_capability({AI_PROVIDER_ADMIN})
    assert not has_ai_provider_admin_capability(set())
    assert not has_ai_provider_admin_capability({"traveler", "owner"})
    assert not has_ai_provider_admin_capability({"content_admin"})
    assert not has_ai_provider_admin_capability("not_ai_provider_admin")


def test_totp_generation_and_bounded_verification():
    secret = new_totp_secret()
    assert len(secret) == 20
    code = totp_code(secret, 1_700_000_010)
    assert verify_totp(secret, code, now=1_700_000_010)
    assert verify_totp(secret, code, now=1_700_000_040, window=1)
    assert not verify_totp(secret, code, now=1_700_000_100, window=1)
    assert not verify_totp(secret, "１２３４５６", now=1_700_000_010)
    assert not verify_totp(secret, "12345x", now=1_700_000_010)
    assert not verify_totp(secret, code, now=1_700_000_010, window=99)


def test_totp_enrollment_uri_is_valid_and_secret_is_not_persisted_by_helper():
    secret = new_totp_secret()
    uri = totp_provisioning_uri(secret, "administrator@example.invalid")
    assert uri.startswith("otpauth://totp/Rahgard%3Aadministrator%40example.invalid?")
    assert "algorithm=SHA1" in uri and "digits=6" in uri and "period=30" in uri
    with pytest.raises(ValueError):
        totp_provisioning_uri(b"short", "admin")


def test_recovery_codes_are_strong_normalized_and_verifiers_are_one_time_inputs():
    codes = generate_recovery_codes()
    assert len(codes) == len(set(codes)) == 10
    assert all(len(normalize_recovery_code(code)) == 16 for code in codes)
    verifiers = [hash_recovery_code(code, PEPPER) for code in codes]
    assert all(len(item) == 32 for item in verifiers)
    assert consume_recovery_code(codes[3].lower().replace("-", " "), verifiers, PEPPER) == 3
    assert consume_recovery_code("not-a-valid-code", verifiers, PEPPER) is None
    assert hash_recovery_code(codes[0], PEPPER) != hash_recovery_code(codes[0], b"different-pepper-00000000000000000")
    with pytest.raises(ValueError):
        hash_recovery_code(codes[0], b"short")


def test_step_up_expiry_is_fail_closed_for_naive_future_or_old_times():
    now = datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    assert step_up_is_fresh(now - timedelta(minutes=4), now=now)
    assert not step_up_is_fresh(now - timedelta(minutes=6), now=now)
    assert not step_up_is_fresh(now + timedelta(seconds=1), now=now)
    assert not step_up_is_fresh(datetime(2026, 11, 11, 12, 0), now=now)
    assert not step_up_is_fresh(None, now=now)
    assert not step_up_is_fresh(now, now=now, max_age=timedelta(hours=1))
