"""Real loopback HTTP contract proof using TourismRagApiV1's API code.

Only an explicitly test-only engine/approval fixture is used. This verifies
transport and mapping mechanics; it is not a populated-corpus quality result.
"""

from __future__ import annotations

import os
import secrets
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from secrets import token_urlsafe
from typing import Iterator
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.api import traveler as traveler_api
from app.api.auth import get_settings as auth_get_settings
from app.main import app
from app.modules.catalog.schemas import ProductionDestinationItem
from app.modules.identity.sms import FakeSmsAdapter
from app.modules.recommendation.contracts import EvidenceSource as RecommendationEvidenceSource
from app.modules.retrieval.contracts import RetrievalRequest, TrustedRetrievalFilters
from app.modules.retrieval.identity_mapping import (
    PublishedClaimProjection,
    PublishedSourceIdentity,
    map_owner_evidence,
)
from app.modules.retrieval.owner_http import OwnerRagHttpAdapter
from test_auth_postgres import connect, make_settings
from test_traveler_postgres import _request_headers, _sign_in

OWNER_ROOT = os.environ.get("OWNER_RAG_TEST_API_ROOT", "").strip()
pytestmark = pytest.mark.skipif(
    not OWNER_ROOT,
    reason="set OWNER_RAG_TEST_API_ROOT to the read-only TourismRagApiV1 source directory",
)

FIXTURE_KEY = "issue5-test-only-eram-garden"
FIXTURE_DOCUMENT = "issue5-test-only-document-v1"
FIXTURE_CLAIM = "issue5.test_only.claim"
FIXTURE_HASH = "8ff8c32c9331707af6144bb64ecebd32d175d0eba2725a675b1a5b34f2f34e15"
FIXTURE_RETRIEVED_AT = datetime(2020, 1, 1, tzinfo=UTC)
FIXTURE_VALID_FROM = datetime(2020, 1, 1, tzinfo=UTC)
FIXTURE_VALID_UNTIL = datetime(2099, 1, 1, tzinfo=UTC)


def _free_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@contextmanager
def _owner_api() -> Iterator[tuple[str, str]]:
    owner_root = Path(OWNER_ROOT).resolve()
    if not (owner_root / "owner_rag_api" / "app.py").is_file():
        raise RuntimeError("OWNER_RAG_TEST_API_ROOT does not contain TourismRagApiV1 API source")
    port = _free_loopback_port()
    token = token_urlsafe(32)
    env = {
        key: os.environ[key]
        for key in ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR")
        if os.environ.get(key)
    }
    env["OWNER_RAG_TEST_API_ROOT"] = str(owner_root)
    env["OWNER_RAG_TEST_API_TOKEN"] = token
    env["PYTHONPATH"] = os.pathsep.join((str(Path(__file__).parent), str(owner_root)))
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "owner_rag_test_api:app",
         "--host", "127.0.0.1", "--port", str(port), "--no-access-log", "--log-level", "error"],
        cwd=Path(__file__).parent,
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("test-only owner API process exited before ready")
            try:
                health = httpx.get(base_url + "/healthz", timeout=0.3, trust_env=False)
                if health.status_code == 200 and health.json().get("index_ready") is True:
                    break
            except httpx.RequestError:
                pass
            time.sleep(0.05)
        else:
            raise RuntimeError("test-only owner API did not become ready")
        yield base_url, token
    finally:
        process.terminate()
        try:
            process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=4)


def _projection(as_of: datetime, *, destination_id: int = 990_001) -> PublishedClaimProjection:
    source = PublishedSourceIdentity(
        source_id="990701",
        source_name="Issue 5 isolated test fixture",
        source_url="https://example.invalid/issue5-test-fixture",
        source_role="test_fixture",
        license="TEST ONLY",
        retrieved_at=FIXTURE_RETRIEVED_AT,
        valid_from=FIXTURE_VALID_FROM,
        valid_until=FIXTURE_VALID_UNTIL,
        is_verified=True,
        is_synthetic=False,
        is_revoked=False,
    )
    return PublishedClaimProjection(
        canonical_entity_key=FIXTURE_KEY,
        destination_id=destination_id,
        document_id=FIXTURE_DOCUMENT,
        claim_key=FIXTURE_CLAIM,
        content_hash=FIXTURE_HASH,
        locale="fa-IR",
        corpus="spatial_destinations",
        valid_from=FIXTURE_VALID_FROM,
        valid_until=FIXTURE_VALID_UNTIL,
        is_published=True,
        is_destination_verified=True,
        is_document_processed=True,
        is_synthetic=False,
        is_revoked=False,
        sources=(source,),
    )


def test_real_owner_api_http_positive_hit_maps_only_exact_current_identity():
    now = datetime.now(UTC).replace(microsecond=0)
    request = RetrievalRequest(
        request_id=uuid4(),
        query="TEST ONLY destination label",
        locale="fa-IR",
        corpus="spatial_destinations",
        limit=3,
        filters=TrustedRetrievalFilters(canonical_entity_key=FIXTURE_KEY),
        as_of=now,
    )
    with _owner_api() as (base_url, token):
        settings = Settings(
            _env_file=None,
            database_password=SecretStr("test-only-not-a-secret"),
        ).model_copy(update={
            "tourism_rag_enabled": True,
            "tourism_rag_api_url": base_url,
            "tourism_rag_api_token": SecretStr(token),
        })
        response = __import__("asyncio").run(
            OwnerRagHttpAdapter(settings).retrieve(request)
        )

    assert response.status == "ok"
    assert response.request_id == request.request_id
    assert len(response.evidence) == 1
    assert response.evidence[0].canonical_entity_key == FIXTURE_KEY
    assert response.evidence[0].document_id == FIXTURE_DOCUMENT
    assert response.evidence[0].claim_key == FIXTURE_CLAIM
    assert response.evidence[0].content_hash == FIXTURE_HASH

    projection = _projection(now)
    mapped = map_owner_evidence(response, request=request, published_claims=[projection])
    assert mapped.status == "mapped"
    assert mapped.withheld_count == 0
    assert len(mapped.mapped) == 1
    citation = mapped.mapped[0]
    assert citation.destination_id == 990_001
    assert citation.sources[0].source_url == "https://example.invalid/issue5-test-fixture"
    assert citation.text.startswith("TEST FIXTURE ONLY:")

    changed_hash = projection.model_copy(update={"content_hash": "0" * 64})
    revoked_source = projection.model_copy(update={
        "sources": (projection.sources[0].model_copy(update={"is_revoked": True}),),
    })
    unknown_source = projection.model_copy(update={
        "sources": (projection.sources[0].model_copy(update={"source_id": "unknown-source"}),),
    })
    for invalid_projection in (changed_hash, revoked_source, unknown_source):
        withheld = map_owner_evidence(
            response, request=request, published_claims=[invalid_projection]
        )
        assert withheld.status == "unmapped"
        assert withheld.mapped == ()
        assert withheld.withheld_count == 1


@pytest.mark.skipif(
    os.environ.get("AUTH_INTEGRATION_TESTS") != "1",
    reason="requires guarded disposable PostgreSQL 17; never shared port 55433",
)
def test_authenticated_recommendation_exposes_only_exact_mapped_test_citation(monkeypatch):
    """The owner API result reaches the real authenticated endpoint and is mapped.

    Catalogue and published-claim projections are process-local QA fixtures;
    the disposable DB's production views must stay empty. This is integration
    mechanics evidence, not editorial publication or traveler advice.
    """
    with _owner_api() as (base_url, token):
        settings = make_settings().model_copy(update={
            "auth_cookie_secure": False,
            "auth_allowed_origins": "https://testserver",
            "tourism_rag_enabled": True,
            "tourism_rag_api_url": base_url,
            "tourism_rag_api_token": SecretStr(token),
        })
        with connect(settings) as conn:
            assert conn.execute(
                "SELECT COUNT(*) AS n FROM knowledge.production_destinations"
            ).fetchone()["n"] == 0
            fixture_row = conn.execute(
                """SELECT destination_id FROM travel.itinerary_stops
                   WHERE is_synthetic=TRUE ORDER BY destination_id LIMIT 1"""
            ).fetchone()
        assert fixture_row is not None
        destination_id = str(fixture_row["destination_id"])
        source_time = FIXTURE_RETRIEVED_AT
        item = ProductionDestinationItem(
            destination_id=destination_id,
            destination_key=FIXTURE_KEY,
            canonical_name="TEST ONLY — no real destination",
            localized_names={
                "fa-IR": "مقصد آزمایشی غیرواقعی",
                "en-US": "Nonexistent test-only destination",
                "ar": "وجهة اختبارية غير حقيقية",
            },
            aliases=[],
            destination_type="heritage_site",
            province_name="TEST ONLY",
            city_name="TEST ONLY",
        )
        source = RecommendationEvidenceSource(
            destination_id=int(destination_id),
            source_id=990_701,
            source_name="Issue 5 isolated test fixture",
            source_url="https://example.invalid/issue5-test-fixture",
            source_role="test_fixture",
            evidence_note="TEST ONLY; no factual tourism claim.",
            retrieved_at=source_time,
            valid_from=FIXTURE_VALID_FROM,
            valid_until=FIXTURE_VALID_UNTIL,
        )
        projection = _projection(
            datetime.now(UTC), destination_id=int(destination_id)
        ).model_copy(update={
            "sources": (_projection(datetime.now(UTC)).sources[0].model_copy(
                update={"source_id": str(source.source_id)}
            ),),
        })

        def projection_loader(_settings):
            def load(keys, locale):
                if tuple(keys) == (FIXTURE_KEY,) and locale == "fa-IR":
                    return {FIXTURE_KEY: [projection]}
                return {}
            return load

        monkeypatch.setattr(
            traveler_api, "production_catalogue_bundle",
            lambda _settings: ([item], {destination_id: [source]}, {}),
        )
        loader_dependency = getattr(
            traveler_api, "get_published_claim_projection_loader", None
        )
        assert loader_dependency is not None, "coordinator route wiring is required"
        previous_settings = app.dependency_overrides.get(auth_get_settings)
        previous_loader = app.dependency_overrides.get(loader_dependency)
        previous_sms = getattr(app.state, "sms_adapter", None)
        app.dependency_overrides[auth_get_settings] = lambda: settings
        app.dependency_overrides[loader_dependency] = lambda: projection_loader(settings)
        sms = FakeSmsAdapter()
        app.state.sms_adapter = sms
        phone = f"+98912{secrets.randbelow(10_000_000):07d}"
        client = TestClient(app)
        user_id = None
        try:
            user_id, csrf = _sign_in(client, sms, phone)
            headers = _request_headers(csrf)
            created = client.post("/api/v1/conversations", headers=headers, json={
                "locale": "fa-IR",
                "request_text": "درخواست آزمایشی؛ هیچ دادهٔ شخصی یا مقصد واقعی ندارد",
                "extracted_requirements": {},
                "idempotency_key": "issue5-test-only-positive-http",
            })
            assert created.status_code == 201, created.status_code
            trip = created.json()["trip"]
            confirmed = client.patch(f"/api/v1/trips/{trip['trip_id']}", headers=headers, json={
                "expected_version": trip["version"],
                "confirmed_requirements": {
                    "confirmation_source": "traveler_reviewed",
                    "duration_days": 1,
                    "destinations": ["TEST ONLY"],
                    "constraints": [],
                },
                "destination_ids": [destination_id],
            })
            assert confirmed.status_code == 200, confirmed.status_code
            recommendation = client.post(
                f"/api/v1/trips/{trip['trip_id']}/recommendations",
                headers=headers,
                json={"selected_destination_ids": [destination_id]},
            )
            assert recommendation.status_code == 201, recommendation.text
            result = recommendation.json()
            assert result["status"] == "available"
            assert len(result["items"]) == 1
            response_item = result["items"][0]
            assert response_item["retrieval_evidence_status"] == "mapped"
            assert len(response_item["retrieval_evidence"]) == 1
            citation = response_item["retrieval_evidence"][0]
            assert citation["evidence_id"] == "issue5-test-only-evidence-v1"
            assert citation["canonical_entity_key"] == FIXTURE_KEY
            assert citation["destination_id"] == int(destination_id)
            assert citation["document_id"] == FIXTURE_DOCUMENT
            assert citation["claim_key"] == FIXTURE_CLAIM
            assert citation["content_hash"] == FIXTURE_HASH
            assert citation["locale"] == "fa-IR"
            assert citation["corpus"] == "spatial_destinations"
            assert citation["text"] == (
                "TEST FIXTURE ONLY: identity-mapping transport evidence; not visitor advice."
            )
            assert citation["sources"][0]["source_id"] == str(source.source_id)
            assert citation["sources"][0]["source_url"] == source.source_url
            assert citation["sources"][0]["license"] == "TEST ONLY"
            reopened = client.get(f"/api/v1/trips/{trip['trip_id']}/recommendations")
            assert reopened.status_code == 200, reopened.status_code
            reopened_citation = reopened.json()["items"][0]["retrieval_evidence"][0]
            assert reopened_citation == citation
            # The test-only injection is not a production publication write.
            assert client.get("/api/v1/catalog/destinations").json()["count"] == 0
            with connect(settings) as conn:
                assert conn.execute(
                    "SELECT COUNT(*) AS n FROM knowledge.production_destinations"
                ).fetchone()["n"] == 0
        finally:
            client.close()
            if previous_settings is None:
                app.dependency_overrides.pop(auth_get_settings, None)
            else:
                app.dependency_overrides[auth_get_settings] = previous_settings
            if previous_loader is None:
                app.dependency_overrides.pop(loader_dependency, None)
            else:
                app.dependency_overrides[loader_dependency] = previous_loader
            app.state.sms_adapter = previous_sms
            with connect(settings) as conn, conn.transaction():
                if user_id is not None:
                    conn.execute("DELETE FROM identity.web_sessions WHERE user_id=%s", (user_id,))
                    conn.execute("DELETE FROM identity.users WHERE user_id=%s", (user_id,))
                conn.execute("DELETE FROM identity.otp_challenges WHERE phone_e164=%s", (phone,))
                conn.execute("DELETE FROM identity.verified_phones WHERE phone_e164=%s", (phone,))
