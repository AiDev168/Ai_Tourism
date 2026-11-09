from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from app.modules.integrations.ai_gateway import (
    AiCapability,
    AiCapabilityUnavailable,
    AiProviderGateway,
)


@dataclass(frozen=True)
class FakeRequest:
    text: str


@dataclass(frozen=True)
class FakeResponse:
    text: str


class DeterministicFakeAdapter:
    def __init__(self, response: FakeResponse | None = None, error: Exception | None = None):
        self.response = response
        self.error = error
        self.requests: list[FakeRequest] = []

    async def invoke(self, request: FakeRequest) -> FakeResponse:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        assert self.response is not None
        return self.response


def test_gateway_invokes_only_its_injected_capability_adapter():
    request = FakeRequest("deterministic test input")
    response = FakeResponse("deterministic test output")
    adapter = DeterministicFakeAdapter(response)
    gateway = AiProviderGateway[FakeRequest, FakeResponse](AiCapability.CHAT, adapter)

    actual = asyncio.run(gateway.invoke(request))

    assert gateway.capability is AiCapability.CHAT
    assert actual is response
    assert adapter.requests == [request]


def test_gateway_maps_adapter_failure_without_leaking_provider_details():
    secret_detail = "secret-token https://provider.invalid/private prompt text"
    adapter = DeterministicFakeAdapter(error=RuntimeError(secret_detail))
    gateway = AiProviderGateway[FakeRequest, FakeResponse](AiCapability.EMBEDDING, adapter)

    with pytest.raises(AiCapabilityUnavailable) as error:
        asyncio.run(gateway.invoke(FakeRequest("private input")))

    assert str(error.value) == "AI capability is temporarily unavailable."
    assert secret_detail not in str(error.value)
    assert error.value.__suppress_context__ is True
    assert len(adapter.requests) == 1


def test_gateway_requires_an_explicit_supported_capability():
    adapter = DeterministicFakeAdapter(FakeResponse("ok"))

    with pytest.raises(TypeError, match="capability must be an AiCapability"):
        AiProviderGateway("chat", adapter)  # type: ignore[arg-type]
