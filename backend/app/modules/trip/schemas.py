"""Bounded API contracts for authenticated traveler-owned trip data."""

import json
import re
from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

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
    traveler_timezone: str | None = Field(default=None, max_length=80)
    traveler_reference_date: date | None = None
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


RequirementField = Literal[
    "origin", "travel_dates", "traveler_count", "budget", "soft_preference",
]


class RequirementConsentRequest(StrictModel):
    """Field-specific traveler choices submitted with explicit profile review."""

    contract_version: Literal["recommendation-consent-v1"]
    field_decisions: dict[RequirementField, Literal["must_have", "advisory"]] = Field(
        default_factory=dict, max_length=32
    )
    advisory_acknowledged_fields: list[RequirementField] = Field(default_factory=list, max_length=5)

    @field_validator("advisory_acknowledged_fields")
    @classmethod
    def unique_acknowledgements(cls, value: list[RequirementField]) -> list[RequirementField]:
        if len(value) != len(set(value)):
            raise ValueError("advisory acknowledgements must be unique")
        return value

    @model_validator(mode="after")
    def acknowledgements_match_advisory_choices(self):
        advisory = {
            field for field, decision in self.field_decisions.items() if decision == "advisory"
        }
        if set(self.advisory_acknowledged_fields) != advisory:
            raise ValueError("each advisory choice requires its explicit acknowledgement")
        return self


class ConfirmTripProfileRequest(StrictModel):
    expected_version: int = Field(ge=1)
    confirmed_requirements: dict[str, Any]
    destination_ids: list[str] = Field(default_factory=list, max_length=50)
    requirement_consent: RequirementConsentRequest | None = None

    @field_validator("confirmed_requirements")
    @classmethod
    def bounded_requirements(cls, value: dict[str, Any]) -> dict[str, Any]:
        if "requirement_consent" in value or "_recommendation_consent" in value:
            raise ValueError("requirement consent must use its dedicated request field")
        return _bounded_json(value)


class CreateRecommendationRequest(StrictModel):
    selected_destination_ids: list[str] = Field(default_factory=list, max_length=50)


class CreateItineraryRequest(StrictModel):
    recommendation_request_id: UUID
    day_count: StrictInt = Field(ge=1, le=365)
    locale: Locale


class ItineraryStopEdit(StrictModel):
    recommendation_id: UUID
    day_number: StrictInt = Field(ge=1, le=365)
    stop_order: StrictInt = Field(ge=1, le=50)
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
    stops: list[ItineraryStopEdit] = Field(max_length=1_000)

    @model_validator(mode="after")
    def bounded_unique_stop_positions(self) -> "UpdateItineraryRequest":
        counts: dict[int, int] = {}
        positions: set[tuple[int, int]] = set()
        recommendation_ids: set[UUID] = set()
        for stop in self.stops:
            counts[stop.day_number] = counts.get(stop.day_number, 0) + 1
            position = (stop.day_number, stop.stop_order)
            if position in positions or stop.recommendation_id in recommendation_ids:
                raise ValueError("itinerary stop positions and recommendations must be unique")
            positions.add(position)
            recommendation_ids.add(stop.recommendation_id)
        if any(count > 50 for count in counts.values()):
            raise ValueError("an itinerary day cannot contain more than 50 stops")
        return self

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
    # A bounded, validated advisory object, never authoritative. The repository
    # sanitizes the metadata through TripRequirementsV1 before exposing it.
    # The validated trip-requirements-v1 envelope has five top-level keys;
    # legacy bounded suggestions can contain more than four named fields.
    candidate_requirements: dict[str, Any] = Field(default_factory=dict, max_length=10)


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


class RetrievalCitationSourceResponse(StrictModel):
    source_id: str
    source_name: str
    source_url: str
    source_role: str
    license: str | None
    retrieved_at: datetime | None
    valid_from: datetime | None
    valid_until: datetime | None


class RetrievalCitationResponse(StrictModel):
    evidence_id: str
    canonical_entity_key: str
    destination_id: int
    document_id: str
    claim_key: str
    content_hash: str
    locale: Locale
    corpus: Literal["spatial_destinations", "culinary_knowledge"]
    text: str
    sources: list[RetrievalCitationSourceResponse] = Field(min_length=1, max_length=32)


class RecommendationItemResponse(StrictModel):
    recommendation_id: UUID
    destination_id: str
    rank: int
    final_score: float
    matched_requirements: list[str]
    unknown_fields: list[str]
    warnings: list[str]
    not_evaluated_fields: list[str] = Field(default_factory=list, max_length=32)
    explanation_key: str
    explanation_by_locale: dict[str, str]
    score_components: list["RecommendationScoreComponent"]
    evidence: list[RecommendationEvidence]
    retrieval_evidence_status: Literal[
        "disabled", "not_requested", "no_evidence", "unavailable", "invalid", "unmapped", "mapped"
    ] = "disabled"
    retrieval_evidence: list[RetrievalCitationResponse] = Field(default_factory=list, max_length=20)
    canonical_name: str
    localized_names: dict[str, str | None]
    city_name: str | None
    province_name: str
    destination_type: str


class RequirementAssessmentResponse(StrictModel):
    field: str
    decision: Literal["must_have", "advisory"] | None
    status: Literal["satisfied", "not_evaluated", "unresolved"]
    reason_code: str


class RecommendationResponse(StrictModel):
    recommendation_request_id: UUID
    status: Literal["available", "empty", "needs_confirmation"]
    reason_code: str | None
    algorithm_version: str
    retrieval_version: str
    trip_version: int
    unresolved_fields: list[str] = Field(default_factory=list, max_length=32)
    requirement_assessments: list[RequirementAssessmentResponse] = Field(default_factory=list, max_length=32)
    waived_fields: list[str] = Field(default_factory=list, max_length=32)
    not_evaluated_fields: list[str] = Field(default_factory=list, max_length=32)
    items: list[RecommendationItemResponse] = Field(max_length=1_000)


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
    day_number: StrictInt = Field(ge=1, le=365)
    stop_order: StrictInt = Field(ge=1, le=50)
    notes_by_locale: dict[str, str]
    canonical_name: str
    localized_names: dict[str, str | None]


class ItineraryResponse(StrictModel):
    itinerary_id: UUID
    trip_id: UUID
    recommendation_request_id: UUID
    version: int
    revision: int
    day_count: StrictInt = Field(ge=1, le=365)
    status: Literal["complete", "partial"]
    unplanned_days: list[StrictInt] = Field(max_length=365)
    warning_codes: list[str] = Field(default_factory=list, max_length=16)
    title_by_locale: dict[str, str]
    stops: list[ItineraryStopResponse]
    updated_at: datetime

    @model_validator(mode="after")
    def consistent_coverage(self) -> "ItineraryResponse":
        planned_days = {stop.day_number for stop in self.stops}
        expected_unplanned = [
            day for day in range(1, self.day_count + 1) if day not in planned_days
        ]
        if self.unplanned_days != expected_unplanned:
            raise ValueError("unplanned days must exactly describe missing coverage")
        expected_status = "partial" if expected_unplanned else "complete"
        if self.status != expected_status:
            raise ValueError("itinerary status must match day coverage")
        return self


class TripDeleteResponse(StrictModel):
    deleted: Literal[True] = True


class ConversationDeleteResponse(StrictModel):
    deleted: Literal[True] = True
