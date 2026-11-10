"""Thin async HTTP adapter for the owner's independently operated RAG API.

The adapter is disabled by default and never falls back to the structured
catalogue. Returned evidence is untrusted: callers must independently resolve
publication, revocation and identity against AI Tourism's approved views.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC
from typing import Literal
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.core.config import Settings
from app.modules.retrieval.contracts import (
    MAX_OWNER_HTTP_LIMIT,
    RetrievalAuthenticationFailed,
    RetrievalInvalidRequest,
    RetrievalPort,
    RetrievalRequest,
    RetrievalResponse,
    RetrievalSource,
    RetrievedEvidence,
    RetrievalUnavailable,
    validate_response_for_request,
)

OWNER_RAG_ENDPOINT = "v1/retrieve"
MAX_OWNER_RESPONSE_BYTES = 2_000_000
_REQUEST_ID_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"


class OwnerRagFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    canonical_entity_key: str | None = Field(default=None, min_length=1, max_length=240)


class OwnerRagRequestWire(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    request_id: str = Field(pattern=_REQUEST_ID_PATTERN)
    query: str = Field(min_length=1, max_length=2_000)
    locale: Literal["fa-IR", "en-US", "ar"]
    corpus: Literal["spatial_destinations", "culinary_knowledge"]
    limit: int = Field(strict=True, ge=1, le=MAX_OWNER_HTTP_LIMIT)
    filters: OwnerRagFilters
    as_of: str = Field(min_length=20, max_length=40)

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if not value.strip() or "\x00" in value:
            raise ValueError("query must be nonblank and contain no NUL")
        return value


class OwnerRagSourceWire(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_id: str = Field(min_length=1, max_length=240)
    source_name: str = Field(min_length=1, max_length=500)
    source_url: str = Field(min_length=1, max_length=2_048)
    source_role: str = Field(min_length=1, max_length=64)
    retrieved_at: str | None = Field(default=None, max_length=40)
    valid_from: str | None = Field(default=None, max_length=40)
    valid_until: str | None = Field(default=None, max_length=40)
    license: str | None = Field(default=None, max_length=500)

    @field_validator("source_url")
    @classmethod
    def require_https_without_credentials(cls, value: str) -> str:
        from urllib.parse import urlsplit

        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("source_url must be credential-free HTTPS")
        return value


class OwnerRagItemWire(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    evidence_id: str = Field(min_length=1, max_length=240)
    document_id: str = Field(min_length=1, max_length=240)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    text: str = Field(min_length=1, max_length=8_000)
    locale: Literal["fa-IR", "en-US", "ar"]
    corpus: Literal["spatial_destinations", "culinary_knowledge"]
    canonical_entity_key: str | None = Field(default=None, min_length=1, max_length=240)
    claim_key: str | None = Field(default=None, min_length=1, max_length=240)
    score: float | None = Field(default=None, strict=True, allow_inf_nan=False)
    sources: list[OwnerRagSourceWire] = Field(min_length=1, max_length=32)


class OwnerRagResponseWire(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_version: Literal["1.0.0"]
    request_id: str = Field(pattern=_REQUEST_ID_PATTERN)
    outcome: Literal["ok", "no_evidence", "unavailable", "invalid_request"]
    items: list[OwnerRagItemWire] = Field(max_length=MAX_OWNER_HTTP_LIMIT)
    corpus_version: str | None = Field(default=None, max_length=160)
    retrieval_version: str | None = Field(default=None, max_length=160)
    generated_at: str = Field(min_length=20, max_length=40)
    warnings: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("generated_at")
    @classmethod
    def validate_generated_at(cls, value: str) -> str:
        from datetime import datetime

        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_outcome_shape(self) -> OwnerRagResponseWire:
        if self.outcome == "ok" and not self.items:
            raise ValueError("ok requires evidence items")
        if self.outcome != "ok" and self.items:
            raise ValueError("non-ok outcomes must not carry evidence items")
        return self


def _utc_isoformat(value) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise RetrievalInvalidRequest()
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def serialize_owner_request(request: RetrievalRequest) -> OwnerRagRequestWire:
    """Build the exact owner request; refuse unsupported filters and limits."""

    if request.limit > MAX_OWNER_HTTP_LIMIT:
        raise RetrievalInvalidRequest()
    filters = request.filters
    unsupported_nonempty = (
        filters.destination_ids
        or filters.destination_keys
        or filters.city_names
        or filters.province_names
    )
    if unsupported_nonempty:
        raise RetrievalInvalidRequest()
    try:
        return OwnerRagRequestWire(
            request_id=str(request.request_id),
            query=request.query,
            locale=request.locale,
            corpus=request.corpus,
            limit=request.limit,
            filters=OwnerRagFilters(
                canonical_entity_key=filters.canonical_entity_key,
            ),
            as_of=_utc_isoformat(request.as_of),
        )
    except (ValidationError, ValueError, TypeError):
        raise RetrievalInvalidRequest() from None


def _parse_datetime(value: str | None):
    if value is None:
        return None
    from datetime import datetime

    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed


def map_owner_response(
    request: RetrievalRequest,
    value: object,
) -> RetrievalResponse:
    """Validate owner wire data and preserve only fields the wire actually has."""

    try:
        wire = OwnerRagResponseWire.model_validate(value)
        if wire.request_id != str(request.request_id) or len(wire.items) > request.limit:
            raise ValueError("response does not match request")
        if wire.outcome == "unavailable":
            raise RetrievalUnavailable()
        if wire.outcome == "invalid_request":
            raise RetrievalInvalidRequest()
        items: list[RetrievedEvidence] = []
        seen_ids: set[str] = set()
        for item in wire.items:
            if item.evidence_id in seen_ids:
                raise ValueError("duplicate evidence id")
            seen_ids.add(item.evidence_id)
            if item.locale != request.locale or item.corpus != request.corpus:
                raise ValueError("evidence locale or corpus mismatch")
            sources = [
                RetrievalSource(
                    source_id=source.source_id,
                    source_name=source.source_name,
                    source_url=source.source_url,
                    source_role=source.source_role,
                    retrieved_at=_parse_datetime(source.retrieved_at),
                    valid_from=_parse_datetime(source.valid_from),
                    valid_until=_parse_datetime(source.valid_until),
                    license=source.license,
                )
                for source in item.sources
            ]
            items.append(
                RetrievedEvidence(
                    evidence_id=item.evidence_id,
                    canonical_entity_key=item.canonical_entity_key,
                    claim_key=item.claim_key,
                    document_id=item.document_id,
                    content_hash=item.content_hash,
                    locale=item.locale,
                    text=item.text,
                    # The owner wire has no item version/retrieved_at/chunk id.
                    version=None,
                    retrieved_at=None,
                    retrieval_score=item.score,
                    sources=sources,
                )
            )
        result = RetrievalResponse(
            request_id=request.request_id,
            corpus=request.corpus,
            locale=request.locale,
            status=wire.outcome,
            contract_version=wire.contract_version,
            corpus_version=wire.corpus_version,
            retrieval_version=wire.retrieval_version,
            generated_at=_parse_datetime(wire.generated_at),
            warnings=wire.warnings,
            evidence=items,
        )
        return validate_response_for_request(request, result)
    except (RetrievalUnavailable, RetrievalInvalidRequest):
        raise
    except Exception:
        raise RetrievalUnavailable() from None


class OwnerRagHttpAdapter(RetrievalPort):
    """Loopback-only, no-redirect, no-retry HTTP implementation of RetrievalPort."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport

    async def retrieve(self, request: RetrievalRequest, /) -> RetrievalResponse:
        if not self._settings.tourism_rag_enabled:
            raise RetrievalUnavailable()
        wire_request = serialize_owner_request(request)
        token = self._settings.tourism_rag_api_token
        if token is None:
            raise RetrievalUnavailable()
        url = urljoin(self._settings.tourism_rag_api_url.rstrip("/") + "/", OWNER_RAG_ENDPOINT)
        timeout = httpx.Timeout(3.0, connect=1.0, read=3.0, write=1.0, pool=1.0)
        headers = {
            "Authorization": f"Bearer {token.get_secret_value()}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=False,
                trust_env=False,
                transport=self._transport,
            ) as client:
                async with asyncio.timeout(4.0):
                    async with client.stream(
                        "POST",
                        url,
                        headers=headers,
                        json=wire_request.model_dump(mode="json", exclude_none=True),
                    ) as response:
                        if response.status_code == 401:
                            raise RetrievalAuthenticationFailed()
                        if response.status_code == 422:
                            raise RetrievalInvalidRequest()
                        if response.status_code == 503 or response.status_code != 200:
                            raise RetrievalUnavailable()
                        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                        if content_type != "application/json":
                            raise RetrievalUnavailable()
                        length = response.headers.get("content-length")
                        if length is not None and int(length) > MAX_OWNER_RESPONSE_BYTES:
                            raise RetrievalUnavailable()
                        body_bytes = bytearray()
                        async for chunk in response.aiter_bytes():
                            body_bytes.extend(chunk)
                            if len(body_bytes) > MAX_OWNER_RESPONSE_BYTES:
                                raise RetrievalUnavailable()
            try:
                body = json.loads(body_bytes)
            except (ValueError, UnicodeDecodeError):
                raise RetrievalUnavailable() from None
            return map_owner_response(request, body)
        except (RetrievalAuthenticationFailed, RetrievalInvalidRequest, RetrievalUnavailable):
            raise
        except (httpx.TimeoutException, TimeoutError, httpx.RequestError):
            raise RetrievalUnavailable() from None
        except Exception:
            raise RetrievalUnavailable() from None
