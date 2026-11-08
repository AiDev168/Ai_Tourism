"""Deterministic requirement assessment, structured retrieval, and ranking."""

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

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
    CandidateSetExceedsBound,
    CandidateRetrievalQuery,
    StructuredDestinationCandidateRetrievalPort,
    StructuredDestinationMetadata,
)

MAX_CANDIDATES = 1_000
MAX_DURATION_DAYS = 365
UNKNOWN_FACT_FIELDS = [
    "opening_hours", "visit_duration", "price", "route_duration",
    "visitor_entrance", "accessibility",
]
_NON_SPATIAL_TYPES = {"food", "dish", "product", "cuisine", "culinary_item"}
_MAX_DESTINATION_ID = 9_223_372_036_854_775_807
_FIELD_CODE_ALIASES = {
    "destination": "destination_resolution", "destinations": "destination_resolution",
    "destination_ids": "destination_resolution", "destination_resolution": "destination_resolution",
    "duration": "duration_days", "durationDays": "duration_days", "duration_days": "duration_days",
    "origin": "origin", "travelDates": "travel_dates", "travel_dates": "travel_dates",
    "date_range": "travel_dates", "dates": "travel_dates", "flexible_dates": "travel_dates", "season": "season",
    "seasonality": "season", "travelerCount": "traveler_count", "traveler_count": "traveler_count",
    "party_size": "traveler_count", "group_size": "traveler_count", "party_composition": "party_composition",
    "partySize": "traveler_count", "groupSize": "traveler_count",
    "group": "party_composition", "budget": "budget", "budget_range": "budget", "max_budget": "budget",
    "access": "accessibility", "accessibility": "accessibility", "access_modes": "accessibility",
    "accessModes": "accessibility", "visitor_access": "accessibility",
    "mobility": "mobility", "mobility_accessibility": "mobility", "mobilityAccessibility": "mobility",
    "surface": "surface",
    "activity": "activity", "activity_type": "activity", "activity_difficulty": "activity_difficulty",
    "difficulty": "activity_difficulty", "activityDifficulty": "activity_difficulty",
    "radius": "radius", "radius_km": "radius", "max_distance_km": "radius",
    "time_window": "time_window", "timeWindow": "time_window", "timeRange": "time_window",
    "start_time": "time_window",
    "end_time": "time_window", "transport": "transport", "preferred_transport": "transport",
    "prohibited_transport": "transport",
    "travel_style": "travel_style", "accommodation": "accommodation", "constraints": "hard_constraint",
    "hard_constraints": "hard_constraint", "terrain": "surface",
    "interest": "interest_match", "interests": "interest_match", "trip_profile": "trip_profile",
}
_ALLOWED_REQUIREMENT_KEYS = {
    "requestText", "locale", "destinations", "destination_ids", "origin",
    "durationDays", "duration_days", "travelDates", "travel_dates", "travelerCount", "traveler_count",
    "budget", "interests",
    "constraints", "extractionStatus", "missingRequired", "ambiguousRequired",
    "confirmationRequired", "destinationVerification", "access", "accessibility", "access_modes",
    "mobility", "mobility_accessibility", "surface", "activity", "activity_type",
    "activity_difficulty", "difficulty", "radius", "radius_km", "season", "seasonality",
    "time_window", "timeWindow", "start_time", "end_time", "date_range", "dates",
    "party_size", "group_size", "partySize", "groupSize", "party_composition", "group", "budget_range", "max_budget",
    "accessModes", "mobilityAccessibility", "activityDifficulty", "timeRange", "visitor_access",
    "transport", "preferred_transport", "prohibited_transport", "travel_style", "accommodation",
    "hard_constraints", "terrain", "max_distance_km", "flexible_dates",
    "interest",
    "confirmation_source",
}
_FIELD_WRAPPED_KEYS = _ALLOWED_REQUIREMENT_KEYS - {
    "requestText", "locale", "destination_ids", "extractionStatus", "missingRequired",
    "ambiguousRequired", "confirmationRequired", "destinationVerification",
}


class _InvalidRequirements(ValueError):
    pass


def _unwrap(requirements: Mapping[str, object], key: str) -> object:
    value = requirements.get(key)
    if isinstance(value, Mapping):
        if not set(value).intersection({"value", "status", "evidence", "candidates"}):
            return value
        if not set(value).issubset({"value", "status", "evidence", "candidates"}):
            raise _InvalidRequirements
        if "value" not in value:
            raise _InvalidRequirements
        status = value.get("status")
        if status is not None and (
            not isinstance(status, str) or status not in {
            "extracted", "confirmed", "unknown", "ambiguous", "missing",
            }
        ):
            raise _InvalidRequirements
        return value["value"]
    return value


def _unwrap_aliases(requirements: Mapping[str, object], *keys: str) -> object:
    present = [key for key in keys if key in requirements]
    if not present:
        return None
    values = [_unwrap(requirements, key) for key in present]
    if any(value != values[0] for value in values[1:]):
        raise _InvalidRequirements
    return values[0]


def _string_list(value: object, *, field: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise _InvalidRequirements
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise _InvalidRequirements
    return tuple(item.strip() for item in value)


def _validate_budget(value: object) -> bool:
    """Validate explicit budget syntax; return whether it is explicitly present."""
    if value is None:
        return False
    if not isinstance(value, Mapping):
        raise _InvalidRequirements
    if not set(value).issubset({"amount", "currency", "unit", "raw"}):
        raise _InvalidRequirements
    amount = value.get("amount")
    currency = value.get("currency")
    unit = value.get("unit")
    if isinstance(amount, bool) or not isinstance(amount, (int, float, str)):
        raise _InvalidRequirements
    try:
        decimal_amount = Decimal(str(amount))
    except (InvalidOperation, ValueError):
        raise _InvalidRequirements from None
    if not decimal_amount.is_finite() or decimal_amount < 0:
        raise _InvalidRequirements
    supported_units = {
        "rial", "toman", "irr", "million rial", "million toman",
        "میلیون ریال", "میلیون تومان", "مليون ريال", "مليون تومان",
    }
    if currency not in {"IRR", None} or (unit is not None and (not isinstance(unit, str) or unit.strip().casefold() not in supported_units)):
        raise _InvalidRequirements
    # Do not infer a currency unit from the ISO currency alone. An explicit
    # amount without an unambiguous unit is malformed for this contract.
    if currency != "IRR" or not isinstance(unit, str) or unit.strip().casefold() not in supported_units:
        raise _InvalidRequirements
    raw = value.get("raw")
    if raw is not None and (not isinstance(raw, str) or len(raw) > 240):
        raise _InvalidRequirements
    return True


def _validate_dates(value: object) -> bool:
    if value is None:
        return False
    if not isinstance(value, Mapping):
        raise _InvalidRequirements
    if set(value) != {"start", "end"}:
        raise _InvalidRequirements
    start, end = value.get("start"), value.get("end")
    if not isinstance(start, str) or not isinstance(end, str):
        raise _InvalidRequirements
    try:
        start_date, end_date = date.fromisoformat(start), date.fromisoformat(end)
    except ValueError:
        raise _InvalidRequirements from None
    if start_date.isoformat() != start or end_date.isoformat() != end or start_date > end_date:
        raise _InvalidRequirements
    return True


def _explicit_strings(value: object) -> bool:
    if isinstance(value, bool):
        raise _InvalidRequirements
    if isinstance(value, str):
        if not value.strip():
            raise _InvalidRequirements
        return True
    if isinstance(value, (list, tuple)):
        if not value or any(not isinstance(item, str) or not item.strip() for item in value):
            raise _InvalidRequirements
        return True
    raise _InvalidRequirements


def _validate_radius(value: object) -> bool:
    if value is None:
        return False
    unit = "km"
    amount = value
    if isinstance(value, Mapping):
        if set(value) != {"amount", "unit"}:
            raise _InvalidRequirements
        amount, unit = value["amount"], value["unit"]
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        raise _InvalidRequirements
    if not isinstance(unit, str) or unit != "km" or not 0 < amount <= 10_000:
        raise _InvalidRequirements
    return True


def _validate_time_window(value: object) -> bool:
    if value is None:
        return False
    if not isinstance(value, Mapping) or set(value) != {"start", "end"}:
        raise _InvalidRequirements
    start, end = value["start"], value["end"]
    if (
        not isinstance(start, str) or not isinstance(end, str)
        or len(start) != 5 or len(end) != 5
    ):
        raise _InvalidRequirements
    try:
        start_time = datetime.strptime(start, "%H:%M").time()
        end_time = datetime.strptime(end, "%H:%M").time()
    except ValueError:
        raise _InvalidRequirements from None
    if start_time >= end_time:
        raise _InvalidRequirements
    return True


def _canonical_list(value: object) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise _InvalidRequirements
    canonical: list[str] = []
    for item in value:
        if item not in _FIELD_CODE_ALIASES:
            raise _InvalidRequirements
        code = _FIELD_CODE_ALIASES[item]
        if code not in canonical:
            canonical.append(code)
    return canonical


def _assess_requirements(
    requirements: Mapping[str, object],
) -> tuple[int | None, tuple[str, ...], tuple[str, ...], tuple[str, ...], bool]:
    unknown_keys = set(requirements) - _ALLOWED_REQUIREMENT_KEYS
    if unknown_keys:
        raise _InvalidRequirements

    request_text = requirements.get("requestText")
    if request_text is not None and (
        not isinstance(request_text, str) or not request_text.strip() or len(request_text) > 1_200
    ):
        raise _InvalidRequirements
    profile_locale = requirements.get("locale")
    if profile_locale is not None and (
        not isinstance(profile_locale, str) or profile_locale not in {"fa-IR", "en-US", "ar"}
    ):
        raise _InvalidRequirements
    destination_verification = requirements.get("destinationVerification")
    if destination_verification is not None and (
        not isinstance(destination_verification, str) or destination_verification != "user_input_unverified"
    ):
        raise _InvalidRequirements
    confirmation_source = requirements.get("confirmation_source")
    if confirmation_source is not None and (
        not isinstance(confirmation_source, str) or confirmation_source != "traveler_reviewed"
    ):
        raise _InvalidRequirements

    extraction_status = requirements.get("extractionStatus")
    missing = requirements.get("missingRequired", [])
    ambiguous = requirements.get("ambiguousRequired", [])
    confirmation = requirements.get("confirmationRequired", [])
    if extraction_status is not None and (
        not isinstance(extraction_status, str) or extraction_status not in {"ready", "needs_clarification"}
    ):
        raise _InvalidRequirements
    missing_codes = _canonical_list(missing)
    ambiguous_codes = _canonical_list(ambiguous)
    confirmation_codes = _canonical_list(confirmation)

    unresolved: list[str] = [*missing_codes, *ambiguous_codes, *confirmation_codes]
    if extraction_status == "needs_clarification":
        unresolved.append("trip_profile")
    for key in requirements:
        if (
            key in _FIELD_WRAPPED_KEYS and isinstance(requirements[key], Mapping)
            and ("value" in requirements[key] or "status" in requirements[key])
        ):
            _unwrap(requirements, key)  # validates shape and status before interpreting it
            if requirements[key].get("status") in {"ambiguous", "missing"}:
                unresolved.append(_FIELD_CODE_ALIASES.get(key, key))

    duration = _unwrap_aliases(requirements, "durationDays", "duration_days")
    if duration is None:
        unresolved.append("duration_days")
    elif isinstance(duration, bool) or not isinstance(duration, int) or not 1 <= duration <= MAX_DURATION_DAYS:
        raise _InvalidRequirements

    # Optional fields are never treated as satisfied merely because they were
    # parsed. Until the approved catalogue exposes matching facts, explicit
    # values require confirmation. Their original values remain in the trip
    # profile and are not converted or discarded here.
    origin = _unwrap(requirements, "origin")
    if origin is not None and (not isinstance(origin, str) or origin.strip()):
        if not isinstance(origin, str):
            raise _InvalidRequirements
        unresolved.append("origin")

    dates = _unwrap_aliases(requirements, "travelDates", "travel_dates")
    if _validate_dates(dates):
        unresolved.append("travel_dates")

    travelers = _unwrap_aliases(requirements, "travelerCount", "traveler_count")
    if travelers is not None:
        if isinstance(travelers, bool) or not isinstance(travelers, int) or not 1 <= travelers <= 100:
            raise _InvalidRequirements
        unresolved.append("traveler_count")

    if _validate_budget(_unwrap(requirements, "budget")):
        unresolved.append("budget")

    for key in ("budget_range", "max_budget"):
        if key in requirements and _validate_budget(_unwrap(requirements, key)):
            unresolved.append("budget")

    for key in ("access", "accessibility", "access_modes", "accessModes", "visitor_access"):
        if key in requirements and _explicit_strings(_unwrap(requirements, key)):
            unresolved.append("accessibility")
    for key in ("mobility", "mobility_accessibility", "mobilityAccessibility"):
        if key in requirements and _explicit_strings(_unwrap(requirements, key)):
            unresolved.append("mobility")
    for key in ("surface", "terrain"):
        if key in requirements and _explicit_strings(_unwrap(requirements, key)):
            unresolved.append("surface")
    for key in ("activity", "activity_type"):
        if key in requirements and _explicit_strings(_unwrap(requirements, key)):
            unresolved.append("activity")
    for key in ("activity_difficulty", "difficulty", "activityDifficulty"):
        if key in requirements and _explicit_strings(_unwrap(requirements, key)):
            unresolved.append("activity_difficulty")
    for key in ("season", "seasonality"):
        if key in requirements and _explicit_strings(_unwrap(requirements, key)):
            unresolved.append("season")
    for key in ("radius", "radius_km", "max_distance_km"):
        if key in requirements and _validate_radius(_unwrap(requirements, key)):
            unresolved.append("radius")
    if any(key in requirements for key in ("time_window", "timeWindow", "timeRange")):
        key = next(key for key in ("time_window", "timeWindow", "timeRange") if key in requirements)
        if _validate_time_window(_unwrap(requirements, key)):
            unresolved.append("time_window")
    start_time = requirements.get("start_time")
    end_time = requirements.get("end_time")
    if (start_time is None) != (end_time is None):
        raise _InvalidRequirements
    if start_time is not None:
        window = {"start": _unwrap(requirements, "start_time"), "end": _unwrap(requirements, "end_time")}
        if _validate_time_window(window):
            unresolved.append("time_window")
    for key in ("transport", "preferred_transport", "prohibited_transport"):
        if key in requirements and _explicit_strings(_unwrap(requirements, key)):
            unresolved.append("transport")
    for key in ("travel_style", "accommodation"):
        if key in requirements and _explicit_strings(_unwrap(requirements, key)):
            unresolved.append(key)

    for key in ("date_range", "dates"):
        if key in requirements and _validate_dates(_unwrap(requirements, key)):
            unresolved.append("travel_dates")
    if "flexible_dates" in requirements and _explicit_strings(_unwrap(requirements, "flexible_dates")):
        unresolved.append("travel_dates")

    for key in ("party_size", "group_size", "partySize", "groupSize"):
        if key in requirements:
            count = _unwrap(requirements, key)
            if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 100:
                raise _InvalidRequirements
            unresolved.append("traveler_count")
    for key in ("party_composition", "group"):
        if key in requirements and _explicit_strings(_unwrap(requirements, key)):
            unresolved.append("party_composition")

    constraint_values: list[str] = []
    for key in ("constraints", "hard_constraints"):
        if key in requirements:
            constraint_values.extend(_string_list(_unwrap(requirements, key), field=key))
    constraints = tuple(constraint_values)
    if constraints:
        unresolved.extend("hard_constraint" for _ in constraints)

    destinations = _string_list(_unwrap(requirements, "destinations"), field="destinations")
    interests = _string_list(_unwrap(requirements, "interests"), field="interests")
    profile_destination_ids = requirements.get("destination_ids")
    if profile_destination_ids is not None:
        normalized_profile_ids = _string_list(profile_destination_ids, field="destination_ids")
    else:
        normalized_profile_ids = ()
    if destinations and not profile_destination_ids:
        unresolved.append("destination_resolution")

    has_destination_text = bool(destinations)
    unique_unresolved = tuple(dict.fromkeys(unresolved))
    return duration, interests, unique_unresolved, normalized_profile_ids, has_destination_text


def recommend_trip(
    *,
    requirements: Mapping[str, object],
    selected_destination_ids: Sequence[str],
    catalogue: Sequence[ProductionDestinationItem],
    evidence_by_destination: Mapping[str, Sequence[EvidenceSource]],
    locale: Locale,
    max_candidates: int = MAX_CANDIDATES,
    metadata_by_destination: Mapping[str, StructuredDestinationMetadata] | None = None,
    retrieval_port: StructuredDestinationCandidateRetrievalPort | None = None,
) -> RecommendationOutcome:
    """Assess confirmed requirements, then rank approved structured candidates.

    Durations are validated as trip-planning requirements but are not used to
    assert destination properties. Explicit party/budget/date/origin/access
    constraints fail closed because those properties are absent from the
    approved spatial catalogue contract. The retrieval path is exact and
    bounded; it is not semantic RAG.
    """
    if not isinstance(max_candidates, int) or isinstance(max_candidates, bool) or not 1 <= max_candidates <= MAX_CANDIDATES:
        return RecommendationOutcome(status="needs_confirmation", reason_code="requirements_invalid", items=[])
    if not isinstance(requirements, Mapping):
        return RecommendationOutcome(status="needs_confirmation", reason_code="requirements_invalid", items=[])
    try:
        duration_days, interests, unresolved, profile_destination_ids, has_destination_text = _assess_requirements(requirements)
    except _InvalidRequirements:
        return RecommendationOutcome(status="needs_confirmation", reason_code="requirements_invalid", items=[])
    if (
        not isinstance(selected_destination_ids, Sequence)
        or isinstance(selected_destination_ids, (str, bytes))
        or len(selected_destination_ids) > 50
    ):
        return RecommendationOutcome(status="needs_confirmation", reason_code="requirements_invalid", items=[])
    selected: list[str] = []
    for raw_id in selected_destination_ids:
        if not isinstance(raw_id, (str, int)) or isinstance(raw_id, bool):
            return RecommendationOutcome(status="needs_confirmation", reason_code="destination_selection_invalid", items=[])
        destination_id = str(raw_id)
        if (
            not destination_id.isascii() or not destination_id.isdecimal()
            or len(destination_id) > 19 or int(destination_id) < 1
            or int(destination_id) > _MAX_DESTINATION_ID
        ):
            return RecommendationOutcome(status="needs_confirmation", reason_code="destination_selection_invalid", items=[])
        if destination_id not in selected:
            selected.append(destination_id)
    if profile_destination_ids and tuple(selected) != profile_destination_ids:
        return RecommendationOutcome(
            status="needs_confirmation", reason_code="requirements_invalid", items=[],
            duration_days=duration_days,
        )
    if unresolved:
        # An exact requested place with no resolved production identity is a
        # catalogue-unavailable outcome when the approved view is empty. Other
        # explicit, unverifiable requirements still need traveler confirmation.
        if not catalogue and unresolved == ("destination_resolution",) and has_destination_text:
            return RecommendationOutcome(status="empty", reason_code="catalogue_empty", items=[])
        if "hard_constraint" in unresolved:
            reason = "hard_constraints_unverifiable"
        elif set(unresolved).issubset({"duration_days", "destination_resolution", "trip_profile"}):
            reason = "requirements_incomplete"
        else:
            reason = "requirements_unverifiable"
        return RecommendationOutcome(
            status="needs_confirmation", reason_code=reason,
            unresolved_fields=list(unresolved), duration_days=duration_days, items=[],
        )
    if not catalogue and selected:
        return RecommendationOutcome(
            status="empty", reason_code="catalogue_empty", items=[], duration_days=duration_days,
        )
    if not selected:
        return RecommendationOutcome(
            status="needs_confirmation", reason_code="destination_selection_required", items=[],
            duration_days=duration_days,
        )

    by_id: dict[str, ProductionDestinationItem] = {}
    conflicted: set[str] = set()
    for candidate in catalogue:
        previous = by_id.get(candidate.destination_id)
        if previous is not None and previous != candidate:
            conflicted.add(candidate.destination_id)
        else:
            by_id[candidate.destination_id] = candidate
    if conflicted:
        return RecommendationOutcome(status="needs_confirmation", reason_code="catalogue_identity_conflict", items=[])
    if any(destination_id not in by_id for destination_id in selected):
        return RecommendationOutcome(
            status="needs_confirmation", reason_code="selected_destination_unavailable", items=[]
        )
    if any(by_id[item].destination_type.strip().casefold() in _NON_SPATIAL_TYPES for item in selected):
        return RecommendationOutcome(status="empty", reason_code="non_spatial_item_not_supported", items=[])

    metadata = metadata_by_destination or {}
    retriever = retrieval_port or ApprovedCatalogueCandidateRetriever()
    try:
        hits = retriever.retrieve(
            query=CandidateRetrievalQuery(
                selected_destination_ids=tuple(selected), interests=interests,
                locale=locale, limit=max_candidates,
            ),
            catalogue=catalogue,
            metadata_by_destination=metadata,
        )
    except CandidateSetExceedsBound:
        return RecommendationOutcome(
            status="needs_confirmation", reason_code="candidate_set_exceeds_bound", items=[],
            duration_days=duration_days,
        )
    except (TypeError, ValueError):
        return RecommendationOutcome(status="needs_confirmation", reason_code="catalogue_identity_conflict", items=[])

    now = datetime.now(UTC)
    eligible: list[tuple[int, float, int, object, list[EvidenceSource]]] = []
    missing_selected_evidence = False
    seen_ids: set[str] = set()
    for hit in hits:
        candidate = hit.destination
        if candidate.destination_id in seen_ids:
            continue
        seen_ids.add(candidate.destination_id)
        if candidate.destination_type.strip().casefold() in _NON_SPATIAL_TYPES:
            if hit.scope_match == "explicit_identity":
                return RecommendationOutcome(status="empty", reason_code="non_spatial_item_not_supported", items=[])
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

        scope_raw = 1.0 if hit.scope_match == "explicit_identity" else 0.7
        score = round(scope_raw, 6)
        eligible.append((hit.request_order, score, int(candidate.destination_id), hit, sources))

    if missing_selected_evidence:
        return RecommendationOutcome(status="empty", reason_code="provenance_unavailable", items=[], duration_days=duration_days)
    if not eligible:
        return RecommendationOutcome(status="empty", reason_code="no_eligible_destination", items=[], duration_days=duration_days)

    eligible.sort(key=lambda row: (row[0], -row[1], row[2]))
    if len(eligible) > max_candidates:
        return RecommendationOutcome(
            status="needs_confirmation", reason_code="candidate_set_exceeds_bound", items=[],
            duration_days=duration_days,
        )
    items: list[RecommendedDestination] = []
    for rank, (_, score, _, hit, sources) in enumerate(eligible, start=1):
        # The current published tag projection has no locale metadata. Exact
        # string equality could compare unrelated scripts/languages, so no
        # interest is scored or claimed as matched until that contract exists.
        matched_interests: list[str] = []
        scope_raw = 1.0 if hit.scope_match == "explicit_identity" else 0.7
        unknown = list(UNKNOWN_FACT_FIELDS)
        warnings = ["ranking_is_structured_match_not_quality_score"]
        if interests:
            unknown.append("interest_match")
            warnings.append("interest_tags_not_locale_typed_unmatched")
        if all(source.retrieved_at is None for source in sources):
            warnings.append("source_freshness_unknown")
        components = [
            RankingComponent(
                component_key="destination_scope", raw_score=scope_raw, weight=0.7,
                weighted_score=round(scope_raw * 0.7, 6), matched_terms=[hit.selected_destination_id],
            )
        ]
        items.append(
            RecommendedDestination(
                destination_id=hit.destination.destination_id, rank=rank, final_score=score,
                matched_requirements=(
                    [f"destination:{hit.selected_destination_id}"]
                    + [f"interest:{term}" for term in matched_interests]
                ),
                unknown_fields=unknown,
                warnings=warnings,
                explanation_key=(
                    "explicit_destination_match" if hit.scope_match == "explicit_identity"
                    else "published_area_candidate"
                ),
                score_components=components, evidence=sources,
            )
        )
    return RecommendationOutcome(status="available", items=items, duration_days=duration_days)
