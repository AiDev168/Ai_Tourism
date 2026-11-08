"""Focused API contract tests; database ownership/isolation is covered by guarded PG tests."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import logging
from fastapi.testclient import TestClient

from app.api.traveler import get_traveler_repository
from app.api.auth import require_authenticated_csrf
from app.main import app
from app.modules.identity.authorization import Principal, get_principal
from app.modules.trip.repository import TravelerConflict


OWNER = UUID("9d6c521e-6d84-4a8c-b463-e0fe5a2dc0d1")
OTHER = UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")
SESSION = UUID("2d878a93-1d6d-4e9a-9910-b5d25ac77fe2")
CONVERSATION = UUID("08b9205a-33e8-4c65-a8f9-a1ff5821f260")
TRIP = UUID("cde18fda-9034-4ad2-a6f5-dcbbe175e488")
MESSAGE = UUID("1807a74f-3879-4acb-8f5d-a460dc0d8251")
RAW_REQUEST = "secret traveler text 7-day Shiraz request"


def _trip(user_id: UUID) -> dict:
    now = datetime.now(UTC)
    return {
        "trip_id": TRIP,
        "conversation_id": CONVERSATION,
        "version": 1,
        "locale": "en-US",
        "original_request": RAW_REQUEST,
        "extracted_requirements": {},
        "confirmed_requirements": {},
        "destination_ids": [],
        "duration_days": 7,
        "traveler_count": None,
        "budget_amount_original": None,
        "budget_currency_iso": None,
        "budget_unit": None,
        "latest_recommendation_request_id": None,
        "latest_itinerary_id": None,
        "trip_status": "draft",
        "created_at": now,
        "updated_at": now,
    }


def _conversation(user_id: UUID) -> dict:
    now = datetime.now(UTC)
    return {
        "conversation_id": CONVERSATION,
        "locale": "en-US",
        "version": 1,
        "started_at": now,
        "updated_at": now,
        "last_message_at": now,
        "trips": [_trip(user_id)],
        "messages": [{
            "message_id": MESSAGE,
            "conversation_id": CONVERSATION,
            "trip_id": TRIP,
            "role": "user",
            "content": RAW_REQUEST,
            "created_at": now,
        }],
    }


class FakeTravelerRepository:
    def __init__(self, owner_id: UUID = OWNER):
        self.owner_id = owner_id
        self.calls: list[tuple[str, UUID]] = []
        self.deleted: set[tuple[str, UUID]] = set()

    def conversation(self, user_id: UUID, conversation_id: UUID):
        self.calls.append(("conversation", user_id))
        if user_id != self.owner_id or conversation_id != CONVERSATION:
            return None
        return _conversation(user_id)

    def trip(self, user_id: UUID, trip_id: UUID):
        self.calls.append(("trip", user_id))
        if user_id != self.owner_id or trip_id != TRIP:
            return None
        return _trip(user_id)

    def list_conversations(self, user_id: UUID, limit: int, cursor):
        self.calls.append(("list", user_id))
        summary = _conversation(user_id)
        summary.pop("messages")
        return ([summary] if user_id == self.owner_id else []), None

    def delete_trip(self, user_id: UUID, trip_id: UUID):
        self.calls.append(("delete_trip", user_id))
        if user_id != self.owner_id or trip_id != TRIP:
            return None
        self.deleted.add(("trip", trip_id))
        return trip_id

    def delete_conversation(self, user_id: UUID, conversation_id: UUID):
        self.calls.append(("delete_conversation", user_id))
        if user_id != self.owner_id or conversation_id != CONVERSATION:
            return False
        self.deleted.add(("conversation", conversation_id))
        return True

    def create_conversation(self, **kwargs):
        self.calls.append(("create", kwargs["user_id"]))
        self.created = kwargs
        return CONVERSATION, TRIP, MESSAGE, True

    def create_trip_in_conversation(self, **kwargs):
        self.calls.append(("create_trip", kwargs["user_id"]))
        self.created = kwargs
        return CONVERSATION, TRIP, MESSAGE, True


def _client(repository: FakeTravelerRepository | None = None, principal: Principal | None = None):
    repository = repository or FakeTravelerRepository()
    app.dependency_overrides[get_traveler_repository] = lambda: repository
    if principal is not None:
        app.dependency_overrides[get_principal] = lambda: principal
        # These mock-principal tests cover route ownership/response contracts;
        # actual session-bound CSRF is exercised in test_traveler_postgres.py.
        app.dependency_overrides[require_authenticated_csrf] = lambda: None
    return TestClient(app), repository


def _clear_overrides():
    app.dependency_overrides.clear()


def test_persisted_traveler_routes_reject_anonymous_requests():
    client, _ = _client()
    try:
        response = client.get("/api/v1/conversations")
        assert response.status_code in (401, 503)
        assert response.status_code != 200
    finally:
        _clear_overrides()


def test_create_conversation_uses_server_principal_and_not_client_identity_fields():
    client, repository = _client(principal=Principal(OWNER, SESSION))
    try:
        response = client.post("/api/v1/conversations", json={
            "locale": "en-US",
            "request_text": RAW_REQUEST,
            "extracted_requirements": {"duration_days": 7},
            "confirmed_requirements": {},
            "destination_ids": [],
            "idempotency_key": "request-0001",
            "user_id": str(OTHER),
        })
        assert response.status_code == 422
        assert repository.calls == []

        response = client.post("/api/v1/conversations", json={
            "locale": "en-US",
            "request_text": RAW_REQUEST,
            "extracted_requirements": {"duration_days": 7},
            "confirmed_requirements": {"unreviewed_claim": "must be ignored"},
            "destination_ids": ["987654"],
            "idempotency_key": "request-0002",
        })
        assert response.status_code == 201
        assert response.headers["cache-control"] == "no-store"
        assert repository.created["user_id"] == OWNER
        assert repository.created["confirmed_requirements"] == {}
        assert repository.created["destination_ids"] == []
        assert response.json()["trip"]["confirmed_requirements"] == {}
        assert response.json()["trip"]["destination_ids"] == []
        assert response.json()["initial_message"]["content"] == RAW_REQUEST
    finally:
        _clear_overrides()


def test_foreign_and_missing_conversation_ids_are_indistinguishable():
    client, _ = _client(principal=Principal(OTHER, SESSION))
    try:
        foreign = client.get(f"/api/v1/conversations/{CONVERSATION}")
        missing = client.get(f"/api/v1/conversations/{uuid4()}")
        assert (foreign.status_code, foreign.json()) == (404, {"error": {"code": "resource_not_found"}})
        assert (missing.status_code, missing.json()) == (404, {"error": {"code": "resource_not_found"}})
        assert foreign.headers["cache-control"] == "no-store"
    finally:
        _clear_overrides()


def test_list_is_server_owner_scoped_and_no_store():
    client, repository = _client(principal=Principal(OWNER, SESSION))
    try:
        response = client.get("/api/v1/conversations?limit=10")
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert len(response.json()["items"]) == 1
        assert repository.calls == [("list", OWNER)]
    finally:
        _clear_overrides()


def test_foreign_trip_is_not_read_or_deleted_and_owned_delete_is_scoped():
    client, repository = _client(principal=Principal(OTHER, SESSION))
    try:
        assert client.get(f"/api/v1/trips/{TRIP}").status_code == 404
        assert client.delete(f"/api/v1/trips/{TRIP}").status_code == 404
        assert repository.deleted == set()
        assert all(user_id == OTHER for _, user_id in repository.calls)
    finally:
        _clear_overrides()

    client, repository = _client(principal=Principal(OWNER, SESSION))
    try:
        response = client.delete(f"/api/v1/conversations/{CONVERSATION}")
        assert response.status_code == 200
        assert response.json() == {"deleted": True}
        assert repository.deleted == {("conversation", CONVERSATION)}
    finally:
        _clear_overrides()


def test_trip_input_limits_and_locale_are_enforced_before_repository_call():
    client, repository = _client(principal=Principal(OWNER, SESSION))
    try:
        too_long = client.post("/api/v1/conversations", json={
            "locale": "fa-IR", "request_text": "x" * 1201, "idempotency_key": "request-limit-1",
        })
        unsupported_locale = client.post("/api/v1/conversations", json={
            "locale": "fr-FR", "request_text": "Bonjour voyage", "idempotency_key": "request-limit-2",
        })
        assert too_long.status_code == 422
        assert unsupported_locale.status_code == 422
        assert repository.calls == []
    finally:
        _clear_overrides()


def test_idempotency_conflict_is_safe_and_does_not_echo_traveler_text():
    class ConflictingRepository(FakeTravelerRepository):
        def create_conversation(self, **kwargs):
            raise TravelerConflict

    client, _ = _client(ConflictingRepository(), Principal(OWNER, SESSION))
    try:
        response = client.post("/api/v1/conversations", json={
            "locale": "fa-IR",
            "request_text": RAW_REQUEST,
            "idempotency_key": "request-conflict-01",
        })
        assert response.status_code == 409
        assert response.json() == {"error": {"code": "idempotency_conflict"}}
        assert RAW_REQUEST not in response.text
    finally:
        _clear_overrides()


def test_persistence_failure_does_not_log_or_return_original_request(caplog):
    class FailingRepository(FakeTravelerRepository):
        def create_conversation(self, **kwargs):
            raise RuntimeError(f"database failed for request {kwargs['request_text']}")

    client, _ = _client(FailingRepository(), Principal(OWNER, SESSION))
    try:
        with caplog.at_level(logging.WARNING):
            response = client.post("/api/v1/conversations", json={
                "locale": "en-US",
                "request_text": RAW_REQUEST,
                "idempotency_key": "request-failure-1",
            })
        assert response.status_code == 503
        assert response.json() == {"error": {"code": "service_unavailable"}}
        assert RAW_REQUEST not in response.text
        assert RAW_REQUEST not in caplog.text
    finally:
        _clear_overrides()
