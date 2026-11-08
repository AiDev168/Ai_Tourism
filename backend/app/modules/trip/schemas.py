"""Bounded API contracts for authenticated traveler-owned trip data."""

import json
import re
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Locale = Literal["fa-IR", "en-US", "ar"]


def _bounded_json(value: dict[str, Any]) -> dict[str, Any]:
    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        raise ValueError("must be JSON-compatible") from None
    if len(encoded) > 32_000:
        raise ValueError("structured trip data is too large")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StartConversationRequest(StrictModel):
    locale: Locale = "fa-IR"
    request_text: str = Field(min_length=1, max_length=1200)
    extracted_requirements: dict[str, Any] = Field(default_factory=dict)
    confirmed_requirements: dict[str, Any] = Field(default_factory=dict)
    destination_ids: list[str] = Field(default_factory=list, max_length=50)
    idempotency_key: str = Field(min_length=8, max_length=128)

    @field_validator("request_text")
    @classmethod
    def nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_text must not be blank")
        return value

    @field_validator("idempotency_key")
    @classmethod
    def safe_idempotency_key(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", value):
            raise ValueError("invalid idempotency key")
        return value

    @field_validator("extracted_requirements", "confirmed_requirements")
    @classmethod
    def bounded_requirement_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _bounded_json(value)


class AppendMessageRequest(StrictModel):
    trip_id: UUID
    content: str = Field(min_length=1, max_length=4000)
    extracted_requirements: dict[str, Any] | None = None
    idempotency_key: str = Field(min_length=8, max_length=128)
    expected_version: int = Field(ge=1)
    replace_previous_request: bool = False

    @field_validator("content")
    @classmethod
    def nonblank_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value

    @field_validator("idempotency_key")
    @classmethod
    def safe_idempotency_key(cls, value: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", value):
            raise ValueError("invalid idempotency key")
        return value

    @field_validator("extracted_requirements")
    @classmethod
    def bounded_extraction(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return _bounded_json(value) if value is not None else None


class ConfirmTripProfileRequest(StrictModel):
    expected_version: int = Field(ge=1)
    confirmed_requirements: dict[str, Any]
    destination_ids: list[str] = Field(default_factory=list, max_length=50)

    @field_validator("confirmed_requirements")
    @classmethod
    def bounded_requirements(cls, value: dict[str, Any]) -> dict[str, Any]:
        return _bounded_json(value)


class CreateRecommendationRequest(StrictModel):
    selected_destination_ids: list[str] = Field(default_factory=list, max_length=50)


class CreateItineraryRequest(StrictModel):
    recommendation_request_id: UUID
    day_count: int = Field(ge=1, le=3)
    locale: Locale


class ItineraryStopEdit(StrictModel):
    recommendation_id: UUID
    day_number: int = Field(ge=1, le=3)
    stop_order: int = Field(ge=1, le=50)
    notes_by_locale: dict[Locale, str] = Field(default_factory=dict)

    @field_validator("notes_by_locale")
    @classmethod
    def bounded_notes(cls, value: dict[Locale, str]) -> dict[Locale, str]:
        if any(len(note) > 2000 for note in value.values()):
            raise ValueError("itinerary note is too long")
        return value


class UpdateItineraryRequest(StrictModel):
    expected_revision: int = Field(ge=1)
    title_by_locale: dict[Locale, str] = Field(default_factory=dict)
    stops: list[ItineraryStopEdit] = Field(max_length=50)

    @field_validator("title_by_locale")
    @classmethod
    def bounded_titles(cls, value: dict[Locale, str]) -> dict[Locale, str]:
        if any(not title.strip() or len(title) > 200 for title in value.values()):
            raise ValueError("itinerary title is invalid")
        return value


class MessageResponse(StrictModel):
    message_id: UUID
    conversation_id: UUID
    trip_id: UUID | None
    role: Literal["user", "assistant", "system", "tool"]
    content: str
    created_at: datetime


class TripResponse(StrictModel):
    trip_id: UUID
    conversation_id: UUID | None
    version: int
    locale: Locale
    original_request: str
    extracted_requirements: dict[str, Any]
    confirmed_requirements: dict[str, Any]
    destination_ids: list[str]
    duration_days: int | None
    traveler_count: int | None
    budget_amount_original: str | None
    budget_currency_iso: str | None
    budget_unit: str | None
    latest_recommendation_request_id: UUID | None
    latest_itinerary_id: UUID | None
    trip_status: str
    created_at: datetime
    updated_at: datetime


class ConversationSummary(StrictModel):
    conversation_id: UUID
    locale: Locale
    version: int
    started_at: datetime
    updated_at: datetime
    last_message_at: datetime | None
    trips: list[TripResponse]


class ConversationDetail(ConversationSummary):
    messages: list[MessageResponse]


class StartConversationResponse(StrictModel):
    conversation: ConversationDetail
    trip: TripResponse
    initial_message: MessageResponse


class MessageAppendResponse(StrictModel):
    conversation: ConversationDetail
    trip: TripResponse
    message: MessageResponse


class ConversationListResponse(StrictModel):
    items: list[ConversationSummary]
    next_cursor: UUID | None


class RecommendationEvidence(StrictModel):
    source_id: int
    source_name: str
    source_url: str
    source_role: str
    evidence_note: str | None = None
    retrieved_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    reliability_score: float | None = None


class RecommendationItemResponse(StrictModel):
    recommendation_id: UUID
    destination_id: str
    rank: int
    final_score: float
    matched_requirements: list[str]
    unknown_fields: list[str]
    warnings: list[str]
    explanation_key: str
    explanation_by_locale: dict[str, str]
    score_components: list["RecommendationScoreComponent"]
    evidence: list[RecommendationEvidence]
    canonical_name: str
    localized_names: dict[str, str | None]
    city_name: str | None
    province_name: str
    destination_type: str


class RecommendationResponse(StrictModel):
    recommendation_request_id: UUID
    status: Literal["available", "empty", "needs_confirmation"]
    reason_code: str | None
    algorithm_version: str
    retrieval_version: str
    trip_version: int
    items: list[RecommendationItemResponse]


class RecommendationScoreComponent(StrictModel):
    component_key: str
    raw_score: float
    weight: float
    weighted_score: float
    matched_terms: list[str]


class ItineraryStopResponse(StrictModel):
    itinerary_stop_id: UUID
    recommendation_id: UUID
    destination_id: str
    day_number: int
    stop_order: int
    notes_by_locale: dict[str, str]
    canonical_name: str
    localized_names: dict[str, str | None]


class ItineraryResponse(StrictModel):
    itinerary_id: UUID
    trip_id: UUID
    recommendation_request_id: UUID
    version: int
    revision: int
    day_count: int
    title_by_locale: dict[str, str]
    stops: list[ItineraryStopResponse]
    updated_at: datetime


class TripDeleteResponse(StrictModel):
    deleted: Literal[True] = True


class ConversationDeleteResponse(StrictModel):
    deleted: Literal[True] = True
