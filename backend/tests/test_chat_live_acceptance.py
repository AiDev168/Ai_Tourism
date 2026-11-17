from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.integrations.ai_gateway import AiCapabilityUnavailable
from app.modules.integrations.chat_adapter import ChatReply, ChatRequest
from scripts.chat_live_acceptance import SmokeBlocked, invoke_one_authorized_chat, main


def _settings(**changes) -> Settings:
    values = {
        "_env_file": None,
        "database_password": SecretStr("test-only-not-used"),
        "app_env": "test",
        "internal_chat_enabled": True,
        "internal_chat_endpoint": "https://chat.example.invalid/v1/completions",
        "internal_chat_model": "test-model",
        "internal_chat_token": SecretStr("test-token"),
    }
    values.update(changes)
    return Settings(**values)


def _authorized_env(**changes) -> dict[str, str]:
    env = {
        "RAHGARD_CHAT_LIVE_ACCEPTANCE_AUTHORIZED": "1",
        "RAHGARD_CHAT_TRAVELER_CONSENT": "1",
        "RAHGARD_CHAT_ACCEPTANCE_CALL_BUDGET": "1",
        "RAHGARD_CHAT_ACCEPTANCE_ID": "issue5-smoke-001",
    }
    env.update(changes)
    return env


@pytest.mark.parametrize(("name", "code"), [
    ("RAHGARD_CHAT_LIVE_ACCEPTANCE_AUTHORIZED", "owner_authorization_missing"),
    ("RAHGARD_CHAT_TRAVELER_CONSENT", "traveler_processing_consent_missing"),
    ("RAHGARD_CHAT_ACCEPTANCE_CALL_BUDGET", "single_call_budget_missing"),
])
def test_missing_explicit_gate_blocks_without_loading_settings_or_gateway(
    tmp_path: Path, name: str, code: str,
) -> None:
    env = _authorized_env(**{name: "0"})
    constructed = []

    def settings_factory():
        constructed.append("settings")
        return _settings()

    with pytest.raises(SmokeBlocked) as raised:
        asyncio.run(invoke_one_authorized_chat(
            env=env, state_dir=tmp_path, settings_factory=settings_factory,
            gateway_factory=lambda _: constructed.append("gateway"),
        ))
    assert raised.value.code == code
    assert constructed == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("overrides", [
    {"internal_chat_enabled": False},
    {"app_env": "production", "internal_chat_enabled": False},
    {"internal_chat_enabled": False, "internal_chat_token": None},
])
def test_missing_or_disabled_provider_configuration_fails_before_consuming_id(
    tmp_path: Path, overrides: dict[str, object],
) -> None:
    settings = _settings(**overrides)
    with pytest.raises(SmokeBlocked) as raised:
        asyncio.run(invoke_one_authorized_chat(
            env=_authorized_env(), state_dir=tmp_path,
            settings_factory=lambda: settings,
            gateway_factory=lambda _: pytest.fail("gateway must not be built"),
        ))
    assert raised.value.code == "remote_chat_configuration_missing_or_disabled"
    assert list(tmp_path.iterdir()) == []


def test_fixed_request_uses_gateway_exactly_once_and_replay_is_blocked(tmp_path: Path) -> None:
    calls: list[ChatRequest] = []

    class FakeGateway:
        async def invoke(self, request: ChatRequest) -> ChatReply:
            calls.append(request)
            return ChatReply(reply="تأیید فنی", requirements={}, clarification="مدت سفر چند روز است؟")

    first = asyncio.run(invoke_one_authorized_chat(
        env=_authorized_env(), state_dir=tmp_path,
        settings_factory=_settings,
        gateway_factory=lambda _: FakeGateway(),
    ))
    assert first.reply == "تأیید فنی"
    assert len(calls) == 1
    assert calls[0].locale == "fa-IR"
    assert "آزمون فنی" in calls[0].text
    assert calls[0].history == []

    with pytest.raises(SmokeBlocked) as raised:
        asyncio.run(invoke_one_authorized_chat(
            env=_authorized_env(RAHGARD_CHAT_ACCEPTANCE_ID="issue5-smoke-002"), state_dir=tmp_path,
            settings_factory=_settings,
            gateway_factory=lambda _: FakeGateway(),
        ))
    assert raised.value.code == "single_call_already_consumed"
    assert len(calls) == 1


def test_transport_failure_consumes_approval_without_retry(tmp_path: Path) -> None:
    calls = []

    class FailingGateway:
        async def invoke(self, request: ChatRequest) -> ChatReply:
            calls.append(request)
            raise RuntimeError("secret endpoint/token/prompt")

    with pytest.raises(AiCapabilityUnavailable) as raised:
        asyncio.run(invoke_one_authorized_chat(
            env=_authorized_env(), state_dir=tmp_path,
            settings_factory=_settings,
            gateway_factory=lambda _: FailingGateway(),
        ))
    assert "secret" not in str(raised.value)
    assert len(calls) == 1


def test_live_cli_does_not_allow_overriding_the_one_shot_ledger(tmp_path: Path) -> None:
    with pytest.raises(SystemExit) as raised:
        main(["--state-dir", str(tmp_path)])
    assert raised.value.code == 2
