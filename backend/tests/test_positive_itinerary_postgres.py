"""Positive 15-day itinerary persistence through REAL API and disposable PostgreSQL.

This is deliberately NOT editorial publication proof. The catalogue adapter is
monkeypatched only inside this TestClient test process using existing synthetic
QA destination IDs. All itinerary/recommendation writes and reads go through
the real authenticated FastAPI and PostgreSQL paths. No real source, place,
model call, remote service, or production view is modified.
"""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api import traveler as traveler_api
from app.api.auth import get_settings
from app.main import app
from app.modules.catalog.schemas import ProductionDestinationItem
from app.modules.identity.sms import FakeSmsAdapter
from app.modules.recommendation.contracts import EvidenceSource
from app.modules.retrieval.contracts import RetrievalRequest, RetrievalResponse
from test_auth_postgres import connect, make_settings
from test_traveler_postgres import _request_headers, _sign_in

pytestmark = pytest.mark.skipif(
    os.environ.get("AUTH_INTEGRATION_TESTS") != "1",
    reason="requires guarded, disposable PostgreSQL 17; never shared port 55433",
)


class EmptyOwnerRetrievalPort:
    """Explicitly simulated owner boundary; never returns factual evidence."""

    def __init__(self):
        self.requests: list[RetrievalRequest] = []

    async def retrieve(self, request: RetrievalRequest, /) -> RetrievalResponse:
        self.requests.append(request)
        return RetrievalResponse(
            request_id=request.request_id,
            corpus=request.corpus,
            locale=request.locale,
            status="no_evidence",
            corpus_version="explicit-empty-test-only",
            retrieval_version="test-fake-v1",
            evidence=[],
        )


def _test_only_catalogue(settings):
    """Return synthetic QA identities from a table the app role may read.

    The app role MUST NOT read raw knowledge.destinations or grant itself
    permissions to unpublished data. Synthetic QA itinerary rows already
    reference the actual FK IDs needed for the persistence layer.
    """
    with connect(settings) as conn:
        published_count = conn.execute(
            "SELECT COUNT(*) AS n FROM knowledge.production_destinations"
        ).fetchone()["n"]
        assert published_count == 0, "This test requires an empty approved catalogue"
        rows = conn.execute(
            """SELECT DISTINCT destination_id FROM travel.itinerary_stops
               WHERE is_synthetic=TRUE ORDER BY destination_id LIMIT 4"""
        ).fetchall()
    assert len(rows) == 4, "Missing four existing synthetic QA fixture destinations"

    entries = []
    sources = {}
    for index, row in enumerate(rows, start=1):
        key = str(row["destination_id"])
        entries.append(ProductionDestinationItem(
            destination_id=key,
            destination_key=f"QA-TEST-ONLY-{index}",
            canonical_name=f"NONEXISTENT QA PLACE {index}",
            localized_names={
                "fa-IR": f"مقصد ساختگی آزمون {index}",
                "en-US": f"Synthetic QA place {index}",
                "ar": f"مكان اختبار اصطناعي {index}",
            },
            aliases=[],
            destination_type="heritage_site",
            province_name="TEST ONLY",
            city_name="TEST ONLY",
        ))
        sources[key] = [EvidenceSource(
            destination_id=int(key),
            source_id=90_000 + index,
            source_name="FAKE EVIDENCE - TEST ONLY",
            source_url=f"https://example.invalid/qa-only/{index}",
            source_role="synthetic_test_only",
            evidence_note="Fabricated only to verify API/PG mechanics in disposable DB.",
            retrieved_at=datetime.now(UTC),
        )]
    return entries, sources, {}


def test_positive_fifteen_day_itinerary_api_persists_edits_and_reopens(monkeypatch):
    # make_settings() enforces loopback, ephemeral non-shared DB, private marker,
    # least-privilege role, and PostgreSQL 17 identity before any write.
    settings = make_settings().model_copy(update={
        "auth_cookie_secure": False,
        "auth_allowed_origins": "https://testserver",
        "tourism_rag_enabled": True,
    })
    owner_retrieval = EmptyOwnerRetrievalPort()
    fake_items, fake_sources, fake_metadata = _test_only_catalogue(settings)
    ids = [item.destination_id for item in fake_items]

    # Scope this fake ONLY to the in-process traveler endpoint, not the
    # catalogue endpoint, deployment settings, knowledge views or shared DB.
    monkeypatch.setattr(
        traveler_api, "production_catalogue_bundle",
        lambda _settings: (fake_items, fake_sources, fake_metadata),
    )
    prior_settings = app.dependency_overrides.get(get_settings)
    prior_retrieval = app.dependency_overrides.get(traveler_api.get_owner_retrieval_port)
    prior_sms = getattr(app.state, "sms_adapter", None)
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[traveler_api.get_owner_retrieval_port] = lambda: owner_retrieval
    sms = FakeSmsAdapter()
    app.state.sms_adapter = sms
    phone = f"+98912{secrets.randbelow(10_000_000):07d}"
    client = TestClient(app)
    user_id = None
    try:
        user_id, csrf = _sign_in(client, sms, phone)
        headers = _request_headers(csrf)

        first = client.post(
            "/api/v1/conversations", headers=headers, json={
                "locale": "fa-IR",
                "request_text": "یک سفر پانزده روزه با مقصدهای آزمایشی",
                "extracted_requirements": {
                    "durationDays": {"value": 15, "status": "extracted"},
                },
                "idempotency_key": str(uuid4()),
            },
        )
        assert first.status_code == 201, first.status_code
        trip = first.json()["trip"]
        trip_id = trip["trip_id"]
        assert trip["confirmed_requirements"] == {}

        review = client.patch(
            f"/api/v1/trips/{trip_id}", headers=headers, json={
                "expected_version": trip["version"],
                "confirmed_requirements": {
                    "confirmation_source": "traveler_reviewed",
                    "duration_days": 15,
                    "destinations": ["TEST ONLY"],
                    "constraints": [],
                },
                "destination_ids": ids,
            },
        )
        assert review.status_code == 200, review.status_code
        assert review.json()["duration_days"] == 15
        assert review.json()["confirmed_requirements"]["confirmation_source"] == "traveler_reviewed"

        suggestion = client.post(
            f"/api/v1/trips/{trip_id}/recommendations",
            headers=headers,
            json={"selected_destination_ids": ids},
        )
        assert suggestion.status_code == 201, suggestion.text
        recommendation = suggestion.json()
        assert recommendation["status"] == "available", recommendation["reason_code"]
        assert len(recommendation["items"]) == 4
        # The recommendation endpoint calls the injected RetrievalPort with
        # an exact approved-projection key and canonical name, never raw trip
        # text. The explicit no_evidence result does not become a false hit.
        assert len(owner_retrieval.requests) == 1
        retrieval_request = owner_retrieval.requests[0]
        assert retrieval_request.corpus == "spatial_destinations"
        assert retrieval_request.filters.canonical_entity_key.startswith("QA-TEST-ONLY-")
        assert retrieval_request.query == fake_items[0].localized_names["fa-IR"]
        assert len(retrieval_request.query) < 80
        assert all(
            "example.invalid/qa-only" in item["evidence"][0]["source_url"]
            for item in recommendation["items"]
        )

        created = client.post(
            f"/api/v1/trips/{trip_id}/itineraries",
            headers=headers, json={
                "recommendation_request_id": recommendation["recommendation_request_id"],
                "day_count": 15, "locale": "fa-IR",
            },
        )
        assert created.status_code == 201, created.text
        itinerary = created.json()
        assert itinerary["day_count"] == 15
        assert itinerary["status"] == "partial"
        assert len(itinerary["stops"]) == 4
        assert itinerary["unplanned_days"] == list(range(5, 16))
        itinerary_id = itinerary["itinerary_id"]

        revised = client.put(
            f"/api/v1/itineraries/{itinerary_id}",
            headers=headers, json={
                "expected_revision": itinerary["revision"],
                "title_by_locale": {"fa-IR": "صرفاً آزمون ۱۵ روزه"},
                "stops": [
                    {
                        "recommendation_id": stop["recommendation_id"],
                        "day_number": index + 1, "stop_order": 1,
                        "notes_by_locale": {
                            "fa-IR": f"یادداشت آزمایشی ویرایش‌شده {index + 1}"
                        },
                    }
                    for index, stop in enumerate(itinerary["stops"])
                ],
            },
        )
        assert revised.status_code == 200, revised.status_code
        updated = revised.json()
        assert updated["revision"] == itinerary["revision"] + 1

        reopened = client.get(f"/api/v1/itineraries/{itinerary_id}")
        assert reopened.status_code == 200, reopened.status_code
        saved = reopened.json()
        assert saved["revision"] == updated["revision"]
        assert saved["day_count"] == 15
        assert saved["status"] == "partial"
        assert len(saved["stops"]) == 4
        assert saved["unplanned_days"] == list(range(5, 16))
        assert saved["stops"][0]["notes_by_locale"]["fa-IR"].startswith(
            "یادداشت آزمایشی ویرایش‌شده"
        )
        assert client.get(f"/api/v1/trips/{trip_id}").json()[
            "latest_itinerary_id"
        ] == itinerary_id

        # The actual published catalogue remains empty in both HTTP and PG.
        catalogue = client.get("/api/v1/catalog/destinations")
        assert catalogue.status_code == 200
        assert catalogue.json()["count"] == 0
        with connect(settings) as conn:
            assert conn.execute(
                "SELECT COUNT(*) AS n FROM knowledge.production_destinations"
            ).fetchone()["n"] == 0
            row = conn.execute(
                """SELECT i.day_count,i.revision,COUNT(s.itinerary_stop_id) AS stops
                   FROM travel.itineraries i
                   JOIN travel.itinerary_stops s USING (itinerary_id)
                   WHERE i.itinerary_id=%s GROUP BY i.day_count,i.revision""",
                (itinerary_id,),
            ).fetchone()
            assert (row["day_count"], row["revision"], row["stops"]) == (15, 2, 4)

    finally:
        client.close()
        if prior_settings is None:
            app.dependency_overrides.pop(get_settings, None)
        else:
            app.dependency_overrides[get_settings] = prior_settings
        if prior_retrieval is None:
            app.dependency_overrides.pop(traveler_api.get_owner_retrieval_port, None)
        else:
            app.dependency_overrides[traveler_api.get_owner_retrieval_port] = prior_retrieval
        app.state.sms_adapter = prior_sms
        with connect(settings) as conn, conn.transaction():
            if user_id is not None:
                conn.execute("DELETE FROM identity.web_sessions WHERE user_id=%s", (user_id,))
            conn.execute(
                "DELETE FROM identity.otp_challenges WHERE phone_e164=%s", (phone,)
            )
            conn.execute(
                "DELETE FROM identity.verified_phones WHERE phone_e164=%s", (phone,)
            )
            if user_id is not None:
                conn.execute("DELETE FROM identity.users WHERE user_id=%s", (user_id,))
