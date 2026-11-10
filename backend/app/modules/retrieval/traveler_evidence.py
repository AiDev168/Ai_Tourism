"""Bounded owner-RAG lookup and publication-map result for one destination."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import ValidationError

from app.modules.retrieval.client import retrieve_validated
from app.modules.retrieval.contracts import (
    RetrievalAuthenticationFailed,
    RetrievalInvalidRequest,
    RetrievalPort,
    RetrievalRequest,
    RetrievalUnavailable,
    TrustedRetrievalFilters,
)
from app.modules.retrieval.identity_mapping import (
    EvidenceMappingResult,
    PublishedClaimProjection,
    map_owner_evidence,
)

RetrievalEvidenceStatus = Literal[
    "no_evidence", "unavailable", "unmapped", "mapped", "invalid"
]


async def retrieve_mapped_destination_evidence(
    port: RetrievalPort,
    *,
    destination_key: str,
    canonical_display_name: str,
    locale: Literal["fa-IR", "en-US", "ar"],
    published_claims: tuple[PublishedClaimProjection, ...] | list[PublishedClaimProjection],
) -> tuple[RetrievalEvidenceStatus, EvidenceMappingResult]:
    """Query only the exact destination, then require the strict app identity map."""

    try:
        request = RetrievalRequest(
            request_id=uuid4(),
            query=canonical_display_name,
            locale=locale,
            corpus="spatial_destinations",
            limit=3,
            filters=TrustedRetrievalFilters(canonical_entity_key=destination_key),
            as_of=datetime.now(UTC),
        )
    except (ValidationError, ValueError, TypeError):
        result = EvidenceMappingResult(status="unmapped", mapped=(), withheld_count=0)
        return "invalid", result

    try:
        response = await retrieve_validated(port, request)
    except RetrievalInvalidRequest:
        result = EvidenceMappingResult(status="unmapped", mapped=(), withheld_count=0)
        return "invalid", result
    except (RetrievalUnavailable, RetrievalAuthenticationFailed):
        result = EvidenceMappingResult(status="unmapped", mapped=(), withheld_count=0)
        return "unavailable", result

    if response.status == "no_evidence":
        return "no_evidence", EvidenceMappingResult(status="unmapped", mapped=(), withheld_count=0)
    if response.status == "unavailable":
        return "unavailable", EvidenceMappingResult(status="unmapped", mapped=(), withheld_count=0)
    if response.status == "invalid_request":
        return "invalid", EvidenceMappingResult(status="unmapped", mapped=(), withheld_count=0)

    result = map_owner_evidence(
        response,
        request=request,
        published_claims=published_claims,
    )
    return ("mapped" if result.status == "mapped" else "unmapped"), result
