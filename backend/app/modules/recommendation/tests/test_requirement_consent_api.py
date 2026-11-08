from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.auth import require_authenticated_csrf
from app.api.traveler import get_traveler_repository
from app.main import app
from app.modules.identity.authorization import Principal, get_principal

OWNER = UUID("9d6c521e-6d84-4a8c-b463-e0fe5a2dc0d1")
SESSION = UUID("2d878a93-1d6d-4e9a-9910-b5d25ac77fe2")
TRIP = UUID("cde18fda-9034-4ad2-a6f5-dcbbe175e488")
CONVERSATION = UUID("08b9205a-33e8-4c65-a8f9-a1ff5821f260")


class FakeRepository:
    def __init__(self):
        self.confirmed = None
        self.saved_consent = None

    def confirm_trip_profile(self, **kwargs):
        self.confirmed = kwargs
        self.saved_consent = None
        if kwargs["requirement_consent"] is not None:
            self.saved_consent = {
                **kwargs["requirement_consent"],
                "profile_version": kwargs["expected_version"] + 1,
            }

    def trip(self, user_id, trip_id):
        now = datetime.now(UTC)
        return {
            "trip_id": TRIP, "conversation_id": CONVERSATION, "version": 5,
            "locale": "en-US", "original_request": "Plan a trip",
            "extracted_requirements": {},
            "confirmed_requirements": {"requirement_consent": self.saved_consent}
            if self.saved_consent else {},
            "destination_ids": [], "duration_days": 4, "traveler_count": None,
            "budget_amount_original": None, "budget_currency_iso": None, "budget_unit": None,
            "latest_recommendation_request_id": None, "latest_itinerary_id": None,
            "trip_status": "draft", "created_at": now, "updated_at": now,
        }


def _client(repository):
    app.dependency_overrides[get_traveler_repository] = lambda: repository
    app.dependency_overrides[get_principal] = lambda: Principal(OWNER, SESSION)
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    return TestClient(app)


def test_profile_confirmation_accepts_field_choices_but_server_owns_binding_version():
    repository = FakeRepository()
    client = _client(repository)
    try:
        response = client.patch(f"/api/v1/trips/{TRIP}", json={
            "expected_version": 4,
            "confirmed_requirements": {
                "durationDays": {"value": 4, "status": "confirmed"},
                "budget": {"value": {"amount": 50, "currency": "IRR", "unit": "million toman"}},
            },
            "destination_ids": [],
            "requirement_consent": {
                "contract_version": "recommendation-consent-v1",
                "field_decisions": {"budget": "advisory"},
            },
        })
        assert response.status_code == 200
        assert repository.confirmed["user_id"] == OWNER
        assert repository.confirmed["requirement_consent"] == {
            "contract_version": "recommendation-consent-v1",
            "field_decisions": {"budget": "advisory"},
        }
        assert repository.saved_consent["profile_version"] == 5
        assert "profile_version" not in repository.confirmed["requirement_consent"]
    finally:
        app.dependency_overrides.clear()


def test_profile_confirmation_rejects_forged_version_unknown_field_and_nested_claim():
    repository = FakeRepository()
    client = _client(repository)
    base = {
        "expected_version": 4,
        "confirmed_requirements": {},
        "destination_ids": [],
    }
    try:
        forged_version = client.patch(f"/api/v1/trips/{TRIP}", json={
            **base,
            "requirement_consent": {
                "contract_version": "recommendation-consent-v1",
                "profile_version": 5,
                "field_decisions": {"budget": "advisory"},
            },
        })
        unknown_field = client.patch(f"/api/v1/trips/{TRIP}", json={
            **base,
            "requirement_consent": {
                "contract_version": "recommendation-consent-v1",
                "field_decisions": {"wheelchair_magic": "advisory"},
            },
        })
        nested_claim = client.patch(f"/api/v1/trips/{TRIP}", json={
            **base,
            "confirmed_requirements": {"requirement_consent": {"field_decisions": {}}},
        })
        assert forged_version.status_code == unknown_field.status_code == nested_claim.status_code == 422
        assert repository.confirmed is None
    finally:
        app.dependency_overrides.clear()
