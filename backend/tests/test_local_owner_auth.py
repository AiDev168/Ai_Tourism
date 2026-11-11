from __future__ import annotations

from uuid import uuid4

import pytest

from app.modules.auth.local_owner import (
    LocalOwnerCredentialError,
    LocalOwnerLoginGuard,
    create_credential,
    parse_credential,
    verify_and_issue,
)
from app.modules.auth.local_owner import credentials as local_auth


PEER = "127.0.0.1"
HOST = "localhost:8443"
ORIGIN = "https://localhost:8443"
PASSWORD = "correct horse battery staple 2026"


def login(credential, password=PASSWORD, **kwargs):
    return verify_and_issue(
        credential, password,
        limiter=kwargs.pop("limiter", LocalOwnerLoginGuard()),
        request_peer=kwargs.pop("request_peer", PEER),
        host=kwargs.pop("host", HOST),
        origin=kwargs.pop("origin", ORIGIN),
        allowed_origin=kwargs.pop("allowed_origin", ORIGIN),
        session_issuer=kwargs.pop("session_issuer", lambda owner_id: (owner_id, "session-issued")),
        forwarded_for=kwargs.pop("forwarded_for", None),
    )


def test_bootstrap_stores_only_pbkdf2_verifier_and_parses_round_trip():
    owner_id = uuid4()
    credential = create_credential(owner_id, PASSWORD)
    record = credential.as_record()
    assert record["owner_id"] == str(owner_id)
    assert record["algorithm"] == "pbkdf2-sha256"
    assert record["iterations"] == 600_000
    assert "password" not in record
    assert PASSWORD not in repr(record)
    assert parse_credential(record) == credential
    assert login(credential) == (owner_id, "session-issued")


def test_long_persian_password_round_trips_without_utf8_byte_truncation():
    # 145 Persian letters occupy more than 256 UTF-8 bytes while remaining
    # within the documented 256-character input limit.
    password = "متنپسوردفارسیطولانیبرایآزمایش" * 5
    assert len(password) == 145
    assert len(password.encode("utf-8")) > 256
    credential = create_credential(uuid4(), password)

    assert login(credential, password) is not None
    assert login(credential, password[:-1] + "ی") is None


@pytest.mark.parametrize("password", ["short", " leading and trailing ", "\x00" + "a" * 20, "x" * 30, "x" * 257])
def test_bootstrap_rejects_weak_or_unsafe_passwords(password):
    with pytest.raises(LocalOwnerCredentialError):
        create_credential(uuid4(), password)


@pytest.mark.parametrize("record", [
    {},
    {"version": True, "algorithm": "pbkdf2-sha256", "owner_id": str(uuid4()),
     "iterations": 600_000, "salt_b64": "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE",
     "verifier_b64": "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE"},
    '{"owner_id":"a","owner_id":"b"}',
])
def test_credential_parser_fails_closed(record):
    with pytest.raises(LocalOwnerCredentialError):
        parse_credential(record)


@pytest.mark.parametrize("context", [
    {"request_peer": "192.168.1.20"},
    {"request_peer": "::ffff:192.168.1.1"},
    {"origin": "http://localhost:8443"},
    {"origin": "https://evil.example", "allowed_origin": "https://localhost:8443"},
    {"host": "127.0.0.1:8443"},
    {"host": "localhost:8444"},
    {"forwarded_for": "127.0.0.1"},
    {"host": "user@localhost:8443"},
])
def test_login_rejects_nonlocal_or_misrouted_request_before_session(context):
    credential = create_credential(uuid4(), PASSWORD)
    issued = []
    assert login(credential, session_issuer=lambda owner: issued.append(owner), **context) is None
    assert issued == []


def test_wrong_password_never_calls_session_issuer():
    credential = create_credential(uuid4(), PASSWORD)
    issued = []
    assert login(credential, "incorrect password value", session_issuer=lambda owner: issued.append(owner)) is None
    assert issued == []


def test_absent_credential_performs_dummy_kdf_and_never_issues_session(monkeypatch):
    calls = []
    original = local_auth.hashlib.pbkdf2_hmac

    def counted(*args, **kwargs):
        calls.append(args)
        return original(*args, **kwargs)

    monkeypatch.setattr(local_auth.hashlib, "pbkdf2_hmac", counted)
    assert login(None) is None
    assert len(calls) == 1
    assert calls[0][3] == 600_000


def test_lockout_is_bounded_and_expires(monkeypatch):
    now = [0.0]
    limiter = LocalOwnerLoginGuard(max_attempts=2, window_seconds=60, maximum_keys=8,
                                   clock=lambda: now[0])
    credential = create_credential(uuid4(), PASSWORD)
    assert login(credential, "wrong password", limiter=limiter) is None
    assert login(credential, "wrong password", limiter=limiter) is None
    calls = []
    assert login(credential, limiter=limiter,
                 session_issuer=lambda owner: calls.append(owner)) is None
    assert calls == []
    now[0] = 61.0
    assert login(credential, limiter=limiter) is not None


def test_limiter_refuses_unbounded_key_growth():
    limiter = LocalOwnerLoginGuard(maximum_keys=8)
    for index in range(8):
        assert limiter.allowed(f"key-{index}")
        limiter.failed(f"key-{index}")
    assert not limiter.allowed("ninth-key")


def test_session_issuer_receives_only_persisted_owner_identity():
    owner_id = uuid4()
    credential = create_credential(owner_id, PASSWORD)
    issued = []
    result = login(credential, session_issuer=lambda user_id: issued.append(user_id) or "opaque-session")
    assert result == "opaque-session"
    assert issued == [owner_id]
