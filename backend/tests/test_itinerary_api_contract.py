"""API-boundary checks for full-duration, bounded editable itineraries."""

from uuid import uuid4

import pytest
from fastapi import Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.traveler import _enrich_itinerary, create_itinerary
from app.modules.catalog.schemas import ProductionDestinationItem
from app.modules.identity.authorization import Principal
from app.modules.trip.repository import _profile_columns
from app.modules.trip.schemas import (
    CreateItineraryRequest,
    ItineraryStopEdit,
    UpdateItineraryRequest,
)

OWNER = uuid4()
SESSION = uuid4()
TRIP = uuid4()


def test_create_itinerary_request_supports_365_days_and_rejects_boolean_duration():
    body = CreateItineraryRequest(
        recommendation_request_id=uuid4(), day_count=365, locale="fa-IR"
    )
    assert body.day_count == 365
    with pytest.raises(ValidationError):
        CreateItineraryRequest(
            recommendation_request_id=uuid4(), day_count=366, locale="fa-IR"
        )
    with pytest.raises(ValidationError):
        CreateItineraryRequest(
            recommendation_request_id=uuid4(), day_count=True, locale="fa-IR"
        )


def test_stop_edits_allow_full_day_range_but_bound_stop_order():
    stop = ItineraryStopEdit(recommendation_id=uuid4(), day_number=365, stop_order=50)
    assert (stop.day_number, stop.stop_order) == (365, 50)
    with pytest.raises(ValidationError):
        ItineraryStopEdit(recommendation_id=uuid4(), day_number=True, stop_order=1)
    with pytest.raises(ValidationError):
        ItineraryStopEdit(recommendation_id=uuid4(), day_number=1, stop_order=51)


def test_update_contract_bounds_aggregate_stops_to_1000_and_each_day_to_50():
    one_day = [
        {"recommendation_id": str(uuid4()), "day_number": 1, "stop_order": index}
        for index in range(1, 51)
    ]
    request = UpdateItineraryRequest(expected_revision=1, stops=one_day)
    assert len(request.stops) == 50

    too_many_in_day = [
        {"recommendation_id": str(uuid4()), "day_number": 1, "stop_order": (index % 50) + 1}
        for index in range(51)
    ]
    with pytest.raises(ValidationError):
        UpdateItineraryRequest(expected_revision=1, stops=too_many_in_day)

    too_many_total = [
        {
            "recommendation_id": str(uuid4()),
            "day_number": index // 50 + 1,
            "stop_order": index % 50 + 1,
        }
        for index in range(1_001)
    ]
    with pytest.raises(ValidationError):
        UpdateItineraryRequest(expected_revision=1, stops=too_many_total)


class DurationBoundaryRepository:
    def __init__(self, duration: int | None):
        self.duration = duration
        self.reads = []

    def trip(self, user_id, trip_id):
        self.reads.append((user_id, trip_id))
        if user_id != OWNER or trip_id != TRIP:
            return None
        return {"duration_days": self.duration}


@pytest.mark.parametrize(
    ("confirmed_duration", "requested_days", "expected_code"),
    [(None, 1, "trip_duration_not_confirmed"), (7, 8, "itinerary_exceeds_confirmed_duration")],
)
def test_itinerary_create_cannot_exceed_confirmed_trip_duration(
    confirmed_duration, requested_days, expected_code
):
    repository = DurationBoundaryRepository(confirmed_duration)
    response = create_itinerary(
        TRIP,
        CreateItineraryRequest(
            recommendation_request_id=uuid4(), day_count=requested_days, locale="en-US"
        ),
        Response(),
        Principal(OWNER, SESSION),
        None,
        repository,
        object(),
    )
    assert isinstance(response, JSONResponse)
    assert response.status_code == 409
    assert response.body == f'{{"error":{{"code":"{expected_code}"}}}}'.encode()
    assert len(repository.reads) == 1


def _published_item(destination_id: str) -> ProductionDestinationItem:
    return ProductionDestinationItem(
        destination_id=destination_id,
        destination_key=f"test-{destination_id}",
        canonical_name=f"Approved place {destination_id}",
        localized_names={"fa-IR": None, "en-US": None, "ar": None},
        aliases=[],
        destination_type="attraction",
        province_name="Test province",
        city_name="Test city",
    )


def test_enriched_plan_shows_all_unplanned_days_after_partial_edit():
    row = {
        "day_count": 10,
        "stops": [
            {
                "destination_id": str(index),
                "day_number": index,
                "stop_order": 1,
                "itinerary_stop_id": uuid4(),
                "recommendation_id": uuid4(),
                "notes_by_locale": {},
            }
            for index in range(1, 5)
        ],
    }
    result = _enrich_itinerary(row, {str(index): _published_item(str(index)) for index in range(1, 5)})
    assert result["status"] == "partial"
    assert result["unplanned_days"] == [5, 6, 7, 8, 9, 10]
    assert [stop["day_number"] for stop in result["stops"]] == [1, 2, 3, 4]
    assert "stop_location_unknown" in result["warning_codes"]
    assert "no_hours_or_routes_inferred" in result["warning_codes"]


def test_enriched_plan_discloses_reference_point_and_geodesic_heuristic():
    row = {
        "day_count": 2,
        "stops": [
            {"destination_id": "1", "day_number": 1, "stop_order": 1,
             "itinerary_stop_id": uuid4(), "recommendation_id": uuid4(), "notes_by_locale": {}},
            {"destination_id": "2", "day_number": 2, "stop_order": 1,
             "itinerary_stop_id": uuid4(), "recommendation_id": uuid4(), "notes_by_locale": {}},
        ],
    }
    first = _published_item("1").model_copy(update={
        "latitude": 29.935, "longitude": 52.891, "coordinate_role": "property_reference",
    })
    second = _published_item("2").model_copy(update={
        "latitude": 29.940, "longitude": 52.900, "coordinate_role": "visitor_entrance",
    })
    result = _enrich_itinerary(row, {"1": first, "2": second})
    assert "geodesic_grouping_heuristic_only" in result["warning_codes"]
    assert "position_not_entrance" in result["warning_codes"]
    assert "no_hours_or_routes_inferred" in result["warning_codes"]


def test_normalized_confirmed_profile_persists_snake_case_duration_and_rejects_bool():
    profile = _profile_columns({
        "duration_days": 10,
        "traveler_count": 2,
        "origin": "Shiraz",
        "travel_dates": {"start": "2026-12-01", "end": "2026-12-10"},
    })
    assert profile["duration"] == 10
    assert profile["travelers"] == 2
    assert profile["origin"] == "Shiraz"
    assert profile["start_date"] == "2026-12-01"
    assert profile["end_date"] == "2026-12-10"
    bool_profile = _profile_columns({"duration_days": True, "traveler_count": False})
    assert bool_profile["duration"] is None
    assert bool_profile["travelers"] is None
