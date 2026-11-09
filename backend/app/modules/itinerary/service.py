"""Build an approximate itinerary draft from eligible recommendation outputs."""

from app.modules.itinerary.contracts import ItineraryDraft, ItineraryStopDraft
from app.modules.recommendation.contracts import Locale, RecommendationOutcome


def generate_itinerary(
    *, recommendation: RecommendationOutcome, day_count: int, locale: Locale
) -> ItineraryDraft | None:
    """Return no plan when there are no eligible places; never invent stops."""
    del locale  # User-authored notes start empty; labels are localized in the PWA.
    if isinstance(day_count, bool) or not isinstance(day_count, int) or not 1 <= day_count <= 365:
        raise ValueError("day_count must be between one and 365")
    if recommendation.status != "available" or not recommendation.items:
        return None

    stops: list[ItineraryStopDraft] = []
    # Give each successive day one eligible stop before filling any day with
    # additional candidates. This keeps long requested plans honest when only
    # a partial evidence-backed candidate set exists.
    selected_items = recommendation.items[: min(len(recommendation.items), 1_000, day_count * 50)]
    assigned: list[tuple[int, object]] = []
    for index, item in enumerate(selected_items):
        assigned.append((index + 1, item) if index < day_count else (index % day_count + 1, item))
    orders_by_day = [0] * day_count
    for day_number, item in assigned:
        orders_by_day[day_number - 1] += 1
        stops.append(
            ItineraryStopDraft(
                destination_id=item.destination_id,
                recommendation_rank=item.rank,
                day_number=day_number,
                stop_order=orders_by_day[day_number - 1],
                user_notes_by_locale={},
                evidence=item.evidence,
            )
        )
    planned_days = {stop.day_number for stop in stops}
    unplanned_days = [day for day in range(1, day_count + 1) if day not in planned_days]
    warnings = ["approximate_order_only", "no_hours_or_routes_inferred"]
    if unplanned_days:
        warnings.append("some_days_unplanned_insufficient_candidates")
    return ItineraryDraft(
        day_count=day_count,
        status="partial" if unplanned_days else "complete",
        warning_codes=warnings,
        unplanned_days=unplanned_days,
        stops=stops,
    )

