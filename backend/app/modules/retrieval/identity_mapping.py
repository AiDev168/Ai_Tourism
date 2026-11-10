"""Strict bridge from untrusted owner-RAG hits to approved app evidence.

The caller must build projections exclusively from AI Tourism's approved
production read views. This module never promotes a hit based on its text,
display name, or source URL alone. It verifies the full stable identity and
source snapshot before making citation text available to the caller.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from hashlib import sha256
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    field_validator,
    model_validator,
)
from urllib.parse import urlsplit

from app.modules.retrieval.contracts import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievalSource,
    RetrievedEvidence,
    validate_response_for_request,
)


class PublishedSourceIdentity(BaseModel):
    """One source snapshot read from the approved publication projection."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    source_id: str = Field(min_length=1, max_length=240)
    source_name: str = Field(min_length=1, max_length=500)
    source_url: str = Field(min_length=1, max_length=2_048)
    source_role: str = Field(min_length=1, max_length=64)
    license: str | None = Field(default=None, max_length=500)
    retrieved_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_verified: StrictBool
    is_synthetic: StrictBool
    is_revoked: StrictBool

    @field_validator("source_url")
    @classmethod
    def require_credential_free_https(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("published source URL must be credential-free HTTPS")
        return value

    @model_validator(mode="after")
    def require_aware_source_dates(self) -> PublishedSourceIdentity:
        _validate_dates(self.retrieved_at, self.valid_from, self.valid_until)
        return self


class PublishedClaimProjection(BaseModel):
    """Exact document/claim identity projected from approved production data.

    `claim_key` must be obtained from an explicit, source-level claim mapping
    in the trusted projection. Do not derive it from a title or free text.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    canonical_entity_key: str = Field(min_length=1, max_length=240)
    destination_id: int = Field(gt=0)
    document_id: str = Field(min_length=1, max_length=240)
    claim_key: str = Field(min_length=1, max_length=240)
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    locale: Literal["fa-IR", "en-US", "ar"]
    corpus: Literal["spatial_destinations", "culinary_knowledge"]
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    is_published: StrictBool
    is_destination_verified: StrictBool
    is_document_processed: StrictBool
    is_synthetic: StrictBool
    is_revoked: StrictBool
    sources: tuple[PublishedSourceIdentity, ...] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def require_aware_claim_dates(self) -> PublishedClaimProjection:
        _validate_dates(None, self.valid_from, self.valid_until)
        return self


class MappedEvidence(BaseModel):
    """Evidence safe to attach to a recommendation after exact mapping."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=1, max_length=240)
    canonical_entity_key: str
    destination_id: int = Field(gt=0)
    document_id: str
    claim_key: str
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    locale: Literal["fa-IR", "en-US", "ar"]
    corpus: Literal["spatial_destinations", "culinary_knowledge"]
    text: str = Field(min_length=1, max_length=8_000)
    sources: tuple[PublishedSourceIdentity, ...]


class EvidenceMappingResult(BaseModel):
    """Mapping result with no upstream errors, raw body, or rejected text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["mapped", "unmapped"]
    mapped: tuple[MappedEvidence, ...] = Field(max_length=20)
    withheld_count: int = Field(ge=0, le=20)


def _is_current(start: datetime | None, end: datetime | None, as_of: datetime) -> bool:
    return (start is None or start <= as_of) and (end is None or end >= as_of)


def _validate_dates(
    retrieved_at: datetime | None,
    valid_from: datetime | None,
    valid_until: datetime | None,
) -> None:
    dates = [value for value in (retrieved_at, valid_from, valid_until) if value is not None]
    if any(value.tzinfo is None or value.utcoffset() is None for value in dates):
        raise ValueError("published evidence timestamps must be timezone-aware")
    if valid_from is not None and valid_until is not None and valid_from > valid_until:
        raise ValueError("published evidence validity window is inverted")


def _source_matches(owner: RetrievalSource, published: PublishedSourceIdentity, as_of: datetime) -> bool:
    return (
        owner.source_id == published.source_id
        and owner.source_name == published.source_name
        and owner.source_url == published.source_url
        and owner.source_role == published.source_role
        and owner.license == published.license
        and owner.retrieved_at == published.retrieved_at
        and owner.valid_from == published.valid_from
        and owner.valid_until == published.valid_until
        and published.is_verified
        and not published.is_synthetic
        and not published.is_revoked
        and _is_current(published.valid_from, published.valid_until, as_of)
        and (published.retrieved_at is None or published.retrieved_at <= as_of)
    )


def _projection_matches(
    hit: RetrievedEvidence,
    projection: PublishedClaimProjection,
    request: RetrievalRequest,
) -> bool:
    filters = request.filters
    if (
        filters.destination_ids
        or filters.destination_keys
        or filters.city_names
        or filters.province_names
        or (
            filters.canonical_entity_key is not None
            and filters.canonical_entity_key != projection.canonical_entity_key
        )
    ):
        return False
    if not (
        projection.is_published
        and projection.is_destination_verified
        and projection.is_document_processed
        and not projection.is_synthetic
        and not projection.is_revoked
        and hit.canonical_entity_key == projection.canonical_entity_key
        and hit.document_id == projection.document_id
        and hit.claim_key == projection.claim_key
        and hit.content_hash == projection.content_hash
        and sha256(hit.text.encode("utf-8")).hexdigest() == projection.content_hash
        and hit.locale == projection.locale == request.locale
        and request.corpus == projection.corpus
        and _is_current(projection.valid_from, projection.valid_until, request.as_of)
    ):
        return False

    if hit.evidence_id is None or not hit.sources:
        return False
    if len(hit.sources) != len(projection.sources):
        return False

    projected_by_id = {source.source_id: source for source in projection.sources}
    if len(projected_by_id) != len(projection.sources):
        return False
    seen: set[str] = set()
    for owner_source in hit.sources:
        if owner_source.source_id in seen:
            return False
        seen.add(owner_source.source_id)
        approved = projected_by_id.get(owner_source.source_id)
        if approved is None or not _source_matches(owner_source, approved, request.as_of):
            return False
    return seen == set(projected_by_id)


def map_owner_evidence(
    response: RetrievalResponse,
    *,
    request: RetrievalRequest,
    published_claims: Sequence[PublishedClaimProjection],
) -> EvidenceMappingResult:
    """Return only hits with a unique, exact and current approved identity.

    A non-``ok`` result, malformed request binding, absent mapping, ambiguous
    mapping, or any source mismatch is withheld. This function deliberately
    has no name/URL fallback and no partial-source acceptance.
    """

    if response.status != "ok":
        return EvidenceMappingResult(status="unmapped", mapped=(), withheld_count=0)
    try:
        validated = validate_response_for_request(request, response)
    except Exception:
        return EvidenceMappingResult(
            status="unmapped", mapped=(), withheld_count=len(response.evidence)
        )

    projections_by_identity: dict[tuple[str, str, str, str, str], list[PublishedClaimProjection]] = {}
    for projection in published_claims:
        identity = (
            projection.canonical_entity_key,
            projection.document_id,
            projection.claim_key,
            projection.locale,
            projection.corpus,
        )
        projections_by_identity.setdefault(identity, []).append(projection)

    mapped: list[MappedEvidence] = []
    withheld = 0
    for hit in validated.evidence:
        identity = (
            hit.canonical_entity_key or "",
            hit.document_id,
            hit.claim_key or "",
            hit.locale,
            validated.corpus,
        )
        candidates = projections_by_identity.get(identity, [])
        if len(candidates) != 1 or not _projection_matches(hit, candidates[0], request):
            withheld += 1
            continue
        projection = candidates[0]
        mapped.append(
            MappedEvidence(
                evidence_id=hit.evidence_id or "",
                canonical_entity_key=projection.canonical_entity_key,
                destination_id=projection.destination_id,
                document_id=projection.document_id,
                claim_key=projection.claim_key,
                content_hash=projection.content_hash,
                locale=projection.locale,
                corpus=projection.corpus,
                text=hit.text,
                sources=projection.sources,
            )
        )

    return EvidenceMappingResult(
        status="mapped" if mapped else "unmapped",
        mapped=tuple(mapped),
        withheld_count=withheld,
    )
