"""Dynamic capability adapters backed by active versioned provider routes."""

from __future__ import annotations

import asyncio
from time import perf_counter

import psycopg
from psycopg.rows import dict_row

from app.core.config import Settings
from app.modules.integrations.ai_gateway import (
    AiCapability,
    AiCapabilityUnavailable,
    AiProviderGateway,
)
from app.modules.integrations.chat_adapter import ChatReply, ChatRequest
from app.modules.provider_admin.providers import OpenAiCompatibleProviderAdapter
from app.modules.provider_admin.registry import ProviderRegistry
from app.modules.provider_admin.vault import DpapiSecretVault


def provider_registry(settings: Settings) -> ProviderRegistry:
    def connect():
        return psycopg.connect(
            host=settings.database_host,
            port=settings.database_port,
            dbname=settings.database_name,
            user=settings.database_user,
            password=settings.database_password.get_secret_value(),
            connect_timeout=settings.database_connect_timeout_seconds,
            application_name="rahgard-ai-provider-runtime",
            row_factory=dict_row,
        )

    return ProviderRegistry(connect)


def make_admin_chat_gateway(settings: Settings) -> AiProviderGateway[ChatRequest, ChatReply]:
    return make_admin_capability_gateway(settings, AiCapability.CHAT)


def make_admin_capability_gateway(settings: Settings, capability: AiCapability):
    """Build the requested provider-neutral route; each call rereads its active revision."""
    if settings.ai_provider_vault_dir is None:
        raise AiCapabilityUnavailable()
    return AiProviderGateway(
        capability,
        AdminManagedCapabilityAdapter(
            provider_registry(settings),
            DpapiSecretVault(settings.ai_provider_vault_dir),
            capability,
        ),
    )


class AdminManagedCapabilityAdapter:
    """Resolve one immutable active snapshot for each capability invocation."""

    def __init__(
        self,
        registry: ProviderRegistry,
        vault: DpapiSecretVault,
        capability: AiCapability = AiCapability.CHAT,
        *,
        adapter_factory=None,
    ) -> None:
        self.registry = registry
        self.vault = vault
        self.capability = capability
        self.adapter_factory = adapter_factory or (
            lambda config: OpenAiCompatibleProviderAdapter(config)
        )
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    async def invoke(self, request):
        snapshot = None
        started = perf_counter()
        try:
            capability = self.capability.value
            snapshot = await asyncio.to_thread(self.registry.active_snapshot, capability)
            if snapshot.revision_id is not None and snapshot.config is not None:
                try:
                    result = await self._invoke_snapshot(snapshot, request)
                except AiCapabilityUnavailable:
                    await self._record(snapshot.revision_id, "unavailable", started)
                    return await self._invoke_explicit_fallback(request, started)
                await self._record(snapshot.revision_id, "success", started)
                return result
            return await self._invoke_explicit_fallback(request, started)
        except Exception:
            raise AiCapabilityUnavailable() from None

    async def _invoke_explicit_fallback(self, request, started: float):
        """Try only this capability's administrator-approved fallback order."""
        capability = self.capability.value
        policy = await asyncio.to_thread(self.registry.get_fallback, capability)
        if not policy["enabled"]:
            raise AiCapabilityUnavailable()
        for revision_id in policy["ordered_revision_ids"]:
            try:
                candidate = await asyncio.to_thread(
                    self.registry.validated_snapshot, capability, revision_id
                )
                result = await self._invoke_snapshot(candidate, request)
            except Exception:
                await self._record(revision_id, "unavailable", started)
                continue
            await self._record(revision_id, "success", started)
            return result
        raise AiCapabilityUnavailable()

    async def _invoke_snapshot(self, snapshot, request):
        if snapshot.revision_id is None or snapshot.config is None:
            raise AiCapabilityUnavailable()
        capability = self.capability.value
        binding = snapshot.config.get("capabilities", {}).get(capability)
        if not isinstance(binding, dict) or not isinstance(binding.get("model_id"), str):
            raise AiCapabilityUnavailable()
        # Refuse an active pointer if its exact revision is no longer the most
        # recently capability-validated candidate. This preserves admin disable.
        eligible = await asyncio.to_thread(
            self.registry.validated_snapshot, capability, snapshot.revision_id
        )
        if eligible.revision_id != snapshot.revision_id:
            raise AiCapabilityUnavailable()
        limit = int(snapshot.config.get("concurrency_limit", 1))
        if not 1 <= limit <= 10:
            raise AiCapabilityUnavailable()
        semaphore = self._semaphores.setdefault(str(snapshot.revision_id), asyncio.Semaphore(limit))
        async with semaphore:
            try:
                return await self.adapter_factory(self._config(snapshot)).invoke(request)
            except AiCapabilityUnavailable:
                raise
            except Exception:
                raise AiCapabilityUnavailable() from None

    async def _record(self, revision_id, outcome: str, started: float) -> None:
        try:
            await asyncio.to_thread(
                self.registry.record_usage,
                capability=self.capability.value,
                revision_id=revision_id,
                outcome=outcome,
                latency_ms=round((perf_counter() - started) * 1000),
            )
        except Exception:
            # Usage logging must not make a successful provider call fail.
            pass

    def _config(self, snapshot):
        from pydantic import SecretStr

        from app.modules.provider_admin.providers import ChatProviderConfig

        config = snapshot.config
        capability = self.capability.value
        binding = config.get("capabilities", {}).get(capability)
        if not isinstance(binding, dict) or not isinstance(binding.get("model_id"), str):
            raise AiCapabilityUnavailable()
        api_key = None
        if snapshot.secret_ref:
            api_key = SecretStr(self.vault.get(snapshot.secret_ref).decode("utf-8"))
        return ChatProviderConfig(
            provider_kind=config["provider_kind"],
            base_url=config["base_url"],
            model_id=binding["model_id"],
            api_key=api_key,
            timeout_seconds=config.get("timeout_seconds", 20),
            max_tokens=binding.get("max_tokens", 800),
            capability=capability,
        )


class AdminManagedChatAdapter(AdminManagedCapabilityAdapter):
    """Backwards-compatible Chat runtime class."""

    def __init__(
        self, registry: ProviderRegistry, vault: DpapiSecretVault, *, adapter_factory=None
    ):
        super().__init__(registry, vault, AiCapability.CHAT, adapter_factory=adapter_factory)
