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


def requirements(**values: object) -> dict[str, object]:
    return {"durationDays": {"value": 10, "status": "confirmed"}, **values}


def test_returns_only_selected_currently_sourced_production_candidates_in_user_order() -> None:
    items = [candidate("2"), candidate("1")]
    result = recommend_trip(
        requirements=requirements(constraints={"value": []}),
        selected_destination_ids=["1", "2", "1"],
        catalogue=items,
        evidence_by_destination={"1": [source(1, 11)], "2": [source(2, 12)]},
        locale="fa-IR",
    )

    assert result.status == "available"
    assert result.algorithm_version == "structured-catalogue-ranking-v3"
    assert [(item.destination_id, item.rank) for item in result.items] == [("1", 1), ("2", 2)]
    assert result.items[0].explanation_key == "explicit_destination_match"
    assert result.items[0].matched_requirements == ["destination:1"]
    assert "opening_hours" in result.items[0].unknown_fields
    assert "route_duration" in result.items[0].unknown_fields
    assert result.items[0].evidence[0].source_url == "https://example.org/source/11"
    assert "ranking_is_structured_match_not_quality_score" in result.items[0].warnings


def test_empty_catalogue_and_unavailable_selection_are_honest_clarification_outcomes() -> None:
    empty = recommend_trip(
        requirements=requirements(), selected_destination_ids=[], catalogue=[],
        evidence_by_destination={}, locale="ar",
    )
    missing_selection = recommend_trip(
        requirements=requirements(), selected_destination_ids=[], catalogue=[candidate("1")],
        evidence_by_destination={}, locale="en-US",
    )

    assert (empty.status, empty.reason_code, empty.items) == ("needs_confirmation", "destination_selection_required", [])
    assert (missing_selection.status, missing_selection.reason_code) == (
        "needs_confirmation", "destination_selection_required"
    )


def test_hard_constraints_do_not_get_overridden_by_a_match_score() -> None:
    result = recommend_trip(
        requirements=requirements(constraints={"value": ["wheelchair access"]}),
        selected_destination_ids=["1"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="en-US",
    )

    assert result.status == "needs_confirmation"
    assert result.reason_code == "hard_constraints_unverifiable"
    assert result.items == []


def test_persian_and_arabic_rial_units_allow_only_explicit_advisory_consent() -> None:
    for currency, unit in (("IRR", "ریال"), ("IRR", "ريال"), (None, "تومان")):
        profile = requirements(
            destinations={"value": ["Shiraz"], "status": "confirmed"},
            budget={"amount": 100_000, "currency": currency, "unit": unit, "raw": "budget"},
            requirement_consent={
                "contract_version": "recommendation-consent-v1",
                "profile_version": 2,
                "field_decisions": {"budget": "advisory"},
                "advisory_acknowledged_fields": ["budget"],
            },
        )
        result = recommend_trip(
            requirements=profile,
            selected_destination_ids=[],
            catalogue=[],
            evidence_by_destination={},
            locale="fa-IR",
            profile_version=2,
        )

        assert result.status == "empty"
        assert result.reason_code == "catalogue_empty"
        assert result.waived_fields == ["budget"]
        assert result.requirement_assessments[0].status == "not_evaluated"


def test_actual_pwa_budget_shapes_reach_mandatory_and_acknowledged_advisory_assessment() -> None:
    # These values mirror parseBudget() output: amount is the quantity typed,
    # unit retains the scale/currency wording, and no FX or Rial/Toman conversion occurs.
    parser_budgets = [
        {"amount": 20, "currency": None, "unit": "million toman", "raw": "20 million toman"},
        {"amount": 20, "currency": "IRR", "unit": "million IRR", "raw": "20 million IRR"},
        {"amount": 20, "currency": "IRR", "unit": "میلیون ریال", "raw": "۲۰ میلیون ریال"},
        {"amount": 20, "currency": "USD", "unit": "million USD", "raw": "20 million USD"},
        {"amount": 20, "currency": "AED", "unit": "مليون درهم", "raw": "٢٠ مليون درهم"},
        {"amount": 20, "currency": "SAR", "unit": "million ر.س", "raw": "20 million ر.س"},
    ]
    for budget in parser_budgets:
        profile = requirements(budget=budget)
        mandatory = recommend_trip(
            requirements=profile, selected_destination_ids=["1"], catalogue=[candidate("1")],
            evidence_by_destination={"1": [source(1, 11)]}, locale="en-US", profile_version=4,
        )
        assert mandatory.status == "needs_confirmation"
        assert mandatory.reason_code == "requirements_unverifiable"
        assert mandatory.unresolved_fields == ["budget"]

        profile["requirement_consent"] = {
            "contract_version": "recommendation-consent-v1", "profile_version": 4,
            "field_decisions": {"budget": "advisory"},
            "advisory_acknowledged_fields": ["budget"],
        }
        advisory = recommend_trip(
            requirements=profile, selected_destination_ids=["1"], catalogue=[candidate("1")],
            evidence_by_destination={"1": [source(1, 11)]}, locale="en-US", profile_version=4,
        )
        assert advisory.status == "available"
        assert advisory.not_evaluated_fields == ["budget"]
        assert advisory.requirement_assessments[0].status == "not_evaluated"
        assert all(component.component_key != "budget" for component in advisory.items[0].score_components)


def test_budget_currency_unit_mismatch_and_malformed_amount_fail_closed() -> None:
    invalid_budgets = [
        {"amount": 20, "currency": "IRR", "unit": "million toman"},
        {"amount": 20, "currency": "USD", "unit": "million AED"},
        {"amount": True, "currency": "IRR", "unit": "million IRR"},
        {"amount": "NaN", "currency": "IRR", "unit": "million IRR"},
        {"amount": 20, "currency": "EUR", "unit": "million EUR"},
    ]
    for budget in invalid_budgets:
        result = recommend_trip(
            requirements=requirements(budget=budget), selected_destination_ids=["1"],
            catalogue=[candidate("1")], evidence_by_destination={"1": [source(1, 11)]},
            locale="en-US", profile_version=4,
        )
        assert result.reason_code == "requirements_invalid"
        assert result.items == []


def test_explicit_soft_preference_can_be_advisory_but_hard_constraints_still_block() -> None:
    soft = requirements(soft_preferences=["paved paths"])
    soft["requirement_consent"] = {
        "contract_version": "recommendation-consent-v1", "profile_version": 4,
        "field_decisions": {"soft_preference": "advisory"},
        "advisory_acknowledged_fields": ["soft_preference"],
    }
    advisory = recommend_trip(
        requirements=soft, selected_destination_ids=["1"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="en-US", profile_version=4,
    )
    assert advisory.status == "available"
    assert advisory.waived_fields == advisory.not_evaluated_fields == ["soft_preference"]
    assert advisory.requirement_assessments[0].reason_code == "preference_unverifiable"
    assert advisory.items[0].not_evaluated_fields == ["soft_preference"]
    assert all(component.component_key != "soft_preference" for component in advisory.items[0].score_components)

    hard = requirements(soft_preferences=["paved paths"], constraints=["avoid rough terrain"])
    hard["requirement_consent"] = soft["requirement_consent"]
    blocked = recommend_trip(
        requirements=hard, selected_destination_ids=["1"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="en-US", profile_version=4,
    )
    assert blocked.status == "needs_confirmation"
    assert blocked.unresolved_fields == ["hard_constraint"]
    assert blocked.waived_fields == ["soft_preference"]
    assert blocked.items == []


def test_no_recommendation_when_source_is_missing_expired_or_bound_to_another_identity() -> None:
    now = datetime.now(UTC)
    cases = [
        [],
        [source(1, 11, valid_until=now - timedelta(seconds=1))],
        [source(2, 11)],
    ]
    for evidence in cases:
        result = recommend_trip(
            requirements=requirements(), selected_destination_ids=["1"], catalogue=[candidate("1")],
            evidence_by_destination={"1": evidence}, locale="fa-IR",
        )
        assert result.status == "empty"
        assert result.reason_code == "provenance_unavailable"
        assert result.items == []


def test_unknown_provenance_freshness_is_a_warning_not_a_claim_of_freshness() -> None:
    result = recommend_trip(
        requirements=requirements(), selected_destination_ids=["1"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11, retrieved_at=None)]}, locale="fa-IR",
    )

    assert result.status == "available"
    assert "source_freshness_unknown" in result.items[0].warnings


def test_non_spatial_knowledge_and_duplicate_identity_conflicts_fail_closed() -> None:
    food = recommend_trip(
        requirements=requirements(), selected_destination_ids=["1"], catalogue=[candidate("1", "food")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="fa-IR",
    )
    conflict = recommend_trip(
        requirements=requirements(), selected_destination_ids=["1"],
        catalogue=[candidate("1"), candidate("1", "city")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="fa-IR",
    )

    assert food.reason_code == "non_spatial_item_not_supported"
    assert food.items == []
    assert conflict.reason_code == "catalogue_identity_conflict"
    assert conflict.items == []


def test_non_numeric_client_identifier_is_not_accepted_as_catalogue_identity() -> None:
    result = recommend_trip(
        requirements=requirements(), selected_destination_ids=["1 OR TRUE"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="fa-IR",
    )
    assert result.reason_code == "destination_selection_invalid"
    assert result.items == []


def test_unresolved_requirement_defaults_to_mandatory_and_blocks() -> None:
    result = recommend_trip(
        requirements=requirements(budget={"amount": 50, "currency": None, "unit": "million toman"}),
        selected_destination_ids=["1"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="en-US", profile_version=4,
    )

    assert result.status == "needs_confirmation"
    assert result.unresolved_fields == ["budget"]
    assert result.waived_fields == result.not_evaluated_fields == []
    assert [assessment.model_dump() for assessment in result.requirement_assessments] == [{
        "field": "budget", "decision": "must_have", "status": "unresolved",
        "reason_code": "budget_unverifiable",
    }]


def test_explicit_version_bound_advisory_is_not_evaluated_or_scored() -> None:
    profile = requirements(budget={"amount": 50, "currency": None, "unit": "million toman"})
    profile["requirement_consent"] = {
        "contract_version": "recommendation-consent-v1",
        "profile_version": 4,
        "field_decisions": {"budget": "advisory"},
        "advisory_acknowledged_fields": ["budget"],
    }
    result = recommend_trip(
        requirements=profile, selected_destination_ids=["1"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="en-US", profile_version=4,
    )

    assert result.status == "available"
    assert result.unresolved_fields == []
    assert result.waived_fields == result.not_evaluated_fields == ["budget"]
    assert result.requirement_assessments[0].model_dump() == {
        "field": "budget", "decision": "advisory", "status": "not_evaluated",
        "reason_code": "budget_unverifiable",
    }
    item = result.items[0]
    assert item.not_evaluated_fields == ["budget"]
    assert "requirements_not_evaluated" in item.warnings
    assert all(component.component_key != "budget" for component in item.score_components)


def test_stale_or_forged_consent_fails_closed() -> None:
    stale = requirements(budget={"amount": 50, "currency": None, "unit": "million toman"})
    stale["requirement_consent"] = {
        "contract_version": "recommendation-consent-v1",
        "profile_version": 3,
        "field_decisions": {"budget": "advisory"},
        "advisory_acknowledged_fields": ["budget"],
    }
    stale_result = recommend_trip(
        requirements=stale, selected_destination_ids=["1"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="en-US", profile_version=4,
    )
    forged = requirements(constraints={"value": ["wheelchair access"]})
    forged["requirement_consent"] = {
        "contract_version": "recommendation-consent-v1",
        "profile_version": 4,
        "field_decisions": {"hard_constraint": "advisory"},
        "advisory_acknowledged_fields": ["hard_constraint"],
    }
    forged_result = recommend_trip(
        requirements=forged, selected_destination_ids=["1"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="en-US", profile_version=4,
    )

    assert stale_result.reason_code == "requirement_consent_stale"
    assert stale_result.unresolved_fields == ["budget"]
    assert stale_result.waived_fields == []
    assert forged_result.reason_code == "requirements_invalid"
    assert forged_result.items == []


def test_consent_cannot_be_applied_to_a_field_no_longer_unresolved() -> None:
    profile = requirements()
    profile["requirement_consent"] = {
        "contract_version": "recommendation-consent-v1",
        "profile_version": 4,
        "field_decisions": {"budget": "advisory"},
        "advisory_acknowledged_fields": ["budget"],
    }
    result = recommend_trip(
        requirements=profile, selected_destination_ids=["1"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="en-US", profile_version=4,
    )
    assert result.reason_code == "requirements_invalid"
    assert result.items == []


def test_advisory_requires_exact_ack_and_safety_fields_are_never_waivable() -> None:
    profile = requirements(budget={"amount": 50, "currency": None, "unit": "million toman"})
    profile["requirement_consent"] = {
        "contract_version": "recommendation-consent-v1",
        "profile_version": 4,
        "field_decisions": {"budget": "advisory"},
        "advisory_acknowledged_fields": [],
    }
    unacknowledged = recommend_trip(
        requirements=profile, selected_destination_ids=["1"], catalogue=[candidate("1")],
        evidence_by_destination={"1": [source(1, 11)]}, locale="en-US", profile_version=4,
    )

    unsafe_profiles = [
        requirements(access={"value": ["step-free"], "status": "confirmed"}),
        requirements(mobility={"value": ["wheelchair"], "status": "confirmed"}),
        requirements(surface={"value": ["flat path"], "status": "confirmed"}),
        requirements(activity={"value": ["climbing"], "status": "confirmed"}),
        requirements(activity_difficulty={"value": ["easy"], "status": "confirmed"}),
        requirements(prohibited_transport={"value": ["car"], "status": "confirmed"}),
        requirements(constraints={"value": ["must be safe"], "status": "confirmed"}),
    ]
    for unsafe in unsafe_profiles:
        unresolved_field = {
            "access": "accessibility", "mobility": "mobility", "surface": "surface",
            "activity": "activity", "activity_difficulty": "activity_difficulty",
            "prohibited_transport": "transport",
            "constraints": "hard_constraint",
        }[next(key for key in unsafe if key != "durationDays")]
        unsafe["requirement_consent"] = {
            "contract_version": "recommendation-consent-v1",
            "profile_version": 4,
            "field_decisions": {unresolved_field: "advisory"},
            "advisory_acknowledged_fields": [unresolved_field],
        }
        result = recommend_trip(
            requirements=unsafe, selected_destination_ids=["1"], catalogue=[candidate("1")],
            evidence_by_destination={"1": [source(1, 11)]}, locale="en-US", profile_version=4,
        )
        assert result.reason_code == "requirements_invalid"
        assert result.items == []

    assert unacknowledged.reason_code == "requirements_invalid"
    assert unacknowledged.items == []
