from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.retrieval.client import retrieve_validated
from app.modules.retrieval.contracts import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievalUnavailable,
)
from app.modules.retrieval.fake import DeterministicRetrievalFake

AS_OF = datetime(2026, 11, 9, 12, tzinfo=UTC)


def request(**overrides) -> RetrievalRequest:
    values = {
        "request_id": uuid4(),
        "query": "quiet gardens in Shiraz",
        "locale": "en-US",
        "corpus": "spatial_destinations",
        "limit": 10,
        "as_of": AS_OF,
    }
    values.update(overrides)
    return RetrievalRequest.model_validate(values)


def evidence(**overrides) -> dict:
    return {
        "canonical_id": "destination:42",
        "document_id": "document:2026-01",
        "claim_id": "claim:visitor-description",
        "chunk_id": "chunk:1",
        "content_hash": "a" * 64,
        "locale": "en-US",
        "text": "A source-backed garden description.",
        "version": "publication-v2",
        "retrieved_at": AS_OF - timedelta(days=1),
        "valid_from": AS_OF - timedelta(days=10),
        "valid_until": AS_OF + timedelta(days=10),
        "retrieval_score": 0.8,
        "sources": [{
            "source_id": "source:12",
            "source_name": "Approved source",
            "source_url": "https://example.org/garden",
            "source_role": "primary",
            "license": "reviewed",
            "retrieved_at": AS_OF - timedelta(days=1),
            "valid_from": AS_OF - timedelta(days=10),
            "valid_until": AS_OF + timedelta(days=10),
        }],
        **overrides,
    }


def response(req: RetrievalRequest, *, evidence_rows: list[dict] | None = None, **overrides):
    values = {
        "request_id": req.request_id,
        "corpus": req.corpus,
        "locale": req.locale,
        "status": "ok" if evidence_rows else "no_evidence",
        "retrieval_version": "owner-contract-draft-v1",
        "evidence": evidence_rows or [],
    }
    values.update(overrides)
    return RetrievalResponse.model_validate(values)


def test_request_requires_bounded_query_allowlisted_filters_and_aware_time():
    with pytest.raises(ValidationError):
        request(query=" ")
    with pytest.raises(ValidationError):
        request(limit=1_001)
    with pytest.raises(ValidationError):
        request(limit=True)
    with pytest.raises(ValidationError):
        request(filters={"unreviewed_filter": ["anything"]})
    with pytest.raises(ValidationError):
        request(filters={"destination_ids": [42]})
    with pytest.raises(ValidationError):
        request(as_of=datetime(2026, 11, 9, 12))


@pytest.mark.parametrize("corpus", ["spatial_destinations", "culinary_knowledge"])
def test_port_keeps_spatial_and_culinary_corpora_separate(corpus: str):
    req = request(corpus=corpus)
    result = asyncio.run(retrieve_validated(DeterministicRetrievalFake(), req))
    assert result.corpus == corpus
    assert result.status == "no_evidence"
    assert result.evidence == []


@pytest.mark.parametrize("locale", ["fa-IR", "en-US", "ar"])
def test_port_preserves_supported_locales(locale: str):
    req = request(locale=locale)
    result = asyncio.run(retrieve_validated(DeterministicRetrievalFake(), req))
    assert result.locale == locale
    assert result.status == "no_evidence"


@pytest.mark.parametrize("status", ["unavailable", "invalid_request"])
def test_failure_statuses_are_distinct_and_carry_no_evidence(status: str):
    req = request()
    result = RetrievalResponse(
        request_id=req.request_id,
        corpus=req.corpus,
        locale=req.locale,
        status=status,
        retrieval_version="contract-v1",
        evidence=[],
    )

    class Port:
        async def retrieve(self, _request):
            return result

    actual = asyncio.run(retrieve_validated(Port(), req))
    assert actual.status == status
    assert actual.evidence == []


def test_valid_evidence_is_bound_to_request_and_keeps_claim_provenance():
    req = request()
    configured = response(req, evidence_rows=[evidence()])
    fake = DeterministicRetrievalFake({(req.corpus, req.locale, req.query): configured})

    actual = asyncio.run(retrieve_validated(fake, req))

    assert actual == configured
    assert actual.evidence[0].claim_id == "claim:visitor-description"
    assert actual.evidence[0].sources[0].source_url.startswith("https://")
    assert actual.evidence[0].retrieval_score == 0.8  # retrieval metadata only


@pytest.mark.parametrize("mutate", [
    lambda req, row: {**row, "locale": "ar"},
    lambda req, row: {**row, "valid_until": AS_OF - timedelta(days=1)},
    lambda req, row: {**row, "retrieved_at": AS_OF + timedelta(seconds=1)},
    lambda req, row: {**row, "content_hash": "not-a-sha256"},
    lambda req, row: {**row, "sources": [{**row["sources"][0], "source_url": "javascript:alert(1)"}]},
])
def test_invalid_provenance_or_stale_evidence_fails_with_safe_error(mutate):
    req = request()
    row = mutate(req, evidence())
    # Pydantic wire errors and semantic validation both map to one safe error.
    raw = {
        "request_id": req.request_id, "corpus": req.corpus, "locale": req.locale,
        "status": "ok", "retrieval_version": "draft-v1", "evidence": [row],
    }
    class AsyncBadPort:
        async def retrieve(self, _request):
            return raw

    with pytest.raises(RetrievalUnavailable) as error:
        asyncio.run(retrieve_validated(AsyncBadPort(), req))
    assert str(error.value) == "Retrieval is temporarily unavailable."
    assert "example.org" not in str(error.value)


def test_response_must_match_request_corpus_locale_and_limit():
    req = request(limit=1)
    valid = response(req, evidence_rows=[evidence()]).model_dump(mode="python")
    valid["locale"] = "fa-IR"

    class Port:
        async def retrieve(self, _request):
            return valid

    with pytest.raises(RetrievalUnavailable):
        asyncio.run(retrieve_validated(Port(), req))


def test_adapter_exception_is_mapped_once_without_retry_or_detail_leak():
    class FailingPort:
        def __init__(self):
            self.calls = 0

        async def retrieve(self, _request):
            self.calls += 1
            raise RuntimeError("secret https://internal.invalid token prompt")

    port = FailingPort()
    with pytest.raises(RetrievalUnavailable) as error:
        asyncio.run(retrieve_validated(port, request()))
    assert str(error.value) == "Retrieval is temporarily unavailable."
    assert port.calls == 1


def test_fake_is_deterministic_and_default_is_honest_empty():
    req = request()
    fake = DeterministicRetrievalFake()
    first = asyncio.run(retrieve_validated(fake, req))
    second = asyncio.run(retrieve_validated(fake, req))
    assert first == second
    assert first.status == "no_evidence"
    assert len(fake.requests) == 2
