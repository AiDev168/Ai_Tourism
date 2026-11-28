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
    request_text = "\u0686\u0647\u0627\u0631 \u0631\u0648\u0632"
    result = asyncio.run(adapter.invoke(ChatRequest(locale="fa-IR", text=request_text)))
    assert result.reply == "Ø³Ù„Ø§Ù…"
    assert result.requirements == {"duration_days": 4}
    assert seen["auth"] is None
    assert '"model":"local-chat"' in seen["body"]
    body = json.loads(seen["body"])
    assert body["messages"][-1] == {"role": "user", "content": request_text}
    assert body["response_format"]["type"] == "json_schema"
    json_schema = body["response_format"]["json_schema"]
    assert json_schema["strict"] is True
    requirement_schema = json_schema["schema"]["properties"]["requirements"]
    assert {"origin", "destination", "duration_days", "traveler_count"}.issubset(
        requirement_schema["properties"]
    )
    assert set(requirement_schema["required"]) == set(requirement_schema["properties"])
    assert requirement_schema["properties"]["duration_days"]["type"] == ["integer", "null"]
    assert set(json_schema["schema"]["required"]) == set(json_schema["schema"]["properties"])
    assert body["temperature"] == 0
    assert "exact shortest source phrase copied from the current message" in body["messages"][0]["content"]
    assert "day after tomorrow" in body["messages"][0]["content"]
    assert "پس‌فردا/پس فردا=2" in body["messages"][0]["content"]
    assert "must not be shortened to only" in body["messages"][0]["content"]
    assert "origin is where the traveler starts" in body["messages"][0]["content"]


def test_lm_studio_structured_contract_accepts_only_named_traveler_fields():
    seen = {}

    async def respond(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "stop",
            "message": {"content": json.dumps({
                "reply": "\u0628\u0631\u0646\u0627\u0645\u0647 \u0631\u0627 \u0622\u0645\u0627\u062f\u0647 \u0645\u06cc \u06a9\u0646\u0645.",
                "requirements": {"origin": "\u0645\u0634\u0647\u062f", "destination": "\u0634\u06cc\u0631\u0627\u0632"},
                "requirement_evidence": {"origin": "\u0627\u0632 \u0645\u0634\u0647\u062f", "destination": "\u0628\u0631\u0645 \u0634\u06cc\u0631\u0627\u0632"},
                "ambiguous_requirements": {"origin": [], "destination": []},
                "clarification": None,
                "provisional_itinerary": None,
            }, ensure_ascii=False)},
        }]})

    provider = OpenAiCompatibleProviderAdapter(config(), transport=httpx.MockTransport(respond))
    request_text = "\u0627\u0632 \u0645\u0634\u0647\u062f \u0645\u06cc \u062e\u0648\u0627\u0645 \u0628\u0631\u0645 \u0634\u06cc\u0631\u0627\u0632"
    result = asyncio.run(provider.invoke(ChatRequest(locale="fa-IR", text=request_text)))
    assert result.requirements == {"origin": "\u0645\u0634\u0647\u062f", "destination": "\u0634\u06cc\u0631\u0627\u0632"}
    assert seen["body"]["response_format"]["json_schema"]["strict"] is True
    assert seen["body"]["messages"][-1]["content"] == request_text


@pytest.mark.parametrize("day_count", [1, 3, 5, 15])
def test_lm_studio_itinerary_uses_compact_exact_day_schema_and_confirmed_context(day_count):
    seen = {}
    itinerary = {
        "status": "provisional_unverified",
        "days": [{
            "day_number": number,
            "stops": [{"name": f"Suggested place {number}", "role": "model_proposed"}],
        } for number in range(1, day_count + 1)],
    }

    async def respond(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "stop",
            "message": {"content": json.dumps({
                "reply": "Unverified draft.",
                "provisional_itinerary": itinerary,
            })},
        }]})

    provider = OpenAiCompatibleChatAdapter(config(), transport=httpx.MockTransport(respond))
    result = asyncio.run(provider.invoke(ChatRequest(
        locale="en-US",
        text="Do not send this client-generated profile summary to the planner.",
        history=[{"role": "user", "content": "Old contradictory request"}],
        reviewed_profile='{"destinations":["Shiraz"],"duration_days":5}',
        provisional_itinerary_days=day_count,
    )))
    assert result.provisional_itinerary is not None
    assert len(result.provisional_itinerary.days) == day_count
    body = seen["body"]
    assert body["max_tokens"] == 800
    assert body["response_format"]["json_schema"]["name"] == "rahgard_provisional_itinerary"
    schema = body["response_format"]["json_schema"]["schema"]["properties"]["provisional_itinerary"]["properties"]["days"]
    assert schema["minItems"] == schema["maxItems"] == day_count
    assert len(body["messages"]) == 3
    assert all("Old contradictory request" not in message["content"] for message in body["messages"])
    assert all("client-generated profile summary" not in message["content"] for message in body["messages"])
    context = json.loads(body["messages"][1]["content"].removeprefix("Context only: "))
    reviewed = json.loads(context["reviewed_profile"])
    assert reviewed["destinations"] == ["Shiraz"]
    assert reviewed["duration_days"] == 5


def test_provider_chat_text_limit_matches_structured_parser_eight_kibibyte_limit():
    content = json.dumps({"reply": "ok", "requirements": {}}) + (" " * 4500)
    parsed = OpenAiCompatibleProviderAdapter._chat_text({"choices": [{
        "finish_reason": "stop",
        "message": {"content": content},
    }]})
    assert len(parsed) > 4000
    assert len(parsed) <= 8192


def test_lm_studio_uses_the_bounded_local_inference_timeout_ceiling():
    seen = {}

    async def respond(request):
        seen["timeouts"] = request.extensions["timeout"]
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "stop",
            "message": {"content": '{"reply":"ok","requirements":{}}'},
        }]})

    provider = OpenAiCompatibleProviderAdapter(
        ChatProviderConfig(
            provider_kind="lm_studio",
            base_url="http://127.0.0.1:1234/v1",
            model_id="local-model",
            timeout_seconds=20,
        ),
        transport=httpx.MockTransport(respond),
    )
    asyncio.run(provider.invoke(ChatRequest(locale="en-US", text="Plan a trip")))
    assert seen["timeouts"] == {"connect": 60.0, "read": 60.0, "write": 60.0, "pool": 60.0}


def test_remote_provider_keeps_its_explicit_timeout():
    seen = {}

    async def respond(request):
        seen["timeouts"] = request.extensions["timeout"]
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "stop",
            "message": {"content": '{"reply":"ok","requirements":{}}'},
        }]})

    provider = OpenAiCompatibleProviderAdapter(
        ChatProviderConfig(
            provider_kind="openai_compatible",
            base_url="https://api.gapgpt.app/v1",
            model_id="remote-model",
            api_key=SecretStr("test-key"),
            timeout_seconds=20,
        ),
        transport=httpx.MockTransport(respond),
    )
    asyncio.run(provider.invoke(ChatRequest(locale="en-US", text="Plan a trip")))
    assert seen["timeouts"] == {"connect": 20.0, "read": 20.0, "write": 20.0, "pool": 20.0}


def test_non_lm_studio_openai_compatible_provider_does_not_receive_local_schema_mode():
    seen = {}

    async def respond(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "stop",
            "message": {"content": '{"reply":"ok","requirements":{}}'},
        }]})

    provider = OpenAiCompatibleProviderAdapter(
        config("openai_compatible", "https://api.gapgpt.app/v1", "test-model", "test-key"),
        transport=httpx.MockTransport(respond),
    )
    asyncio.run(provider.invoke(ChatRequest(locale="en-US", text="Plan a trip")))
    assert "response_format" not in seen["body"]


def test_provider_failure_is_safe_and_not_a_successful_connection():
    async def respond(_request):
        return httpx.Response(503, text="secret upstream detail")

    adapter = OpenAiCompatibleChatAdapter(config(), transport=httpx.MockTransport(respond))
    with pytest.raises(ProviderTransportError, match="unavailable"):
        asyncio.run(adapter.test_connection())
    with pytest.raises(AiCapabilityUnavailable):
        asyncio.run(adapter.invoke(ChatRequest(locale="fa-IR", text="سلام")))


def test_provider_chat_does_not_parse_token_truncated_content_as_a_complete_reply():
    async def respond(_request):
        return httpx.Response(200, json={"choices": [{
            "finish_reason": "length",
            "message": {"content": '{"reply":"partial'},
        }]})

    adapter = OpenAiCompatibleChatAdapter(config(), transport=httpx.MockTransport(respond))
    with pytest.raises(AiCapabilityUnavailable):
        asyncio.run(adapter.invoke(ChatRequest(locale="en-US", text="Create a plan")))


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
