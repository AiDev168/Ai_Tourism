"""Build an approximate itinerary draft from eligible recommendation outputs."""

from collections.abc import Mapping, Sequence
from math import asin, cos, isfinite, radians, sin, sqrt
from typing import Literal, TypedDict

from app.modules.itinerary.contracts import ItineraryDraft, ItineraryStopDraft
from app.modules.recommendation.contracts import Locale, RecommendationOutcome, RecommendedDestination


class DestinationGeography(TypedDict):
    """Trusted catalogue point metadata; absent values stay absent."""

    latitude: float
    longitude: float
    coordinate_role: Literal[
        "visitor_entrance", "property_reference", "representative_point", "test_fixture"
    ]


_VALID_POINT_ROLES = frozenset(
    {"visitor_entrance", "property_reference", "representative_point", "test_fixture"}
)
_NON_ARRIVAL_ROLES = frozenset({"property_reference", "representative_point"})
_EARTH_RADIUS_KM = 6_371.0088
_MAX_STOPS_PER_DAY = 50


def _point(value: object) -> tuple[float, float, str] | None:
    """Accept only finite WGS84 point metadata with a known coordinate role."""
    if not isinstance(value, Mapping):
        return None
    latitude = value.get("latitude")
    longitude = value.get("longitude")
    role = value.get("coordinate_role")
    if (
        isinstance(latitude, bool)
        or isinstance(longitude, bool)
        or not isinstance(latitude, (float, int))
        or not isinstance(longitude, (float, int))
        or not isfinite(float(latitude))
        or not isfinite(float(longitude))
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
        or not isinstance(role, str)
        or role not in _VALID_POINT_ROLES
    ):
        return None
    return float(latitude), float(longitude), role


def _distance_km(left: tuple[float, float, str], right: tuple[float, float, str]) -> float:
    """Great-circle distance for rough grouping only, never road travel."""
    lat1, lon1 = radians(left[0]), radians(left[1])
    lat2, lon2 = radians(right[0]), radians(right[1])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    haversine = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    return 2 * _EARTH_RADIUS_KM * asin(sqrt(min(1.0, haversine)))


def _geographic_days(
    *,
    items: Sequence[RecommendedDestination],
    day_count: int,
    geography_by_destination: Mapping[str, DestinationGeography] | None,
    origin: DestinationGeography | None,
) -> tuple[dict[int, list[int]], list[str]]:
    """Cluster nearby eligible points into days with deterministic farthest seeds.

    This only arranges an editable suggestion. There is deliberately no
    arbitrary distance cutoff, route feasibility decision, or travel-time
    estimate in this layer.
    """
    geography = geography_by_destination or {}
    points = {
        index: _point(geography.get(item.destination_id))
        for index, item in enumerate(items)
    }
    valid_indices = [index for index, point in points.items() if point is not None]
    missing = [index for index, point in points.items() if point is None]
    warnings: list[str] = []
    if missing:
        warnings.append("stop_location_unknown")
    if len(valid_indices) > 1:
        warnings.append("geodesic_grouping_heuristic_only")
    if any(points[index][2] in _NON_ARRIVAL_ROLES for index in valid_indices):
        warnings.append("position_not_entrance")

    groups: dict[int, list[int]] = {}
    if not valid_indices:
        # With no usable geography, retain a transparent ranked round-robin
        # layout so the requested days are visible. The warning above says
        # location data is unknown; no spatial assertion is made.
        for index in range(len(items)):
            day = index % day_count + 1
            groups.setdefault(day, []).append(index)
        return groups, warnings

    origin_point = _point(origin)
    if origin_point is not None:
        first_seed = min(
            valid_indices,
            key=lambda index: (_distance_km(origin_point, points[index]), index),
        )
    else:
        first_seed = valid_indices[0]
    seeds = [first_seed]
    seed_limit = min(day_count, len(valid_indices))
    while len(seeds) < seed_limit:
        remaining = [index for index in valid_indices if index not in seeds]
        # Farthest-first seeding keeps geographically distant candidates on
        # separate days when the confirmed trip has enough days.
        next_seed = max(
            remaining,
            key=lambda index: (
                min(_distance_km(points[index], points[seed]) for seed in seeds),
                -index,
            ),
        )
        seeds.append(next_seed)

    assigned: dict[int, list[int]] = {
        day: [seed] for day, seed in enumerate(seeds, start=1)
    }
    for index in valid_indices:
        if index in seeds:
            continue
        day = min(
            (candidate_day for candidate_day in assigned if len(assigned[candidate_day]) < _MAX_STOPS_PER_DAY),
            key=lambda candidate_day: (
                min(
                    _distance_km(points[index], points[member])
                    for member in assigned[candidate_day]
                ),
                candidate_day,
            ),
        )
        assigned[day].append(index)

    # Unknown-location stops use unoccupied days first where available; if
    # every day is already represented, place them on the least-filled day.
    for index in missing:
        available_days = [
            day
            for day in range(1, day_count + 1)
            if len(assigned.get(day, [])) < _MAX_STOPS_PER_DAY
        ]
        unused_days = [day for day in available_days if day not in assigned]
        if unused_days:
            assigned[unused_days[0]] = [index]
        elif available_days:
            day = min(available_days, key=lambda value: (len(assigned.get(value, [])), value))
            assigned.setdefault(day, []).append(index)
        else:
            # The caller bounds total stops to day_count * 50, so reaching
            # this branch would indicate an internal allocation bug.
            raise ValueError("itinerary stop capacity exceeded")

    # Within each day, arrange available points by nearest neighbour. This is
    # a display order heuristic only; it is not a route or road-distance claim.
    result: dict[int, list[int]] = {}
    for day, indices in assigned.items():
        pending = list(indices)
        point_indices = [index for index in pending if points[index] is not None]
        if not point_indices:
            result[day] = pending
            continue
        if origin_point is not None and len(seeds) == 1:
            current = min(point_indices, key=lambda index: (_distance_km(origin_point, points[index]), index))
        else:
            current = min(point_indices)
        ordered = [current]
        remaining_points = set(point_indices) - {current}
        while remaining_points:
            following = min(
                remaining_points,
                key=lambda index: (_distance_km(points[current], points[index]), index),
            )
            ordered.append(following)
            remaining_points.remove(following)
            current = following
        ordered.extend(index for index in pending if points[index] is None)
        result[day] = ordered
    return result, warnings


def generate_itinerary(
    *,
    recommendation: RecommendationOutcome,
    day_count: int,
    locale: Locale,
    geography_by_destination: Mapping[str, DestinationGeography] | None = None,
    origin: DestinationGeography | None = None,
) -> ItineraryDraft | None:
    """Return no plan when there are no eligible places; never invent stops."""
    del locale  # User-authored notes start empty; labels are localized in the PWA.
    if isinstance(day_count, bool) or not isinstance(day_count, int) or not 1 <= day_count <= 365:
        raise ValueError("day_count must be between one and 365")
    if recommendation.status != "available" or not recommendation.items:
        return None

    # Keep distinct eligible identities only and bound total/per-day payloads.
    selected_items = []
    seen_destination_ids: set[str] = set()
    for item in recommendation.items:
        if item.destination_id in seen_destination_ids:
            continue
        seen_destination_ids.add(item.destination_id)
        selected_items.append(item)
        if len(selected_items) >= min(len(recommendation.items), 1_000, day_count * 50):
            break

    assigned_by_day, geographic_warnings = _geographic_days(
        items=selected_items,
        day_count=day_count,
        geography_by_destination=geography_by_destination,
        origin=origin,
    )
    stops: list[ItineraryStopDraft] = []
    day_by_index = {
        index: day_number
        for day_number, indices in assigned_by_day.items()
        for index in indices
    }
    order_by_index = {
        index: order
        for indices in assigned_by_day.values()
        for order, index in enumerate(indices, start=1)
    }
    # Keep the recommendation order in the payload for compatibility; day and
    # stop_order carry the editable grouping independently.
    for index, item in enumerate(selected_items):
        stops.append(
            ItineraryStopDraft(
                destination_id=item.destination_id,
                recommendation_rank=item.rank,
                day_number=day_by_index[index],
                stop_order=order_by_index[index],
                user_notes_by_locale={},
                evidence=item.evidence,
            )
        )
    planned_days = {stop.day_number for stop in stops}
    unplanned_days = [day for day in range(1, day_count + 1) if day not in planned_days]
    warnings = ["approximate_order_only", "no_hours_or_routes_inferred", *geographic_warnings]
    if unplanned_days:
        warnings.append("some_days_unplanned_insufficient_candidates")
    return ItineraryDraft(
        day_count=day_count,
        status="partial" if unplanned_days else "complete",
        warning_codes=warnings,
        unplanned_days=unplanned_days,
        stops=stops,
    )

