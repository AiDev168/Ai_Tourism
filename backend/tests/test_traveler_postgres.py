"""End-to-end traveler persistence checks against the guarded disposable PG17 target."""

from __future__ import annotations

import os
import secrets
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.auth import get_settings
from app.core.config import Settings
from app.main import app
from app.modules.identity.sms import FakeSmsAdapter
from test_auth_postgres import connect, make_settings

pytestmark = pytest.mark.skipif(
    os.environ.get("AUTH_INTEGRATION_TESTS") != "1",
    reason="requires the explicitly selected disposable PostgreSQL integration database",
)

TEST_PHONES = tuple(
    f"+98912{number:07d}" for number in secrets.SystemRandom().sample(range(10_000_000), 2)
)


def _clean_test_records(settings: Settings) -> None:
    with connect(settings) as connection, connection.transaction():
        connection.execute(
            """DELETE FROM identity.web_sessions
               WHERE user_id IN (SELECT user_id FROM identity.users WHERE phone_e164 = ANY(%s))""",
            (list(TEST_PHONES),),
        )
        connection.execute("DELETE FROM identity.verified_phones WHERE phone_e164=ANY(%s)", (list(TEST_PHONES),))
        connection.execute("DELETE FROM identity.otp_challenges WHERE phone_e164=ANY(%s)", (list(TEST_PHONES),))
        connection.execute("DELETE FROM identity.auth_rate_limits")
        connection.execute(
            "DELETE FROM identity.users WHERE phone_e164=ANY(%s) AND is_synthetic=FALSE",
            (list(TEST_PHONES),),
        )


def _count(connection, table: str, column: str, value) -> int:
    # Table/column are fixed literals in this test, never user input.
    return connection.execute(
        f"SELECT COUNT(*) AS n FROM {table} WHERE {column}=%s", (value,)
    ).fetchone()["n"]


def _sign_in(client: TestClient, sms: FakeSmsAdapter, phone: str) -> tuple[str, str]:
    challenge = client.post(
        "/api/v1/auth/otp/challenges", json={"phone_number": phone, "locale": "en-US"}
    )
    assert challenge.status_code == 202
    challenge_data = challenge.json()
    assert challenge_data["status"] == "accepted"
    assert challenge_data["challenge_id"]
    assert "verification_code" not in challenge.text
    message = sms.take_messages()[0]
    assert message.recipient == phone
    verify = client.post(
        "/api/v1/auth/otp/verify",
        json={"challenge_id": challenge_data["challenge_id"], "code": message.verification_code},
    )
    assert verify.status_code == 200
    assert verify.headers["cache-control"] == "no-store"
    csrf_token = verify.json()["csrf_token"]
    assert csrf_token
    session_cookie = "rahgard_session"
    assert session_cookie in verify.cookies
    return verify.json()["user"]["user_id"], csrf_token


def _request_headers(csrf: str) -> dict[str, str]:
    return {"Origin": "https://testserver", "X-CSRF-Token": csrf}


def test_real_app_persists_owner_scoped_trip_and_deletes_all_content():
    settings: Settings = make_settings()
    settings = settings.model_copy(update={
        "auth_cookie_secure": False,
        "auth_allowed_origins": "https://testserver",
    })
    _clean_test_records(settings)
    sms = FakeSmsAdapter()
    previous_settings = app.dependency_overrides.get(get_settings)
    previous_sms = getattr(app.state, "sms_adapter", None)
    app.dependency_overrides[get_settings] = lambda: settings
    app.state.sms_adapter = sms
    client_a = TestClient(app)
    client_b = TestClient(app)
    try:
        user_a, csrf_a = _sign_in(client_a, sms, TEST_PHONES[0])
        user_b, csrf_b = _sign_in(client_b, sms, TEST_PHONES[1])
        assert user_a != user_b

        request_body = {
            "locale": "en-US",
            "request_text": "Please plan a four-day trip; keep the original request.",
            "extracted_requirements": {
                "durationDays": {"value": 4},
                "origin": {"value": None},
            },
            "confirmed_requirements": {"unreviewed_claim": "not traveler-confirmed"},
            "destination_ids": ["987654"],
            "idempotency_key": "traveler-pg-create-0001",
        }

        # Unsafe cookie-authenticated requests require both exact Origin and
        # the session-bound CSRF token; invalid attempts do not create a row.
        missing_csrf = client_a.post("/api/v1/conversations", json=request_body)
        missing_origin = client_a.post(
            "/api/v1/conversations", json=request_body,
            headers={"X-CSRF-Token": csrf_a},
        )
        wrong_origin = client_a.post(
            "/api/v1/conversations", json=request_body,
            headers={"Origin": "https://attacker.invalid", "X-CSRF-Token": csrf_a},
        )
        wrong_csrf = client_a.post(
            "/api/v1/conversations", json=request_body,
            headers={"Origin": "https://testserver", "X-CSRF-Token": csrf_b},
        )
        assert missing_csrf.status_code == 403
        assert missing_origin.status_code == 403
        assert wrong_origin.status_code == 403
        assert wrong_csrf.status_code == 403
        with connect(settings) as connection:
            assert connection.execute(
                "SELECT COUNT(*) AS n FROM conversation.conversations WHERE user_id=%s",
                (user_a,),
            ).fetchone()["n"] == 0

        created = client_a.post(
            "/api/v1/conversations", json=request_body, headers=_request_headers(csrf_a)
        )
        assert created.status_code == 201
        assert created.headers["cache-control"] == "no-store"
        assert created.json()["initial_message"]["content"] == request_body["request_text"]
        conversation = created.json()["conversation"]
        trip = created.json()["trip"]
        conversation_id = conversation["conversation_id"]
        trip_id = trip["trip_id"]
        assert trip["confirmed_requirements"] == {}
        assert trip["destination_ids"] == []
        with connect(settings) as connection:
            persisted_profile = connection.execute(
                "SELECT origin_text,duration_days,confirmed_requirements FROM travel.trips WHERE trip_id=%s",
                (trip_id,),
            ).fetchone()
            assert persisted_profile["origin_text"] is None
            assert persisted_profile["duration_days"] == 4
            assert persisted_profile["confirmed_requirements"] == {}

        confirmed = client_a.patch(
            f"/api/v1/trips/{trip_id}",
            headers=_request_headers(csrf_a),
            json={
                "expected_version": trip["version"],
                "confirmed_requirements": {
                    "durationDays": {"value": 4},
                    "origin": {"value": None},
                },
                "destination_ids": [],
            },
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["duration_days"] == 4

        # This profile has no requested or resolved destination, so the API
        # must request destination selection rather than infer an empty-catalogue
        # result. It must still return no candidate.
        recommendations = client_a.post(
            f"/api/v1/trips/{trip_id}/recommendations",
            headers=_request_headers(csrf_a),
            json={"selected_destination_ids": []},
        )
        assert recommendations.status_code == 201
        recommendation_body = recommendations.json()
        assert recommendation_body["items"] == []
        assert recommendation_body["status"] == "needs_confirmation"
        assert recommendation_body["reason_code"] == "destination_selection_required"
        recommendation_id = recommendation_body["recommendation_request_id"]

        itinerary = client_a.post(
            f"/api/v1/trips/{trip_id}/itineraries",
            headers=_request_headers(csrf_a),
            json={
                "recommendation_request_id": recommendation_id,
                "day_count": 1,
                "locale": "en-US",
            },
        )
        assert itinerary.status_code == 409
        assert itinerary.json() == {"error": {"code": "no_eligible_recommendations"}}

        listed = client_a.get("/api/v1/conversations?limit=10")
        reopened = client_a.get(f"/api/v1/conversations/{conversation_id}")
        assert listed.status_code == reopened.status_code == 200
        assert any(item["conversation_id"] == conversation_id for item in listed.json()["items"])
        assert reopened.json()["messages"][0]["content"] == request_body["request_text"]

        # Another authenticated account cannot read, mutate, or delete IDs
        # learned from a different owner's response.
        assert client_b.get(f"/api/v1/conversations/{conversation_id}").status_code == 404
        assert client_b.get(f"/api/v1/trips/{trip_id}").status_code == 404
        assert client_b.patch(
            f"/api/v1/trips/{trip_id}",
            headers=_request_headers(csrf_b),
            json={"expected_version": 2, "confirmed_requirements": {}, "destination_ids": []},
        ).status_code == 404
        assert client_b.delete(f"/api/v1/trips/{trip_id}", headers=_request_headers(csrf_b)).status_code == 404

        # Deleting the last trip removes its conversation, request, and all raw
        # messages. The route response deliberately makes no ownership hint.
        deleted_trip = client_a.delete(
            f"/api/v1/trips/{trip_id}", headers=_request_headers(csrf_a)
        )
        assert deleted_trip.status_code == 200
        assert client_a.get(f"/api/v1/trips/{trip_id}").status_code == 404
        assert client_a.get(f"/api/v1/conversations/{conversation_id}").status_code == 404
        with connect(settings) as connection:
            assert _count(connection, "travel.trips", "trip_id", trip_id) == 0
            assert _count(connection, "conversation.conversations", "conversation_id", conversation_id) == 0
            assert _count(connection, "conversation.messages", "conversation_id", conversation_id) == 0
            assert _count(connection, "recommendation.recommendation_requests", "trip_id", trip_id) == 0
            assert _count(connection, "travel.itineraries", "trip_id", trip_id) == 0

        # Explicit conversation deletion also removes its nested trip and text.
        second = client_a.post(
            "/api/v1/conversations",
            headers=_request_headers(csrf_a),
            json={**request_body, "idempotency_key": "traveler-pg-create-0002"},
        )
        assert second.status_code == 201
        second_conversation_id = second.json()["conversation"]["conversation_id"]
        second_trip_id = second.json()["trip"]["trip_id"]
        deleted_conversation = client_a.delete(
            f"/api/v1/conversations/{second_conversation_id}",
            headers=_request_headers(csrf_a),
        )
        assert deleted_conversation.status_code == 200
        with connect(settings) as connection:
            assert _count(connection, "conversation.conversations", "conversation_id", second_conversation_id) == 0
            assert _count(connection, "travel.trips", "trip_id", second_trip_id) == 0
            assert _count(connection, "conversation.messages", "conversation_id", second_conversation_id) == 0

        # Account deletion is explicit, CSRF protected, and removes the
        # account's remaining identity/session and traveler-owned data.
        account_trip = client_b.post(
            "/api/v1/conversations",
            headers=_request_headers(csrf_b),
            json={**request_body, "idempotency_key": "traveler-pg-account-0001"},
        )
        assert account_trip.status_code == 201
        account_conversation_id = account_trip.json()["conversation"]["conversation_id"]
        account_trip_id = account_trip.json()["trip"]["trip_id"]
        user_b_uuid = UUID(user_b)
        user_a_uuid = UUID(user_a)
        test_external_link_id = uuid4()
        with connect(settings) as connection, connection.transaction():
            # These owner-scoped records are created only in the guarded,
            # disposable integration database. Keep User A records as a
            # sentinel proving User B deletion does not cross ownership.
            connection.execute(
                """INSERT INTO operations.feedback
                   (feedback_id,user_id,trip_id,feedback_type,comment,is_synthetic)
                   VALUES (%s,%s,%s,'other','test-owned deletion record',FALSE),
                          (%s,%s,NULL,'other','other-owner preservation record',FALSE)""",
                (uuid4(), user_b_uuid, account_trip_id, uuid4(), user_a_uuid),
            )
            connection.execute(
                """INSERT INTO integration.external_links
                   (external_link_id,provider_name,service_type,label_fa,target_url,is_active,is_synthetic)
                   VALUES (%s,'test-only','official_info','آزمون','https://example.invalid/test',TRUE,TRUE)""",
                (test_external_link_id,),
            )
            connection.execute(
                """INSERT INTO integration.outbound_clicks
                   (external_link_id,user_id,trip_id,is_synthetic)
                   VALUES (%s,%s,%s,FALSE),(%s,%s,NULL,FALSE)""",
                (test_external_link_id, user_b_uuid, account_trip_id, test_external_link_id, user_a_uuid),
            )
            challenge_ids_by_phone = connection.execute(
                """SELECT phone_e164, array_agg(challenge_id) AS ids
                   FROM identity.otp_challenges WHERE phone_e164=ANY(%s::text[])
                   GROUP BY phone_e164""",
                (list(TEST_PHONES),),
            ).fetchall()
            challenge_ids = {row["phone_e164"]: row["ids"] for row in challenge_ids_by_phone}
            assert all(phone in challenge_ids for phone in TEST_PHONES)
            user_a_challenge_ids = challenge_ids[TEST_PHONES[0]]
            user_b_challenge_ids = challenge_ids[TEST_PHONES[1]]
        account_delete = client_b.delete("/api/v1/auth/me", headers=_request_headers(csrf_b))
        assert account_delete.status_code == 204
        assert client_b.get("/api/v1/auth/me").status_code == 401
        with connect(settings) as connection:
            assert _count(connection, "identity.users", "user_id", user_b_uuid) == 0
            assert _count(connection, "identity.web_sessions", "user_id", user_b_uuid) == 0
            assert _count(connection, "conversation.conversations", "conversation_id", account_conversation_id) == 0
            assert _count(connection, "travel.trips", "trip_id", account_trip_id) == 0
            assert _count(connection, "conversation.messages", "conversation_id", account_conversation_id) == 0
            assert _count(connection, "operations.feedback", "user_id", user_b_uuid) == 0
            assert _count(connection, "operations.feedback", "user_id", user_a_uuid) == 1
            assert _count(connection, "integration.outbound_clicks", "user_id", user_b_uuid) == 0
            assert _count(connection, "integration.outbound_clicks", "user_id", user_a_uuid) == 1
            assert connection.execute(
                "SELECT COUNT(*) AS n FROM identity.otp_challenges WHERE challenge_id=ANY(%s::uuid[])",
                (user_b_challenge_ids,),
            ).fetchone()["n"] == 0
            assert connection.execute(
                "SELECT COUNT(*) AS n FROM identity.otp_challenges WHERE challenge_id=ANY(%s::uuid[])",
                (user_a_challenge_ids,),
            ).fetchone()["n"] == len(user_a_challenge_ids)
    finally:
        client_a.close()
        client_b.close()
        app.dependency_overrides.pop(get_settings, None)
        if previous_settings is not None:
            app.dependency_overrides[get_settings] = previous_settings
        app.state.sms_adapter = previous_sms
        _clean_test_records(settings)
        with connect(settings) as connection, connection.transaction():
            connection.execute(
                "DELETE FROM integration.outbound_clicks WHERE external_link_id=%s",
                (test_external_link_id,),
            )
            connection.execute(
                "DELETE FROM integration.external_links WHERE external_link_id=%s",
                (test_external_link_id,),
            )
