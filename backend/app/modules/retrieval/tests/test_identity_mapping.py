from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

import pytest

from app.modules.retrieval.contracts import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievalSource,
    RetrievedEvidence,
    TrustedRetrievalFilters,
)
from app.modules.retrieval.identity_mapping import (
    PublishedClaimProjection,
    PublishedSourceIdentity,
    map_owner_evidence,
)

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)
KEY = "shiraz-eram-garden-v1"
DOC = "00000000-0000-4000-8000-000000000001"
CLAIM = "visitor_site_identity"
TEXT = "متن مستند آزمایشی؛ فقط پس از تطبیق هویت قابل استفاده است."
HASH = sha256(TEXT.encode("utf-8")).hexdigest()
SOURCE_ID = "42"


def request(**overrides) -> RetrievalRequest:
    values = {
        "request_id": UUID("47ad3a14-1a53-47e1-aa50-721d3cb69a26"),
        "query": "باغ ارم",
        "locale": "fa-IR",
        "corpus": "spatial_destinations",
        "limit": 3,
        "filters": TrustedRetrievalFilters(canonical_entity_key=KEY),
        "as_of": NOW,
    }
    values.update(overrides)
    return RetrievalRequest(**values)


def published_source(**overrides) -> PublishedSourceIdentity:
    values = {
        "source_id": SOURCE_ID,
        "source_name": "Official test source",
        "source_url": "https://example.invalid/eram",
        "source_role": "site_identity",
        "license": "CC-BY-4.0",
        "retrieved_at": NOW - timedelta(hours=1),
        "valid_from": NOW - timedelta(days=2),
        "valid_until": NOW + timedelta(days=2),
        "is_verified": True,
        "is_synthetic": False,
        "is_revoked": False,
    }
    values.update(overrides)
    return PublishedSourceIdentity(**values)


def projection(**overrides) -> PublishedClaimProjection:
    values = {
        "canonical_entity_key": KEY,
        "destination_id": 701,
        "document_id": DOC,
        "claim_key": CLAIM,
        "content_hash": HASH,
        "locale": "fa-IR",
        "corpus": "spatial_destinations",
        "valid_from": NOW - timedelta(days=2),
        "valid_until": NOW + timedelta(days=2),
        "is_published": True,
        "is_destination_verified": True,
        "is_document_processed": True,
        "is_synthetic": False,
        "is_revoked": False,
        "sources": (published_source(),),
    }
    values.update(overrides)
    return PublishedClaimProjection(**values)


def hit(**overrides) -> RetrievedEvidence:
    values = {
        "evidence_id": "opaque-owner-evidence-001",
        "canonical_entity_key": KEY,
        "claim_key": CLAIM,
        "document_id": DOC,
        "content_hash": HASH,
        "locale": "fa-IR",
        "text": TEXT,
        "retrieval_score": 0.91,
        "sources": [
            RetrievalSource(
                source_id=SOURCE_ID,
                source_name="Official test source",
                source_url="https://example.invalid/eram",
                source_role="site_identity",
                license="CC-BY-4.0",
                retrieved_at=NOW - timedelta(hours=1),
                valid_from=NOW - timedelta(days=2),
                valid_until=NOW + timedelta(days=2),
            )
        ],
    }
    values.update(overrides)
    return RetrievedEvidence(**values)


def response(*items: RetrievedEvidence) -> RetrievalResponse:
    return RetrievalResponse(
        request_id=UUID("47ad3a14-1a53-47e1-aa50-721d3cb69a26"),
        corpus="spatial_destinations",
        locale="fa-IR",
        status="ok",
        evidence=list(items),
    )


def test_positive_mapping_preserves_exact_document_claim_hash_and_citation():
    result = map_owner_evidence(response(hit()), request=request(), published_claims=[projection()])

    assert result.status == "mapped"
    assert result.withheld_count == 0
    mapped = result.mapped[0]
    assert mapped.canonical_entity_key == KEY
    assert mapped.destination_id == 701
    assert mapped.document_id == DOC
    assert mapped.claim_key == CLAIM
    assert mapped.content_hash == HASH
    assert mapped.sources[0].source_id == SOURCE_ID
    assert mapped.text == TEXT
    assert not hasattr(mapped, "retrieval_score")


@pytest.mark.parametrize(
    "projection_changes",
    [
        {"canonical_entity_key": "same-display-name-different-key"},
        {"document_id": "00000000-0000-4000-8000-000000000009"},
        {"claim_key": "different-claim"},
        {"content_hash": "b" * 64},
        {"locale": "en-US"},
        {"corpus": "culinary_knowledge"},
        {"is_published": False},
        {"is_destination_verified": False},
        {"is_document_processed": False},
        {"is_synthetic": True},
        {"is_revoked": True},
        {"valid_until": NOW - timedelta(seconds=1)},
    ],
)
def test_any_projection_identity_or_publication_mismatch_withholds_text(projection_changes):
    result = map_owner_evidence(
        response(hit()), request=request(), published_claims=[projection(**projection_changes)]
    )

    assert result.status == "unmapped"
    assert result.mapped == ()
    assert result.withheld_count == 1
    assert "متن مستند" not in result.model_dump_json()


@pytest.mark.parametrize(
    "source_changes",
    [
        {"source_id": "0042"},
        {"source_name": "Other source"},
        {"source_url": "https://example.invalid/other"},
        {"source_role": "other_claim"},
        {"license": "different-license"},
        {"is_verified": False},
        {"is_synthetic": True},
        {"is_revoked": True},
        {"valid_until": NOW - timedelta(seconds=1)},
    ],
)
def test_any_source_mismatch_or_revocation_withholds_whole_claim(source_changes):
    approved = published_source(**source_changes)
    owner = RetrievalSource(
        source_id=SOURCE_ID,
        source_name="Official test source",
        source_url="https://example.invalid/eram",
        source_role="site_identity",
        license="CC-BY-4.0",
        retrieved_at=NOW - timedelta(hours=1),
        valid_from=NOW - timedelta(days=2),
        valid_until=NOW + timedelta(days=2),
    )
    result = map_owner_evidence(
        response(hit(sources=[owner])),
        request=request(),
        published_claims=[projection(sources=(approved,))],
    )

    assert result.status == "unmapped"
    assert result.withheld_count == 1


def test_url_or_display_name_alone_cannot_map_evidence():
    # Matching URL and visible source label do not compensate for absent claim
    # identity and content hash in the approved projection.
    wrong_claim = hit(claim_key="unregistered-claim")
    wrong_hash = hit(content_hash="c" * 64)
    result = map_owner_evidence(
        response(wrong_claim, wrong_hash),
        request=request(),
        published_claims=[projection()],
    )

    assert result.status == "unmapped"
    assert result.withheld_count == 2
    assert result.mapped == ()


def test_duplicate_projection_identity_is_ambiguous_and_withheld():
    result = map_owner_evidence(
        response(hit()),
        request=request(),
        published_claims=[projection(), projection()],
    )

    assert result.status == "unmapped"
    assert result.withheld_count == 1


def test_non_ok_result_never_maps_or_returns_owner_text():
    empty = RetrievalResponse(
        request_id=request().request_id,
        corpus="spatial_destinations",
        locale="fa-IR",
        status="no_evidence",
        evidence=[],
    )
    result = map_owner_evidence(empty, request=request(), published_claims=[projection()])

    assert result.status == "unmapped"
    assert result.mapped == ()
    assert result.withheld_count == 0


def test_exact_key_document_claim_hash_locale_and_corpus_are_required():
    result = map_owner_evidence(
        response(hit()),
        request=request(filters=TrustedRetrievalFilters(canonical_entity_key="other-key")),
        published_claims=[projection()],
    )

    assert result.status == "unmapped"
    assert result.withheld_count == 1
