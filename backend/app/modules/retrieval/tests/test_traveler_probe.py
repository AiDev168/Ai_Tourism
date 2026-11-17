from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.modules.recommendation.contracts import EvidenceSource
from app.modules.retrieval.contracts import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievalSource,
    RetrievedEvidence,
    RetrievalUnavailable,
)
from app.modules.retrieval.traveler_probe import probe_selected_destination

NOW = datetime.now(UTC)
OWNER_TEXT = "Owner-only retrieved description must never be returned."


class StaticPort:
    def __init__(self, response: RetrievalResponse | Exception):
        self.response = response
        self.requests: list[RetrievalRequest] = []

    async def retrieve(self, request: RetrievalRequest, /) -> RetrievalResponse:
        self.requests.append(request)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response.model_copy(update={"request_id": request.request_id})


def approved_source(**overrides) -> EvidenceSource:
    values = {
        "destination_id": 17,
        "source_id": 42,
        "source_name": "Approved test source",
        "source_url": "https://example.invalid/source",
        "source_role": "claim_support",
        "retrieved_at": NOW - timedelta(days=1),
        "valid_from": NOW - timedelta(days=2),
        "valid_until": NOW + timedelta(days=1),
    }
    values.update(overrides)
    return EvidenceSource(**values)


def owner_source(**overrides) -> RetrievalSource:
    values = {
        "source_id": "42",
        "source_name": "Approved test source",
        "source_url": "https://example.invalid/source",
        "source_role": "claim_support",
        "retrieved_at": NOW - timedelta(days=1),
        "valid_from": NOW - timedelta(days=2),
        "valid_until": NOW + timedelta(days=1),
        "license": None,
    }
    values.update(overrides)
    return RetrievalSource(**values)


def evidence(*, key="destination:17", sources=None) -> RetrievedEvidence:
    return RetrievedEvidence(
        evidence_id="evidence:private-1",
        canonical_entity_key=key,
        claim_key="claim:summary",
        document_id="document:private-1",
        content_hash="a" * 64,
        locale="fa-IR",
        text=OWNER_TEXT,
        retrieval_score=0.8,
        sources=sources or [owner_source()],
    )


def response(status="ok", items=None) -> RetrievalResponse:
    return RetrievalResponse(
        request_id=UUID("e8e0489f-7adc-4ec2-85d4-12b75d6c7803"),
        corpus="spatial_destinations",
        locale="fa-IR",
        status=status,
        evidence=items or [],
    )


def test_exact_key_and_source_are_validated_but_text_is_withheld():
    port = StaticPort(response(items=[evidence()]))
    result = asyncio.run(
        probe_selected_destination(
            port,
            destination_key="destination:17",
            canonical_display_name="نام مقصد تأییدشده",
            locale="fa-IR",
            approved_sources=[approved_source()],
        )
    )

    request = port.requests[0]
    assert request.query == "نام مقصد تأییدشده"
    assert request.corpus == "spatial_destinations"
    assert request.locale == "fa-IR"
    assert request.limit == 3
    assert request.filters.canonical_entity_key == "destination:17"
    assert request.as_of.tzinfo is UTC
    assert result.status == "evidence_unmapped"
    assert result.evidence_count == 1
    assert result.source_validated_count == 1
    assert result.withheld_evidence_count == 1
    assert "text" not in result.model_dump()
    assert OWNER_TEXT not in result.model_dump_json()


def test_wrong_canonical_key_is_withheld_as_unmapped():
    port = StaticPort(response(items=[evidence(key="destination:other")]))
    result = asyncio.run(
        probe_selected_destination(
            port,
            destination_key="destination:17",
            canonical_display_name="Verified name",
            locale="fa-IR",
            approved_sources=[approved_source()],
        )
    )
    assert result.status == "evidence_unmapped"
    assert result.source_validated_count == 0
    assert result.withheld_evidence_count == 1


@pytest.mark.parametrize(
    "mismatch",
    [
        {"source_name": "Different name"},
        {"source_url": "https://example.invalid/other"},
        {"source_role": "other_role"},
        {"retrieved_at": None},
        {"valid_from": None},
        {"valid_until": None},
        {"license": "unprojected-license"},
        {"source_id": "0042"},
    ],
)
def test_stale_or_mismatched_source_metadata_is_not_accepted(mismatch):
    port = StaticPort(response(items=[evidence(sources=[owner_source(**mismatch)])]))
    result = asyncio.run(
        probe_selected_destination(
            port,
            destination_key="destination:17",
            canonical_display_name="Verified name",
            locale="fa-IR",
            approved_sources=[approved_source()],
        )
    )
    assert result.status == "evidence_unmapped"
    assert result.source_validated_count == 0
    assert result.withheld_evidence_count == 1
    assert OWNER_TEXT not in result.model_dump_json()


def test_no_evidence_is_distinct_from_unmapped_evidence():
    port = StaticPort(response(status="no_evidence"))
    result = asyncio.run(
        probe_selected_destination(
            port,
            destination_key="destination:17",
            canonical_display_name="Verified name",
            locale="fa-IR",
            approved_sources=[approved_source()],
        )
    )
    assert result.status == "no_evidence"
    assert result.evidence_count == result.withheld_evidence_count == 0


def test_unavailable_adapter_is_reported_without_details():
    port = StaticPort(RetrievalUnavailable())
    result = asyncio.run(
        probe_selected_destination(
            port,
            destination_key="destination:17",
            canonical_display_name="Verified name",
            locale="fa-IR",
            approved_sources=[approved_source()],
        )
    )
    assert result.status == "unavailable"
    assert result.evidence_count == 0
    assert OWNER_TEXT not in result.model_dump_json()


def test_invalid_request_payload_is_distinct():
    port = StaticPort(response(status="invalid_request"))
    result = asyncio.run(
        probe_selected_destination(
            port,
            destination_key="destination:17",
            canonical_display_name="Verified name",
            locale="fa-IR",
            approved_sources=[approved_source()],
        )
    )
    assert result.status == "invalid"
