from __future__ import annotations

import asyncio
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
