import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from app.modules.integrations.ai_gateway import AiCapabilityUnavailable
from app.modules.integrations.chat_adapter import ChatRequest
from app.modules.provider_admin.providers import (
    ChatProviderConfig,
    OpenAiCompatibleChatAdapter,
    OpenAiCompatibleProviderAdapter,
    ProviderAuthenticationError,
    ProviderCapabilityUnsupported,
    ProviderConfigurationError,
    ProviderTransportError,
    _PinnedGapGptBackend,
    _resolve_public_gapgpt_addresses,
    validate_chat_config,
)


def config(
    kind="lm_studio",
    url="http://127.0.0.1:1234/v1",
    model="local-chat",
    key=None,
    capability="chat",
):
    return ChatProviderConfig(
        provider_kind=kind,
        base_url=url,
        model_id=model,
        api_key=SecretStr(key) if key else None,
        capability=capability,
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


def test_model_discovery_does_not_claim_inference_passed():
    requests = []

    async def respond(request):
        requests.append((request.method, request.url.path))
        return httpx.Response(200, json={"data": [{"id": "local-chat"}]})

    adapter = OpenAiCompatibleProviderAdapter(config(), transport=httpx.MockTransport(respond))
    result = asyncio.run(
        adapter.test_capability("chat", "local-chat", test_kind="discovery", max_output_tokens=16)
    )
    assert result["status"] == "models_catalog_reachable"
    assert result["model_selected"] is True
    assert result["capability_verified"] is False
    assert result["actual_inference_passed"] is False
    assert requests == [("GET", "/v1/models")]


def test_explicit_chat_inference_uses_bounded_fixed_payload():
    requests = []

    async def respond(request):
        requests.append(request)
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "local-chat"}]})
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "READY"},
                    }
                ]
            },
        )

    adapter = OpenAiCompatibleProviderAdapter(config(), transport=httpx.MockTransport(respond))
    result = asyncio.run(
        adapter.test_capability("chat", "local-chat", test_kind="inference", max_output_tokens=17)
    )
    assert result["status"] == "inference_passed"
    assert result["capability_verified"] is result["actual_inference_passed"] is True
    body = json.loads(requests[1].read())
    assert body["max_tokens"] == 17
    assert body["messages"][0]["content"] == "Reply with the word READY."


def test_embedding_inference_validates_vector_shape_without_returning_it():
    paths = []

    async def respond(request):
        paths.append(request.url.path)
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "embed-model"}]})
        return httpx.Response(200, json={"data": [{"embedding": [0.25, -0.5]}]})

    adapter = OpenAiCompatibleProviderAdapter(
        config(model="embed-model", capability="embedding"),
        transport=httpx.MockTransport(respond),
    )
    result = asyncio.run(adapter.test_capability("embedding", "embed-model", test_kind="inference"))
    assert result["status"] == "inference_passed"
    assert paths == ["/v1/models", "/v1/embeddings"]


def test_vision_inference_uses_tiny_fixed_image_and_bounded_output():
    requests = []

    async def respond(request):
        requests.append(request)
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "vision-model"}]})
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": "one pixel"},
                    }
                ]
            },
        )

    adapter = OpenAiCompatibleProviderAdapter(
        config(model="vision-model", capability="vision"),
        transport=httpx.MockTransport(respond),
    )
    result = asyncio.run(
        adapter.test_capability(
            "vision", "vision-model", test_kind="inference", max_output_tokens=12
        )
    )
    assert result["status"] == "inference_passed"
    payload = json.loads(requests[1].read())
    assert payload["max_tokens"] == 12
    assert payload["messages"][0]["content"][1]["image_url"]["url"].startswith(
        "data:image/png;base64,"
    )


def test_missing_reranking_endpoint_is_unsupported_not_green():
    paths = []

    async def respond(request):
        paths.append(request.url.path)
        if request.url.path.endswith("/models"):
            return httpx.Response(200, json={"data": [{"id": "rerank-model"}]})
        return httpx.Response(404, json={"error": "unsupported"})

    adapter = OpenAiCompatibleProviderAdapter(
        config(model="rerank-model", capability="reranking"),
        transport=httpx.MockTransport(respond),
    )
    with pytest.raises(ProviderCapabilityUnsupported):
        asyncio.run(adapter.test_capability("reranking", "rerank-model", test_kind="inference"))
    assert paths == ["/v1/models", "/v1/rerank"]


def test_remote_resolution_rejects_private_and_pins_public_address(monkeypatch):
    import httpcore
    import app.modules.provider_admin.providers as providers

    monkeypatch.setattr(
        providers.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(0, 0, 0, "", ("8.8.8.8", 443))],
    )
    assert _resolve_public_gapgpt_addresses("api.gapgpt.app") == ("8.8.8.8",)
    pinned = _PinnedGapGptBackend(("8.8.8.8",))
    assert pinned.pinned_host("api.gapgpt.app", 443) == "8.8.8.8"
    assert pinned.pinned_host("api.gapgpt.app", 80) == "api.gapgpt.app"
    connected = {}

    async def fake_connect(
        _self, host, port, timeout=None, local_address=None, socket_options=None
    ):
        connected.update(host=host, port=port)
        return object()

    monkeypatch.setattr(httpcore.AnyIOBackend, "connect_tcp", fake_connect)
    asyncio.run(pinned.connect_tcp("api.gapgpt.app", 443))
    assert connected == {"host": "8.8.8.8", "port": 443}

    monkeypatch.setattr(
        providers.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(0, 0, 0, "", ("127.0.0.1", 443))],
    )
    with pytest.raises(ProviderConfigurationError):
        _resolve_public_gapgpt_addresses("api.gapgpt.app")
