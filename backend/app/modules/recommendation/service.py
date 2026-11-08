"""Deterministic hard eligibility, structured retrieval, and soft ranking."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from app.modules.catalog.schemas import ProductionDestinationItem
from app.modules.recommendation.contracts import (
    EvidenceSource,
    Locale,
    RankingComponent,
    RecommendationOutcome,
    RecommendedDestination,
)
from app.modules.recommendation.retrieval import (
    ApprovedCatalogueCandidateRetriever,
    CandidateRetrievalQuery,
    StructuredDestinationCandidateRetrievalPort,
    StructuredDestinationMetadata,
)

MAX_RECOMMENDATIONS = 3
UNKNOWN_FACT_FIELDS = [
    "opening_hours", "visit_duration", "price", "route_duration",
    "visitor_entrance", "accessibility",
]
_NON_SPATIAL_TYPES = {"food", "dish", "product", "cuisine", "culinary_item"}
_MAX_DESTINATION_ID = 9_223_372_036_854_775_807


def _field_values(requirements: Mapping[str, object], key: str) -> tuple[str, ...]:
    value: object = requirements.get(key)
    if isinstance(value, Mapping):
        value = value.get("value")
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, (list, tuple)):
        return tuple(item.strip() for item in value if isinstance(item, str) and item.strip())
    return ()


def _has_explicit_constraints(requirements: Mapping[str, object]) -> bool:
    return bool(_field_values(requirements, "constraints"))


def recommend_trip(
    *,
    requirements: Mapping[str, object],
    selected_destination_ids: Sequence[str],
    catalogue: Sequence[ProductionDestinationItem],
    evidence_by_destination: Mapping[str, Sequence[EvidenceSource]],
    locale: Locale,
    metadata_by_destination: Mapping[str, StructuredDestinationMetadata] | None = None,
    retrieval_port: StructuredDestinationCandidateRetrievalPort | None = None,
) -> RecommendationOutcome:
    """Rank explicit destinations and exact structured interest matches.

    A selected city/town/region/province may retrieve candidates whose
    ``city_name`` exactly identifies that selected area. A selected attraction
    does not expand to all places in its city. Interest matches use only exact
    normalized values in approved, unlocalized tag projections; there is no
    translation, transliteration, fuzzy match, or semantic RAG.
    """
    if not catalogue:
        return RecommendationOutcome(status="empty", reason_code="catalogue_empty", items=[])
    if _has_explicit_constraints(requirements):
        return RecommendationOutcome(
            status="needs_confirmation", reason_code="hard_constraints_not_verifiable", items=[]
        )

    selected: list[str] = []
    for raw_id in selected_destination_ids:
        destination_id = str(raw_id)
        if (
            not destination_id.isascii() or not destination_id.isdecimal()
            or len(destination_id) > 19 or int(destination_id) < 1
            or int(destination_id) > _MAX_DESTINATION_ID
        ):
            return RecommendationOutcome(
                status="needs_confirmation", reason_code="destination_selection_invalid", items=[]
            )
        if destination_id not in selected:
            selected.append(destination_id)
    if not selected:
        return RecommendationOutcome(
            status="needs_confirmation", reason_code="destination_selection_required", items=[]
        )

    by_id: dict[str, ProductionDestinationItem] = {}
    conflicted: set[str] = set()
    for candidate in catalogue:
        previous = by_id.get(candidate.destination_id)
        if previous is not None and previous != candidate:
            conflicted.add(candidate.destination_id)
        else:
            by_id[candidate.destination_id] = candidate
    if any(destination_id in conflicted for destination_id in selected):
        return RecommendationOutcome(
            status="needs_confirmation", reason_code="catalogue_identity_conflict", items=[]
        )
    if any(destination_id not in by_id for destination_id in selected):
        reason = "catalogue_empty" if not catalogue else "selected_destination_unavailable"
        return RecommendationOutcome(status="needs_confirmation", reason_code=reason, items=[])
    if any(by_id[item].destination_type.strip().casefold() in _NON_SPATIAL_TYPES for item in selected):
        return RecommendationOutcome(status="empty", reason_code="non_spatial_item_not_supported", items=[])

    metadata = metadata_by_destination or {}
    retriever = retrieval_port or ApprovedCatalogueCandidateRetriever()
    try:
        hits = retriever.retrieve(
            query=CandidateRetrievalQuery(
                selected_destination_ids=tuple(selected),
                interests=_field_values(requirements, "interests"),
                locale=locale,
            ),
            catalogue=catalogue,
            metadata_by_destination=metadata,
        )
    except (TypeError, ValueError):
        return RecommendationOutcome(
            status="needs_confirmation", reason_code="catalogue_identity_conflict", items=[]
        )

    now = datetime.now(UTC)
    eligible: list[tuple[int, float, int, object, list[EvidenceSource]]] = []
    missing_selected_evidence = False
    for hit in hits:
        candidate = hit.destination
        if candidate.destination_type.strip().casefold() in _NON_SPATIAL_TYPES:
            if hit.scope_match == "explicit_identity":
                return RecommendationOutcome(
                    status="empty", reason_code="non_spatial_item_not_supported", items=[]
                )
            continue
        sources = sorted(
            (
                source for source in evidence_by_destination.get(candidate.destination_id, ())
                if source.destination_id == int(candidate.destination_id)
                and (source.valid_from is None or source.valid_from <= now)
                and (source.valid_until is None or source.valid_until >= now)
            ),
            key=lambda source: (source.source_id, source.source_role),
        )
        if not sources:
            if hit.scope_match == "explicit_identity":
                missing_selected_evidence = True
            continue

        interests = _field_values(requirements, "interests")
        match_fraction = len(hit.matched_interest_terms) / len(interests) if interests else 0.0
        scope_raw = 1.0 if hit.scope_match == "explicit_identity" else 0.7
        score = round((scope_raw * 0.7) + (match_fraction * 0.3), 6)
        eligible.append((hit.request_order, score, int(candidate.destination_id), hit, sources))

    if missing_selected_evidence:
        return RecommendationOutcome(status="empty", reason_code="provenance_unavailable", items=[])
    if not eligible:
        return RecommendationOutcome(status="empty", reason_code="no_eligible_destination", items=[])

    eligible.sort(key=lambda row: (row[0], -row[1], row[2]))
    items: list[RecommendedDestination] = []
    for rank, (_, score, _, hit, sources) in enumerate(eligible[:MAX_RECOMMENDATIONS], start=1):
        interests = _field_values(requirements, "interests")
        matched_interests = list(hit.matched_interest_terms)
        match_fraction = len(matched_interests) / len(interests) if interests else 0.0
        scope_raw = 1.0 if hit.scope_match == "explicit_identity" else 0.7
        unknown = list(UNKNOWN_FACT_FIELDS)
        warnings = ["ranking_is_structured_match_not_quality_score"]
        if interests and not matched_interests:
            unknown.append("interest_match")
            warnings.append("interest_not_matched_in_published_tags")
        if matched_interests:
            warnings.append("tag_language_unspecified_exact_match_only")
        if interests and metadata_by_destination is None:
            warnings.append("published_tag_projection_unavailable")
        if all(source.retrieved_at is None for source in sources):
            warnings.append("source_freshness_unknown")
        components = [
            RankingComponent(
                component_key="destination_scope", raw_score=scope_raw, weight=0.7,
                weighted_score=round(scope_raw * 0.7, 6),
                matched_terms=[hit.selected_destination_id],
            )
        ]
        if interests:
            components.append(
                RankingComponent(
                    component_key="exact_interest_tag_match", raw_score=match_fraction,
                    weight=0.3, weighted_score=round(match_fraction * 0.3, 6),
                    matched_terms=matched_interests,
                )
            )
        items.append(
            RecommendedDestination(
                destination_id=hit.destination.destination_id,
                rank=rank,
                final_score=score,
                matched_requirements=(
                    [f"destination:{hit.selected_destination_id}"]
                    + [f"interest:{term}" for term in matched_interests]
                ),
                unknown_fields=unknown,
                warnings=warnings,
                explanation_key=(
                    "explicit_destination_match"
                    if hit.scope_match == "explicit_identity"
                    else "published_area_candidate"
                ),
                score_components=components,
                evidence=sources,
            )
        )
    return RecommendationOutcome(status="available", items=items)
