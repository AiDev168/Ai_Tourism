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
