import pytest

from app.modules.itinerary.service import generate_itinerary
from app.modules.recommendation.contracts import (
    EvidenceSource,
    RankingComponent,
    RecommendationOutcome,
    RecommendedDestination,
)


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
    assert [stop.destination_id for stop in plan.stops] == ["1", "2", "3"]
    assert [(stop.day_number, stop.stop_order) for stop in plan.stops] == [(1, 1), (2, 1), (2, 2)]
    assert all(stop.planned_start_time is None for stop in plan.stops)
    assert all(stop.duration_minutes is None for stop in plan.stops)
    assert all(stop.travel_to_next_estimate_minutes is None for stop in plan.stops)
    assert all(stop.user_notes_by_locale == {} for stop in plan.stops)
    assert all(stop.evidence for stop in plan.stops)
    assert "no_hours_or_routes_inferred" in plan.warning_codes


def test_itinerary_day_count_is_bounded() -> None:
    with pytest.raises(ValueError):
        generate_itinerary(recommendation=recommendation(), day_count=4, locale="en-US")
