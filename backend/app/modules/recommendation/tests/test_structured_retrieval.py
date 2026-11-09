from app.modules.catalog.schemas import ApprovedDestinationAlias, ProductionDestinationItem
from app.modules.recommendation.contracts import EvidenceSource
from app.modules.recommendation.retrieval import StructuredDestinationMetadata
from app.modules.recommendation.service import recommend_trip


def requirements(**values: object) -> dict[str, object]:
    return {"durationDays": {"value": 10, "status": "confirmed"}, **values}


def destination(
    destination_id: str,
    *,
    name: str,
    kind: str,
    city: str | None,
    aliases: tuple[str, ...] = (),
) -> ProductionDestinationItem:
    return ProductionDestinationItem(
        destination_id=destination_id,
        destination_key=f"destination-{destination_id}",
        canonical_name=name,
        localized_names={"fa-IR": name, "en-US": None, "ar": None},
        aliases=[
            ApprovedDestinationAlias(locale="fa-IR", value=value, alias_type="spelling_variant")
            for value in aliases
        ],
        destination_type=kind,
        province_name="Province",
        city_name=city,
    )


def source(destination_id: int) -> EvidenceSource:
    return EvidenceSource(
        destination_id=destination_id,
        source_id=destination_id + 100,
        source_name="Approved source",
        source_url=f"https://example.org/{destination_id}",
        source_role="official_reference",
        reliability_score=0.9,
    )


def test_selected_city_retrieves_exact_candidates_but_untagged_interests_are_not_scored() -> None:
    city = destination("1", name="شیراز", kind="city", city=None, aliases=("Shiraz",))
    garden = destination("2", name="Eram Garden", kind="attraction", city="شیراز")
    museum = destination("3", name="Museum", kind="attraction", city="شیراز")
    other = destination("4", name="Garden", kind="attraction", city="اصفهان")
    catalogue = [city, garden, museum, other]
    result = recommend_trip(
        requirements=requirements(interests={"value": ["gardens"]}),
        selected_destination_ids=["1"],
        catalogue=catalogue,
        evidence_by_destination={str(index): [source(index)] for index in range(1, 5)},
        metadata_by_destination={
            "2": StructuredDestinationMetadata(tags=("gardens",)),
            "3": StructuredDestinationMetadata(tags=("museums",)),
            "4": StructuredDestinationMetadata(tags=("gardens",)),
        },
        locale="fa-IR",
    )

    assert result.status == "available"
    assert [item.destination_id for item in result.items] == ["2", "3"]
    assert result.items[0].explanation_key == "published_area_candidate"
    assert result.items[0].matched_requirements == ["destination:1"]
    assert [component.component_key for component in result.items[0].score_components] == ["destination_scope"]
    assert result.items[0].warnings == [
        "ranking_is_structured_match_not_quality_score",
        "interest_tags_not_locale_typed_unmatched",
        "source_freshness_unknown",
    ]
    assert "interest_match" in result.items[0].unknown_fields
    assert "4" not in [item.destination_id for item in result.items]


def test_selected_poi_does_not_expand_to_other_places_in_the_same_city() -> None:
    selected = destination("1", name="Eram Garden", kind="attraction", city="Shiraz")
    sibling = destination("2", name="Other place", kind="attraction", city="Shiraz")
    result = recommend_trip(
        requirements=requirements(), selected_destination_ids=["1"], catalogue=[selected, sibling],
        evidence_by_destination={"1": [source(1)], "2": [source(2)]}, locale="en-US",
    )

    assert [item.destination_id for item in result.items] == ["1"]


def test_area_aliases_require_exact_unicode_normalized_match_and_no_transliteration() -> None:
    city = destination("1", name="کاشان", kind="city", city=None)
    arabic_variant = destination("2", name="كاشان", kind="attraction", city="كاشان")
    unrelated = destination("3", name="Kashan Garden", kind="attraction", city="Kashan")
    result = recommend_trip(
        requirements=requirements(), selected_destination_ids=["1"], catalogue=[city, arabic_variant, unrelated],
        evidence_by_destination={"1": [source(1)], "2": [source(2)], "3": [source(3)]},
        locale="fa-IR",
    )

    assert [item.destination_id for item in result.items] == ["2"]


def test_soft_interests_are_not_claimed_when_no_published_tag_projection_exists() -> None:
    selected = destination("1", name="Shiraz", kind="city", city=None)
    result = recommend_trip(
        requirements=requirements(interests={"value": ["gardens"]}),
        selected_destination_ids=["1"], catalogue=[selected],
        evidence_by_destination={"1": [source(1)]}, locale="en-US",
    )

    assert result.status == "empty"
    assert result.reason_code == "no_eligible_destination"


def test_structured_retrieval_returns_all_candidates_with_stable_numeric_id_tiebreak() -> None:
    city = destination("10", name="City", kind="city", city=None)
    candidates = [city] + [
        destination(str(index), name=f"Place {index}", kind="attraction", city="City")
        for index in (9, 2, 4, 1)
    ]
    result = recommend_trip(
        requirements=requirements(), selected_destination_ids=["10"], catalogue=candidates,
        evidence_by_destination={
            str(item.destination_id): [source(int(item.destination_id))] for item in candidates
        }, locale="en-US",
    )

    assert len(result.items) == 4
    assert [item.destination_id for item in result.items] == ["1", "2", "4", "9"]
    assert [item.rank for item in result.items] == [1, 2, 3, 4]


def test_ten_day_request_returns_ten_provenance_backed_candidates_without_three_item_cap() -> None:
    city = destination("100", name="City", kind="city", city=None)
    places = [
        destination(str(index), name=f"Place {index}", kind="attraction", city="City")
        for index in range(1, 11)
    ]
    catalogue = [city, *places]
    result = recommend_trip(
        requirements={"durationDays": {"value": 10, "status": "confirmed"}},
        selected_destination_ids=["100"], catalogue=catalogue,
        evidence_by_destination={str(index): [source(index)] for index in range(1, 101)},
        locale="en-US",
    )

    assert result.status == "available"
    assert result.duration_days == 10
    assert len(result.items) == 10
    assert [item.rank for item in result.items] == list(range(1, 11))


def test_invalid_requirement_types_fail_closed_and_explicit_unverifiable_fields_are_reported() -> None:
    selected = destination("1", name="Eram Garden", kind="attraction", city="Shiraz")
    evidence = {"1": [source(1)]}
    invalid_cases = [
        {"durationDays": {"value": True, "status": "confirmed"}},
        {"durationDays": {"value": 366, "status": "confirmed"}},
        {"durationDays": {"value": "ten", "status": "confirmed"}},
        {"durationDays": {"value": 10, "status": "confirmed"}, "travelerCount": {"value": "4"}},
        {"durationDays": {"value": 10, "status": "confirmed"}, "budget": {"value": {"amount": 2, "currency": "USD", "unit": "dollars"}}},
        {"durationDays": {"value": 10, "status": "confirmed"}, "unknownHardRequirement": True},
    ]
    for profile in invalid_cases:
        result = recommend_trip(
            requirements=profile, selected_destination_ids=["1"], catalogue=[selected],
            evidence_by_destination=evidence, locale="en-US",
        )
        assert result.status == "needs_confirmation"
        assert result.reason_code in {"requirements_invalid", "requirements_incomplete"}
        assert result.items == []

    unverified = recommend_trip(
        requirements=requirements(
            travelerCount={"value": 4, "status": "confirmed"},
            budget={"value": {"amount": 20, "currency": None, "unit": "میلیون تومان", "raw": "۲۰ میلیون تومان"}},
            travelDates={"value": {"start": "2026-12-01", "end": "2026-12-10"}, "status": "confirmed"},
        ),
        selected_destination_ids=["1"], catalogue=[selected],
        evidence_by_destination=evidence, locale="en-US",
    )
    assert unverified.status == "needs_confirmation"
    assert set(unverified.unresolved_fields) == {"traveler_count", "budget", "travel_dates"}
    assert unverified.items == []

    zero_budget = recommend_trip(
        requirements=requirements(budget={"value": {"amount": 0, "currency": "IRR", "unit": "rial"}}),
        selected_destination_ids=["1"], catalogue=[selected],
        evidence_by_destination=evidence, locale="en-US",
    )
    assert zero_budget.status == "needs_confirmation"
    assert zero_budget.unresolved_fields == ["budget"]


def test_documented_hard_requirement_keys_have_stable_unresolved_codes() -> None:
    selected = destination("1", name="Eram Garden", kind="attraction", city="Shiraz")
    evidence = {"1": [source(1)]}
    cases = {
        "access": ("wheelchair access", "accessibility"),
        "mobility_accessibility": ("step-free", "mobility"),
        "surface": ("paved", "surface"),
        "activity": ("hiking", "activity"),
        "activity_difficulty": ("easy", "activity_difficulty"),
        "radius": (5, "radius"),
        "season": ("spring", "season"),
        "time_window": ({"start": "09:00", "end": "12:00"}, "time_window"),
        "party_size": (4, "traveler_count"),
        "party_composition": (["children"], "party_composition"),
        "transport": ("rail", "transport"),
        "travel_style": ("slow travel", "travel_style"),
        "accommodation": ("hotel", "accommodation"),
    }
    for key, (value, field_code) in cases.items():
        result = recommend_trip(
            requirements=requirements(**{key: {"value": value, "status": "confirmed"}}),
            selected_destination_ids=["1"], catalogue=[selected],
            evidence_by_destination=evidence, locale="en-US",
        )
        assert result.status == "needs_confirmation", key
        assert result.unresolved_fields == [field_code], key
        assert result.items == [], key


def test_malformed_status_and_unknown_missing_field_codes_fail_closed_without_type_errors() -> None:
    selected = destination("1", name="Eram Garden", kind="attraction", city="Shiraz")
    evidence = {"1": [source(1)]}
    malformed_profiles = [
        requirements(durationDays={"value": 10, "status": []}),
        requirements(missingRequired=["arbitrary-new-field"]),
        requirements(ambiguousRequired=[{"key": "destination"}]),
        requirements(confirmationRequired=["unknown-constraint"]),
        requirements(access={"value": True, "status": "confirmed"}),
        requirements(mobility_accessibility={"value": False, "status": "confirmed"}),
        requirements(surface=True),
        requirements(activity=False),
        requirements(difficulty=True),
        requirements(radius=True),
        requirements(season=False),
        requirements(time_window={"value": True, "status": "confirmed"}),
        requirements(party_size=True),
    ]
    for profile in malformed_profiles:
        result = recommend_trip(
            requirements=profile, selected_destination_ids=["1"], catalogue=[selected],
            evidence_by_destination=evidence, locale="fa-IR",
        )
        assert result.status == "needs_confirmation"
        assert result.reason_code == "requirements_invalid"
        assert result.items == []


def test_empty_catalogue_is_distinct_from_malformed_or_incomplete_profiles() -> None:
    valid_complete = recommend_trip(
        requirements=requirements(destinations={"value": ["Shiraz"], "status": "confirmed"}),
        selected_destination_ids=[], catalogue=[], evidence_by_destination={}, locale="fa-IR",
    )
    malformed = recommend_trip(
        requirements={"durationDays": {"value": True, "status": "confirmed"}},
        selected_destination_ids=[], catalogue=[], evidence_by_destination={}, locale="fa-IR",
    )
    incomplete = recommend_trip(
        requirements={}, selected_destination_ids=[], catalogue=[],
        evidence_by_destination={}, locale="fa-IR",
    )

    assert (valid_complete.status, valid_complete.reason_code) == ("empty", "catalogue_empty")
    assert (malformed.status, malformed.reason_code) == ("needs_confirmation", "requirements_invalid")
    assert (incomplete.status, incomplete.reason_code) == ("needs_confirmation", "requirements_incomplete")


def test_traveler_confirmed_snake_case_profile_is_accepted_and_validated() -> None:
    selected = destination("1", name="Eram Garden", kind="attraction", city="Shiraz")
    confirmed_profile = {
        "destinations": ["Shiraz"],
        "destination_ids": ["1"],
        "duration_days": 10,
        "origin": None,
        "travel_dates": None,
        "traveler_count": None,
        "budget": None,
        "interests": ["gardens"],
        "constraints": [],
        "confirmation_source": "traveler_reviewed",
    }
    result = recommend_trip(
        requirements=confirmed_profile,
        selected_destination_ids=["1"], catalogue=[selected],
        evidence_by_destination={"1": [source(1)]}, locale="fa-IR",
    )
    assert result.status == "available"
    assert result.duration_days == 10
    assert result.items[0].destination_id == "1"
    assert "interest_match" in result.items[0].unknown_fields

    invalid = recommend_trip(
        requirements={**confirmed_profile, "duration_days": True},
        selected_destination_ids=["1"], catalogue=[selected],
        evidence_by_destination={"1": [source(1)]}, locale="fa-IR",
    )
    assert (invalid.status, invalid.reason_code) == ("needs_confirmation", "requirements_invalid")

    unsupported_metadata = recommend_trip(
        requirements={**confirmed_profile, "confirmation_source": "client_claimed_admin"},
        selected_destination_ids=["1"], catalogue=[selected],
        evidence_by_destination={"1": [source(1)]}, locale="fa-IR",
    )
    assert (unsupported_metadata.status, unsupported_metadata.reason_code) == (
        "needs_confirmation", "requirements_invalid"
    )

