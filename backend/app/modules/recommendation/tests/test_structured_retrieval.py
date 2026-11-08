from app.modules.catalog.schemas import ApprovedDestinationAlias, ProductionDestinationItem
from app.modules.recommendation.contracts import EvidenceSource
from app.modules.recommendation.retrieval import StructuredDestinationMetadata
from app.modules.recommendation.service import recommend_trip


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


def test_selected_city_retrieves_only_exact_published_city_entities_then_ranks_exact_tags() -> None:
    city = destination("1", name="شیراز", kind="city", city=None, aliases=("Shiraz",))
    garden = destination("2", name="Eram Garden", kind="attraction", city="شیراز")
    museum = destination("3", name="Museum", kind="attraction", city="شیراز")
    other = destination("4", name="Garden", kind="attraction", city="اصفهان")
    catalogue = [city, garden, museum, other]
    result = recommend_trip(
        requirements={"interests": {"value": ["gardens"]}},
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
    assert "interest:gardens" in result.items[0].matched_requirements
    assert result.items[0].score_components[-1].component_key == "exact_interest_tag_match"
    assert result.items[0].warnings == [
        "ranking_is_structured_match_not_quality_score",
        "tag_language_unspecified_exact_match_only",
        "source_freshness_unknown",
    ]
    assert "4" not in [item.destination_id for item in result.items]


def test_selected_poi_does_not_expand_to_other_places_in_the_same_city() -> None:
    selected = destination("1", name="Eram Garden", kind="attraction", city="Shiraz")
    sibling = destination("2", name="Other place", kind="attraction", city="Shiraz")
    result = recommend_trip(
        requirements={}, selected_destination_ids=["1"], catalogue=[selected, sibling],
        evidence_by_destination={"1": [source(1)], "2": [source(2)]}, locale="en-US",
    )

    assert [item.destination_id for item in result.items] == ["1"]


def test_area_aliases_require_exact_unicode_normalized_match_and_no_transliteration() -> None:
    city = destination("1", name="کاشان", kind="city", city=None)
    arabic_variant = destination("2", name="كاشان", kind="attraction", city="كاشان")
    unrelated = destination("3", name="Kashan Garden", kind="attraction", city="Kashan")
    result = recommend_trip(
        requirements={}, selected_destination_ids=["1"], catalogue=[city, arabic_variant, unrelated],
        evidence_by_destination={"1": [source(1)], "2": [source(2)], "3": [source(3)]},
        locale="fa-IR",
    )

    assert [item.destination_id for item in result.items] == ["2"]


def test_soft_interests_are_not_claimed_when_no_published_tag_projection_exists() -> None:
    selected = destination("1", name="Shiraz", kind="city", city=None)
    result = recommend_trip(
        requirements={"interests": {"value": ["gardens"]}},
        selected_destination_ids=["1"], catalogue=[selected],
        evidence_by_destination={"1": [source(1)]}, locale="en-US",
    )

    assert result.status == "empty"
    assert result.reason_code == "no_eligible_destination"


def test_structured_retrieval_output_is_bounded_to_three_and_stable_by_numeric_id() -> None:
    city = destination("10", name="City", kind="city", city=None)
    candidates = [city] + [
        destination(str(index), name=f"Place {index}", kind="attraction", city="City")
        for index in (9, 2, 4, 1)
    ]
    result = recommend_trip(
        requirements={}, selected_destination_ids=["10"], catalogue=candidates,
        evidence_by_destination={
            str(item.destination_id): [source(int(item.destination_id))] for item in candidates
        }, locale="en-US",
    )

    assert len(result.items) == 3
    assert [item.destination_id for item in result.items] == ["1", "2", "4"]
    assert [item.rank for item in result.items] == [1, 2, 3]

