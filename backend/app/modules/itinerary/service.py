"""Build an approximate itinerary draft from eligible recommendation outputs."""

from app.modules.itinerary.contracts import ItineraryDraft, ItineraryStopDraft
from app.modules.recommendation.contracts import Locale, RecommendationOutcome


def generate_itinerary(
    *, recommendation: RecommendationOutcome, day_count: int, locale: Locale
) -> ItineraryDraft | None:
    """Return no plan when there are no eligible places; never invent stops."""
    del locale  # User-authored notes start empty; labels are localized in the PWA.
    if day_count not in (1, 2, 3):
        raise ValueError("day_count must be between one and three")
    if recommendation.status != "available" or not recommendation.items:
        return None

    stops: list[ItineraryStopDraft] = []
    orders_by_day = [0, 0, 0]
    for index, item in enumerate(recommendation.items):
        day_number = min(index + 1, day_count)
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
    return ItineraryDraft(day_count=day_count, stops=stops)

