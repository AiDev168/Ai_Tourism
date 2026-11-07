"""Disposable PostgreSQL integration tests. Set AUTH_INTEGRATION_TESTS=1 explicitly."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import os
import re
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import psycopg
from psycopg.rows import dict_row
import pytest
from fastapi import Depends, FastAPI
from uuid import UUID

from app.core.config import Settings
from app.core.config import get_settings
from app.api.auth import router as auth_router
from app.modules.identity.auth_service import AuthenticationService
from app.modules.identity.auth_repository import AuthRepository
from app.modules.identity.authorization import Principal, require_capability_dependency, require_owner_dependency
from app.modules.identity.sms import FakeSmsAdapter, SmsDeliveryError, SmsFailureCategory

pytestmark = pytest.mark.skipif(
    os.environ.get("AUTH_INTEGRATION_TESTS") != "1",
    reason="requires the explicitly selected disposable PostgreSQL integration database",
)


TEST_PHONES = tuple(
    f"+98912{number:07d}" for number in secrets.SystemRandom().sample(range(10_000_000), 5)
)


class FailingSmsAdapter:
    def send(self, message, *, timeout_seconds):
        del message, timeout_seconds
        raise SmsDeliveryError(SmsFailureCategory.PROVIDER_UNAVAILABLE)


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(
            f"PostgreSQL auth integration precondition failed: set {name} for an isolated disposable PostgreSQL 17 database."
        )
    return value


def make_settings() -> Settings:
    host = _required_env("AUTH_TEST_DATABASE_HOST")
    database_name = _required_env("AUTH_TEST_DATABASE_NAME")
    database_user = _required_env("AUTH_TEST_DATABASE_USER")
    password = _required_env("AUTH_TEST_DATABASE_PASSWORD")
    marker = _required_env("AUTH_TEST_DATABASE_MARKER")
    try:
        port = int(_required_env("AUTH_TEST_DATABASE_PORT"))
        address = ipaddress.ip_address("127.0.0.1" if host.lower() == "localhost" else host)
    except ValueError:
        raise RuntimeError(
            "PostgreSQL auth integration precondition failed: host and port must identify a loopback target."
        ) from None
    if not address.is_loopback or not 1 <= port <= 65535 or port == 55433:
        raise RuntimeError(
            "PostgreSQL auth integration precondition failed: target must be loopback and must not use the shared development port."
        )
    if database_name == "ai_tourism_dev" or not re.fullmatch(
        r"ai_tourism_auth_test_[a-z0-9][a-z0-9_-]{5,40}", database_name
    ):
        raise RuntimeError(
            "PostgreSQL auth integration precondition failed: use a unique ai_tourism_auth_test_* database name."
        )
    if database_user != "ai_tourism_app":
        raise RuntimeError(
            "PostgreSQL auth integration precondition failed: use the least-privilege ai_tourism_app role."
        )
    if not re.fullmatch(r"[a-fA-F0-9]{32,128}", marker):
        raise RuntimeError(
            "PostgreSQL auth integration precondition failed: marker must be a private random hexadecimal value."
        )
    try:
        with psycopg.connect(
            host=host, port=port, dbname=database_name, user=database_user,
            password=password, connect_timeout=2, row_factory=dict_row,
        ) as connection:
            identity = connection.execute(
                """SELECT current_database() AS database_name,
                          current_user AS database_user,
                          current_setting('server_version_num')::INTEGER AS version_num,
                          (SELECT COUNT(*) FROM public.ai_tourism_auth_test_marker) AS marker_count,
                          (SELECT MIN(marker_value) FROM public.ai_tourism_auth_test_marker) AS marker_value"""
            ).fetchone()
    except Exception:
        raise RuntimeError(
            "PostgreSQL auth integration precondition failed: target is unreachable or lacks the disposable marker table."
        ) from None
    if (
        identity["database_name"] != database_name
        or identity["database_user"] != "ai_tourism_app"
        or not 170000 <= identity["version_num"] < 180000
        or identity["marker_count"] != 1
        or not hmac.compare_digest(identity["marker_value"] or "", marker)
    ):
        raise RuntimeError(
            "PostgreSQL auth integration precondition failed: database identity, PostgreSQL 17 version, role, or disposable marker did not match."
        )
    return Settings(
        _env_file=None,
        app_env="test",
        database_host=host,
        database_port=port,
        database_name=database_name,
        database_user=database_user,
        database_password=password,
        auth_enabled=True,
        auth_sms_adapter="fake",
        auth_otp_hmac_secret="integration-otp-key-only-test-000000000001",
        auth_csrf_secret="integration-csrf-key-only-test-000000000001",
        auth_rate_limit_secret="integration-rate-key-only-test-000000000001",
        auth_session_idle_seconds=1800,
        auth_session_absolute_seconds=43200,
        auth_allowed_origins="https://testserver",
        auth_rate_window_seconds=600,
        auth_phone_issue_limit=20,
        auth_ip_issue_limit=100,
        auth_global_issue_limit=1000,
        auth_phone_verify_limit=100,
        auth_ip_verify_limit=100,
    )


def connect(settings: Settings):
    return psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password.get_secret_value(),
        row_factory=dict_row,
    )


def _clean_test_auth_records(settings: Settings) -> None:
    with connect(settings) as connection, connection.transaction():
        connection.execute(
            """DELETE FROM identity.web_sessions
               WHERE user_id IN (SELECT user_id FROM identity.users WHERE phone_e164 = ANY(%s))""",
            (list(TEST_PHONES),),
        )
        connection.execute(
            "DELETE FROM identity.verified_phones WHERE phone_e164 = ANY(%s)", (list(TEST_PHONES),)
        )
        connection.execute(
            "DELETE FROM identity.otp_challenges WHERE phone_e164 = ANY(%s)", (list(TEST_PHONES),)
        )
        # Rate-limit subjects are keyed digests; this isolated database belongs
        # exclusively to these tests, so their complete ledger can be cleared.
        connection.execute("DELETE FROM identity.auth_rate_limits")
        connection.execute(
            "DELETE FROM identity.users WHERE phone_e164 = ANY(%s) AND is_synthetic=FALSE",
            (list(TEST_PHONES),),
        )


@pytest.fixture(autouse=True)
def disposable_auth_database_cleanup():
    settings = make_settings()
    _clean_test_auth_records(settings)
    yield
    _clean_test_auth_records(settings)


def test_postgres_otp_session_atomicity_and_revocation():
    settings = make_settings()
    sms = FakeSmsAdapter()
    repository = AuthRepository(settings)
    service = AuthenticationService(settings, sms, repository)

    # One successful OTP establishes verification evidence and a hashed-only session.
    issued = service.issue(TEST_PHONES[0], "integration-ip-a", "en-US")
    assert issued.challenge_id is not None
    code = re.search(r"[0-9]{6}", sms.take_messages()[0].body).group()
    verified = service.verify(issued.challenge_id, code, "integration-ip-a")
    assert verified is not None
    user, raw_session, _csrf = verified
    assert service.authenticate(raw_session) is not None

    with connect(settings) as conn:
        challenge = conn.execute(
            "SELECT verifier_hmac, phone_e164, consumed_at FROM identity.otp_challenges WHERE challenge_id=%s",
            (issued.challenge_id,),
        ).fetchone()
        stored_session = conn.execute(
            "SELECT token_hash, csrf_hash FROM identity.web_sessions WHERE user_id=%s AND token_hash=%s",
            (user.user_id, hashlib.sha256(raw_session.encode()).digest()),
        ).fetchone()
        evidence = conn.execute(
            "SELECT phone_e164, user_id FROM identity.verified_phones WHERE user_id=%s",
            (user.user_id,),
        ).fetchone()
        assert challenge["consumed_at"] is not None
        assert code not in bytes(challenge["verifier_hmac"]).hex()
        assert stored_session["token_hash"] == hashlib.sha256(raw_session.encode()).digest()
        assert raw_session.encode() not in bytes(stored_session["token_hash"])
        assert evidence["phone_e164"] == TEST_PHONES[0]
        assert evidence["user_id"] == user.user_id

    # A challenge can be consumed only once even under concurrent valid requests.
    concurrent = service.issue(TEST_PHONES[1], "integration-ip-b", "fa-IR")
    concurrent_code = re.search(r"[0-9]{6}", sms.take_messages()[0].body).group()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda _: service.verify(concurrent.challenge_id, concurrent_code, "integration-ip-b"),
            range(2),
        ))
    assert sum(result is not None for result in results) == 1

    # Server-side expiration and account disablement invalidate sessions; the DB trigger revokes.
    with connect(settings) as conn:
        conn.execute(
            "UPDATE identity.web_sessions SET idle_expires_at=%s WHERE user_id=%s",
            (datetime.now(UTC) - timedelta(seconds=1), user.user_id),
        )
    assert service.authenticate(raw_session) is None
    with connect(settings) as conn:
        conn.execute("UPDATE identity.users SET account_status='disabled' WHERE user_id=%s", (user.user_id,))
        revoked = conn.execute(
            "SELECT revoked_at, revoked_reason FROM identity.web_sessions WHERE user_id=%s",
            (user.user_id,),
        ).fetchone()
        assert revoked["revoked_at"] is not None
        assert revoked["revoked_reason"] == "account_disabled"

    # Invalid codes consume a bounded attempt and cannot create identity evidence.
    invalid = service.issue(TEST_PHONES[2], "integration-ip-c", "ar")
    assert invalid.challenge_id is not None
    valid_code = re.search(r"[0-9]{6}", sms.take_messages()[0].body).group()
    invalid_code = "000000" if valid_code != "000000" else "000001"
    for _ in range(settings.auth_otp_max_attempts):
        assert service.verify(invalid.challenge_id, invalid_code, "integration-ip-c") is None
    with connect(settings) as conn:
        failed = conn.execute(
            "SELECT failed_attempts, locked_at FROM identity.otp_challenges WHERE challenge_id=%s",
            (invalid.challenge_id,),
        ).fetchone()
        evidence_count = conn.execute(
            "SELECT COUNT(*) FROM identity.verified_phones WHERE phone_e164=%s",
            (TEST_PHONES[2],),
        ).fetchone()["count"]
        assert failed["failed_attempts"] == settings.auth_otp_max_attempts
        assert failed["locked_at"] is not None
        assert evidence_count == 0


def test_failed_sms_delivery_cannot_be_verified_or_create_identity_evidence():
    settings = make_settings()
    repository = AuthRepository(settings)
    service = AuthenticationService(settings, FailingSmsAdapter(), repository)

    result = service.issue(TEST_PHONES[4], "integration-ip-delivery-failure", "en-US")
    assert result.accepted is False
    assert result.challenge_id is None

    with connect(settings) as conn:
        challenge = conn.execute(
            """SELECT challenge_id, delivery_status FROM identity.otp_challenges
               WHERE phone_e164=%s ORDER BY created_at DESC LIMIT 1""",
            (TEST_PHONES[4],),
        ).fetchone()
        assert challenge is not None
        assert challenge["delivery_status"] == "failed"
        challenge_id = challenge["challenge_id"]

    assert service.verify(challenge_id, "123456", "integration-ip-delivery-failure") is None
    with connect(settings) as conn:
        assert conn.execute(
            "SELECT COUNT(*) FROM identity.users WHERE phone_e164=%s", (TEST_PHONES[4],)
        ).fetchone()["count"] == 0
        assert conn.execute(
            "SELECT COUNT(*) FROM identity.verified_phones WHERE phone_e164=%s", (TEST_PHONES[4],)
        ).fetchone()["count"] == 0
        assert conn.execute(
            """SELECT COUNT(*) FROM identity.web_sessions s
               JOIN identity.users u ON u.user_id=s.user_id WHERE u.phone_e164=%s""",
            (TEST_PHONES[4],),
        ).fetchone()["count"] == 0


def test_actual_fastapi_flow_uses_app_role_and_secure_cookie():
    from fastapi.testclient import TestClient

    settings = make_settings()
    sms = FakeSmsAdapter()
    api = FastAPI()
    api.state.sms_adapter = sms
    api.include_router(auth_router)
    api.dependency_overrides[get_settings] = lambda: settings

    @api.get("/test/resources/{owner_id}")
    def read_resource(
        owner_id: UUID,
        principal: Principal = Depends(require_owner_dependency()),
    ):
        return {"user_id": str(principal.user_id), "owner_id": str(owner_id)}

    @api.get(
        "/test/provider-admin",
        dependencies=[Depends(require_capability_dependency("ai_provider:admin"))],
    )
    def privileged_resource():
        return {"ok": True}

    try:
        with TestClient(api, base_url="https://testserver") as client:
            requested = client.post(
                "/api/v1/auth/otp/challenges",
                json={"phone_number": "0" + TEST_PHONES[3][3:], "locale": "ar"},
            )
            assert requested.status_code == 202
            code = re.search(r"[0-9]{6}", sms.take_messages()[0].body).group()
            verified = client.post(
                "/api/v1/auth/otp/verify",
                json={"challenge_id": requested.json()["challenge_id"], "code": code},
            )
            assert verified.status_code == 200
            cookie = verified.headers["set-cookie"].lower()
            assert "__host-rahgard_session=" in cookie
            assert "secure" in cookie and "httponly" in cookie and "samesite=lax" in cookie
            assert "domain=" not in cookie
            assert code not in verified.text
            current = client.get("/api/v1/auth/me")
            assert current.status_code == 200
            csrf = current.json()["csrf_token"]
            authenticated_id = current.json()["user"]["user_id"]
            own = client.get(
                f"/test/resources/{authenticated_id}",
                params={"user_id": str(UUID(int=0)), "organization_id": str(UUID(int=1)), "is_admin": "true"},
            )
            assert own.status_code == 200 and own.json()["user_id"] == authenticated_id
            impersonation = client.get(
                f"/test/resources/{UUID(int=2)}", params={"user_id": authenticated_id}
            )
            assert impersonation.status_code == 403
            forged_capability = client.get(
                "/test/provider-admin",
                params={"capability": "ai_provider:admin", "role": "admin", "is_admin": "true"},
            )
            assert forged_capability.status_code == 403
            assert client.post(
                "/api/v1/auth/logout",
                headers={"Origin": "https://testserver", "X-CSRF-Token": csrf},
            ).status_code == 204
            assert client.get("/api/v1/auth/me").status_code == 401
    finally:
        api.dependency_overrides.clear()
