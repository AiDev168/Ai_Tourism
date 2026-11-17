from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from pydantic import ValidationError

from app.core.config import Settings
from app.modules.retrieval.contracts import (
    RetrievalAuthenticationFailed,
    RetrievalInvalidRequest,
    RetrievalRequest,
    RetrievalUnavailable,
    TrustedRetrievalFilters,
)
from app.modules.retrieval.owner_http import (
    OwnerRagHttpAdapter,
    map_owner_response,
    serialize_owner_request,
)

AS_OF = datetime(2026, 11, 9, 12, 0, 0, 123456, tzinfo=UTC)


def make_request(**overrides) -> RetrievalRequest:
    values = {
        "request_id": uuid4(),
        "query": "دیدنی‌های شیراز",
        "locale": "fa-IR",
        "corpus": "spatial_destinations",
        "limit": 5,
        "as_of": AS_OF,
    }
    values.update(overrides)
    return RetrievalRequest.model_validate(values)


def settings(**overrides) -> Settings:
    values = {
        "database_password": "test-only-not-a-secret",
        "app_env": "test",
        "tourism_rag_enabled": True,
        "tourism_rag_api_token": SecretStr("test-owner-token"),
    }
    values.update(overrides)
    return Settings(**values)


def no_evidence(req: RetrievalRequest) -> dict:
    return {
        "contract_version": "1.0.0",
        "request_id": str(req.request_id),
        "outcome": "no_evidence",
        "items": [],
        "corpus_version": "explicit-empty-approved-v1",
        "retrieval_version": "empty-approved-v1",
        "generated_at": "2026-11-09T12:00:01Z",
        "warnings": [],
    }


def item(req: RetrievalRequest, **overrides) -> dict:
    value = {
        "evidence_id": "evidence:test-only-001",
        "document_id": "document:test-only-001",
        "content_hash": "a" * 64,
        "text": "Test-only evidence; not a published tourism fact.",
        "locale": req.locale,
        "corpus": req.corpus,
        "canonical_entity_key": "test-only:place-001",
        "claim_key": "test-only:description",
        "score": None,
        "sources": [
            {
                "source_id": "test-source-001",
                "source_name": "Test fixture source",
                "source_url": "https://example.invalid/test-only",
                "source_role": "test_fixture",
                "retrieved_at": None,
                "valid_from": None,
                "valid_until": None,
                "license": None,
            }
        ],
    }
    value.update(overrides)
    return value


def owner_ok(req: RetrievalRequest, *, rows: list[dict] | None = None) -> dict:
    return {
        **no_evidence(req),
        "outcome": "ok",
        "items": rows or [item(req)],
    }


def test_serializes_actual_wire_contract_and_preserves_instant():
    req = make_request(
        as_of=datetime(2026, 11, 9, 15, 30, 0, 987654, tzinfo=UTC),
        filters=TrustedRetrievalFilters(canonical_entity_key="place:approved-1"),
    )
    wire = serialize_owner_request(req)
    assert wire.model_dump(mode="json") == {
        "request_id": str(req.request_id),
        "query": req.query,
        "locale": "fa-IR",
        "corpus": "spatial_destinations",
        "limit": 5,
        "filters": {"canonical_entity_key": "place:approved-1"},
        "as_of": "2026-11-09T15:30:00.987654Z",
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"limit": 21},
        {"filters": TrustedRetrievalFilters(destination_keys=["place:1"])},
        {"filters": TrustedRetrievalFilters(city_names=["Shiraz"])},
    ],
)
def test_refuses_unsupported_limit_or_filters_without_truncation(overrides):
    req = make_request(**overrides)
    with pytest.raises(RetrievalInvalidRequest):
        serialize_owner_request(req)


def test_maps_empty_and_preserves_optional_response_metadata():
    req = make_request()
    result = map_owner_response(req, no_evidence(req))
    assert result.status == "no_evidence"
    assert result.evidence == []
    assert result.contract_version == "1.0.0"
    assert result.corpus_version == "explicit-empty-approved-v1"
    assert result.retrieval_version == "empty-approved-v1"


def test_maps_wire_evidence_without_inventing_chunk_version_or_time():
    req = make_request()
    result = map_owner_response(req, owner_ok(req))
    evidence = result.evidence[0]
    assert evidence.evidence_id == "evidence:test-only-001"
    assert evidence.canonical_entity_key == "test-only:place-001"
    assert evidence.claim_key == "test-only:description"
    assert evidence.canonical_id is None
    assert evidence.claim_id is None
    assert evidence.chunk_id is None
    assert evidence.version is None
    assert evidence.retrieved_at is None
    assert evidence.retrieval_score is None
    assert evidence.sources[0].source_id == "test-source-001"
    assert evidence.sources[0].retrieved_at is None


def test_accepts_owner_wire_maximum_text_and_metadata_without_truncation():
    req = make_request()
    row = item(
        req,
        evidence_id="e" * 160,
        document_id="d" * 160,
        canonical_entity_key="c" * 160,
        claim_key="k" * 160,
        text="x" * 12_000,
        sources=[{
            "source_id": "s" * 160,
            "source_name": "n" * 250,
            "source_url": "https://example.invalid/source",
            "source_role": "r" * 100,
            "retrieved_at": None,
            "valid_from": None,
            "valid_until": None,
            "license": "l" * 200,
        }],
    )
    result = map_owner_response(req, owner_ok(req, rows=[row]))
    assert len(result.evidence[0].text) == 12_000
    assert result.evidence[0].sources[0].source_role == "r" * 100


@pytest.mark.parametrize(
    "mutate",
    [
        lambda body: body["items"][0].update(text="x" * 12_001),
        lambda body: body.update(warnings=["w"] * 11),
        lambda body: body.update(generated_at="2026-11-09T13:00:01+01:00"),
        lambda body: body["items"][0]["sources"][0].update(
            retrieved_at="2026-11-09T13:00:00+01:00"
        ),
    ],
)
def test_rejects_values_outside_owner_wire_limits_and_timestamp_contract(mutate):
    req = make_request()
    body = owner_ok(req)
    mutate(body)
    with pytest.raises(RetrievalUnavailable):
        map_owner_response(req, body)


@pytest.mark.parametrize(
    ("outcome", "exception"),
    [
        ("unavailable", RetrievalUnavailable),
        ("invalid_request", RetrievalInvalidRequest),
    ],
)
def test_owner_200_failure_outcomes_remain_distinct(outcome, exception):
    req = make_request()
    body = {**no_evidence(req), "outcome": outcome}
    with pytest.raises(exception):
        map_owner_response(req, body)


@pytest.mark.parametrize(
    ("status", "exception"),
    [
        (401, RetrievalAuthenticationFailed),
        (422, RetrievalInvalidRequest),
        (503, RetrievalUnavailable),
        (500, RetrievalUnavailable),
        (302, RetrievalUnavailable),
    ],
)
def test_http_statuses_are_typed_safe_and_never_follow_redirect(status, exception):
    req = make_request()
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(status, text="sensitive provider body and token")

    adapter = OwnerRagHttpAdapter(settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(exception) as raised:
        asyncio.run(adapter.retrieve(req))
    assert str(raised.value) not in "sensitive provider body and token test-owner-token"
    assert len(calls) == 1
    assert calls[0].method == "POST"
    assert str(calls[0].url) == "http://127.0.0.1:8765/v1/retrieve"
    assert calls[0].headers["authorization"] == "Bearer test-owner-token"


def test_adapter_sends_exact_payload_and_accepts_empty_result():
    req = make_request()
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json=no_evidence(req),
        )

    adapter = OwnerRagHttpAdapter(settings(), transport=httpx.MockTransport(handler))
    result = asyncio.run(adapter.retrieve(req))
    payload = json.loads(calls[0].content)
    assert calls[0].method == "POST"
    assert calls[0].headers["accept"] == "application/json"
    assert payload["request_id"] == str(req.request_id)
    assert payload["filters"] == {}
    assert result.status == "no_evidence"
    assert result.evidence == []
    assert len(calls) == 1


def test_adapter_maps_valid_ok_response_with_exact_owner_identity():
    req = make_request()

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/json; charset=utf-8"},
            json=owner_ok(req),
        )

    adapter = OwnerRagHttpAdapter(settings(), transport=httpx.MockTransport(handler))
    result = asyncio.run(adapter.retrieve(req))
    assert result.status == "ok"
    assert result.evidence[0].evidence_id == "evidence:test-only-001"
    assert result.evidence[0].canonical_entity_key == "test-only:place-001"
    assert result.evidence[0].claim_key == "test-only:description"
    assert result.evidence[0].canonical_id is None
    assert result.evidence[0].sources[0].source_id == "test-source-001"


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, headers={"content-type": "text/plain"}, text="not json"),
        httpx.Response(200, headers={"content-type": "application/json"}, content=b"{"),
    ],
)
def test_wrong_content_type_and_malformed_json_fail_safely(response):
    adapter = OwnerRagHttpAdapter(
        settings(), transport=httpx.MockTransport(lambda _request: response)
    )
    with pytest.raises(RetrievalUnavailable):
        asyncio.run(adapter.retrieve(make_request()))


@pytest.mark.parametrize("failure", [httpx.ConnectError("secret endpoint"), httpx.ReadTimeout("secret query")])
def test_connection_and_timeout_failures_are_safe_and_not_retried(failure):
    calls = []

    def handler(_request: httpx.Request) -> httpx.Response:
        calls.append(1)
        raise failure

    adapter = OwnerRagHttpAdapter(settings(), transport=httpx.MockTransport(handler))
    with pytest.raises(RetrievalUnavailable) as raised:
        asyncio.run(adapter.retrieve(make_request()))
    assert str(raised.value) == "Retrieval is temporarily unavailable."
    assert calls == [1]


def test_disabled_adapter_makes_no_request():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={})

    adapter = OwnerRagHttpAdapter(
        settings(tourism_rag_enabled=False), transport=httpx.MockTransport(handler)
    )
    with pytest.raises(RetrievalUnavailable):
        asyncio.run(adapter.retrieve(make_request()))
    assert calls == []


def test_settings_keep_owner_rag_disabled_by_default_and_fail_closed_outside_dev():
    default_settings = Settings(database_password="test-only-not-a-secret")
    assert default_settings.tourism_rag_enabled is False

    with pytest.raises(ValidationError):
        settings(app_env="production")

    with pytest.raises(ValidationError):
        settings(tourism_rag_api_token=None)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda req, body: {**body, "contract_version": "2.0.0"},
        lambda req, body: {**body, "request_id": "wrong-req-123"},
        lambda req, body: {**body, "unexpected": True},
        lambda req, body: {
            **body,
            "outcome": "ok",
            "items": [item(req, locale="ar")],
        },
        lambda req, body: {
            **body,
            "outcome": "ok",
            "items": [item(req, corpus="culinary_knowledge")],
        },
        lambda req, body: {
            **body,
            "outcome": "ok",
            "items": [item(req, content_hash="bad")],
        },
        lambda req, body: {
            **body,
            "outcome": "ok",
            "items": [
                item(
                    req,
                    sources=[
                        {
                            **item(req)["sources"][0],
                            "source_url": "http://example.invalid/not-https",
                        }
                    ],
                )
            ],
        },
        lambda req, body: {
            **body,
            "outcome": "ok",
            "items": [item(req), item(req)],
        },
    ],
)
def test_malformed_or_mismatched_owner_payload_fails_closed(mutate):
    req = make_request(limit=1)
    body = mutate(req, owner_ok(req))
    with pytest.raises(RetrievalUnavailable):
        map_owner_response(req, body)


def test_rag_identity_is_not_promoted_to_traveler_destination_identity():
    req = make_request()
    result = map_owner_response(req, owner_ok(req))
    hit = result.evidence[0]
    assert hit.canonical_entity_key == "test-only:place-001"
    assert hit.canonical_id is None
    # The application recommendation path remains a separate structured
    # catalogue path; this adapter creates no destination model or citation.
    assert not hasattr(hit, "destination_id")
