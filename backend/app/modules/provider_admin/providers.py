"""Bounded provider adapters. Inventory discovery is separate from inference."""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import json
import logging
import math
import socket
import time
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit, urlunsplit

import httpx
import httpcore
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictStr, field_validator

from app.modules.integrations.ai_gateway import AiCapabilityUnavailable
from app.modules.integrations.chat_adapter import (
    ChatReply,
    ChatRequest,
    _parse_provider_content,
    _provisional_itinerary_system_prompt,
)

CAPABILITIES = frozenset({"chat", "vision", "embedding", "reranking"})
TEST_MAX_OUTPUT_TOKENS = 64
_MAX_RESPONSE_BYTES = 65_536
logger = logging.getLogger("ai_tourism.provider_admin.transport")
_TEST_PNG = base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
        "0000000b49444154789c636000020000050001a5f645400000000049454e44ae426082"
    )
).decode("ascii")
_TEST_IMAGE_URL = f"data:image/png;base64,{_TEST_PNG}"


class ProviderConfigurationError(ValueError):
    pass


class ProviderTransportError(RuntimeError):
    pass


class ProviderAuthenticationError(ProviderTransportError):
    pass


class ProviderCapabilityUnsupported(ProviderTransportError):
    pass


@dataclass(frozen=True, slots=True)
class ChatProviderConfig:
    provider_kind: str
    base_url: str
    model_id: str
    api_key: SecretStr | None = None
    timeout_seconds: int = 30
    max_tokens: int = 800
    capability: str = "chat"


_CHAT_REQUIREMENT_FIELDS = {
    "destination": "string",
    "origin": "string",
    "duration_days": "integer",
    "traveler_count": "integer",
    "budget_text": "string",
    "interest": "string",
    "soft_preference": "string",
    "relative_start_date": "integer",
    "travel_start": "string",
    "travel_end": "string",
    "hard_constraint": "string",
    "accessibility": "string",
    "travel_difficulty": "string",
    "weather_preference": "string",
    "local_cuisine": "string",
}

_TRAVELER_CHAT_SYSTEM_PROMPT = """
You are Rahgard's structured travel-intake assistant. Read the LATEST user message carefully and return the required JSON object.
Use only facts explicitly stated in that latest message. Conversation history and reviewed profile are context only; never copy an old value as if it were stated now. Never invent dates, locations, duration, currency, preferences, or safety facts. Use null for every absent or uncertain field and an empty array for ambiguous_requirements unless the current wording genuinely supports multiple explicit locations.

For every non-null requirement, requirement_evidence for the same key MUST contain the exact shortest source phrase copied from the current message. Do not translate, normalize, paraphrase, or combine separate spans. If you cannot quote a phrase exactly, return null for that requirement. `reply` and `clarification` must use the requested locale.

Field meanings:
- origin is where the traveler starts; destination is where they intend to visit. In Persian/Arabic/English route wording equivalent to "from X ... go/travel to Y", use X as origin and Y as destination, even if the destination follows a future-tense verb.
- duration_days is length of stay. A phrase such as "for five days" / "برای پنج روز" is duration.
- relative_start_date is departure timing as an integer offset from the supplied traveler-local reference date: امروز=0, فردا=1, پس‌فردا/پس فردا=2, سه روز دیگر/دیگه=3. English equivalents are today=0, tomorrow=1, day after tomorrow=2, three days from now=3. In particular, «از پس‌فردا» means offset 2. Quote only the relative departure phrase. Never interpret this as duration or an end date.
- traveler_count is the explicit number of people traveling, not a nearby budget or duration number.
- budget_text is the exact phrase that states an amount and scale. Currency may be omitted; do not infer it. Persian number words/digits are valid.
- interest, soft_preference, hard_constraint, accessibility, travel_difficulty, weather_preference, and local_cuisine are separate categories. Preserve safety/access needs and prohibitions as hard constraints, never soft preferences. Each non-null value must be supported by its own exact phrase. For `interest`, preserve every explicitly requested interest in the same exact source span, including conjunctions; e.g. «جاهای تاریخی و باغ‌ها» must not be shortened to only «جاهای تاریخی».
- travel_start and travel_end are a pair of explicit Gregorian ISO dates only. Do not convert Jalali dates or infer an end date from duration.

Preserve all explicit facts in the message, including facts embedded in conversational or informal phrasing. If a correction is stated in the latest message, extract the corrected value and quote the correction phrase. Ask a concise clarification only for genuinely missing or ambiguous information. Any itinerary must contain only proposed stop names, use role=model_proposed, and be marked provisional_unverified; never claim hours, prices, accessibility, routes, or other unverified facts.
""".strip()


def _lm_studio_chat_response_format() -> dict[str, object]:
    """Return an explicit LM Studio JSON Schema for the traveler contract.

    The schema names each accepted requirement. A generic object schema caused
    small local models to invent keys, while the adapter correctly discarded
    those keys and ultimately turned an otherwise successful inference into a
    503. Values remain untrusted suggestions and pass the existing evidence
    and domain validation after parsing.
    """
    # Strict structured output must require a decision for every field. A
    # merely optional object schema allows an empty `requirements` object even
    # when the current message contains an explicit trip request. Nullable
    # values make absence explicit without asking the model to invent facts.
    requirement_properties = {
        name: {"type": [kind, "null"]} for name, kind in _CHAT_REQUIREMENT_FIELDS.items()
    }
    evidence_properties = {
        name: {"type": ["string", "null"]} for name in _CHAT_REQUIREMENT_FIELDS
    }
    nullable_itinerary = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["provisional_unverified"]},
            "days": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "day_number": {"type": "integer"},
                        "stops": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "role": {"type": "string", "enum": ["model_proposed"]},
                                },
                                "required": ["name", "role"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["day_number", "stops"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["status", "days"],
        "additionalProperties": False,
    }
    schema = {
        "type": "object",
        "properties": {
            "reply": {"type": "string"},
            "requirements": {
                "type": "object",
                "properties": requirement_properties,
                "required": list(_CHAT_REQUIREMENT_FIELDS),
                "additionalProperties": False,
            },
            "requirement_evidence": {
                "type": "object",
                "properties": evidence_properties,
                "required": list(_CHAT_REQUIREMENT_FIELDS),
                "additionalProperties": False,
            },
            "ambiguous_requirements": {
                "type": "object",
                "properties": {
                    "origin": {"type": ["array", "null"], "items": {"type": "string"}},
                    "destination": {"type": ["array", "null"], "items": {"type": "string"}},
                },
                "required": ["origin", "destination"],
                "additionalProperties": False,
            },
            "clarification": {"type": ["string", "null"]},
            "provisional_itinerary": {
                "anyOf": [nullable_itinerary, {"type": "null"}],
            },
        },
        "required": [
            "reply", "requirements", "requirement_evidence", "ambiguous_requirements",
            "clarification", "provisional_itinerary",
        ],
        "additionalProperties": False,
    }
    return {
        "type": "json_schema",
        "json_schema": {"name": "rahgard_traveler_turn", "strict": True, "schema": schema},
    }


def _lm_studio_itinerary_response_format(day_count: int) -> dict[str, object]:
    """Use a compact output schema for itinerary generation, separate from intake."""
    day_numbers = list(range(1, day_count + 1))
    schema = {
        "type": "object",
        "properties": {
            "reply": {"type": "string", "maxLength": 160},
            "provisional_itinerary": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["provisional_unverified"]},
                    "days": {
                        "type": "array",
                        "minItems": day_count,
                        "maxItems": day_count,
                        "items": {
                            "type": "object",
                            "properties": {
                                "day_number": {"type": "integer", "enum": day_numbers},
                                "stops": {
                                    "type": "array",
                                    "minItems": 1,
                                    "maxItems": 1,
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string", "minLength": 1, "maxLength": 60},
                                            "role": {"type": "string", "enum": ["model_proposed"]},
                                        },
                                        "required": ["name", "role"],
                                        "additionalProperties": False,
                                    },
                                },
                            },
                            "required": ["day_number", "stops"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["status", "days"],
                "additionalProperties": False,
            },
        },
        "required": ["reply", "provisional_itinerary"],
        "additionalProperties": False,
    }
    return {
        "type": "json_schema",
        "json_schema": {"name": "rahgard_provisional_itinerary", "strict": True, "schema": schema},
    }


class EmbeddingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    input: StrictStr = Field(min_length=1, max_length=8192)


class EmbeddingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    embedding: tuple[float, ...] = Field(min_length=1, max_length=8192)

    @field_validator("embedding")
    @classmethod
    def finite(cls, value):
        if any(not math.isfinite(item) for item in value):
            raise ValueError("Embedding must be finite")
        return value


class VisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    prompt: StrictStr = Field(min_length=1, max_length=2000)
    image_data_url: StrictStr = Field(min_length=32, max_length=2_800_000)

    @field_validator("image_data_url")
    @classmethod
    def bounded_png(cls, value: str) -> str:
        prefix = "data:image/png;base64,"
        if not value.startswith(prefix):
            raise ValueError("Only PNG data URLs are supported")
        try:
            decoded = base64.b64decode(value[len(prefix) :], validate=True)
        except (ValueError, TypeError):
            raise ValueError("Invalid image data") from None
        if not 8 <= len(decoded) <= 2_000_000:
            raise ValueError("Image size is outside supported bounds")
        return value


class VisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    text: StrictStr = Field(min_length=1, max_length=4000)


class RerankingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    query: StrictStr = Field(min_length=1, max_length=2000)
    documents: tuple[StrictStr, ...] = Field(min_length=1, max_length=50)

    @field_validator("documents")
    @classmethod
    def bounded_docs(cls, value):
        if any(not text.strip() or len(text) > 4000 for text in value):
            raise ValueError("Reranking documents are outside bounds")
        return value


class RerankingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    scores: tuple[float, ...] = Field(min_length=1, max_length=50)

    @field_validator("scores")
    @classmethod
    def finite(cls, value):
        if any(not math.isfinite(item) for item in value):
            raise ValueError("Reranking scores must be finite")
        return value


class ModelEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(min_length=1, max_length=160)


class ModelList(BaseModel):
    model_config = ConfigDict(extra="ignore")
    data: list[ModelEntry] = Field(max_length=200)


async def _read_bounded(response: httpx.Response) -> bytes:
    output = bytearray()
    async for chunk in response.aiter_bytes():
        output.extend(chunk)
        if len(output) > _MAX_RESPONSE_BYTES:
            raise ProviderTransportError("Provider response was too large")
    return bytes(output)


def validate_provider_base_config(
    provider_kind: str, base_url: str, api_key: SecretStr | None
) -> str:
    """Validate the current approved origins without requiring a Chat binding."""
    parsed = urlsplit(base_url)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ProviderConfigurationError("Provider URL is not allowed")
    if provider_kind == "lm_studio":
        if parsed.scheme != "http" or not parsed.hostname or parsed.port is None:
            raise ProviderConfigurationError(
                "LM Studio must use a numeric loopback URL and explicit port"
            )
        try:
            if not ipaddress.ip_address(parsed.hostname).is_loopback:
                raise ProviderConfigurationError("LM Studio URL must be numeric loopback")
        except ValueError:
            raise ProviderConfigurationError("LM Studio URL must be numeric loopback") from None
        if parsed.path.rstrip("/") not in {"", "/v1"}:
            raise ProviderConfigurationError("LM Studio base path is unsupported")
    elif provider_kind == "openai_compatible":
        # Do not treat the OpenAI-compatible label as approval for arbitrary
        # hosts. The owner account host remains explicitly pinned until its
        # actual service contract is verified.
        if (
            parsed.scheme != "https"
            or parsed.hostname != "api.gapgpt.app"
            or parsed.port not in (None, 443)
            or parsed.path.rstrip("/") != "/v1"
        ):
            raise ProviderConfigurationError("Remote provider URL is not approved")
        if api_key is None or not api_key.get_secret_value().strip():
            raise ProviderConfigurationError("Remote provider API key is required")
    else:
        raise ProviderConfigurationError("Provider type is unsupported")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", ""))


def validate_chat_config(config: ChatProviderConfig) -> str:
    if not 1 <= config.timeout_seconds <= 60 or not 1 <= config.max_tokens <= 4096:
        raise ProviderConfigurationError("Provider limits are outside supported bounds")
    if (
        not config.model_id
        or len(config.model_id) > 160
        or any(ord(char) < 32 or ord(char) == 127 for char in config.model_id)
    ):
        raise ProviderConfigurationError("Model identifier is invalid")
    if config.capability not in CAPABILITIES:
        raise ProviderConfigurationError("Capability is unsupported")
    return validate_provider_base_config(config.provider_kind, config.base_url, config.api_key)


def _resolve_public_gapgpt_addresses(host: str) -> tuple[str, ...]:
    try:
        addresses = {
            ipaddress.ip_address(item[4][0])
            for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        }
    except OSError:
        raise ProviderTransportError("Provider is unavailable") from None
    if not addresses or any(not address.is_global for address in addresses):
        raise ProviderConfigurationError("Provider endpoint resolution is not allowed")
    return tuple(sorted(str(address) for address in addresses))


class _PinnedGapGptBackend(httpcore.AnyIOBackend):
    """Pin TCP to the validated IP while retaining hostname TLS verification."""

    def __init__(self, addresses: tuple[str, ...]):
        super().__init__()
        if not addresses:
            raise ProviderConfigurationError("Provider endpoint resolution is not allowed")
        self._address = addresses[0]

    def pinned_host(self, host: str, port: int) -> str:
        return (
            self._address if host.lower().rstrip(".") == "api.gapgpt.app" and port == 443 else host
        )

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        return await super().connect_tcp(
            self.pinned_host(host, port), port, timeout, local_address, socket_options
        )


def _pinned_gapgpt_transport(addresses: tuple[str, ...]) -> httpx.AsyncHTTPTransport:
    # HTTPX has no public resolver hook. Build its standard httpcore pool with
    # a pinned backend; TLS still verifies the original request hostname.
    transport = httpx.AsyncHTTPTransport(trust_env=False, retries=0)
    transport._pool = httpcore.AsyncConnectionPool(
        ssl_context=httpx.create_ssl_context(verify=True),
        network_backend=_PinnedGapGptBackend(addresses),
        retries=0,
    )
    return transport


class OpenAiCompatibleProviderAdapter:
    def __init__(
        self, config: ChatProviderConfig, *, transport: httpx.AsyncBaseTransport | None = None
    ):
        self.config = config
        self.base_url = validate_chat_config(config)
        self.transport = transport

    async def discover_models(self) -> tuple[str, ...]:
        status, content = await self._request("GET", f"{self.base_url}/models")
        if status in {401, 403}:
            raise ProviderAuthenticationError("Provider authentication was rejected")
        if status != 200:
            raise ProviderTransportError("Provider is unavailable")
        try:
            payload = ModelList.model_validate(json.loads(content))
            return tuple(dict.fromkeys(item.id for item in payload.data))
        except Exception:
            raise ProviderTransportError("Provider returned invalid model inventory") from None

    def capability_support(self) -> dict[str, str]:
        if self.config.provider_kind == "lm_studio":
            # Official LM Studio OpenAI compatibility docs cover these API
            # surfaces; inference tests still determine model-specific support.
            return {
                "chat": "supported",
                "vision": "supported",
                "embedding": "supported",
                "reranking": "unknown",
            }
        return {cap: "unknown" for cap in sorted(CAPABILITIES)}

    async def test_connection(self) -> dict[str, str | int | bool]:
        """Backward-compatible non-generative model-list test for Chat."""
        started = time.perf_counter()
        models = await self.discover_models()
        return {
            "ok": self.config.model_id in models,
            "model_available": self.config.model_id in models,
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "capability": "chat",
        }

    async def test_capability(
        self,
        capability: str,
        model_id: str,
        *,
        test_kind: Literal["discovery", "inference"],
        max_output_tokens: int = 32,
    ) -> dict[str, str | int | bool]:
        if capability not in CAPABILITIES:
            raise ProviderCapabilityUnsupported("Capability is unsupported")
        if model_id != self.config.model_id:
            raise ProviderConfigurationError("Test model differs from selected revision")
        if (
            type(max_output_tokens) is not int
            or not 1 <= max_output_tokens <= TEST_MAX_OUTPUT_TOKENS
        ):
            raise ProviderConfigurationError("Inference test token bound is invalid")
        started = time.perf_counter()
        models = await self.discover_models()
        selected = model_id in models
        result: dict[str, str | int | bool] = {
            "success": False,
            "status": "model_not_found" if not selected else "models_catalog_reachable",
            "latency_ms": round((time.perf_counter() - started) * 1000),
            "capability": capability,
            "model_id": model_id,
            "test_kind": test_kind,
            "models_catalog_reachable": True,
            "model_selected": selected,
            "capability_verified": False,
            "actual_inference_passed": False,
        }
        if not selected:
            return result
        if test_kind == "discovery":
            if self.capability_support()[capability] == "unsupported":
                result["status"] = "unsupported"
            return result
        await self._run_fixed_inference(capability, max_output_tokens)
        result.update(
            {
                "success": True,
                "status": "inference_passed",
                "latency_ms": round((time.perf_counter() - started) * 1000),
                "capability_verified": True,
                "actual_inference_passed": True,
            }
        )
        return result

    async def invoke(
        self, request: ChatRequest | VisionRequest | EmbeddingRequest | RerankingRequest
    ):
        cap = self.config.capability
        if cap == "chat" and isinstance(request, ChatRequest):
            return await self._invoke_chat(request)
        if cap == "vision" and isinstance(request, VisionRequest):
            return await self._invoke_vision(request)
        if cap == "embedding" and isinstance(request, EmbeddingRequest):
            return await self._invoke_embedding(request)
        if cap == "reranking" and isinstance(request, RerankingRequest):
            return await self._invoke_reranking(request)
        raise AiCapabilityUnavailable()

    async def _invoke_chat(self, request: ChatRequest) -> ChatReply:
        itinerary_days = request.provisional_itinerary_days
        system_prompt = (
            _provisional_itinerary_system_prompt(itinerary_days)
            if itinerary_days is not None
            else f"{_TRAVELER_CHAT_SYSTEM_PROMPT}\nRequested locale: {request.locale}."
        )
        messages = [{"role": "system", "content": system_prompt}]
        if itinerary_days is None:
            messages.extend({"role": item.role, "content": item.content} for item in request.history)
        context = {
            "traveler_timezone": request.traveler_timezone,
            "traveler_reference_date": (
                request.traveler_reference_date.isoformat() if request.traveler_reference_date else None
            ),
            "reviewed_profile": request.reviewed_profile,
        }
        messages.append({"role": "system", "content": "Context only: " + json.dumps(context, ensure_ascii=False)})
        if itinerary_days is None:
            messages.append({"role": "user", "content": request.text})
        else:
            messages.append({
                "role": "user",
                "content": json.dumps({
                    "locale": request.locale,
                    "requested_day_count": itinerary_days,
                }, ensure_ascii=False),
            })
        body: dict[str, object] = {
            "model": self.config.model_id,
            "max_tokens": min(self.config.max_tokens, 4096),
            "temperature": 0,
            "messages": messages,
            "stream": False,
        }
        if self.config.provider_kind == "lm_studio":
            body["response_format"] = (
                _lm_studio_itinerary_response_format(request.provisional_itinerary_days)
                if request.provisional_itinerary_days is not None
                else _lm_studio_chat_response_format()
            )
        stage = "request"
        try:
            response_body = await self._post_json("/chat/completions", body)
            stage = "provider_response_validation"
            content = self._chat_text(response_body)
            stage = "traveler_reply_validation"
            return _parse_provider_content(
                content,
                locale=request.locale,
                expected_itinerary_days=request.provisional_itinerary_days,
            )
        except Exception as error:
            logger.warning(
                "provider.chat_unavailable provider_kind=%s stage=%s error_type=%s",
                self.config.provider_kind, stage, type(error).__name__,
            )
            raise AiCapabilityUnavailable() from None

    async def _invoke_vision(self, request: VisionRequest) -> VisionResponse:
        validated = VisionRequest.model_validate(request)
        body = await self._post_json(
            "/chat/completions",
            {
                "model": self.config.model_id,
                "max_tokens": self.config.max_tokens,
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": validated.prompt},
                            {"type": "image_url", "image_url": {"url": validated.image_data_url}},
                        ],
                    }
                ],
            },
        )
        return VisionResponse(text=self._chat_text(body))

    async def _invoke_embedding(self, request: EmbeddingRequest) -> EmbeddingResponse:
        validated = EmbeddingRequest.model_validate(request)
        body = await self._post_json(
            "/embeddings",
            {
                "model": self.config.model_id,
                "input": validated.input,
            },
        )
        try:
            data = body["data"]
            if not isinstance(data, list) or len(data) != 1:
                raise ValueError
            return EmbeddingResponse(embedding=tuple(data[0]["embedding"]))
        except Exception:
            raise ProviderTransportError("Provider embedding response was invalid") from None

    async def _invoke_reranking(self, request: RerankingRequest) -> RerankingResponse:
        validated = RerankingRequest.model_validate(request)
        body = await self._post_json(
            "/rerank",
            {
                "model": self.config.model_id,
                "query": validated.query,
                "documents": list(validated.documents),
            },
            capability_probe=True,
        )
        try:
            rows = body.get("results", body.get("data"))
            if not isinstance(rows, list) or len(rows) != len(validated.documents):
                raise ValueError
            scores: list[float | None] = [None] * len(rows)
            for row in rows:
                index = row["index"]
                score = row.get("relevance_score", row.get("score"))
                if (
                    type(index) is not int
                    or not 0 <= index < len(scores)
                    or scores[index] is not None
                ):
                    raise ValueError
                if type(score) not in (int, float) or not math.isfinite(score):
                    raise ValueError
                scores[index] = float(score)
            if any(score is None for score in scores):
                raise ValueError
            return RerankingResponse(scores=tuple(scores))
        except Exception:
            raise ProviderTransportError("Provider reranking response was invalid") from None

    async def _run_fixed_inference(self, capability: str, max_output_tokens: int) -> None:
        if capability == "chat":
            body = await self._post_json(
                "/chat/completions",
                {
                    "model": self.config.model_id,
                    "max_tokens": max_output_tokens,
                    "stream": False,
                    "messages": [{"role": "user", "content": "Reply with the word READY."}],
                },
                capability_probe=True,
            )
            self._chat_text(body)
            return
        if capability == "vision":
            body = await self._post_json(
                "/chat/completions",
                {
                    "model": self.config.model_id,
                    "max_tokens": max_output_tokens,
                    "stream": False,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Describe this test image in one short phrase.",
                                },
                                {"type": "image_url", "image_url": {"url": _TEST_IMAGE_URL}},
                            ],
                        }
                    ],
                },
                capability_probe=True,
            )
            self._chat_text(body)
            return
        if capability == "embedding":
            body = await self._post_json(
                "/embeddings",
                {
                    "model": self.config.model_id,
                    "input": "Rahgard capability verification.",
                },
                capability_probe=True,
            )
            try:
                data = body["data"]
                if not isinstance(data, list) or len(data) != 1:
                    raise ValueError
                EmbeddingResponse(embedding=tuple(data[0]["embedding"]))
                return
            except Exception:
                raise ProviderTransportError("Provider embedding response was invalid") from None
        if capability == "reranking":
            await self._invoke_reranking(
                RerankingRequest(
                    query="Rahgard capability test",
                    documents=("test candidate one", "test candidate two"),
                )
            )
            return
        raise ProviderCapabilityUnsupported("Provider capability is unsupported")

    async def _post_json(self, path: str, payload: dict, *, capability_probe: bool = False) -> dict:
        status, raw = await self._request("POST", f"{self.base_url}{path}", json=payload)
        if status in {401, 403}:
            raise ProviderAuthenticationError("Provider authentication was rejected")
        if capability_probe and status in {404, 405, 415, 422, 501}:
            raise ProviderCapabilityUnsupported("Provider capability endpoint is unsupported")
        if capability_probe and status == 400:
            raise ProviderCapabilityUnsupported("Selected model rejected this capability")
        if status != 200:
            logger.warning(
                "provider.http_error provider_kind=%s status=%s capability_probe=%s",
                self.config.provider_kind, status, capability_probe,
            )
            raise ProviderTransportError("Provider is unavailable")
        try:
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError
            return value
        except Exception:
            raise ProviderTransportError("Provider returned invalid JSON") from None

    async def _request(
        self, method: str, url: str, *, json: dict | None = None
    ) -> tuple[int, bytes]:
        transport = self.transport
        if self.config.provider_kind == "openai_compatible" and transport is None:
            addresses = await asyncio.to_thread(_resolve_public_gapgpt_addresses, "api.gapgpt.app")
            transport = _pinned_gapgpt_transport(addresses)
        # A local model can take longer than a hosted endpoint while emitting
        # the strict structured intake contract. LM Studio URLs are validated
        # as numeric loopback only, and the provider profile itself is already
        # capped at 60 seconds; use that existing hard ceiling rather than
        # turning a normal local generation into a premature 503 at the
        # default 30-second profile timeout. Remote providers continue to use
        # their explicitly configured timeout unchanged.
        request_timeout = (
            60 if self.config.provider_kind == "lm_studio"
            else self.config.timeout_seconds
        )
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(request_timeout),
                follow_redirects=False,
                trust_env=False,
                transport=transport,
            ) as client:
                async with asyncio.timeout(request_timeout + 2):
                    async with client.stream(
                        method, url, headers=self._headers(), json=json
                    ) as response:
                        return response.status_code, await _read_bounded(response)
        except ProviderTransportError:
            raise
        except Exception as error:
            logger.warning(
                "provider.request_failed provider_kind=%s error_type=%s",
                self.config.provider_kind, type(error).__name__,
            )
            raise ProviderTransportError("Provider is unavailable") from None

    @staticmethod
    def _chat_text(body: dict) -> str:
        try:
            choices = body["choices"]
            if not isinstance(choices, list) or len(choices) != 1:
                raise ValueError
            choice = choices[0]
            # A token-limit finish may contain plausible partial text but can
            # never satisfy the structured contract. Do not parse it as a
            # complete assistant turn or trigger an implicit retry.
            if choice.get("finish_reason") != "stop":
                raise ValueError
            text = choice["message"]["content"]
            # Structured itinerary replies can exceed the ordinary short-chat
            # size. Keep this aligned with the parser's 8 KiB contract.
            if not isinstance(text, str) or not 1 <= len(text) <= 8192:
                raise ValueError
            return text
        except Exception:
            raise ProviderTransportError("Provider inference response was invalid") from None

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.config.api_key is not None:
            headers["Authorization"] = f"Bearer {self.config.api_key.get_secret_value()}"
        return headers


class OpenAiCompatibleChatAdapter(OpenAiCompatibleProviderAdapter):
    """Backwards-compatible Chat adapter name used by the traveler runtime."""

    pass
