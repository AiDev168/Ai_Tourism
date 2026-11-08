"""Typed itinerary draft contracts. User-authored content is separate from facts."""

from pydantic import BaseModel, ConfigDict, Field

from app.modules.recommendation.contracts import EvidenceSource


class ItineraryStopDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    destination_id: str = Field(pattern=r"^[0-9]+$")
    recommendation_rank: int = Field(ge=1, le=3)
    day_number: int = Field(ge=1, le=3)
    stop_order: int = Field(ge=1, le=3)
    planned_start_time: None = None
    duration_minutes: None = None
    travel_to_next_estimate_minutes: None = None
    user_notes_by_locale: dict[str, str] = Field(default_factory=dict)
    evidence: list[EvidenceSource] = Field(min_length=1, max_length=32)


class ItineraryDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    day_count: int = Field(ge=1, le=3)
    status: str = "editable_suggestion"
    warning_codes: list[str] = Field(default_factory=lambda: [
        "approximate_order_only",
        "no_hours_or_routes_inferred",
    ])
    stops: list[ItineraryStopDraft] = Field(max_length=9)

