from __future__ import annotations

import asyncio
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from uuid import uuid4

from app.modules.integrations.ai_gateway import AiCapability, AiCapabilityUnavailable
from app.modules.integrations.chat_adapter import ChatReply, ChatRequest
from app.modules.provider_admin.runtime import (
    AdminManagedCapabilityAdapter,
    AdminManagedChatAdapter,
)
from app.modules.provider_admin.providers import (
    EmbeddingRequest,
    EmbeddingResponse,
    RerankingRequest,
    RerankingResponse,
    VisionRequest,
    VisionResponse,
)
from app.api import assistant


def _snapshot(revision_id, capability="chat", model="m1"):
    return SimpleNamespace(
        revision_id=revision_id,
        generation=1,
        config={
            "provider_kind": "lm_studio",
            "base_url": "http://127.0.0.1:1234/v1",
            "timeout_seconds": 10,
            "concurrency_limit": 1,
            "capabilities": {capability: {"model_id": model, "max_tokens": 30}},
        },
        secret_ref=None,
    )


class _Registry:
    def __init__(self, active, policy=None, snapshots=None):
        self.active = active
        self.policy = policy or {"enabled": False, "ordered_revision_ids": []}
        self.snapshots = snapshots or {}
        self.usage = []

    def active_snapshot(self, capability):
        return self.active.get(capability) if isinstance(self.active, dict) else self.active

    def get_fallback(self, _capability):
        return self.policy

    def validated_snapshot(self, _capability, revision_id):
        if revision_id in self.snapshots:
            return self.snapshots[revision_id]
        if isinstance(self.active, dict):
            return next(item for item in self.active.values() if item.revision_id == revision_id)
        return self.active

    def record_usage(self, **event):
        self.usage.append(event)


class _Vault:
    def get(self, _ref):
        raise AssertionError("test snapshots should not require a secret")


def test_fallback_is_off_by_default_and_does_not_mask_active_failure():
    active_id = uuid4()
    registry = _Registry(_snapshot(active_id))

    class FailedAdapter:
        async def invoke(self, _request):
            raise AiCapabilityUnavailable()

    runtime = AdminManagedChatAdapter(
        registry, _Vault(), adapter_factory=lambda _config: FailedAdapter()
    )
    try:
        asyncio.run(runtime.invoke(ChatRequest(locale="fa-IR", text="سلام")))
    except AiCapabilityUnavailable:
        pass
    else:
        raise AssertionError("disabled fallback must preserve provider unavailability")
    assert registry.usage == [
        {
            "capability": "chat",
            "revision_id": active_id,
            "outcome": "unavailable",
            "latency_ms": registry.usage[0]["latency_ms"],
        }
    ]


def test_enabled_fallback_uses_only_explicit_validated_order_after_active_failure():
    active_id, fallback_id = uuid4(), uuid4()
    registry = _Registry(
        _snapshot(active_id),
        {"enabled": True, "ordered_revision_ids": [fallback_id]},
        {fallback_id: _snapshot(fallback_id)},
    )
    used = []

    class ConfiguredAdapter:
        def __init__(self, model_id):
            self.model_id = model_id

        async def invoke(self, _request):
            used.append(self.model_id)
            if self.model_id == "primary":
                raise AiCapabilityUnavailable()
            return ChatReply(
                reply="ok", requirements={}, requirement_evidence={}, clarification=None
            )

    def factory(config):
        # Exact revision identity is supplied by the resolved snapshot in this test.
        model = "fallback" if len(used) else "primary"
        return ConfiguredAdapter(model)

    # Avoid any secrets and retain the real active/fallback resolution behavior.
    runtime = AdminManagedChatAdapter(registry, _Vault(), adapter_factory=factory)
    result = asyncio.run(runtime.invoke(ChatRequest(locale="fa-IR", text="سلام")))
    assert result.reply == "ok"
    assert used == ["primary", "fallback"]
    assert [item["outcome"] for item in registry.usage] == ["unavailable", "success"]
    assert [item["revision_id"] for item in registry.usage] == [active_id, fallback_id]


def test_authenticated_assistant_dependency_selects_dynamic_gateway_only_when_enabled(monkeypatch):
    configured = object()
    monkeypatch.setattr(assistant, "make_admin_chat_gateway", lambda _settings: configured)
    settings = SimpleNamespace(ai_provider_admin_enabled=True)
    assert assistant.get_chat_gateway(settings) is configured

    ordinary = object()
    monkeypatch.setattr(assistant, "make_chat_gateway", lambda _settings: ordinary)
    settings.ai_provider_admin_enabled = False
    assert assistant.get_chat_gateway(settings) is ordinary


def test_per_capability_runtime_dispatch_uses_its_own_active_snapshot_and_usage():
    cases = [
        (
            "vision",
            VisionRequest(
                prompt="Describe it", image_data_url="data:image/png;base64,iVBORw0KGgo="
            ),
            VisionResponse(text="image"),
            "image",
        ),
        (
            "embedding",
            EmbeddingRequest(input="text"),
            EmbeddingResponse(embedding=(0.1, -0.2)),
            "vector",
        ),
        (
            "reranking",
            RerankingRequest(query="q", documents=("a", "b")),
            RerankingResponse(scores=(0.2, 0.8)),
            "scores",
        ),
    ]
    for capability, request, expected, _kind in cases:
        revision_id = uuid4()
        snapshot = _snapshot(revision_id, capability)
        registry = _Registry({capability: snapshot})
        observed = []

        class Adapter:
            async def invoke(self, received):
                observed.append((received, capability))
                return expected

        runtime = AdminManagedCapabilityAdapter(
            registry,
            _Vault(),
            AiCapability(capability),
            adapter_factory=lambda config: Adapter() if config.capability == capability else None,
        )
        result = asyncio.run(runtime.invoke(request))
        assert result == expected
        assert observed == [(request, capability)]
        assert registry.usage[0]["capability"] == capability
        assert registry.usage[0]["revision_id"] == revision_id


def test_admin_managed_gateway_reads_new_active_chat_revision_on_next_turn():
    first, second = uuid4(), uuid4()
    registry = _Registry(_snapshot(first, model="first"))
    selected = []

    class Adapter:
        def __init__(self, config):
            self.config = config

        async def invoke(self, _request):
            selected.append(self.config.model_id)
            return ChatReply(
                reply=self.config.model_id,
                requirements={},
                requirement_evidence={},
                clarification=None,
            )

    runtime = AdminManagedChatAdapter(registry, _Vault(), adapter_factory=Adapter)
    one = asyncio.run(runtime.invoke(ChatRequest(locale="fa-IR", text="test")))
    registry.active = _snapshot(second, model="second")
    two = asyncio.run(runtime.invoke(ChatRequest(locale="fa-IR", text="test")))
    assert one.reply == "first"
    assert two.reply == "second"
    assert selected == ["first", "second"]


def test_admin_managed_chat_switches_real_loopback_http_endpoint_on_next_turn():
    """Exercise the provider-neutral runtime through real bounded HTTP requests.

    This is a controlled local protocol fixture, not evidence of live model
    inference. It verifies the runtime's active-revision lookup selects the
    configured endpoint/model for each traveler invocation.
    """
    received = {"a": [], "b": []}

    def make_server(label):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                body = json.loads(self.rfile.read(length))
                received[label].append((self.path, body.get("model")))
                content = json.dumps({
                    "reply": label,
                    "requirements": {},
                    "requirement_evidence": {},
                    "clarification": None,
                }, ensure_ascii=False)
                response = json.dumps({
                    "choices": [{
                        "finish_reason": "stop",
                        "message": {"content": content},
                    }]
                }).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            def log_message(self, *_args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread

    server_a, thread_a = make_server("a")
    server_b, thread_b = make_server("b")
    try:
        revision_a, revision_b = uuid4(), uuid4()

        def snapshot(revision, label, server):
            return SimpleNamespace(
                revision_id=revision,
                generation=1,
                secret_ref=None,
                config={
                    "provider_kind": "lm_studio",
                    "base_url": f"http://127.0.0.1:{server.server_port}/v1",
                    "timeout_seconds": 3,
                    "concurrency_limit": 1,
                    "capabilities": {"chat": {"model_id": f"model-{label}", "max_tokens": 20}},
                },
            )

        active = snapshot(revision_a, "a", server_a)
        registry = _Registry(active, snapshots={
            revision_a: active,
            revision_b: snapshot(revision_b, "b", server_b),
        })
        runtime = AdminManagedChatAdapter(registry, _Vault())

        first = asyncio.run(runtime.invoke(ChatRequest(locale="fa-IR", text="turn one")))
        registry.active = registry.snapshots[revision_b]
        second = asyncio.run(runtime.invoke(ChatRequest(locale="fa-IR", text="turn two")))

        assert (first.reply, second.reply) == ("a", "b")
        assert received["a"] == [("/v1/chat/completions", "model-a")]
        assert received["b"] == [("/v1/chat/completions", "model-b")]
        assert [event["outcome"] for event in registry.usage] == ["success", "success"]
    finally:
        for server, thread in ((server_a, thread_a), (server_b, thread_b)):
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()
