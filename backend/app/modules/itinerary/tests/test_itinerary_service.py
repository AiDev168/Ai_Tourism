import pytest

from app.modules.catalog.schemas import ProductionDestinationItem
from app.modules.itinerary.service import generate_itinerary
from app.modules.itinerary.contracts import ItineraryDraft
from app.modules.recommendation.contracts import (
    EvidenceSource,
    RankingComponent,
    RecommendationOutcome,
    RecommendedDestination,
)
from app.modules.recommendation.service import recommend_trip


def recommendation(count: int = 2) -> RecommendationOutcome:
    sources = [EvidenceSource(
        destination_id=index,
        source_id=index + 100,
        source_name=f"Source {index}",
        source_url=f"https://example.org/{index}",
        source_role="official_reference",
    ) for index in range(1, count + 1)]
    items = [RecommendedDestination(
        destination_id=str(index),
        rank=index,
        final_score=1,
        matched_requirements=["explicit_destination_selection"],
        unknown_fields=["opening_hours", "price"],
        warnings=["ranking_is_identity_match_not_quality_score"],
        explanation_key="explicit_destination_match",
        score_components=[RankingComponent(
            component_key="destination_scope", raw_score=1, weight=0.7,
            weighted_score=0.7, matched_terms=[str(index)],
        )],
        evidence=[sources[index - 1]],
    ) for index in range(1, count + 1)]
    return RecommendationOutcome(status="available", items=items)


def test_no_itinerary_is_created_when_no_eligible_recommendations_exist() -> None:
    assert generate_itinerary(
        recommendation=RecommendationOutcome(status="empty", reason_code="catalogue_empty", items=[]),
        day_count=3,
        locale="fa-IR",
    ) is None


def test_itinerary_contains_only_recommended_entities_and_no_invented_schedule() -> None:
    plan = generate_itinerary(recommendation=recommendation(3), day_count=2, locale="ar")

    assert plan is not None
    assert plan.day_count == 2
    assert plan.status == "complete"
    assert plan.editable is True
    assert [stop.destination_id for stop in plan.stops] == ["1", "2", "3"]
    assert [(stop.day_number, stop.stop_order) for stop in plan.stops] == [(1, 1), (2, 1), (1, 2)]
    assert all(stop.planned_start_time is None for stop in plan.stops)
    assert all(stop.duration_minutes is None for stop in plan.stops)
    assert all(stop.travel_to_next_estimate_minutes is None for stop in plan.stops)
    assert all(stop.user_notes_by_locale == {} for stop in plan.stops)
    assert all(stop.evidence for stop in plan.stops)
    assert "no_hours_or_routes_inferred" in plan.warning_codes


def test_itinerary_supports_long_trip_duration_and_bounds_at_365_days() -> None:
    plan = generate_itinerary(recommendation=recommendation(10), day_count=10, locale="en-US")
    assert plan is not None
    assert plan.day_count == 10
    assert [stop.day_number for stop in plan.stops] == list(range(1, 11))
    assert plan.unplanned_days == []
    assert plan.status == "complete"

    with pytest.raises(ValueError):
        generate_itinerary(recommendation=recommendation(), day_count=366, locale="en-US")


def test_partial_long_itinerary_marks_every_unplanned_day_and_never_fabricates_stops() -> None:
    plan = generate_itinerary(recommendation=recommendation(4), day_count=10, locale="fa-IR")
    assert plan is not None
    assert plan.day_count == 10
    assert [stop.day_number for stop in plan.stops] == [1, 2, 3, 4]
    assert plan.unplanned_days == [5, 6, 7, 8, 9, 10]
    assert "some_days_unplanned_insufficient_candidates" in plan.warning_codes
    assert plan.status == "partial"
    assert all(stop.evidence for stop in plan.stops)


def test_partial_fifteen_day_itinerary_keeps_four_evidenced_stops_and_eleven_unplanned_days() -> None:
    plan = generate_itinerary(recommendation=recommendation(4), day_count=15, locale="fa-IR")
    assert plan is not None
    assert plan.day_count == 15
    assert [stop.day_number for stop in plan.stops] == [1, 2, 3, 4]
    assert plan.unplanned_days == list(range(5, 16))
    assert plan.status == "partial"
    assert all(stop.evidence for stop in plan.stops)


def test_itinerary_allows_at_most_fifty_stops_per_day_and_one_thousand_total() -> None:
    plan = generate_itinerary(recommendation=recommendation(1_000), day_count=20, locale="ar")
    assert plan is not None
    assert len(plan.stops) == 1_000
    assert max(sum(stop.day_number == day for stop in plan.stops) for day in range(1, 21)) == 50
    assert max(stop.stop_order for stop in plan.stops) == 50


def test_itinerary_contract_rejects_inconsistent_unplanned_days_and_status() -> None:
    partial = generate_itinerary(recommendation=recommendation(1), day_count=2, locale="en-US")
    assert partial is not None
    payload = partial.model_dump()
    payload["unplanned_days"] = [2, 2]
    with pytest.raises(ValueError, match="unique"):
        ItineraryDraft.model_validate(payload)

    payload = partial.model_dump()
    payload["status"] = "complete"
    with pytest.raises(ValueError, match="status"):
        ItineraryDraft.model_validate(payload)

    payload = partial.model_dump()
    payload["unplanned_days"] = [365]
    with pytest.raises(ValueError, match="outside"):
        ItineraryDraft.model_validate(payload)


def test_ten_evidenced_recommendations_compose_into_an_editable_ten_day_itinerary() -> None:
    # Isolated test-only catalogue candidates; no runtime or database data.
    city = ProductionDestinationItem(
        destination_id="100",
        destination_key="test-city",
        canonical_name="Test City",
        localized_names={"fa-IR": "Test City", "en-US": "Test City", "ar": "Test City"},
        aliases=[],
        destination_type="city",
        province_name="Test Province",
        city_name=None,
    )
    places = [
        ProductionDestinationItem(
            destination_id=str(index),
            destination_key=f"test-place-{index}",
            canonical_name=f"Test Place {index}",
            localized_names={"fa-IR": None, "en-US": None, "ar": None},
            aliases=[],
            destination_type="attraction",
            province_name="Test Province",
            city_name="Test City",
        )
        for index in range(1, 11)
    ]
    catalogue = [city, *places]
    provenance = {
        str(index): [
            EvidenceSource(
                destination_id=index,
                source_id=index + 1_000,
                source_name=f"Test-only source {index}",
                source_url=f"https://example.invalid/test-source/{index}",
                source_role="test_fixture",
            )
        ]
        for index in range(1, 11)
    }

    outcome = recommend_trip(
        requirements={"duration_days": 10, "destinations": ["Test City"], "destination_ids": ["100"]},
        selected_destination_ids=["100"],
        catalogue=catalogue,
        evidence_by_destination=provenance,
        locale="en-US",
    )
    plan = generate_itinerary(recommendation=outcome, day_count=10, locale="en-US")

    assert outcome.status == "available"
    assert len(outcome.items) == 10
    assert plan is not None
    assert plan.day_count == 10
    assert plan.status == "complete"
    assert plan.editable is True
    assert [stop.destination_id for stop in plan.stops] == [str(index) for index in range(1, 11)]
    assert len({stop.destination_id for stop in plan.stops}) == 10
    assert [stop.day_number for stop in plan.stops] == list(range(1, 11))
    assert all(stop.evidence for stop in plan.stops)


def test_geographic_grouping_clusters_nearby_stops_and_separates_distant_stops():
    source = [
        {
            "destination_id": "1",
            "latitude": 29.60,
            "longitude": 52.50,
            "coordinate_role": "visitor_entrance",
        },
        {
            "destination_id": "2",
            "latitude": 29.61,
            "longitude": 52.51,
            "coordinate_role": "visitor_entrance",
        },
        {
            "destination_id": "3",
            "latitude": 30.20,
            "longitude": 53.10,
            "coordinate_role": "visitor_entrance",
        },
        {
            "destination_id": "4",
            "latitude": 30.21,
            "longitude": 53.11,
            "coordinate_role": "visitor_entrance",
        },
    ]
    geography = {
        item["destination_id"]: {
            "latitude": item["latitude"],
            "longitude": item["longitude"],
            "coordinate_role": item["coordinate_role"],
        }
        for item in source
    }

    plan = generate_itinerary(
        recommendation=recommendation(4),
        day_count=2,
        locale="fa-IR",
        geography_by_destination=geography,
    )

    assert plan is not None
    by_day = {
        day: {stop.destination_id for stop in plan.stops if stop.day_number == day}
        for day in (1, 2)
    }
    assert by_day == {1: {"1", "2"}, 2: {"3", "4"}}
    assert "geodesic_grouping_heuristic_only" in plan.warning_codes
    assert "no_hours_or_routes_inferred" in plan.warning_codes
    assert all(stop.travel_to_next_estimate_minutes is None for stop in plan.stops)


def test_fifteen_day_shiraz_cluster_and_persepolis_plan_leaves_thirteen_days_unplanned():
    # Test-only coordinates mirror the candidate review geometry: three compact
    # Shiraz points and a distant Marvdasht property reference. These fixtures
    # are never loaded into a production catalogue.
    geography = {
        "1": {"latitude": 29.6254028, "longitude": 52.5583194, "coordinate_role": "representative_point"},
        "2": {"latitude": 29.63583, "longitude": 52.52528, "coordinate_role": "representative_point"},
        "3": {"latitude": 29.6149806, "longitude": 52.5467972, "coordinate_role": "representative_point"},
        "4": {"latitude": 29.93444, "longitude": 52.89028, "coordinate_role": "property_reference"},
    }

    plan = generate_itinerary(
        recommendation=recommendation(4),
        day_count=15,
        locale="fa-IR",
        geography_by_destination=geography,
    )

    assert plan is not None
    assert plan.day_count == 15
    assert {stop.destination_id for stop in plan.stops if stop.day_number == 1} == {"1", "2", "3"}
    assert {stop.destination_id for stop in plan.stops if stop.day_number == 2} == {"4"}
    assert plan.unplanned_days == list(range(3, 16))
    assert plan.status == "partial"
    assert "geodesic_grouping_heuristic_only" in plan.warning_codes
    assert "position_not_entrance" in plan.warning_codes
    assert all(stop.travel_to_next_estimate_minutes is None for stop in plan.stops)


def test_property_reference_is_never_presented_as_an_entrance_or_route_point():
    plan = generate_itinerary(
        recommendation=recommendation(2),
        day_count=2,
        locale="en-US",
        geography_by_destination={
            "1": {
                "latitude": 29.93444,
                "longitude": 52.89028,
                "coordinate_role": "property_reference",
            },
            "2": {
                "latitude": 29.60,
                "longitude": 52.50,
                "coordinate_role": "representative_point",
            },
        },
    )

    assert plan is not None
    assert "position_not_entrance" in plan.warning_codes
    assert "geodesic_grouping_heuristic_only" in plan.warning_codes
    assert all(stop.planned_start_time is None for stop in plan.stops)
    assert all(stop.travel_to_next_estimate_minutes is None for stop in plan.stops)


def test_missing_or_malformed_geography_stays_unknown_and_preserves_eligible_stops():
    plan = generate_itinerary(
        recommendation=recommendation(3),
        day_count=5,
        locale="ar",
        geography_by_destination={
            "1": {
                "latitude": True,
                "longitude": 52.5,
                "coordinate_role": "visitor_entrance",
            },
            "2": {
                "latitude": 29.61,
                "longitude": 52.51,
                "coordinate_role": "unrecognized_role",
            },
        },
    )

    assert plan is not None
    assert len(plan.stops) == 3
    assert "stop_location_unknown" in plan.warning_codes
    assert plan.status == "partial"
    assert plan.unplanned_days == [4, 5]


def test_confirmed_origin_seeds_the_nearest_day_without_changing_eligibility():
    plan = generate_itinerary(
        recommendation=recommendation(3),
        day_count=2,
        locale="fa-IR",
        geography_by_destination={
            "1": {"latitude": 29.6, "longitude": 52.5, "coordinate_role": "visitor_entrance"},
            "2": {"latitude": 29.7, "longitude": 52.6, "coordinate_role": "visitor_entrance"},
            "3": {"latitude": 30.2, "longitude": 53.1, "coordinate_role": "visitor_entrance"},
        },
        origin={"latitude": 29.61, "longitude": 52.51, "coordinate_role": "representative_point"},
    )

    assert plan is not None
    assert {stop.destination_id for stop in plan.stops if stop.day_number == 1} == {"1", "2"}
    assert {stop.destination_id for stop in plan.stops if stop.day_number == 2} == {"3"}
    assert {stop.destination_id for stop in plan.stops} == {"1", "2", "3"}


def test_geographic_cluster_assignment_respects_fifty_stop_day_capacity():
    # A dense cluster must still split across days within the API's hard bound.
    geography = {
        str(index): {
            "latitude": 29.6 + index * 0.000001,
            "longitude": 52.5 + index * 0.000001,
            "coordinate_role": "visitor_entrance",
        }
        for index in range(1, 101)
    }

    plan = generate_itinerary(
        recommendation=recommendation(100),
        day_count=2,
        locale="fa-IR",
        geography_by_destination=geography,
    )

    assert plan is not None
    counts = [sum(stop.day_number == day for stop in plan.stops) for day in (1, 2)]
    assert counts == [50, 50]
    assert max(stop.stop_order for stop in plan.stops) == 50
    assert len({stop.destination_id for stop in plan.stops}) == 100
