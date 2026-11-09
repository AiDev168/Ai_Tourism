"""Internal, provider-neutral capability gateway seam.

This module defines only the backend capability boundary required by ADR-0008.
It is not an owner-RAG integration, a provider implementation, a provider
selector, or production provider activation. Each capability gateway is bound
to one explicitly injected adapter; it never falls back to another adapter.
Capability request/response schemas and provider policies remain owned by the
calling module and any future approved provider contract.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Generic, Protocol, TypeVar


class AiCapability(StrEnum):
    """AI capabilities that may cross the server-side gateway boundary."""

    CHAT = "chat"
    VISION = "vision"
    EMBEDDING = "embedding"
    RERANKING = "reranking"


RequestT = TypeVar("RequestT", contravariant=True)
ResponseT = TypeVar("ResponseT", covariant=True)


class CapabilityAdapter(Protocol[RequestT, ResponseT]):
    """Single-capability adapter contract, injectable by trusted backend code.

    Implementations are responsible for their approved bounded timeout,
    retry, rate/cost, and transport policies. This seam supplies no defaults.
    """

    async def invoke(self, request: RequestT, /) -> ResponseT: ...


class AiCapabilityUnavailable(RuntimeError):
    """Provider-neutral failure safe for propagation above the gateway."""

    def __init__(self) -> None:
        super().__init__("AI capability is temporarily unavailable.")


class AiProviderGateway(Generic[RequestT, ResponseT]):
    """A fixed capability-to-adapter boundary with safe failure mapping.

    Construct one instance per capability in trusted server wiring. The
    gateway intentionally has no routing table, configuration API, retries,
    fallback adapter, or provider metadata surface.
    """

    def __init__(
        self,
        capability: AiCapability,
        adapter: CapabilityAdapter[RequestT, ResponseT],
    ) -> None:
        if not isinstance(capability, AiCapability):
            raise TypeError("capability must be an AiCapability")
        self._capability = capability
        self._adapter = adapter

    @property
    def capability(self) -> AiCapability:
        """Return the static capability bound to this gateway instance."""

        return self._capability

    async def invoke(self, request: RequestT, /) -> ResponseT:
        """Invoke only the bound adapter, mapping all adapter errors safely."""

        try:
            return await self._adapter.invoke(request)
        except Exception:
            # Provider exception strings and causes can contain endpoints,
            # credentials, prompts, or vendor response bodies. Do not expose.
            raise AiCapabilityUnavailable() from None
