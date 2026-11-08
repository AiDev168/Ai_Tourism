"""Typed itinerary draft contracts. User-authored content is separate from facts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.recommendation.contracts import EvidenceSource


class ItineraryStopDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    destination_id: str = Field(pattern=r"^[0-9]+$")
    recommendation_rank: int = Field(ge=1, le=1_000)
    day_number: int = Field(ge=1, le=365)
    stop_order: int = Field(ge=1, le=50)
    planned_start_time: None = None
    duration_minutes: None = None
    travel_to_next_estimate_minutes: None = None
    user_notes_by_locale: dict[str, str] = Field(default_factory=dict)
    evidence: list[EvidenceSource] = Field(min_length=1, max_length=32)


class ItineraryDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    day_count: int = Field(ge=1, le=365)
    status: Literal["complete", "partial"]
    editable: Literal[True] = True
    warning_codes: list[str] = Field(default_factory=lambda: [
        "approximate_order_only",
        "no_hours_or_routes_inferred",
    ])
    unplanned_days: list[int] = Field(default_factory=list, max_length=365)
    stops: list[ItineraryStopDraft] = Field(max_length=1_000)

    @model_validator(mode="after")
    def consistent_coverage(self) -> "ItineraryDraft":
        if len(set(self.unplanned_days)) != len(self.unplanned_days):
            raise ValueError("unplanned days must be unique")
        if any(day < 1 or day > self.day_count for day in self.unplanned_days):
            raise ValueError("unplanned day is outside the requested itinerary")
        if any(stop.day_number > self.day_count for stop in self.stops):
            raise ValueError("stop day is outside the requested itinerary")
        planned = {stop.day_number for stop in self.stops}
        if any(day in planned for day in self.unplanned_days):
            raise ValueError("a day cannot be both planned and unplanned")
        expected = [day for day in range(1, self.day_count + 1) if day not in planned]
        if self.unplanned_days != expected:
            raise ValueError("unplanned days must exactly describe missing coverage")
        expected_status = "complete" if not expected else "partial"
        if self.status != expected_status:
            raise ValueError("itinerary status must match day coverage")
        return self

