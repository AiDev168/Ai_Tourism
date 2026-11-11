"""Dynamic Chat adapter backed by the active versioned provider route."""

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
from app.modules.provider_admin.providers import OpenAiCompatibleChatAdapter
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
    if settings.ai_provider_vault_dir is None:
        raise AiCapabilityUnavailable()
    return AiProviderGateway(
        AiCapability.CHAT,
        AdminManagedChatAdapter(
            provider_registry(settings),
            DpapiSecretVault(settings.ai_provider_vault_dir),
        ),
    )


class AdminManagedChatAdapter:
    """Resolve an immutable active snapshot for each call, enabling live switches."""

    def __init__(self, registry: ProviderRegistry, vault: DpapiSecretVault, *, adapter_factory=None) -> None:
        self.registry = registry
        self.vault = vault
        self.adapter_factory = adapter_factory or (lambda config: OpenAiCompatibleChatAdapter(config))
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    async def invoke(self, request: ChatRequest) -> ChatReply:
        snapshot = None
        started = perf_counter()
        try:
            snapshot = await asyncio.to_thread(self.registry.active_snapshot, "chat")
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

    async def _invoke_explicit_fallback(self, request: ChatRequest, started: float) -> ChatReply:
        """Try only the administrator's explicit, validated fallback order."""
        policy = await asyncio.to_thread(self.registry.get_fallback, "chat")
        if not policy["enabled"]:
            raise AiCapabilityUnavailable()
        for revision_id in policy["ordered_revision_ids"]:
            try:
                candidate = await asyncio.to_thread(
                    self.registry.validated_snapshot, "chat", revision_id
                )
                result = await self._invoke_snapshot(candidate, request)
            except Exception:
                await self._record(revision_id, "unavailable", started)
                continue
            await self._record(revision_id, "success", started)
            return result
        raise AiCapabilityUnavailable()

    async def _invoke_snapshot(self, snapshot, request: ChatRequest) -> ChatReply:
        if snapshot.revision_id is None or snapshot.config is None:
            raise AiCapabilityUnavailable()
        limit = int(snapshot.config.get("concurrency_limit", 1))
        if not 1 <= limit <= 10:
            raise AiCapabilityUnavailable()
        semaphore = self._semaphores.setdefault(
            str(snapshot.revision_id), asyncio.Semaphore(limit)
        )
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
                capability="chat",
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
        binding = config.get("capabilities", {}).get("chat")
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
        )
