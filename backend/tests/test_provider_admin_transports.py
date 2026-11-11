import asyncio

import httpx
import pytest
from pydantic import SecretStr

from app.modules.integrations.ai_gateway import AiCapabilityUnavailable
from app.modules.integrations.chat_adapter import ChatRequest
from app.modules.provider_admin.providers import (
    ChatProviderConfig,
    OpenAiCompatibleChatAdapter,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderTransportError,
    validate_chat_config,
)


def config(kind="lm_studio", url="http://127.0.0.1:1234/v1", model="local-chat", key=None):
    return ChatProviderConfig(
        provider_kind=kind, base_url=url, model_id=model, api_key=SecretStr(key) if key else None
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://192.168.1.2:1234/v1",
        "http://localhost:1234/v1",
        "http://127.0.0.1:1234/v1?x=1",
        "https://api.gapgpt.app/v1",
    ],
)
def test_rejects_untrusted_or_unverified_provider_urls(url):
    with pytest.raises(ProviderConfigurationError):
        validate_chat_config(config(url=url))


def test_gapgpt_requires_exact_service_endpoint_and_key():
    with pytest.raises(ProviderConfigurationError):
        validate_chat_config(
            config("openai_compatible", "https://api.gapgpt.app/v1", "gpt-4o-mini")
        )
    assert (
        validate_chat_config(
            config("openai_compatible", "https://api.gapgpt.app/v1", "gpt-4o-mini", "secret")
        )
        == "https://api.gapgpt.app/v1"
    )


def test_model_discovery_and_non_billable_connection_test_uses_real_wire_shape():
    requests = []

    async def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"data": [{"id": "local-chat"}, {"id": "embed-only"}]})

    adapter = OpenAiCompatibleChatAdapter(config(), transport=httpx.MockTransport(respond))
    assert asyncio.run(adapter.discover_models()) == ("local-chat", "embed-only")
    result = asyncio.run(adapter.test_connection())
    assert result["ok"] is True and result["capability"] == "chat"
    assert [request.url.path for request in requests] == ["/v1/models", "/v1/models"]


def test_chat_turn_uses_selected_model_and_maps_untrusted_output():
    seen = {}

    async def respond(request):
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = request.read().decode()
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": '{"reply":"Ø³Ù„Ø§Ù…","requirements":{"duration_days":4},'
                            '"requirement_evidence":{"duration_days":"چهار روز"},"clarification":null}'
                        },
                    }
                ]
            },
        )

    adapter = OpenAiCompatibleChatAdapter(config(), transport=httpx.MockTransport(respond))
    result = asyncio.run(adapter.invoke(ChatRequest(locale="fa-IR", text="چهار روز")))
    assert result.reply == "Ø³Ù„Ø§Ù…"
    assert result.requirements == {"duration_days": 4}
    assert seen["auth"] is None
    assert '"model":"local-chat"' in seen["body"]


def test_provider_failure_is_safe_and_not_a_successful_connection():
    async def respond(_request):
        return httpx.Response(503, text="secret upstream detail")

    adapter = OpenAiCompatibleChatAdapter(config(), transport=httpx.MockTransport(respond))
    with pytest.raises(ProviderTransportError, match="unavailable"):
        asyncio.run(adapter.test_connection())
    with pytest.raises(AiCapabilityUnavailable):
        asyncio.run(adapter.invoke(ChatRequest(locale="fa-IR", text="سلام")))


def test_rejected_provider_key_is_distinct_without_exposing_upstream_body():
    async def respond(_request):
        return httpx.Response(401, text="credential secret-detail")

    adapter = OpenAiCompatibleChatAdapter(
        config("openai_compatible", "https://api.gapgpt.app/v1", "model", "key"),
        transport=httpx.MockTransport(respond),
    )
    with pytest.raises(ProviderAuthenticationError) as error:
        asyncio.run(adapter.test_connection())
    assert "credential secret-detail" not in str(error.value)


@pytest.mark.parametrize("operation", ["models", "chat"])
def test_oversized_provider_payload_is_rejected(operation):
    async def respond(_request):
        return httpx.Response(200, content=b"x" * 65_537)

    adapter = OpenAiCompatibleChatAdapter(config(), transport=httpx.MockTransport(respond))
    if operation == "models":
        with pytest.raises(ProviderTransportError):
            asyncio.run(adapter.discover_models())
    else:
        with pytest.raises(AiCapabilityUnavailable):
            asyncio.run(adapter.invoke(ChatRequest(locale="fa-IR", text="سلام")))
