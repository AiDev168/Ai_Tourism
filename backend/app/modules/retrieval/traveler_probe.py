"""Safe, non-authoritative owner-RAG probe for one selected destination.

Owner evidence is never exposed to a traveler by this probe. The current
application projection can validate source rows, but cannot prove that an
owner document, claim, or content hash is published for those rows.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.modules.recommendation.contracts import EvidenceSource as ApprovedEvidenceSource
from app.modules.retrieval.client import retrieve_validated
from app.modules.retrieval.contracts import (
    RetrievalAuthenticationFailed,
    RetrievalInvalidRequest,
    RetrievalPort,
    RetrievalRequest,
    RetrievalUnavailable,
    TrustedRetrievalFilters,
)

ProbeStatus = Literal["no_evidence", "evidence_unmapped", "unavailable", "invalid"]
PROBE_LIMIT = 3


class TravelerProbeResult(BaseModel):
    """Safe outcome metadata; intentionally has no evidence/text fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ProbeStatus
    evidence_count: int = Field(ge=0, le=PROBE_LIMIT)
    source_validated_count: int = Field(ge=0, le=96)
    withheld_evidence_count: int = Field(ge=0, le=PROBE_LIMIT)


def _source_matches_approved_projection(
    owner_source: object,
    approved_sources: tuple[ApprovedEvidenceSource, ...],
) -> bool:
    source_id = getattr(owner_source, "source_id", None)
    for approved in approved_sources:
        # Source identifiers are numeric in the approved catalogue. Preserve
        # exact identity; do not accept alternate numeric spellings.
        if source_id != str(approved.source_id):
            continue
        if (
            getattr(owner_source, "source_name", None) == approved.source_name
            and getattr(owner_source, "source_url", None) == approved.source_url
            and getattr(owner_source, "source_role", None) == approved.source_role
            and getattr(owner_source, "retrieved_at", None) == approved.retrieved_at
            and getattr(owner_source, "valid_from", None) == approved.valid_from
            and getattr(owner_source, "valid_until", None) == approved.valid_until
            # The application projection has no license column. A non-null
            # owner license therefore cannot be independently verified.
            and getattr(owner_source, "license", None) is None
        ):
            return True
    return False


async def probe_selected_destination(
    port: RetrievalPort,
    *,
    destination_key: str,
    canonical_display_name: str,
    locale: Literal["fa-IR", "en-US", "ar"],
    approved_sources: tuple[ApprovedEvidenceSource, ...] | list[ApprovedEvidenceSource],
) -> TravelerProbeResult:
    """Probe the owner RAG for one approved destination without returning text.

    The query is the selected destination's canonical display name, never the
    traveler conversation. Every returned item is withheld even when its
    source rows match: the app has no approved document/claim/hash projection.
    """

    try:
        request = RetrievalRequest(
            request_id=uuid4(),
            query=canonical_display_name,
            locale=locale,
            corpus="spatial_destinations",
            limit=PROBE_LIMIT,
            filters=TrustedRetrievalFilters(canonical_entity_key=destination_key),
            as_of=datetime.now(UTC),
        )
    except (ValidationError, ValueError, TypeError):
        return TravelerProbeResult(
            status="invalid", evidence_count=0, source_validated_count=0,
            withheld_evidence_count=0,
        )

    try:
        response = await retrieve_validated(port, request)
    except RetrievalInvalidRequest:
        return TravelerProbeResult(
            status="invalid", evidence_count=0, source_validated_count=0,
            withheld_evidence_count=0,
        )
    except (RetrievalUnavailable, RetrievalAuthenticationFailed):
        return TravelerProbeResult(
            status="unavailable", evidence_count=0, source_validated_count=0,
            withheld_evidence_count=0,
        )

    if response.status == "no_evidence":
        return TravelerProbeResult(
            status="no_evidence", evidence_count=0, source_validated_count=0,
            withheld_evidence_count=0,
        )
    if response.status == "unavailable":
        return TravelerProbeResult(
            status="unavailable", evidence_count=0, source_validated_count=0,
            withheld_evidence_count=0,
        )
    if response.status == "invalid_request":
        return TravelerProbeResult(
            status="invalid", evidence_count=0, source_validated_count=0,
            withheld_evidence_count=0,
        )

    approved = tuple(approved_sources)
    source_validated_count = 0
    for evidence in response.evidence:
        if evidence.canonical_entity_key != destination_key:
            continue
        if not evidence.sources or not all(
            _source_matches_approved_projection(source, approved)
            for source in evidence.sources
        ):
            continue
        source_validated_count += len(evidence.sources)

    evidence_count = len(response.evidence)
    return TravelerProbeResult(
        # Even source-valid evidence is not traveler-usable until the
        # document/claim/content-hash publication projection exists.
        status="evidence_unmapped",
        evidence_count=evidence_count,
        source_validated_count=source_validated_count,
        withheld_evidence_count=evidence_count,
    )
