"""Guarded FastAPI process for the Playwright traveler E2E harness.

The only OTP bridge is stdin/stdout between test processes. No HTTP OTP or
debug endpoint is registered. Run with cwd=backend so the repository-root
.env is not a Settings source.
"""

from __future__ import annotations

import ipaddress
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
sys.path.insert(0, str(BACKEND_ROOT))


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
            else:
                result = {"ok": False}
        except Exception:
            result = {"ok": False}
        self.wfile.write(json.dumps(result, separators=(",", ":")).encode() + b"\n")


def main() -> None:
    database = _verify_disposable_database()
    # Construct Settings explicitly with _env_file=None; neither repository
    # root nor backend .env participates in this harness.
    api_port = int(_required("E2E_API_PORT"))
    web_origin = _required("E2E_WEB_ORIGIN")
    control_port = int(_required("E2E_CONTROL_PORT"))
    control_token = _required("E2E_CONTROL_TOKEN")
    import uvicorn

    import app.core.config as config

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
        internal_chat_endpoint="https://example.invalid/v1/chat/completions",
        internal_chat_model="offline-browser-fixture",
        internal_chat_token=__import__("pydantic").SecretStr(token_hex(32)),
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
    from app.main import app
    from app.modules.identity.sms import FakeSmsAdapter
    from app.api.assistant import get_chat_gateway
    from app.modules.integrations.chat_adapter import ChatReply

    class SimulatedChatGateway:
        """Only for guarded E2E. Simulates model content; makes zero HTTP calls."""

        def __init__(self) -> None:
            self.call_count = 0

        async def invoke(self, request):
            self.call_count += 1
            if not request.history or not request.text.strip():
                raise RuntimeError("simulated_e2e_history_or_input_missing")
            replies = {
                "fa-IR": "پیشنهاد آزمایشی: کاشان برای دو روز؛ ابتدا خودتان بررسی کنید.",
                "en-US": "Simulated suggestion: Kashan for two days. Review it first.",
                "ar": "اقتراح تجريبي: كاشان لمدة يومين. راجعه أولاً.",
            }
            return ChatReply(
                reply=replies[request.locale],
                requirements={"destination": "Kashan", "duration_days": 2},
            )

    chat_gateway = SimulatedChatGateway()
    app.dependency_overrides[get_chat_gateway] = lambda: chat_gateway
    adapter = FakeSmsAdapter()
    app.state.sms_adapter = adapter
    app.dependency_overrides[config.get_settings] = lambda: settings
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
    control = socketserver.ThreadingTCPServer(("127.0.0.1", control_port), _ControlHandler)
    control.daemon_threads = True
    control.adapter = adapter
    control.database = database
    control.chat_gateway = chat_gateway
    control.control_token = control_token
    control_thread = threading.Thread(target=control.serve_forever, daemon=True)
    control_thread.start()
    # stdout carries readiness only. OTP values are returned on the authenticated
    # private loopback test-control socket, never stdout or an HTTP API.
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
        sys.stderr.write(f"E2E server failed closed: {type(exc).__name__}\n")
        raise SystemExit(2)
