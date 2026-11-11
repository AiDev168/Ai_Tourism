import json
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.auth import require_authenticated_csrf
from app.main import app
from app.modules.identity.authorization import Principal, get_principal
from app.modules.trip.requirements_interpretation import (
    interpret_trip_requirements,
    trip_requirements_storage_view,
)


def test_authenticated_interpretation_api_preserves_unknown_currency_and_relative_departure():
    user_id, session_id = uuid4(), uuid4()
    app.dependency_overrides[get_principal] = lambda: Principal(user_id, session_id)
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    try:
        client = TestClient(app)
        text = "از دو روز دیگه با 4 نفر میخوام برم از مناطق تاریخی شیراز دیدن کنم و فقط 10 میلیون هزینه میخوام بکنم"
        response = client.post(
            "/api/v1/requirements/interpret",
            json={"request_text": text, "locale": "fa-IR"},
        )
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        requirements = response.json()["requirements"]
        assert requirements["original_text"] == text
        fields = requirements["fields"]
        assert fields["destination"]["value"] == "شیراز"
        assert fields["travelers"]["value"] == 4
        assert fields["relative_start_date"]["value"]["offset_days"] == 2
        assert fields["relative_start_date"]["value"]["anchor_date"] is None
        assert fields["duration_days"]["status"] == "missing"
        assert fields["interests"]["value"] == ["historical_attractions"]
        assert fields["budget"]["value"]["amount"] == "10"
        assert fields["budget"]["value"]["scale"] == "million"
        assert fields["budget"]["value"]["currency"] is None
        assert "duration_days" in requirements["clarification"]["question_fields"]
        assert "budget.currency" in requirements["clarification"]["question_fields"]
    finally:
        app.dependency_overrides.pop(get_principal, None)
        app.dependency_overrides.pop(require_authenticated_csrf, None)


def test_persisted_requirements_view_keeps_v1_evidence_and_exact_original_budget():
    text = "برای 10 میلیون هزینه می‌خواهم"
    interpreted = interpret_trip_requirements(text, "fa-IR")
    stored = trip_requirements_storage_view(interpreted)
    json.dumps(stored)
    assert stored["requestText"] == text
    assert stored["requirements_v1"]["original_text"] == text
    budget = stored["requirements_v1"]["fields"]["budget"]
    assert budget["evidence_span"]["text"] == "10 میلیون"
    assert budget["value"]["amount"] == "10"
    assert budget["value"]["currency"] is None
    assert stored["clarificationFields"] == ["destination", "duration_days", "budget.currency"]
