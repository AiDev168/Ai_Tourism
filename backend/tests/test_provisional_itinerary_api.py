from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.auth import require_authenticated_csrf
from app.api.traveler import get_provisional_itinerary_repository
from app.main import app
from app.modules.identity.authorization import Principal, get_principal
from app.modules.trip.provisional_itinerary import (
    ProvisionalItineraryConflict,
    ProvisionalItineraryNotFound,
    ProvisionalItineraryProfileNotConfirmed,
)

OWNER = UUID("f59c8a69-a7ed-4122-a3b7-18e37ff25a99")
OTHER = UUID("84d9e2db-b4e7-4777-8a86-13e5bb716d92")
SESSION = UUID("eb2d1b43-a0d4-4134-a755-f9694569b331")
TRIP = UUID("8f60716c-32b5-4c4a-a45f-8afc0718b9e9")
ITINERARY = UUID("046f762d-7d01-4bba-a0df-512f3f053aaf")


class FakeRepository:
    def __init__(self):
        self.row = None
        self.user_id = OWNER
        self.trip_version = 7
        self.duration = 5
        self.profile_confirmed = True

    @staticmethod
    def public(row):
        days = row["days"]
        return {
            "provisional_itinerary_id": ITINERARY,
            "trip_id": TRIP,
            "revision": row["revision"],
            "day_count": row["day_count"],
            "locale": row["locale"],
            "title_by_locale": row["title_by_locale"],
            "status": "provisional_unverified",
            "days": [
                {"day_number": day["day_number"], "stops": [
                    {**stop, "verification_status": "unverified"}
                    for stop in day["stops"]
                ]}
                for day in days
            ],
            "unplanned_days": [day["day_number"] for day in days if not day["stops"]],
            "updated_at": datetime.now(UTC),
        }

    def create(self, *, user_id, trip_id, expected_trip_version, day_count,
               locale, title_by_locale, days):
        if user_id != self.user_id or trip_id != TRIP:
            raise ProvisionalItineraryNotFound
        if expected_trip_version != self.trip_version:
            raise ProvisionalItineraryConflict
        if not self.profile_confirmed:
            raise ProvisionalItineraryProfileNotConfirmed
        if self.duration and day_count > self.duration:
            from app.modules.trip.provisional_itinerary import ProvisionalItineraryInvalid
            raise ProvisionalItineraryInvalid
        if self.row:
            return self.public(self.row), False
        self.row = {
            "revision": 1, "day_count": day_count, "locale": locale,
            "title_by_locale": title_by_locale, "days": days,
        }
        return self.public(self.row), True

    def get_latest(self, *, user_id, trip_id):
        if user_id != self.user_id or trip_id != TRIP or not self.row:
            return None
        return self.public(self.row)

    def update(self, *, user_id, itinerary_id, expected_revision, day_count,
               title_by_locale, days):
        if user_id != self.user_id or itinerary_id != ITINERARY or not self.row:
            raise ProvisionalItineraryNotFound
        if expected_revision != self.row["revision"]:
            raise ProvisionalItineraryConflict
        self.row.update({
            "revision": self.row["revision"] + 1,
            "day_count": day_count,
            "title_by_locale": title_by_locale,
            "days": days,
        })
        return self.public(self.row)


def _client(repository):
    app.dependency_overrides[get_provisional_itinerary_repository] = lambda: repository
    app.dependency_overrides[get_principal] = lambda: Principal(OWNER, SESSION)
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    return TestClient(app)


def _draft(day_count=3):
    return {
        "expected_trip_version": 7,
        "day_count": day_count,
        "locale": "fa-IR",
        "title_by_locale": {"fa-IR": "پیش‌نویس پیشنهادی"},
        "days": [
            {"day_number": day, "stops": ([{
                "name": "بازار وکیل", "role": "model_proposed",
                "notes_by_locale": {"fa-IR": "نام پیشنهادی؛ بررسی شود"},
            }] if day == 1 else [])}
            for day in range(1, day_count + 1)
        ],
    }


def test_provisional_draft_create_read_edit_and_revision_conflict():
    repository = FakeRepository()
    client = _client(repository)
    try:
        created = client.post(f"/api/v1/trips/{TRIP}/provisional-itineraries", json=_draft())
        assert created.status_code == 201
        payload = created.json()
        assert payload["status"] == "provisional_unverified"
        assert payload["revision"] == 1
        assert payload["unplanned_days"] == [2, 3]
        assert payload["days"][0]["stops"][0]["verification_status"] == "unverified"
        assert created.headers["cache-control"] == "no-store"

        reopened = client.get(f"/api/v1/trips/{TRIP}/provisional-itineraries")
        assert reopened.status_code == 200
        reopened_payload = reopened.json()
        assert {key: value for key, value in reopened_payload.items() if key != "updated_at"} == {
            key: value for key, value in payload.items() if key != "updated_at"
        }

        edited_days = _draft()["days"]
        edited_days[1]["stops"] = [{
            "name": "باغ ارم", "role": "traveler_provided", "notes_by_locale": {},
        }]
        edited = client.put(f"/api/v1/provisional-itineraries/{payload['provisional_itinerary_id']}", json={
            "expected_revision": 1, "day_count": 3,
            "title_by_locale": {"fa-IR": "برنامه ویرایش‌شده"}, "days": edited_days,
        })
        assert edited.status_code == 200
        assert edited.json()["revision"] == 2
        assert edited.json()["unplanned_days"] == [3]
        stale = client.put(f"/api/v1/provisional-itineraries/{payload['provisional_itinerary_id']}", json={
            "expected_revision": 1, "day_count": 3,
            "title_by_locale": {}, "days": _draft()["days"],
        })
        assert stale.status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_provisional_draft_cannot_smuggle_facts_or_foreign_ids():
    repository = FakeRepository()
    client = _client(repository)
    try:
        invalid_role_id = _draft()
        invalid_role_id["days"][0]["stops"][0]["destination_id"] = "some-production-destination"
        response = client.post(f"/api/v1/trips/{TRIP}/provisional-itineraries", json=invalid_role_id)
        assert response.status_code == 422

        unsupported_fact_fields = _draft()
        unsupported_fact_fields["days"][0]["stops"][0]["opening_hours"] = "open all day"
        response = client.post(f"/api/v1/trips/{TRIP}/provisional-itineraries", json=unsupported_fact_fields)
        assert response.status_code == 422

        unapproved_map_candidate = _draft()
        unapproved_map_candidate["days"][0]["stops"][0].update({
            "role": "map_reviewed_candidate", "destination_id": "some-other-place-v1",
        })
        response = client.post(f"/api/v1/trips/{TRIP}/provisional-itineraries", json=unapproved_map_candidate)
        assert response.status_code == 422

        incomplete_days = _draft()
        incomplete_days["days"].pop()
        response = client.post(f"/api/v1/trips/{TRIP}/provisional-itineraries", json=incomplete_days)
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_owner_reviewed_map_candidate_remains_unverified_for_travel_claims():
    repository = FakeRepository()
    client = _client(repository)
    body = _draft(day_count=1)
    body["days"][0]["stops"][0] = {
        "name": "حافظیه", "role": "map_reviewed_candidate",
        "destination_id": "shiraz-hafezieh-v1", "notes_by_locale": {},
    }
    try:
        response = client.post(f"/api/v1/trips/{TRIP}/provisional-itineraries", json=body)
        assert response.status_code == 201
        stop = response.json()["days"][0]["stops"][0]
        assert stop["destination_id"] == "shiraz-hafezieh-v1"
        assert stop["role"] == "map_reviewed_candidate"
        assert stop["verification_status"] == "unverified"
        assert "opening_hours" not in stop
        assert "price" not in stop
        assert "accessibility" not in stop
    finally:
        app.dependency_overrides.clear()


def test_provisional_draft_is_owner_scoped_and_trip_version_bound():
    repository = FakeRepository()
    client = _client(repository)
    try:
        repository.trip_version += 1
        stale = client.post(f"/api/v1/trips/{TRIP}/provisional-itineraries", json=_draft())
        assert stale.status_code == 409
        missing = client.get(f"/api/v1/trips/{TRIP}/provisional-itineraries")
        assert missing.status_code == 404
        repository.user_id = OTHER
        foreign = client.get(f"/api/v1/trips/{TRIP}/provisional-itineraries")
        assert foreign.status_code == 404
        repository.user_id = OWNER
        repository.trip_version = 7
        repository.profile_confirmed = False
        unconfirmed = client.post(f"/api/v1/trips/{TRIP}/provisional-itineraries", json=_draft())
        assert unconfirmed.status_code == 409
        assert unconfirmed.json()["error"]["code"] == "trip_profile_not_confirmed"
    finally:
        app.dependency_overrides.clear()
