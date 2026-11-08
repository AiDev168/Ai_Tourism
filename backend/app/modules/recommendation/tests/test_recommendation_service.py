from datetime import UTC, datetime, timedelta

from app.modules.catalog.schemas import ProductionDestinationItem
from app.modules.recommendation.contracts import EvidenceSource
from app.modules.recommendation.service import recommend_trip


def candidate(destination_id: str, kind: str = "heritage_site") -> ProductionDestinationItem:
    return ProductionDestinationItem(
        destination_id=destination_id,
        destination_key=f"destination-{destination_id}",
        canonical_name=f"Place {destination_id}",
        localized_names={"fa-IR": None, "en-US": None, "ar": None},
        aliases=[],
        destination_type=kind,
        province_name="Province",
        city_name="City",
    )


def source(destination_id: int, source_id: int, **overrides: object) -> EvidenceSource:
    values = {
        "destination_id": destination_id,
        "source_id": source_id,
        "source_name": f"Source {source_id}",
        "source_url": f"https://example.org/source/{source_id}",
        "source_role": "official_reference",
        "evidence_note": "Published source relationship",
        "retrieved_at": datetime.now(UTC),
        "valid_from": None,
        "valid_until": None,
        "reliability_score": 0.9,
    }
    values.update(overrides)
    return EvidenceSource.model_validate(values)


def test_returns_only_selected_currently_sourced_production_candidates_in_user_order() -> None:
    items = [candidate("2"), candidate("1")]
    result = recommend_trip(
        requirements={"constraints": {"value": []}},
        selected_destination_ids=["1", "2", "1"],
        catalogue=items,
        evidence_by_destination={"1": [source(1, 11)], "2": [source(2, 12)]},
        locale="fa-IR",
    )

    assert result.status == "available"
    assert result.algorithm_version == "structured-catalogue-ranking-v1"
    assert [(item.destination_id, item.rank) for item in result.items] == [("1", 1), ("2", 2)]
    assert result.items[0].explanation_key == "explicit_destination_match"
    assert result.items[0].matched_requirements == ["destination:1"]
    assert "opening_hours" in result.items[0].unknown_fields
    assert "route_duration" in result.items[0].unknown_fields
    assert result.items[0].evidence[0].source_url == "https://example.org/source/11"
    assert "ranking_is_structured_match_not_quality_score" in result.items[0].warnings


def test_empty_catalogue_and_unavailable_selection_are_honest_clarification_outcomes() -> None:
    empty = recommend_trip(
        requirements={}, selected_destination_ids=[], catalogue=[],
        evidence_by_destination={}, locale="ar",
    )
    missing_selection = recommend_trip(
        requirements={}, selected_destination_ids=[], catalogue=[candidate("1")],
        evidence_by_destination={}, locale="en-US",
    )

    assert (empty.status, empty.reason_code, empty.items) == ("empty", "catalogue_empty", [])
    assert (missing_selection.status, missing_selection.reason_code) == (
        "needs_confirmation", "destination_selection_required"
    )


def test_hard_constraints_do_not_get_overridden_by_a_match_score() -> None:
    result = recommend_trip(
        requirements={"constraints": {"value": ["wheelchair access"]}},
        selected_destination_ids=["1"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="en-US",
    )

    assert result.status == "needs_confirmation"
    assert result.reason_code == "hard_constraints_not_verifiable"
    assert result.items == []


def test_no_recommendation_when_source_is_missing_expired_or_bound_to_another_identity() -> None:
    now = datetime.now(UTC)
    cases = [
        [],
        [source(1, 11, valid_until=now - timedelta(seconds=1))],
        [source(2, 11)],
    ]
    for evidence in cases:
        result = recommend_trip(
            requirements={}, selected_destination_ids=["1"], catalogue=[candidate("1")],
            evidence_by_destination={"1": evidence}, locale="fa-IR",
        )
        assert result.status == "empty"
        assert result.reason_code == "provenance_unavailable"
        assert result.items == []


def test_unknown_provenance_freshness_is_a_warning_not_a_claim_of_freshness() -> None:
    result = recommend_trip(
        requirements={}, selected_destination_ids=["1"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11, retrieved_at=None)]}, locale="fa-IR",
    )

    assert result.status == "available"
    assert "source_freshness_unknown" in result.items[0].warnings


def test_non_spatial_knowledge_and_duplicate_identity_conflicts_fail_closed() -> None:
    food = recommend_trip(
        requirements={}, selected_destination_ids=["1"], catalogue=[candidate("1", "food")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="fa-IR",
    )
    conflict = recommend_trip(
        requirements={}, selected_destination_ids=["1"],
        catalogue=[candidate("1"), candidate("1", "city")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="fa-IR",
    )

    assert food.reason_code == "non_spatial_item_not_supported"
    assert food.items == []
    assert conflict.reason_code == "catalogue_identity_conflict"
    assert conflict.items == []


def test_non_numeric_client_identifier_is_not_accepted_as_catalogue_identity() -> None:
    result = recommend_trip(
        requirements={}, selected_destination_ids=["1 OR TRUE"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="fa-IR",
    )
    assert result.reason_code == "destination_selection_invalid"
    assert result.items == []
