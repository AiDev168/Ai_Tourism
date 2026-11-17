"""One-shot, fail-closed remote Chat acceptance command.

This command is deliberately separate from application startup and never reads
dotenv files. It uses only server-side process environment, a non-sensitive
fixed test prompt, explicit owner/traveler gates, and a consumed one-use ID.
It prints status metadata only; provider text, endpoint, model and token are
never emitted.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from pathlib import Path
from typing import Mapping, Protocol

from pydantic import SecretStr, ValidationError

# Make ``python scripts/chat_live_acceptance.py`` work from backend/ without
# requiring package installation or loading any project dotenv file.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings
from app.modules.integrations.ai_gateway import AiCapabilityUnavailable
from app.modules.integrations.chat_adapter import ChatReply, ChatRequest, make_chat_gateway

_AUTHORIZATION_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
_REQUIRED_GATES = (
    ("RAHGARD_CHAT_LIVE_ACCEPTANCE_AUTHORIZED", "owner_authorization_missing"),
    ("RAHGARD_CHAT_TRAVELER_CONSENT", "traveler_processing_consent_missing"),
    ("RAHGARD_CHAT_ACCEPTANCE_CALL_BUDGET", "single_call_budget_missing"),
)
_FIXED_REQUEST = ChatRequest(
    locale="fa-IR",
    text=(
        "آزمون فنی یک‌باره اتصال دستیار سفر: لطفاً فقط یک پرسش روشن‌کننده درباره مدت سفر بپرسید. "
        "هیچ اطلاعات شخصی یا واقعیت گردشگری را حدس نزنید."
    ),
)


class SmokeBlocked(RuntimeError):
    """Safe, stable preflight failure code; contains no configuration values."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ChatGateway(Protocol):
    async def invoke(self, request: ChatRequest, /) -> ChatReply: ...


def _settings_from_environment() -> Settings:
    # Settings requires a database password even though this standalone smoke
    # never opens a database connection. The inert value is not used or logged.
    try:
        return Settings(_env_file=None, database_password=SecretStr("unused-chat-smoke"))
    except ValidationError:
        raise SmokeBlocked("remote_chat_configuration_invalid") from None


def _consume_single_use_id(state_dir: Path, authorization_id: str) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    # One acceptance call per local ledger, regardless of a caller choosing a
    # fresh authorization ID or CLI state path. This is a deliberately global
    # one-shot gate for the workspace, not a reusable per-ID budget.
    marker = state_dir / "single-provider-call.consumed"
    try:
        descriptor = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        raise SmokeBlocked("single_call_already_consumed") from None
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as stream:
            stream.write(f"consumed:{authorization_id}\n")
    except OSError:
        try:
            marker.unlink(missing_ok=True)
        except OSError:
            pass
        raise SmokeBlocked("authorization_state_unavailable") from None


async def invoke_one_authorized_chat(
    *,
    env: Mapping[str, str],
    state_dir: Path,
    settings_factory=_settings_from_environment,
    gateway_factory=make_chat_gateway,
) -> ChatReply:
    """Make at most one workspace provider request after all explicit gates pass."""

    for name, code in _REQUIRED_GATES:
        expected = "1"
        if env.get(name) != expected:
            raise SmokeBlocked(code)
    authorization_id = env.get("RAHGARD_CHAT_ACCEPTANCE_ID", "")
    if not _AUTHORIZATION_ID.fullmatch(authorization_id):
        raise SmokeBlocked("authorization_id_invalid")

    settings = settings_factory()
    if (not settings.internal_chat_enabled
            or settings.app_env.lower() not in {"development", "test"}
            or not settings.internal_chat_endpoint
            or not settings.internal_chat_model
            or settings.internal_chat_token is None
            or not settings.internal_chat_token.get_secret_value().strip()):
        raise SmokeBlocked("remote_chat_configuration_missing_or_disabled")

    # Consume before attempting transport. A timeout/unknown cost cannot be
    # retried using the same owner authorization ID.
    _consume_single_use_id(state_dir, authorization_id)
    gateway = gateway_factory(settings)
    try:
        return await gateway.invoke(_FIXED_REQUEST)
    except Exception:
        # Do not preserve provider details, raw text, URL or token in errors.
        raise AiCapabilityUnavailable() from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args(argv)
    state_dir = Path(__file__).resolve().parents[1] / ".pytest_cache" / "chat-live-acceptance"
    try:
        reply = asyncio.run(invoke_one_authorized_chat(
            env=os.environ,
            state_dir=state_dir,
        ))
    except SmokeBlocked as exc:
        print(f"BLOCKED:{exc.code}", file=sys.stderr)
        return 2
    except AiCapabilityUnavailable:
        print("FAILED:provider_unavailable; authorization consumed; do not retry automatically", file=sys.stderr)
        return 3

    # Deliberately do not print the response text, model, endpoint or candidate values.
    print("PASS:one authorized remote Chat response received")
    print(f"reply_characters={len(reply.reply)}")
    print(f"advisory_candidate_field_count={len(reply.requirements)}")
    print(f"clarification_present={reply.clarification is not None}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
