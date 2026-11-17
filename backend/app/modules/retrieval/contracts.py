"""Application-side, read-only contract for the separately owned RAG system.

This contract does not implement retrieval. The owner RAG remains responsible
for indexing and search; callers must independently verify publication and
authorization before using returned evidence in traveler-facing decisions.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Literal, Protocol
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_validator, model_validator

RetrievalLocale = Literal["fa-IR", "en-US", "ar"]
RetrievalCorpus = Literal["spatial_destinations", "culinary_knowledge"]
RetrievalStatus = Literal["ok", "no_evidence", "unavailable", "invalid_request"]
MAX_RETRIEVAL_LIMIT = 1_000
MAX_OWNER_HTTP_LIMIT = 20


class TrustedRetrievalFilters(BaseModel):
    """Small allowlist for filters constructed by trusted backend code only."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    destination_ids: list[StrictStr] = Field(default_factory=list, max_length=100)
    destination_keys: list[StrictStr] = Field(default_factory=list, max_length=100)
    city_names: list[StrictStr] = Field(default_factory=list, max_length=20)
    province_names: list[StrictStr] = Field(default_factory=list, max_length=20)
    canonical_entity_key: StrictStr | None = Field(default=None, min_length=1, max_length=240)

    @field_validator("destination_ids", "destination_keys", "city_names", "province_names")
    @classmethod
    def validate_filter_values(cls, values: list[str]) -> list[str]:
        if any(not value.strip() or len(value) > 240 for value in values):
            raise ValueError("filter values must be non-empty and bounded")
        if len(values) != len(set(values)):
            raise ValueError("filter values must be unique")
        return values

    @field_validator("canonical_entity_key")
    @classmethod
    def validate_canonical_entity_key(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("canonical entity key must not be blank")
        return value


class RetrievalRequest(BaseModel):
    """Bounded request metadata; do not put raw conversation history here."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: UUID
    query: str = Field(min_length=1, max_length=1_200)
    locale: RetrievalLocale
    corpus: RetrievalCorpus
    limit: int = Field(strict=True, ge=1, le=MAX_RETRIEVAL_LIMIT)
    filters: TrustedRetrievalFilters = Field(default_factory=TrustedRetrievalFilters)
    as_of: datetime

    @field_validator("query")
    @classmethod
    def validate_query(cls, value: str) -> str:
        if not value.strip() or "\x00" in value:
            raise ValueError("query must be nonblank and contain no NUL")
        return value

    @field_validator("as_of")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        return value


class RetrievalSource(BaseModel):
    """Provenance attached to the specific claim returned by retrieval."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1, max_length=160, pattern=r"^[\w.:-]+$")
    source_name: str = Field(min_length=1, max_length=250)
    source_url: str = Field(min_length=1, max_length=2_048)
    source_role: str = Field(min_length=1, max_length=100)
    license: str | None = Field(default=None, max_length=200)
    retrieved_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("source URL must be credential-free HTTPS")
        return value

    @model_validator(mode="after")
    def validate_source_window(self) -> RetrievalSource:
        if self.retrieved_at is not None:
            _require_aware(self.retrieved_at)
        if self.valid_from is not None:
            _require_aware(self.valid_from)
        if self.valid_until is not None:
            _require_aware(self.valid_until)
        if self.valid_from and self.valid_until and self.valid_from > self.valid_until:
            raise ValueError("source validity window is inverted")
        return self


class RetrievedEvidence(BaseModel):
    """One RAG claim/document hit; retrieval score is not recommendation quality."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str | None = Field(default=None, min_length=1, max_length=240)
    canonical_entity_key: str | None = Field(default=None, min_length=1, max_length=240)
    claim_key: str | None = Field(default=None, min_length=1, max_length=240)
    # Legacy application-fake fields remain optional; owner wire identities are
    # preserved in their distinct canonical_entity_key/claim_key fields.
    canonical_id: str | None = Field(default=None, min_length=1, max_length=240)
    document_id: str = Field(min_length=1, max_length=240)
    claim_id: str | None = Field(default=None, min_length=1, max_length=240)
    chunk_id: str | None = Field(default=None, min_length=1, max_length=240)
    content_hash: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    locale: RetrievalLocale
    # TourismRagApiV1's actual v1 DTO permits up to 12,000 characters.
    # Keep the application adapter capable of preserving a valid hit; identity
    # and publication checks remain independent and exact.
    text: str = Field(min_length=1, max_length=12_000)
    version: str | None = Field(default=None, min_length=1, max_length=160)
    retrieved_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    retrieval_score: float | None = Field(default=None, strict=True, allow_inf_nan=False)
    sources: list[RetrievalSource] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def validate_evidence_window(self) -> RetrievedEvidence:
        if self.retrieved_at is not None:
            _require_aware(self.retrieved_at)
        if self.valid_from is not None:
            _require_aware(self.valid_from)
        if self.valid_until is not None:
            _require_aware(self.valid_until)
        if self.valid_from and self.valid_until and self.valid_from > self.valid_until:
            raise ValueError("evidence validity window is inverted")
        return self


class RetrievalResponse(BaseModel):
    """Typed read result. Statuses are distinct from recommendation outcomes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: UUID
    corpus: RetrievalCorpus
    locale: RetrievalLocale
    status: RetrievalStatus
    contract_version: str | None = Field(default=None, max_length=32)
    corpus_version: str | None = Field(default=None, max_length=160)
    retrieval_version: str | None = Field(default=None, max_length=160)
    generated_at: datetime | None = None
    warnings: list[str] = Field(default_factory=list, max_length=32)
    evidence: list[RetrievedEvidence] = Field(max_length=MAX_RETRIEVAL_LIMIT)

    @model_validator(mode="after")
    def validate_status_evidence_shape(self) -> RetrievalResponse:
        if self.status == "ok" and not self.evidence:
            raise ValueError("ok retrieval requires evidence")
        if self.status != "ok" and self.evidence:
            raise ValueError("non-ok retrieval must not contain evidence")
        if self.generated_at is not None:
            _require_aware(self.generated_at)
        return self


class RetrievalPort(Protocol):
    """Read-only application boundary to an owner-managed retrieval system."""

    async def retrieve(self, request: RetrievalRequest, /) -> RetrievalResponse: ...


class RetrievalPortError(RuntimeError):
    """Safe typed failures returned by a RetrievalPort adapter."""


class RetrievalUnavailable(RetrievalPortError):
    """Safe provider-neutral failure; contains no request or provider details."""

    def __init__(self) -> None:
        super().__init__("Retrieval is temporarily unavailable.")


class RetrievalAuthenticationFailed(RetrievalPortError):
    """The RAG service rejected its configured server-side credential."""

    def __init__(self) -> None:
        super().__init__("Retrieval service authentication failed.")


class RetrievalInvalidRequest(RetrievalPortError):
    """The application request cannot be represented by the owner wire API."""

    def __init__(self) -> None:
        super().__init__("Retrieval request is invalid or unsupported.")


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")


def validate_response_for_request(
    request: RetrievalRequest,
    response: RetrievalResponse | Mapping[str, object],
) -> RetrievalResponse:
    """Validate untrusted adapter data and bind it to the originating request.

    This checks wire shape, bounds, provenance syntax and source validity at
    ``as_of``. It does not prove publication or ownership; the caller must
    independently check those using its approved application read model.
    """

    try:
        result = (
            response
            if isinstance(response, RetrievalResponse)
            else RetrievalResponse.model_validate(response)
        )
        if (
            result.request_id != request.request_id
            or result.corpus != request.corpus
            or result.locale != request.locale
            or len(result.evidence) > request.limit
        ):
            raise ValueError("retrieval response does not match request")
        identities: set[tuple[str, str, str]] = set()
        evidence_ids: set[str] = set()
        for hit in result.evidence:
            canonical_key = hit.canonical_entity_key or hit.canonical_id or ""
            claim_key = hit.claim_key or hit.claim_id or ""
            identity = (canonical_key, hit.document_id, claim_key)
            if (
                (hit.canonical_entity_key is not None or hit.canonical_id is not None)
                and (hit.claim_key is not None or hit.claim_id is not None)
                and identity in identities
            ) or hit.locale != request.locale:
                raise ValueError("duplicate or wrong-locale evidence")
            if hit.canonical_entity_key is not None or hit.canonical_id is not None:
                if hit.claim_key is not None or hit.claim_id is not None:
                    identities.add(identity)
            if hit.evidence_id is not None:
                if hit.evidence_id in evidence_ids:
                    raise ValueError("duplicate evidence identity")
                evidence_ids.add(hit.evidence_id)
            if hit.retrieved_at is not None and hit.retrieved_at > request.as_of:
                raise ValueError("evidence was retrieved after the request time")
            if hit.valid_from is not None and request.as_of < hit.valid_from:
                raise ValueError("evidence is not yet valid")
            if hit.valid_until is not None and request.as_of > hit.valid_until:
                raise ValueError("evidence has expired")
            for source in hit.sources:
                if source.retrieved_at is not None and source.retrieved_at > request.as_of:
                    raise ValueError("source was retrieved after the request time")
                if source.valid_from is not None and request.as_of < source.valid_from:
                    raise ValueError("source is not yet valid")
                if source.valid_until is not None and request.as_of > source.valid_until:
                    raise ValueError("source has expired")
        return result
    except Exception:
        # Do not propagate validation messages containing source text or URLs.
        raise RetrievalUnavailable() from None
