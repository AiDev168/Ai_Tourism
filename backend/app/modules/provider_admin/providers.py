"""Small bounded OpenAI-compatible adapter for the admin-managed Chat route.

Only the GapGPT API host and an explicit numeric loopback LM Studio
host are accepted. Model inventory is obtained from the actual /models API;
capabilities other than Chat remain unsupported until tested adapters exist.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import time
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.modules.integrations.ai_gateway import AiCapabilityUnavailable
from app.modules.integrations.chat_adapter import ChatReply, ChatRequest, _parse_provider_content


class ProviderConfigurationError(ValueError):
    pass


class ProviderTransportError(RuntimeError):
    pass


class ProviderAuthenticationError(ProviderTransportError):
    """The configured bearer credential was rejected by the upstream API."""


@dataclass(frozen=True, slots=True)
class ChatProviderConfig:
    provider_kind: str
    base_url: str
    model_id: str
    api_key: SecretStr | None = None
    timeout_seconds: int = 20
    max_tokens: int = 800


class ModelList(BaseModel):
    model_config = ConfigDict(extra="ignore")
    data: list[dict] = Field(max_length=200)


class OpenAiChatResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    choices: list[dict] = Field(min_length=1, max_length=1)


async def _read_bounded(response: httpx.Response, *, maximum: int = 65_536) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in response.aiter_bytes():
        size += len(chunk)
        if size > maximum:
            raise ProviderTransportError("Provider response was too large")
        chunks.append(chunk)
    return b"".join(chunks)


def validate_chat_config(config: ChatProviderConfig) -> str:
    if not 1 <= config.timeout_seconds <= 60 or not 1 <= config.max_tokens <= 4096:
        raise ProviderConfigurationError("Provider limits are outside the supported range")
    parsed = urlsplit(config.base_url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ProviderConfigurationError("Provider URL is not allowed")
    if config.provider_kind == "lm_studio":
        if parsed.scheme != "http" or not parsed.hostname or parsed.port is None:
            raise ProviderConfigurationError(
                "LM Studio must use an explicit loopback HTTP URL and port"
            )
        try:
            if not ipaddress.ip_address(parsed.hostname).is_loopback:
                raise ProviderConfigurationError("LM Studio URL must be numeric loopback")
        except ValueError:
            raise ProviderConfigurationError("LM Studio URL must be numeric loopback") from None
        if parsed.path.rstrip("/") not in {"", "/v1"}:
            raise ProviderConfigurationError("LM Studio base path is not supported")
    elif config.provider_kind == "openai_compatible":
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.gapgpt.app"
            or parsed.port not in (None, 443)
            or parsed.path.rstrip("/") != "/v1"
        ):
            raise ProviderConfigurationError("GapGPT URL must match its HTTPS API endpoint")
        if config.api_key is None or not config.api_key.get_secret_value().strip():
            raise ProviderConfigurationError("GapGPT API key is required")
    else:
        raise ProviderConfigurationError("Provider type is unsupported")
    if (
        not config.model_id
        or len(config.model_id) > 160
        or any(ord(c) < 32 for c in config.model_id)
    ):
        raise ProviderConfigurationError("Model identifier is invalid")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def _assert_public_gapgpt_resolution(host: str) -> None:
    try:
        addresses = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        }
    except OSError:
        raise ProviderTransportError("Provider is unavailable") from None
    if not addresses or any(not address.is_global for address in addresses):
        raise ProviderConfigurationError("Provider endpoint resolution is not allowed")


class OpenAiCompatibleChatAdapter:
    """Explicitly configured, one-call adapter; no retries or implicit fallback."""

    def __init__(
        self, config: ChatProviderConfig, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self.config = config
        self.base_url = validate_chat_config(config)
        self.transport = transport

    async def discover_models(self) -> tuple[str, ...]:
        if self.config.provider_kind == "openai_compatible":
            await asyncio.to_thread(_assert_public_gapgpt_resolution, "api.gapgpt.app")
        headers = self._headers()
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout_seconds),
                follow_redirects=False,
                trust_env=False,
                transport=self.transport,
            ) as client:
                async with asyncio.timeout(self.config.timeout_seconds + 2):
                    async with client.stream(
                        "GET", f"{self.base_url}/models", headers=headers
                    ) as response:
                        if response.status_code in {401, 403}:
                            raise ProviderAuthenticationError(
                                "Provider authentication was rejected"
                            )
                        if response.status_code != 200:
                            raise ProviderTransportError("Provider is unavailable")
                        content = await _read_bounded(response)
            parsed = ModelList.model_validate(json.loads(content))
            ids = tuple(
                dict.fromkeys(
                    item["id"]
                    for item in parsed.data
                    if isinstance(item, dict)
                    and isinstance(item.get("id"), str)
                    and 1 <= len(item["id"]) <= 160
                    and not any(ord(c) < 32 for c in item["id"])
                )
            )
            return ids
        except ProviderTransportError:
            raise
        except Exception:
            raise ProviderTransportError(
                "Provider is unavailable or returned an invalid response"
            ) from None

    async def test_connection(self) -> dict[str, str | int | bool]:
        started = time.perf_counter()
        models = await self.discover_models()
        return {
            "ok": self.config.model_id in models,
            "model_available": self.config.model_id in models,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "capability": "chat",
        }

    async def invoke(self, request: ChatRequest) -> ChatReply:
        if self.config.provider_kind == "openai_compatible":
            await asyncio.to_thread(_assert_public_gapgpt_resolution, "api.gapgpt.app")
        messages = [
            {
                "role": "system",
                "content": (
                    "Return a JSON object with reply, requirements, requirement_evidence, clarification. "
                    "Only extract facts explicitly stated in the current user message. Preserve exact wording "
                    "in evidence. Requirements are untrusted suggestions requiring traveler review. Do not "
                    "invent or confirm travel facts. Reply in the requested locale."
                ),
            }
        ]
        messages.extend({"role": item.role, "content": item.content} for item in request.history)
        messages.append(
            {
                "role": "user",
                "content": json.dumps(
                    {"locale": request.locale, "text": request.text},
                    ensure_ascii=False,
                ),
            }
        )
        payload = {
            "model": self.config.model_id,
            "max_tokens": self.config.max_tokens,
            "messages": messages,
            "stream": False,
        }
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout_seconds),
                follow_redirects=False,
                trust_env=False,
                transport=self.transport,
            ) as client:
                async with asyncio.timeout(self.config.timeout_seconds + 2):
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers=self._headers(),
                    ) as response:
                        if response.status_code in {401, 403}:
                            raise ProviderAuthenticationError(
                                "Provider authentication was rejected"
                            )
                        if response.status_code != 200:
                            raise ProviderTransportError("Provider is unavailable")
                        content = await _read_bounded(response)
            if len(content) > 65536:
                raise ProviderTransportError("Provider request failed")
            envelope = OpenAiChatResponse.model_validate(json.loads(content))
            item = envelope.choices[0]
            if item.get("finish_reason") not in {"stop", "length"}:
                raise ProviderTransportError("Provider response was incomplete")
            message = item.get("message")
            if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                raise ProviderTransportError("Provider response was invalid")
            return _parse_provider_content(message["content"])
        except Exception:
            raise AiCapabilityUnavailable() from None

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.config.api_key is not None:
            headers["Authorization"] = f"Bearer {self.config.api_key.get_secret_value()}"
        return headers
