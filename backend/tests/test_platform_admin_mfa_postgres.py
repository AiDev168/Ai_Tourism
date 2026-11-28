"""Real app-role MFA workflow against an explicitly marked disposable PG17 DB."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import psycopg
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr
from psycopg.rows import dict_row

os.environ.setdefault("DATABASE_PASSWORD", "isolated-mfa-test-only")

from app.api.auth import authenticated_user
from app.api.admin_guards import require_privileged_admin_step_up
from app.core.config import Settings, get_settings
from app.main import app
from app.modules.identity.auth_service import AuthenticatedUser, AuthenticationService
from app.modules.identity.sms import DisabledSmsAdapter
from app.modules.provider_admin.security import totp_code


pytestmark = pytest.mark.skipif(
    os.environ.get("RAHGARD_PLATFORM_MFA_POSTGRES_TESTS") != "1",
    reason="requires explicit guarded disposable PostgreSQL 17 environment",
)


def _identity():
    host = os.environ.get("AUTH_TEST_DATABASE_HOST", "")
    database = os.environ.get("AUTH_TEST_DATABASE_NAME", "")
    user = os.environ.get("AUTH_TEST_DATABASE_USER", "")
    marker = os.environ.get("AUTH_TEST_DATABASE_MARKER", "")
    try:
        address = __import__("ipaddress").ip_address("127.0.0.1" if host == "localhost" else host)
        port = int(os.environ.get("AUTH_TEST_DATABASE_PORT", "0"))
    except ValueError:
        pytest.fail("invalid_disposable_database_address")
    if (not address.is_loopback or port in {0, 55433}
            or not re.fullmatch(r"ai_tourism_auth_test_[a-z0-9][a-z0-9_-]{5,40}", database)
            or user != "ai_tourism_app" or not re.fullmatch(r"[a-fA-F0-9]{32,128}", marker)):
        pytest.fail("disposable_database_guard_rejected")
    app_password = os.environ.get("AUTH_TEST_DATABASE_PASSWORD", "")
    owner_password = os.environ.get("AUTH_TEST_DATABASE_OWNER_PASSWORD", "")
    if not app_password or not owner_password:
        pytest.fail("disposable_database_credentials_missing")
    base = {"host": host, "port": port, "dbname": database, "connect_timeout": 3,
            "row_factory": dict_row}
    with psycopg.connect(**base, user=user, password=app_password) as conn:
        state = conn.execute(
            """SELECT current_database() AS db,current_user AS role,
                      current_setting('server_version_num')::int AS pg,
                      (SELECT count(*) FROM public.ai_tourism_auth_test_marker) AS marker_count,
                      (SELECT min(marker_value) FROM public.ai_tourism_auth_test_marker) AS marker,
                      (SELECT max(migration_id) FROM system.schema_migrations) AS latest"""
        ).fetchone()
    if (state["db"] != database or state["role"] != user or not 170000 <= state["pg"] < 180000
            or state["marker_count"] != 1 or not hmac.compare_digest(state["marker"] or "", marker)
            or state["latest"] not in {
                "0026_platform_reviewer_mfa",
                "0027_server_ai_provider_admin",
                "0028_server_ai_provider_actor_context",
            }):
        pytest.fail("disposable_database_identity_or_migration_guard_rejected")
    return base, app_password, owner_password


def test_real_postgres_totp_recovery_session_binding_and_rls(monkeypatch):
    base, app_password, owner_password = _identity()
    admin_id, operator_id, traveler_id, session_id = (uuid4() for _ in range(4))
    raw_session = secrets.token_urlsafe(32)
    settings = Settings(
        _env_file=None, app_env="staging", auth_enabled=True, auth_cookie_secure=True,
        auth_sms_adapter="disabled", staging_auth_enabled=True,
        staging_public_host="mfa.acceptance.test", auth_allowed_origins="https://mfa.acceptance.test",
        auth_otp_hmac_secret=SecretStr("o" * 32), auth_csrf_secret=SecretStr("c" * 32),
        auth_rate_limit_secret=SecretStr("r" * 32), auth_session_idle_seconds=1800,
        auth_session_absolute_seconds=43200, database_host=base["host"], database_port=base["port"],
        database_name=base["dbname"], database_user="ai_tourism_app", database_password=app_password,
        platform_admin_mfa_encryption_key_hex=SecretStr("a" * 64),
        platform_admin_recovery_pepper=SecretStr("p" * 32),
    )
    user = AuthenticatedUser(admin_id, None, session_id, "staging_invite")
    monkeypatch.setattr("app.api.platform_admin_mfa._ATTEMPT_LIMIT", 10)
    csrf = AuthenticationService(settings, DisabledSmsAdapter()).csrf_token(raw_session)
    now = datetime.now(UTC)
    with psycopg.connect(**base, user="ai_tourism_owner", password=owner_password) as conn, conn.transaction():
        conn.execute(
            """INSERT INTO identity.users(user_id,email,display_name,is_synthetic)
               VALUES (%s,%s,'MFA isolated admin',true),(%s,%s,'MFA isolated operator',true),
                      (%s,%s,'MFA isolated traveler',true)""",
            (admin_id, f"mfa-admin-{admin_id}@example.test", operator_id,
             f"mfa-operator-{operator_id}@example.test", traveler_id,
             f"mfa-traveler-{traveler_id}@example.test"),
        )
        conn.execute(
            """INSERT INTO identity.web_sessions
               (session_id,token_hash,user_id,csrf_hash,created_at,last_seen_at,idle_expires_at,absolute_expires_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (session_id, hashlib.sha256(raw_session.encode()).digest(), admin_id,
             hashlib.sha256(csrf.encode()).digest(), now, now, now + timedelta(minutes=30),
             now + timedelta(hours=12)),
        )
        conn.execute(
            """INSERT INTO partner.platform_grants(user_id,capability,granted_by,reason)
               VALUES (%s,'admin_overview_read',%s,'Isolated MFA acceptance grant.')""",
            (admin_id, operator_id),
        )
        conn.execute(
            """INSERT INTO partner.platform_grant_events
               (grant_domain,target_user_id,capability,action,actor_user_id,reason)
               VALUES ('partner',%s,'admin_overview_read','granted',%s,'Isolated MFA acceptance grant.')""",
            (admin_id, operator_id),
        )

    app.dependency_overrides.clear()
    app.dependency_overrides[authenticated_user] = lambda: user
    app.dependency_overrides[get_settings] = lambda: settings
    headers = {"Origin": "https://mfa.acceptance.test", "X-CSRF-Token": csrf}
    try:
        with TestClient(app, base_url="https://mfa.acceptance.test") as client:
            denied = client.post("/api/v1/admin/mfa/enroll")
            assert denied.status_code == 403
            enrolled = client.post("/api/v1/admin/mfa/enroll", headers=headers)
            assert enrolled.status_code == 200
            assert "no-store" in enrolled.headers["cache-control"]
            secret_text = enrolled.json()["secret"]
            secret = base64.b32decode(secret_text + "=" * (-len(secret_text) % 8))
            verified = client.post("/api/v1/admin/mfa/verify", headers=headers,
                                   json={"code": totp_code(secret)})
            assert verified.status_code == 200
            assert len(verified.json()["recovery_codes"]) == 10
            assert "no-store" in verified.headers["cache-control"]
            require_privileged_admin_step_up(settings, user)
            with psycopg.connect(**base, user="ai_tourism_owner", password=owner_password) as conn, conn.transaction():
                conn.execute("UPDATE identity.web_sessions SET revoked_at=now() WHERE session_id=%s", (session_id,))
            with pytest.raises(HTTPException) as revoked_session:
                require_privileged_admin_step_up(settings, user)
            assert revoked_session.value.status_code == 403
            with psycopg.connect(**base, user="ai_tourism_owner", password=owner_password) as conn, conn.transaction():
                conn.execute("UPDATE identity.web_sessions SET revoked_at=NULL WHERE session_id=%s", (session_id,))

            # A fresh TOTP is accepted once; using it again is replay-blocked.
            future_counter_time = (int(datetime.now(UTC).timestamp()) // 30 + 1) * 30
            next_code = totp_code(secret, future_counter_time)
            stepped = client.post("/api/v1/admin/mfa/step-up", headers=headers,
                                  json={"code": next_code})
            assert stepped.status_code == 200
            replay = client.post("/api/v1/admin/mfa/step-up", headers=headers,
                                 json={"code": next_code})
            assert replay.status_code == 401

            recovery_code = verified.json()["recovery_codes"][0]
            recovered = client.post("/api/v1/admin/mfa/recovery", headers=headers,
                                     json={"code": recovery_code})
            assert recovered.status_code == 200
            reused = client.post("/api/v1/admin/mfa/recovery", headers=headers,
                                 json={"code": recovery_code})
            assert reused.status_code == 401

            # A step-up cannot be transferred to a second session.
            with pytest.raises(HTTPException) as wrong_session:
                require_privileged_admin_step_up(settings, AuthenticatedUser(admin_id, None, uuid4(), "staging_invite"))
            assert wrong_session.value.status_code == 403
            reset = client.post("/api/v1/admin/mfa/reset", headers=headers)
            assert reset.status_code == 200
            with pytest.raises(HTTPException) as after_reset:
                require_privileged_admin_step_up(settings, user)
            assert after_reset.value.status_code == 403

            # The ordinary traveler sees no administrator MFA rows and cannot insert one.
            with psycopg.connect(**base, user="ai_tourism_app", password=app_password) as app_conn, app_conn.transaction():
                app_conn.execute("SELECT set_config('app.actor_id',%s,true)", (str(traveler_id),))
                assert app_conn.execute("SELECT count(*) AS n FROM identity.platform_admin_mfa").fetchone()["n"] == 0
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    app_conn.execute(
                        "INSERT INTO identity.platform_admin_mfa(user_id) VALUES (%s)", (traveler_id,)
                    )

        with psycopg.connect(**base, user="ai_tourism_owner", password=owner_password) as conn:
            audit_count = conn.execute(
                "SELECT count(*) AS n FROM identity.platform_admin_mfa_events WHERE actor_user_id=%s",
                (admin_id,),
            ).fetchone()["n"]
            assert audit_count >= 5
    finally:
        app.dependency_overrides.clear()
        with psycopg.connect(**base, user="ai_tourism_owner", password=owner_password) as conn, conn.transaction():
            conn.execute("DELETE FROM identity.platform_admin_mfa_events WHERE actor_user_id=ANY(%s)",
                         ([admin_id, operator_id, traveler_id],))
            conn.execute("DELETE FROM partner.platform_grant_events WHERE target_user_id=ANY(%s) OR actor_user_id=ANY(%s)",
                         ([admin_id, operator_id, traveler_id], [admin_id, operator_id, traveler_id]))
            conn.execute("DELETE FROM partner.platform_grants WHERE user_id=ANY(%s)", ([admin_id, operator_id, traveler_id],))
            conn.execute("DELETE FROM identity.users WHERE user_id=ANY(%s)", ([admin_id, operator_id, traveler_id],))
