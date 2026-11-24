"""Guarded FastAPI process for the Playwright traveler E2E harness.

The only OTP bridge is stdin/stdout between test processes. No HTTP OTP or
debug endpoint is registered. Run with cwd=backend so the repository-root
.env is not a Settings source.
"""

from __future__ import annotations

import ipaddress
import hashlib
import json
import os
import re
import socketserver
import sys
from secrets import token_hex
import threading
import time
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(BACKEND_ROOT))
_SAFE_PHASE = "startup"


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"E2E precondition failed: required test variable {name} is missing")
    return value


def _verify_disposable_database() -> dict[str, Any]:
    if os.environ.get("AUTH_INTEGRATION_TESTS") != "1":
        raise RuntimeError("E2E precondition failed: AUTH_INTEGRATION_TESTS=1 is required")
    host = _required("AUTH_TEST_DATABASE_HOST")
    database = _required("AUTH_TEST_DATABASE_NAME")
    user = _required("AUTH_TEST_DATABASE_USER")
    password = _required("AUTH_TEST_DATABASE_PASSWORD")
    marker = _required("AUTH_TEST_DATABASE_MARKER")
    try:
        address = ipaddress.ip_address("127.0.0.1" if host.lower() == "localhost" else host)
        port = int(_required("AUTH_TEST_DATABASE_PORT"))
    except ValueError:
        raise RuntimeError("E2E precondition failed: database host or port is invalid") from None
    if (
        not address.is_loopback
        or not 1 <= port <= 65535
        or port == 55433
        or database == "ai_tourism_dev"
        or not re.fullmatch(r"ai_tourism_auth_test_[a-z0-9][a-z0-9_-]{5,40}", database)
        or user != "ai_tourism_app"
        or not re.fullmatch(r"[a-fA-F0-9]{32,128}", marker)
    ):
        raise RuntimeError("E2E precondition failed: target does not meet disposable PG17 naming/role/loopback rules")
    try:
        with psycopg.connect(
            host=host, port=port, dbname=database, user=user, password=password,
            connect_timeout=2, row_factory=dict_row,
        ) as connection:
            identity = connection.execute(
                """SELECT current_database() AS database_name,
                          current_user AS database_user,
                          current_setting('server_version_num')::INTEGER AS version_num,
                          (SELECT COUNT(*) FROM public.ai_tourism_auth_test_marker) AS marker_count,
                          (SELECT MIN(marker_value) FROM public.ai_tourism_auth_test_marker) AS marker_value"""
            ).fetchone()
    except Exception:
        raise RuntimeError("E2E precondition failed: isolated marker database could not be verified") from None
    if (
        identity["database_name"] != database
        or identity["database_user"] != user
        or not 170000 <= identity["version_num"] < 180000
        or identity["marker_count"] != 1
        or not __import__("hmac").compare_digest(identity["marker_value"] or "", marker)
    ):
        raise RuntimeError("E2E precondition failed: identity, PG major, least-privilege role, or marker mismatch")
    return {"host": host, "port": port, "dbname": database, "user": user, "password": password}


def _grant_catalogue_capabilities(database: dict[str, Any], user_id: str, capabilities: list[str], granted_by: str) -> bool:
    """Test-control-only grants on the marked national-catalogue disposable DB."""
    if os.environ.get("RAHGARD_NATIONAL_CATALOGUE_E2E") != "1":
        return False
    if (not re.fullmatch(r"[0-9a-fA-F-]{36}", user_id)
            or not re.fullmatch(r"[0-9a-fA-F-]{36}", granted_by)
            or user_id == granted_by or not capabilities or len(capabilities) > 3):
        return False
    allowed = {"candidate_review", "source_review", "catalogue_publish"}
    if any(value not in allowed for value in capabilities) or len(set(capabilities)) != len(capabilities):
        return False
    owner_password = os.environ.get("AUTH_TEST_DATABASE_OWNER_PASSWORD", "")
    if not owner_password:
        return False
    try:
        with psycopg.connect(
            **{**database, "user": "ai_tourism_owner", "password": owner_password},
            connect_timeout=2,
            row_factory=dict_row,
        ) as connection, connection.transaction():
            row = connection.execute(
                """SELECT current_database() AS db,
                          (SELECT count(*) FROM public.ai_tourism_auth_test_marker) AS marker_count,
                          (SELECT min(marker_value) FROM public.ai_tourism_auth_test_marker) AS marker"""
            ).fetchone()
            if row["db"] != database["dbname"] or row["marker_count"] != 1 or not __import__("hmac").compare_digest(
                row["marker"] or "", os.environ.get("AUTH_TEST_DATABASE_MARKER", "")
            ):
                return False
            exists = connection.execute("SELECT count(*)=2 AS ok FROM identity.users WHERE user_id IN (%s,%s)",
                                        (user_id, granted_by)).fetchone()["ok"]
            if not exists:
                return False
            for capability in capabilities:
                connection.execute(
                    """INSERT INTO identity.catalogue_review_grants(user_id,capability,granted_by,reason)
                       VALUES (%s,%s,%s,'Isolated national catalogue browser acceptance only')""",
                    (user_id, capability, granted_by),
                )
                connection.execute(
                    """INSERT INTO partner.platform_grant_events
                       (grant_domain,target_user_id,capability,action,actor_user_id,reason)
                       VALUES ('catalogue',%s,%s,'granted',%s,
                               'Isolated national catalogue browser acceptance only')""",
                    (user_id, capability, granted_by),
                )
        return True
    except Exception:
        return False


def _approve_isolated_test_organization(
    database: dict[str, Any], organization_id: str, created_by: str, display_name: str,
) -> tuple[bool, str]:
    """Mark only the browser-created acceptance organization eligible in disposable PG."""
    provider_test = os.environ.get("RAHGARD_REAL_CHAT_PROVIDER", "").strip().lower() in {
        "lm_studio", "remote_vllm",
    }
    national_test = os.environ.get("RAHGARD_NATIONAL_CATALOGUE_E2E") == "1"
    if not (provider_test or national_test):
        return False, "test_mode_disabled"
    allowed_name = (
        (national_test and display_name == "Acceptance Travel Co")
        or (provider_test and bool(re.fullmatch(r"V2 acceptance Company [0-9]{4}", display_name)))
    )
    if not allowed_name:
        return False, "test_name_not_allowed"
    if not all(re.fullmatch(r"[0-9a-fA-F-]{36}", value) for value in (organization_id, created_by)):
        return False, "invalid_test_identity"
    owner_password = os.environ.get("AUTH_TEST_DATABASE_OWNER_PASSWORD", "")
    marker = os.environ.get("AUTH_TEST_DATABASE_MARKER", "")
    if not owner_password or not marker:
        return False, "isolated_db_guard_missing"
    try:
        with psycopg.connect(
            **{**database, "user": "ai_tourism_owner", "password": owner_password},
            connect_timeout=2, row_factory=dict_row,
        ) as connection, connection.transaction():
            identity = connection.execute(
                """SELECT current_database() AS db,
                          (SELECT count(*) FROM public.ai_tourism_auth_test_marker) AS marker_count,
                          (SELECT min(marker_value) FROM public.ai_tourism_auth_test_marker) AS marker"""
            ).fetchone()
            if (identity["db"] != database["dbname"] or identity["marker_count"] != 1
                    or not __import__("hmac").compare_digest(identity["marker"] or "", marker)):
                return False, "isolated_db_marker_mismatch"
            row = connection.execute(
                """UPDATE partner.organizations
                   SET verification_status='verified',participation_status='active',
                       application_status='approved',updated_at=now()
                   WHERE organization_id=%s AND created_by=%s
                     AND display_name=%s
                     AND verification_status='pending' AND participation_status='inactive'
                     AND application_status='draft'
                   RETURNING organization_id""",
                (organization_id, created_by, display_name),
            ).fetchone()
            return (True, "approved") if row is not None else (False, "organization_state_mismatch")
    except Exception:
        return False, "isolated_db_update_failed"


def _national_catalogue_counts(database: dict[str, Any]) -> dict[str, int] | None:
    if os.environ.get("RAHGARD_NATIONAL_CATALOGUE_E2E") != "1":
        return None
    try:
        owner_password = os.environ.get("AUTH_TEST_DATABASE_OWNER_PASSWORD", "")
        marker = os.environ.get("AUTH_TEST_DATABASE_MARKER", "")
        if not owner_password or not marker:
            return None
        with psycopg.connect(
            **{**database, "user": "ai_tourism_owner", "password": owner_password},
            connect_timeout=2,
            row_factory=dict_row,
        ) as connection:
            identity = connection.execute(
                """SELECT current_database() AS db,
                          (SELECT count(*) FROM public.ai_tourism_auth_test_marker) AS marker_count,
                          (SELECT min(marker_value) FROM public.ai_tourism_auth_test_marker) AS marker"""
            ).fetchone()
            if (
                identity["db"] != database["dbname"]
                or identity["marker_count"] != 1
                or not __import__("hmac").compare_digest(identity["marker"] or "", marker)
            ):
                return None
            row = connection.execute(
                """SELECT
                     (SELECT count(*) FROM knowledge.destination_candidates) AS candidates,
                     (SELECT count(*) FROM knowledge.destination_candidates WHERE candidate_kind='destination_identity') AS identities,
                     (SELECT count(*) FROM knowledge.destination_candidates WHERE candidate_kind='discovery_lead') AS leads,
                     (SELECT count(*) FROM knowledge.destination_candidates WHERE candidate_kind='discovery_lead' AND candidate_status='needs_review') AS unpublished_leads,
                     (SELECT count(*) FROM knowledge.source_candidates) AS source_candidates,
                     (SELECT count(*) FROM operations.dataset_import_batches) AS import_batches,
                     (SELECT count(*) FROM knowledge.knowledge_sources WHERE verification_status='verified' AND NOT is_synthetic) AS verified_sources,
                     (SELECT count(*) FROM knowledge.production_destinations) AS published_destinations,
                     (SELECT count(*) FROM partner.organizations) AS organizations,
                     (SELECT count(*) FROM partner.services) AS services,
                     (SELECT count(*) FROM partner.schedules) AS schedules,
                     (SELECT count(*) FROM partner.offers) AS offers,
                     (SELECT count(*) FROM partner.prices) AS prices,
                     (SELECT count(*) FROM partner.availability_snapshots) AS availability,
                     (SELECT count(*) FROM travel.itineraries) AS itineraries"""
            ).fetchone()
        return {key: int(value) for key, value in row.items()}
    except Exception:
        return None


def _grant_isolated_partner_reviewer(database: dict[str, Any], user_id: str, actor_id: str) -> dict[str, Any]:
    """Provision only the reviewer used by this disposable browser acceptance."""
    if os.environ.get("RAHGARD_NATIONAL_CATALOGUE_E2E") != "1":
        return {"ok": False, "reason": "acceptance_mode_disabled"}
    if (not re.fullmatch(r"[0-9a-fA-F-]{36}", user_id)
            or not re.fullmatch(r"[0-9a-fA-F-]{36}", actor_id)
            or user_id == actor_id):
        return {"ok": False, "reason": "invalid_test_identity"}
    owner_password = os.environ.get("AUTH_TEST_DATABASE_OWNER_PASSWORD", "")
    marker = os.environ.get("AUTH_TEST_DATABASE_MARKER", "")
    if not owner_password or not marker:
        return {"ok": False, "reason": "isolated_owner_guard_unavailable"}
    try:
        with psycopg.connect(
            **{**database, "user": "ai_tourism_owner", "password": owner_password},
            connect_timeout=2, row_factory=dict_row,
        ) as connection, connection.transaction():
            identity = connection.execute(
                """SELECT current_database() AS db,
                          (SELECT count(*) FROM public.ai_tourism_auth_test_marker) AS marker_count,
                          (SELECT min(marker_value) FROM public.ai_tourism_auth_test_marker) AS marker"""
            ).fetchone()
            if (identity["db"] != database["dbname"] or identity["marker_count"] != 1
                    or not __import__("hmac").compare_digest(identity["marker"] or "", marker)):
                return {"ok": False, "reason": "database_marker_mismatch"}
            if not connection.execute(
                "SELECT count(*)=2 AS ok FROM identity.users WHERE user_id IN (%s,%s)", (user_id, actor_id),
            ).fetchone()["ok"]:
                return {"ok": False, "reason": "test_user_not_found"}
            connection.execute(
                """INSERT INTO partner.platform_grants(user_id,capability,granted_by,reason)
                   VALUES (%s,'organization_review',%s,
                           'Disposable partner workspace browser acceptance only')""",
                (user_id, actor_id),
            )
            connection.execute(
                """INSERT INTO partner.platform_grant_events
                   (grant_domain,target_user_id,capability,action,actor_user_id,reason)
                   VALUES ('partner',%s,'organization_review','granted',%s,
                           'Disposable partner workspace browser acceptance only')""",
                (user_id, actor_id),
            )
        return {"ok": True}
    except psycopg.Error as exc:
        return {"ok": False, "sqlstate": exc.sqlstate or "unknown_sqlstate",
                "error_class": type(exc).__name__}
    except Exception as exc:
        return {"ok": False, "error_class": type(exc).__name__}


def _grant_isolated_admin_overview(database: dict[str, Any], user_id: str, actor_id: str) -> dict[str, Any]:
    """Seed the aggregate-only owner overview grant in marked disposable PG17."""
    if os.environ.get("RAHGARD_NATIONAL_CATALOGUE_E2E") != "1":
        return {"ok": False, "reason": "acceptance_mode_disabled"}
    if (not re.fullmatch(r"[0-9a-fA-F-]{36}", user_id)
            or not re.fullmatch(r"[0-9a-fA-F-]{36}", actor_id)
            or user_id == actor_id):
        return {"ok": False, "reason": "invalid_or_self_grant_identity"}
    owner_password = os.environ.get("AUTH_TEST_DATABASE_OWNER_PASSWORD", "")
    marker = os.environ.get("AUTH_TEST_DATABASE_MARKER", "")
    if not owner_password or not marker:
        return {"ok": False, "reason": "isolated_owner_guard_unavailable"}
    try:
        with psycopg.connect(
            **{**database, "user": "ai_tourism_owner", "password": owner_password},
            connect_timeout=2, row_factory=dict_row,
        ) as connection, connection.transaction():
            identity = connection.execute(
                """SELECT current_database() AS db,
                          current_setting('server_version_num')::integer AS version_num,
                          COALESCE(inet_server_port(),0) AS port,
                          (SELECT count(*) FROM public.ai_tourism_auth_test_marker) AS marker_count,
                          (SELECT min(marker_value) FROM public.ai_tourism_auth_test_marker) AS marker,
                          (SELECT sha256 FROM system.schema_migrations WHERE migration_id='0025_owner_control_center') AS migration_hash"""
            ).fetchone()
            expected_hash = hashlib.sha256(
                (Path(__file__).resolve().parents[2] / "engineering/pilot/sql/025_owner_control_center.sql").read_bytes()
            ).hexdigest()
            if (identity["db"] != database["dbname"]
                    or not 170000 <= identity["version_num"] < 180000
                    or identity["port"] == 55433
                    or identity["marker_count"] != 1
                    or not __import__("hmac").compare_digest(identity["marker"] or "", marker)
                    or (identity["migration_hash"] or "").strip() != expected_hash):
                return {"ok": False, "reason": "disposable_database_or_migration_guard_failed"}
            if not connection.execute(
                "SELECT count(*)=2 AS ok FROM identity.users WHERE user_id IN (%s,%s)",
                (user_id, actor_id),
            ).fetchone()["ok"]:
                return {"ok": False, "reason": "test_identities_not_found"}
            connection.execute(
                """INSERT INTO partner.platform_grants(user_id,capability,granted_by,reason)
                   VALUES (%s,'admin_overview_read',%s,
                           'Disposable owner control-center browser acceptance only')""",
                (user_id, actor_id),
            )
            connection.execute(
                """INSERT INTO partner.platform_grant_events
                   (grant_domain,target_user_id,capability,action,actor_user_id,reason)
                   VALUES ('partner',%s,'admin_overview_read','granted',%s,
                           'Disposable owner control-center browser acceptance only')""",
                (user_id, actor_id),
            )
        return {"ok": True}
    except psycopg.Error as exc:
        return {"ok": False, "sqlstate": exc.sqlstate or "unknown_sqlstate"}
    except Exception as exc:
        return {"ok": False, "error_class": type(exc).__name__}


def _isolated_partner_counts(database: dict[str, Any]) -> dict[str, int] | None:
    """Return aggregate QA counts only; refuse to query outside marked disposable PG."""
    if os.environ.get("RAHGARD_NATIONAL_CATALOGUE_E2E") != "1":
        return None
    owner_password = os.environ.get("AUTH_TEST_DATABASE_OWNER_PASSWORD", "")
    marker = os.environ.get("AUTH_TEST_DATABASE_MARKER", "")
    if not owner_password or not marker:
        return None
    try:
        with psycopg.connect(
            **{**database, "user": "ai_tourism_owner", "password": owner_password},
            connect_timeout=2, row_factory=dict_row,
        ) as connection:
            identity = connection.execute(
                """SELECT current_database() AS db,
                          (SELECT count(*) FROM public.ai_tourism_auth_test_marker) AS marker_count,
                          (SELECT min(marker_value) FROM public.ai_tourism_auth_test_marker) AS marker"""
            ).fetchone()
            if (identity["db"] != database["dbname"] or identity["marker_count"] != 1
                    or not __import__("hmac").compare_digest(identity["marker"] or "", marker)):
                return None
            row = connection.execute(
                """SELECT
                     (SELECT count(*) FROM partner.organizations) organizations,
                     (SELECT count(*) FROM partner.share_eligible_organizations) eligible_organizations,
                     (SELECT count(*) FROM partner.verification_cases) verification_cases,
                     (SELECT count(*) FROM partner.review_events) review_events,
                     (SELECT count(*) FROM partner.services) services,
                     (SELECT count(*) FROM partner.schedules) schedules,
                     (SELECT count(*) FROM partner.offers) offers,
                     (SELECT count(*) FROM partner.prices) prices,
                     (SELECT count(*) FROM partner.availability_snapshots) availability"""
            ).fetchone()
        return {key: int(value) for key, value in row.items()}
    except Exception:
        return None


def _account_state(database: dict[str, Any], user_id: str, phone: str) -> dict[str, Any]:
    with psycopg.connect(**database, connect_timeout=2, row_factory=dict_row) as connection:
        row = connection.execute(
            """SELECT
                (SELECT COUNT(*) FROM identity.users WHERE user_id=%s) AS users,
                (SELECT COUNT(*) FROM identity.web_sessions WHERE user_id=%s) AS sessions,
                (SELECT COUNT(*) FROM travel.trips WHERE user_id=%s) AS trips,
                (SELECT COUNT(*) FROM conversation.conversations WHERE user_id=%s) AS conversations,
                (SELECT COUNT(*) FROM conversation.messages m JOIN conversation.conversations c USING (conversation_id) WHERE c.user_id=%s) AS messages,
                (SELECT COUNT(*) FROM identity.otp_challenges WHERE phone_e164=%s) AS otp_challenges,
                (SELECT COUNT(*) FROM identity.verified_phones WHERE phone_e164=%s) AS verified_phones""",
            (user_id, user_id, user_id, user_id, user_id, phone, phone),
        ).fetchone()
    return {key: int(value) for key, value in row.items()}


def _cleanup_phones(database: dict[str, Any], phones: list[str]) -> None:
    if len(phones) != 2 or any(not re.fullmatch(r"\+989[0-9]{9}", phone) for phone in phones):
        raise RuntimeError("E2E cleanup refused: test phone set is malformed")
    with psycopg.connect(**database, connect_timeout=2, row_factory=dict_row) as connection:
        with connection.transaction():
            connection.execute(
                "DELETE FROM identity.web_sessions WHERE user_id IN (SELECT user_id FROM identity.users WHERE phone_e164=ANY(%s))",
                (phones,),
            )
            connection.execute("DELETE FROM identity.verified_phones WHERE phone_e164=ANY(%s)", (phones,))
            connection.execute("DELETE FROM identity.otp_challenges WHERE phone_e164=ANY(%s)", (phones,))
            connection.execute("DELETE FROM identity.users WHERE phone_e164=ANY(%s) AND is_synthetic=FALSE", (phones,))


def _phones_unused(database: dict[str, Any], phones: list[str]) -> bool:
    if len(phones) != 2 or any(not re.fullmatch(r"\+989[0-9]{9}", phone) for phone in phones):
        return False
    with psycopg.connect(**database, connect_timeout=2, row_factory=dict_row) as connection:
        row = connection.execute(
            """SELECT
                (SELECT COUNT(*) FROM identity.users WHERE phone_e164=ANY(%s)) +
                (SELECT COUNT(*) FROM identity.verified_phones WHERE phone_e164=ANY(%s)) +
                (SELECT COUNT(*) FROM identity.otp_challenges WHERE phone_e164=ANY(%s)) AS matches""",
            (phones, phones, phones),
        ).fetchone()
    return row["matches"] == 0


class _ControlHandler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        line = self.rfile.readline(16_384)
        try:
            command = json.loads(line)
            token = str(command.pop("token", ""))
            if not __import__("hmac").compare_digest(token, self.server.control_token):
                result = {"ok": False}
                self.wfile.write(json.dumps(result, separators=(",", ":")).encode() + b"\n")
                return
            action = command.get("action")
            if action == "next_otp":
                deadline = time.monotonic() + 15
                messages = []
                while time.monotonic() < deadline and not messages:
                    messages = self.server.adapter.take_messages()
                    if not messages:
                        time.sleep(0.025)
                result = {"ok": len(messages) == 1, "code": messages[0].verification_code if len(messages) == 1 else None}
            elif action == "assistant_call_count":
                # The private authenticated control socket exposes only counts.
                result = {"ok": True, "count": self.server.chat_gateway.call_count}
            elif action == "assistant_call_status":
                snapshot = getattr(self.server.chat_gateway, "safe_snapshot", None)
                result = {"ok": True, **snapshot()} if callable(snapshot) else {
                    "ok": True, "attempts": self.server.chat_gateway.call_count,
                    "successes": 0, "failures": 0,
                    "route": {"scheme": "simulated", "host": None, "port": None,
                              "model_id": "simulated-test-gateway"},
                }
            elif action == "owner_rag_call_counts":
                if self.server.owner_rag_counter is None:
                    result = {
                        "ok": True,
                        "enabled": False,
                        "calls": 0,
                        "outcomes": {
                            "ok": 0,
                            "no_evidence": 0,
                            "unavailable": 0,
                            "invalid_request": 0,
                            "authentication_failed": 0,
                        },
                    }
                else:
                    result = {"ok": True, **self.server.owner_rag_counter.safe_snapshot()}
            elif action == "enable_itinerary_fixture":
                # This test-only projection is deliberately isolated to the
                # traveler recommendation dependency. Public catalogue views
                # remain unchanged; no canonical rows are written.
                with psycopg.connect(**self.server.database, connect_timeout=2, row_factory=dict_row) as connection:
                    published_keys = [row["destination_key"] for row in connection.execute(
                        "SELECT destination_key FROM knowledge.production_destinations ORDER BY destination_key"
                    ).fetchall()]
                allowed_qa_keys = {
                    "shiraz-hafezieh-v1", "shiraz-eram-garden-v1",
                    "shiraz-vakil-bazaar-v1", "unesco-persepolis-v1",
                }
                if len(published_keys) > 4 or not set(published_keys).issubset(allowed_qa_keys):
                    result = {"ok": False, "reason": "unexpected_published_catalogue"}
                else:
                    self.server.fixture_state["enabled"] = True
                    result = {"ok": True, "destination_ids": self.server.itinerary_fixture_ids,
                              "replaced_qa_catalogue_count": len(published_keys)}
            elif action == "disable_itinerary_fixture":
                self.server.fixture_state["enabled"] = False
                result = {"ok": True}
            elif action == "account_state":
                user_id = str(command.get("user_id", ""))
                phone = str(command.get("phone", ""))
                if not re.fullmatch(r"[0-9a-fA-F-]{36}", user_id) or not re.fullmatch(r"\+989[0-9]{9}", phone):
                    result = {"ok": False}
                else:
                    result = {"ok": True, **_account_state(self.server.database, user_id, phone)}
            elif action == "cleanup_phones":
                phones = command.get("phones")
                if not isinstance(phones, list) or any(not isinstance(phone, str) for phone in phones):
                    result = {"ok": False}
                else:
                    _cleanup_phones(self.server.database, phones)
                    result = {"ok": True}
            elif action == "assert_phones_unused":
                phones = command.get("phones")
                result = {"ok": isinstance(phones, list) and _phones_unused(self.server.database, phones)}
            elif action == "grant_catalogue_capabilities":
                caps = command.get("capabilities")
                result = {"ok": isinstance(caps, list) and _grant_catalogue_capabilities(
                    self.server.database, str(command.get("user_id", "")), caps,
                    str(command.get("granted_by", "")),
                )}
            elif action == "grant_isolated_partner_reviewer":
                result = _grant_isolated_partner_reviewer(
                    self.server.database, str(command.get("user_id", "")),
                    str(command.get("actor_id", "")),
                )
            elif action == "grant_isolated_admin_overview":
                result = _grant_isolated_admin_overview(
                    self.server.database, str(command.get("user_id", "")),
                    str(command.get("actor_id", "")),
                )
            elif action == "isolated_partner_counts":
                counts = _isolated_partner_counts(self.server.database)
                result = {"ok": counts is not None, **(counts or {})}
            elif action == "approve_isolated_test_organization":
                approved, reason = _approve_isolated_test_organization(
                    self.server.database,
                    str(command.get("organization_id", "")),
                    str(command.get("created_by", "")),
                    str(command.get("display_name", "")),
                )
                result = {"ok": approved, "reason": reason}
            elif action == "national_catalogue_counts":
                counts = _national_catalogue_counts(self.server.database)
                result = {"ok": counts is not None, **(counts or {})}
            else:
                result = {"ok": False}
        except Exception:
            result = {"ok": False}
        self.wfile.write(json.dumps(result, separators=(",", ":")).encode() + b"\n")


def main() -> None:
    global _SAFE_PHASE
    _SAFE_PHASE = "database_verification"
    database = _verify_disposable_database()
    # Construct Settings explicitly with _env_file=None; neither repository
    # root nor backend .env participates in this harness.
    api_port = int(_required("E2E_API_PORT"))
    web_origin = _required("E2E_WEB_ORIGIN")
    control_port = int(_required("E2E_CONTROL_PORT"))
    control_token = _required("E2E_CONTROL_TOKEN")
    rag_flag = os.environ.get("TOURISM_RAG_ENABLED", "").strip().lower()
    if rag_flag in {"", "0", "false", "no", "off"}:
        rag_enabled = False
    elif rag_flag in {"1", "true", "yes", "on"}:
        rag_enabled = True
    else:
        raise RuntimeError("E2E precondition failed: owner RAG enable flag is invalid")
    rag_url = os.environ.get("TOURISM_RAG_API_URL", "http://127.0.0.1:8765")
    rag_token = os.environ.get("TOURISM_RAG_API_TOKEN", "")
    geo_qa_mode = os.environ.get("RAHGARD_REAL_GEO_E2E", "") == "1"
    national_catalogue_mode = os.environ.get("RAHGARD_NATIONAL_CATALOGUE_E2E", "") == "1"
    real_chat_provider = os.environ.get("RAHGARD_REAL_CHAT_PROVIDER", "").strip().lower()
    if real_chat_provider not in {"", "lm_studio", "remote_vllm", "forced_outage"}:
        raise RuntimeError("E2E precondition failed: real Chat provider mode is invalid")
    if geo_qa_mode and (os.environ.get("RAHGARD_RUN_GEO_QA") != "1" or rag_enabled):
        raise RuntimeError("E2E real geographic QA mode requires explicit opt-in and no RAG")
    if rag_enabled:
        from urllib.parse import urlsplit

        parsed_rag_url = urlsplit(rag_url)
        if (
            parsed_rag_url.scheme != "http"
            or parsed_rag_url.hostname != "127.0.0.1"
            or parsed_rag_url.port != 8765
            or parsed_rag_url.path not in {"", "/"}
            or parsed_rag_url.query
            or parsed_rag_url.fragment
            or parsed_rag_url.username
            or parsed_rag_url.password
            or not rag_token
            or rag_token != rag_token.strip()
            or "\r" in rag_token
            or "\n" in rag_token
        ):
            raise RuntimeError("E2E precondition failed: owner RAG must use configured loopback service credentials")
    import uvicorn

    import app.core.config as config
    settings_dependency = config.get_settings

    real_chat_endpoint = os.environ.get("RAHGARD_REAL_CHAT_ENDPOINT", "")
    real_chat_model = os.environ.get("RAHGARD_REAL_CHAT_MODEL", "")
    real_chat_token = os.environ.get("RAHGARD_REAL_CHAT_TOKEN", "")
    loopback_http_port = None
    if real_chat_provider in {"lm_studio", "forced_outage"}:
        from urllib.parse import urlsplit

        parsed_chat = urlsplit(real_chat_endpoint)
        try:
            loopback_http_port = int(os.environ.get("RAHGARD_REAL_CHAT_LOOPBACK_HTTP_PORT", ""))
        except ValueError:
            raise RuntimeError("E2E precondition failed: local Chat port is invalid") from None
        if (
            parsed_chat.scheme != "http" or parsed_chat.hostname != "127.0.0.1"
            or parsed_chat.port != loopback_http_port or parsed_chat.path != "/v1/chat/completions"
            or parsed_chat.username or parsed_chat.password or parsed_chat.query or parsed_chat.fragment
            or not real_chat_model or not real_chat_token or not 1024 <= loopback_http_port <= 65535
        ):
            raise RuntimeError("E2E precondition failed: local Chat target must be explicit loopback")
    elif real_chat_provider == "remote_vllm":
        from urllib.parse import urlsplit

        parsed_chat = urlsplit(real_chat_endpoint)
        if (
            parsed_chat.scheme != "https" or parsed_chat.hostname != "llm.hinaa.ir"
            or parsed_chat.path != "/v1/chat/completions" or parsed_chat.username
            or parsed_chat.password or parsed_chat.query or parsed_chat.fragment
            or real_chat_model != "TaHa1_VL" or not real_chat_token
        ):
            raise RuntimeError("E2E precondition failed: remote Chat target is not the approved endpoint/model")
    _SAFE_PHASE = "settings_validation"
    settings = config.Settings(
        _env_file=None,
        app_env="test",
        app_host="127.0.0.1",
        app_port=api_port,
        database_host=database["host"],
        database_port=database["port"],
        database_name=database["dbname"],
        database_user=database["user"],
        database_password=database["password"],
        auth_enabled=True,
        # Offline E2E enables the API route, but overrides its gateway before
        # any request can reach the network. No paid or external model traffic.
        internal_chat_enabled=True,
        internal_chat_endpoint=(real_chat_endpoint if real_chat_provider else
                                "https://example.invalid/v1/chat/completions"),
        internal_chat_model=(real_chat_model if real_chat_provider else "offline-browser-fixture"),
        internal_chat_token=__import__("pydantic").SecretStr(
            real_chat_token if real_chat_provider else token_hex(32),
        ),
        internal_chat_loopback_http_port=loopback_http_port,
        tourism_rag_enabled=rag_enabled,
        tourism_rag_api_url=rag_url,
        tourism_rag_api_token=(
            __import__("pydantic").SecretStr(rag_token) if rag_enabled else None
        ),
        auth_sms_adapter="fake",
        auth_cookie_secure=False,
        auth_allowed_origins=web_origin,
        auth_otp_hmac_secret="e2e-otp-key-only-test-000000000000000000000001",
        auth_csrf_secret="e2e-csrf-key-only-test-000000000000000000000001",
        auth_rate_limit_secret="e2e-rate-key-only-test-000000000000000000000001",
        auth_session_idle_seconds=1800,
        auth_session_absolute_seconds=43200,
        auth_phone_issue_limit=20,
        auth_ip_issue_limit=100,
        auth_global_issue_limit=1000,
        auth_phone_verify_limit=100,
        auth_ip_verify_limit=100,
    )
    config.get_settings = lambda: settings
    _SAFE_PHASE = "application_import"
    from app.main import app, safe_http_exception
    from fastapi import HTTPException as FastAPIHTTPException
    from fastapi.responses import JSONResponse
    from app.modules.identity.sms import FakeSmsAdapter
    from app.api.assistant import get_chat_gateway
    from app.modules.integrations.chat_adapter import ChatReply
    from app.api import traveler as traveler_api
    from app.modules.catalog.schemas import ProductionDestinationItem
    from app.modules.recommendation.contracts import EvidenceSource
    from app.modules.recommendation.retrieval import StructuredDestinationMetadata
    from app.modules.retrieval.contracts import (
        RetrievalAuthenticationFailed,
        RetrievalInvalidRequest,
        RetrievalUnavailable,
    )
    from app.modules.retrieval.owner_http import OwnerRagHttpAdapter

    class CountingOwnerRetrievalPort:
        """Count safe outcomes only; never retain query or response evidence."""

        def __init__(self, adapter):
            self.adapter = adapter
            self.call_count = 0
            self.outcomes = {
                "ok": 0,
                "no_evidence": 0,
                "unavailable": 0,
                "invalid_request": 0,
                "authentication_failed": 0,
            }

        async def retrieve(self, request, /):
            self.call_count += 1
            try:
                response = await self.adapter.retrieve(request)
            except RetrievalAuthenticationFailed:
                self.outcomes["authentication_failed"] += 1
                raise
            except RetrievalInvalidRequest:
                self.outcomes["invalid_request"] += 1
                raise
            except RetrievalUnavailable:
                self.outcomes["unavailable"] += 1
                raise
            self.outcomes[response.status] += 1
            return response

        def safe_snapshot(self):
            return {"enabled": True, "calls": self.call_count, "outcomes": dict(self.outcomes)}

    class SimulatedChatGateway:
        """Only for guarded E2E. Simulates model content; makes zero HTTP calls."""

        def __init__(self) -> None:
            self.call_count = 0

        async def invoke(self, request):
            self.call_count += 1
            # The first traveler turn has no prior conversation history; its
            # current text is the persisted initial request. Follow-up turns
            # add history naturally. Requiring history here rejected a valid
            # initial request before the simulated provider could respond.
            if not request.text.strip():
                raise RuntimeError("simulated_e2e_input_missing")
            prompts = {
                "fa-IR": ("\u0628\u0631\u0627\u06cc \u0633\u0641\u0631 2 \u0631\u0648\u0632 \u0633\u0641\u0631 \u0628\u0647 \u0634\u06cc\u0631\u0627\u0632 \u067e\u06cc\u0634\u0646\u0647\u0627\u062f \u0628\u062f\u0647.", "\u0634\u06cc\u0631\u0627\u0632", "2 \u0631\u0648\u0632 \u0633\u0641\u0631"),
                "en-US": ("Please suggest a 2-day trip to Shiraz.", "Shiraz", "2-day trip"),
                "ar": ("\u0627\u0642\u062a\u0631\u062d \u0631\u062d\u0644\u0629 \u0644\u0645\u062f\u0629 2 \u064a\u0648\u0645 \u0625\u0644\u0649 Shiraz.", "Shiraz", "\u0644\u0645\u062f\u0629 2 \u064a\u0648\u0645"),
            }
            _, destination, duration_quote = prompts[request.locale]
            replies = {
                "fa-IR": "\u067e\u06cc\u0634\u0646\u0647\u0627\u062f \u0622\u0632\u0645\u0627\u06cc\u0634\u06cc: \u0633\u0641\u0631 \u062f\u0648 \u0631\u0648\u0632\u0647 \u0628\u0647 \u0634\u06cc\u0631\u0627\u0632. \u0627\u0628\u062a\u062f\u0627 \u0622\u0646 \u0631\u0627 \u0628\u0631\u0631\u0633\u06cc \u06a9\u0646\u06cc\u062f.",
                "en-US": "Simulated suggestion: a two-day trip to Shiraz. Review it first.",
                "ar": "\u0627\u0642\u062a\u0631\u0627\u062d \u062a\u062c\u0631\u064a\u0628\u064a: \u0631\u062d\u0644\u0629 \u0644\u0645\u062f\u0629 \u064a\u0648\u0645\u064a\u0646 \u0625\u0644\u0649 Shiraz. \u0631\u0627\u062c\u0639\u0647\u0627 \u0623\u0648\u0644\u0627.",
            }
            return ChatReply(
                reply=replies[request.locale],
                requirements={"destination": destination, "duration_days": 2},
                requirement_evidence={"destination": destination, "duration_days": duration_quote},
            )

    class CountingChatGateway:
        """Count calls around the actual production gateway without retaining prompts or replies."""

        def __init__(self, gateway, route_settings):
            self.gateway = gateway
            self.adapter = getattr(gateway, "_adapter", None)
            self.call_count = 0
            self.success_count = 0
            self.failure_count = 0
            self.response_field_keys: list[str] = []
            self.response_evidence_keys: list[str] = []
            self.latency_ms: list[int] = []
            self.model_id = route_settings.internal_chat_model
            parsed = __import__("urllib.parse", fromlist=["urlsplit"]).urlsplit(
                route_settings.internal_chat_endpoint,
            )
            self.route = {
                "scheme": parsed.scheme, "host": parsed.hostname,
                "port": parsed.port, "model_id": self.model_id,
            }

        async def invoke(self, request):
            started = __import__("time").perf_counter()
            self.call_count += 1
            try:
                result = await self.gateway.invoke(request)
            except Exception:
                self.failure_count += 1
                self.latency_ms.append(round((__import__("time").perf_counter() - started) * 1000))
                raise
            self.success_count += 1
            self.latency_ms.append(round((__import__("time").perf_counter() - started) * 1000))
            # Keep only schema key names for private acceptance diagnostics;
            # never retain the request, model reply, or evidence text.
            self.response_field_keys = sorted(result.requirements.keys())[:20]
            self.response_evidence_keys = sorted(result.requirement_evidence.keys())[:20]
            return result

        def safe_snapshot(self):
            return {
                "attempts": self.call_count, "successes": self.success_count,
                "failures": self.failure_count, "route": self.route,
                "response_field_keys": self.response_field_keys,
                "response_evidence_keys": self.response_evidence_keys,
                "latency_ms": self.latency_ms[-12:],
                "last_failure_category": getattr(self.adapter, "last_failure_category", None),
            }

    if real_chat_provider:
        from app.modules.integrations.chat_adapter import make_chat_gateway

        chat_gateway = CountingChatGateway(make_chat_gateway(settings), settings)
    else:
        chat_gateway = SimulatedChatGateway()
    app.dependency_overrides[get_chat_gateway] = lambda: chat_gateway
    owner_rag_counter = None
    if rag_enabled:
        owner_rag_counter = CountingOwnerRetrievalPort(OwnerRagHttpAdapter(settings))
        app.dependency_overrides[traveler_api.get_owner_retrieval_port] = lambda: owner_rag_counter

    # Existing synthetic itinerary-stop identities are read-only test fixtures.
    # Their fake provenance is explicitly marked and never enters the approved
    # production projection. The private loopback control socket gates access.
    _SAFE_PHASE = "fixture_query"
    with psycopg.connect(**database, connect_timeout=2, row_factory=dict_row) as connection:
        published_count = connection.execute(
            "SELECT COUNT(*) AS n FROM knowledge.production_destinations"
        ).fetchone()["n"]
        fixture_rows = connection.execute(
            """SELECT DISTINCT destination_id FROM travel.itinerary_stops
               WHERE is_synthetic=TRUE ORDER BY destination_id LIMIT 4"""
        ).fetchall()
        geo_rows = connection.execute(
            """SELECT destination_key, coordinate_role FROM knowledge.production_destinations"""
        ).fetchall() if geo_qa_mode else []
    _SAFE_PHASE = "fixture_assertions"
    # Real-provider acceptance exercises the provisional itinerary path and
    # deliberately starts with no catalogue records. The four synthetic stop
    # identities belong only to the historical simulated recommendation
    # journey; requiring them here prevented the provider from ever being
    # invoked on a clean disposable database.
    if not real_chat_provider and len(fixture_rows) != 4:
        raise RuntimeError("E2E seeded QA fixture prerequisite failed")
    if geo_qa_mode:
        expected_geo = {
            "shiraz-hafezieh-v1": "representative_point",
            "shiraz-eram-garden-v1": "representative_point",
            "shiraz-vakil-bazaar-v1": "representative_point",
            "unesco-persepolis-v1": "property_reference",
        }
        actual_geo = {row["destination_key"]: row["coordinate_role"] for row in geo_rows}
        if published_count != 4 or actual_geo != expected_geo:
            raise RuntimeError("E2E geo QA expects exactly four real canonical published map points")
    elif published_count != 0 and not national_catalogue_mode and not real_chat_provider:
        raise RuntimeError("E2E historical fixture mode requires an empty production catalogue")
    # Pending content-pack geometry is borrowed only to exercise the coordinate
    # grouping path with synthetic destination identities. It is not canonical,
    # independently verified, returned as a traveler coordinate, or written to
    # PostgreSQL. The first three points are a compact Shiraz cluster; the last
    # is the regional Persepolis reference point in Marvdasht.
    pending_review_test_geometry = (
        (29.6254028, 52.5583194, "representative_point"),
        (29.63583, 52.52528, "representative_point"),
        (29.6149806, 52.5467972, "representative_point"),
        (29.93444, 52.89028, "property_reference"),
    )
    fixture_items = []
    fixture_sources = {}
    for index, row in enumerate(fixture_rows, start=1):
        destination_id = str(row["destination_id"])
        latitude, longitude, coordinate_role = pending_review_test_geometry[index - 1]
        fixture_items.append(ProductionDestinationItem(
            destination_id=destination_id,
            destination_key=f"E2E-TEST-ONLY-{index}",
            canonical_name=f"NONEXISTENT E2E TEST PLACE {index}",
            localized_names={
                "fa-IR": f"مقصد ساختگی آزمون {index}",
                "en-US": f"Synthetic E2E test place {index}",
                "ar": f"وجهة اختبار اصطناعية {index}",
            },
            aliases=[],
            destination_type="heritage_site",
            province_name="TEST ONLY",
            city_name="TEST ONLY",
            latitude=latitude,
            longitude=longitude,
            coordinate_role=coordinate_role,
        ))
        fixture_sources[destination_id] = [EvidenceSource(
            destination_id=int(destination_id),
            source_id=98_000 + index,
            source_name="FAKE EVIDENCE — TEST ONLY",
            source_url=f"https://example.invalid/e2e-test-only/{index}",
            source_role="synthetic_test_only",
            evidence_note="Fabricated solely for guarded API and persistence verification.",
        )]
    fixture_bundle = (
        fixture_items,
        fixture_sources,
        {str(item.destination_id): StructuredDestinationMetadata(tags=[]) for item in fixture_items},
    )
    original_bundle = traveler_api.production_catalogue_bundle
    fixture_state = {"enabled": False}

    def guarded_catalogue_bundle(settings):
        if fixture_state["enabled"]:
            return fixture_bundle
        return original_bundle(settings)

    # Never inject synthetic recommendation identities in real-catalogue mode.
    if not geo_qa_mode and not national_catalogue_mode:
        traveler_api.production_catalogue_bundle = guarded_catalogue_bundle
    adapter = FakeSmsAdapter()
    app.state.sms_adapter = adapter
    if national_catalogue_mode:
        async def safe_isolated_forbidden_code(request, error):
            # Isolated-only diagnostics expose a strict allowlist of generic
            # authorization reason codes. Production keeps the normal
            # privacy-preserving `request_rejected` response.
            safe_codes = {
                "csrf_rejected", "self_review_forbidden", "partner_review_not_granted",
                "organization_access_denied", "organization_owner_required",
            }
            if isinstance(error, FastAPIHTTPException) and error.status_code == 403 \
                    and isinstance(error.detail, str) and (
                        error.detail in safe_codes
                        or re.fullmatch(r"db_privilege_denied_[A-Za-z0-9_]+_[A-Za-z0-9_.]+", error.detail)
                    ):
                return JSONResponse(status_code=403, content={"error": {"code": error.detail}})
            return await safe_http_exception(request, error)

        app.add_exception_handler(FastAPIHTTPException, safe_isolated_forbidden_code)
    # Routers imported the original cached dependency function by reference.
    # Override that exact callable; patching config.get_settings alone replaces
    # only the module attribute and leaves route dependencies on defaults.
    app.dependency_overrides[settings_dependency] = lambda: settings
    _SAFE_PHASE = "api_server_start"
    server = uvicorn.Server(uvicorn.Config(
        app, host="127.0.0.1", port=api_port, log_level="warning", access_log=False, log_config=None
    ))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not server.started:
        time.sleep(0.025)
    if not server.started:
        raise RuntimeError("E2E API server did not start")
    _SAFE_PHASE = "control_server_start"
    control = socketserver.ThreadingTCPServer(("127.0.0.1", control_port), _ControlHandler)
    control.daemon_threads = True
    control.adapter = adapter
    control.database = database
    control.chat_gateway = chat_gateway
    control.owner_rag_counter = owner_rag_counter
    control.itinerary_fixture_enabled = False
    control.itinerary_fixture_ids = [str(row["destination_id"]) for row in fixture_rows]
    # Keep the closure state shared with the private control handler.
    control.fixture_state = fixture_state
    control.control_token = control_token
    control_thread = threading.Thread(target=control.serve_forever, daemon=True)
    control_thread.start()
    # stdout carries readiness only. OTP values are returned on the authenticated
    # private loopback test-control socket, never stdout or an HTTP API.
    _SAFE_PHASE = "ready"
    print(json.dumps({"ok": True, "event": "ready"}), flush=True)
    try:
        thread.join()
    finally:
        control.shutdown()
        control.server_close()
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Diagnostics are stable and must never contain credentials or IDs.
        sys.stderr.write(f"E2E server failed closed: {type(exc).__name__} phase={_SAFE_PHASE}\n")
        raise SystemExit(2)
