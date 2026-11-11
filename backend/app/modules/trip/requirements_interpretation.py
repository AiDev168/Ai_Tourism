"""Deterministic, server-authoritative first-pass trip requirement interpretation.

This contract preserves the original traveler wording and only extracts
explicit, high-confidence facts. It deliberately never consults the host
clock or guesses currency, stay length, or destination identity.
"""

from __future__ import annotations

import re
import json
from datetime import date, datetime, timedelta
from typing import Generic, Literal, TypeVar
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from app.modules.trip.schemas import Locale

T = TypeVar("T")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EvidenceSpan(_StrictModel):
    """Offsets are Unicode code-point offsets into the exact original text."""

    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1, max_length=400)

    @model_validator(mode="after")
    def valid_range(self):
        if self.end <= self.start:
            raise ValueError("evidence span must be nonempty")
        return self


class RequirementValue(_StrictModel, Generic[T]):
    status: Literal["known", "ambiguous", "missing"]
    value: T | None = None
    evidence_span: EvidenceSpan | None = None
    source: Literal["traveler", "llm", "correction"] = "traveler"
    candidates: list[T] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def consistent_state(self):
        if self.status == "known" and self.value is None:
            raise ValueError("known requirements need a value")
        if self.status != "known" and self.value is not None:
            raise ValueError("unresolved requirements cannot carry a selected value")
        if self.status == "ambiguous" and len(self.candidates) < 2:
            raise ValueError("ambiguous requirements need at least two candidates")
        if self.status != "ambiguous" and self.candidates:
            raise ValueError("only ambiguous requirements may carry candidates")
        return self


class RelativeStartDateValue(_StrictModel):
    offset_days: StrictInt = Field(ge=0, le=365)
    anchor_date: date | None = None
    timezone: str | None = Field(default=None, max_length=80)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("timezone must be a recognized IANA timezone") from None
        return value


class BudgetValue(_StrictModel):
    amount: str = Field(min_length=1, max_length=32, pattern=r"^\d+(?:\.\d+)?$")
    scale: Literal["unit", "thousand", "million", "billion"] | None = None
    currency: str | None = Field(default=None, max_length=12)
    currency_status: Literal["known", "unknown", "ambiguous"]
    raw: str = Field(min_length=1, max_length=120)


class TripRequirementFields(_StrictModel):
    destination: RequirementValue[str]
    origin: RequirementValue[str]
    relative_start_date: RequirementValue[RelativeStartDateValue]
    duration_days: RequirementValue[StrictInt]
    travel_dates: RequirementValue[dict[str, date]]
    travelers: RequirementValue[StrictInt]
    budget: RequirementValue[BudgetValue]
    interests: RequirementValue[list[str]]
    hard_constraints: RequirementValue[list[str]]
    accessibility: RequirementValue[list[str]]


class TripClarification(_StrictModel):
    missing_fields: list[str] = Field(default_factory=list, max_length=20)
    ambiguous_fields: list[str] = Field(default_factory=list, max_length=20)
    question_fields: list[str] = Field(default_factory=list, max_length=20)


class TripRequirementsV1(_StrictModel):
    contract_version: Literal["trip-requirements-v1"] = "trip-requirements-v1"
    original_text: str = Field(min_length=1, max_length=1200)
    locale: Locale
    fields: TripRequirementFields
    clarification: TripClarification


class TripInterpretationRequest(_StrictModel):
    request_text: str = Field(min_length=1, max_length=1200)
    locale: Locale = "fa-IR"
    # Supplied only from an explicit traveler-selected date/timezone. The
    # interpreter never substitutes datetime.now() or the server timezone.
    traveler_timezone: str | None = Field(default=None, max_length=80)
    traveler_reference_date: date | None = None

    @field_validator("request_text")
    @classmethod
    def nonblank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("request_text must not be blank")
        return value

    @field_validator("traveler_timezone")
    @classmethod
    def valid_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("timezone must be a recognized IANA timezone") from None
        return value


class TripInterpretationResponse(_StrictModel):
    requirements: TripRequirementsV1


_DIGIT_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"
)
_NUMBER_WORDS: dict[str, int] = {
    "یک": 1, "يهك": 1, "دو": 2, "سه": 3, "چهار": 4, "پنج": 5,
    "شش": 6, "هفت": 7, "هشت": 8, "نه": 9, "ده": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_NUMBER = r"(?P<number>\d{1,3}|یک|يهك|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده|one|two|three|four|five|six|seven|eight|nine|ten)"


def _number(value: str) -> int | None:
    normalized = value.translate(_DIGIT_TRANSLATION).casefold().strip()
    if normalized.isdecimal():
        return int(normalized)
    return _NUMBER_WORDS.get(normalized)


def _span(text: str, start: int, end: int) -> EvidenceSpan:
    return EvidenceSpan(start=start, end=end, text=text[start:end])


def _known(value: T, span: EvidenceSpan | None) -> RequirementValue[T]:
    return RequirementValue(status="known", value=value, evidence_span=span, source="traveler")


def _missing() -> RequirementValue[T]:
    return RequirementValue(status="missing", value=None, source="traveler")


def _find_first(text: str, patterns: list[str]) -> tuple[re.Match[str] | None, str | None]:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
        if match:
            return match, match.group(0)
    return None, None


def interpret_trip_requirements(
    request_text: str,
    locale: Locale,
    *,
    traveler_timezone: str | None = None,
    traveler_reference_date: date | None = None,
) -> TripRequirementsV1:
    """Interpret explicit supported facts, leaving all other fields unresolved."""
    if not request_text.strip() or len(request_text) > 1200:
        raise ValueError("request_text must contain 1 to 1200 characters")
    if traveler_timezone is not None:
        ZoneInfo(traveler_timezone)

    destination_match, _ = _find_first(request_text, [
        r"شیراز", r"\bshiraz\b", r"شيراز", r"شيراز",
    ])
    destination = (
        _known(destination_match.group(0), _span(request_text, *destination_match.span()))
        if destination_match else _missing()
    )

    traveler_match = re.search(
        rf"(?:با|همراه\s+با|with)\s*{_NUMBER}\s*(?:نفر|مسافر|people|travelers|travellers)",
        request_text, re.IGNORECASE | re.UNICODE,
    )
    travelers = _number(traveler_match.group("number")) if traveler_match else None
    if travelers is not None and 1 <= travelers <= 50:
        travelers_field = _known(travelers, _span(request_text, *traveler_match.span()))
    elif traveler_match:
        travelers_field = _missing()
    else:
        travelers_field = _missing()

    relative_match = re.search(
        rf"(?:از\s*)?{_NUMBER}\s*(?:روز|day|days)\s*(?:دیگه|دیگر|بعد|later|from\s+now|after)?"
        rf"(?=\s|$|[،,.!?؟])",
        request_text, re.IGNORECASE | re.UNICODE,
    )
    # A bare duration is not a departure date. Only a relative marker makes
    # this a relative start date; and it must be separated from stay duration.
    relative_marker = re.compile(r"(?:دیگه|دیگر|بعد|later|from\s+now|in\s+\d+\s+days?)", re.I | re.U)
    english_in = re.search(rf"\bin\s+{_NUMBER}\s+days?\b", request_text, re.I | re.U)
    if relative_match and (relative_marker.search(relative_match.group(0)) or english_in):
        offset = _number(relative_match.group("number"))
        if offset is not None and 0 <= offset <= 365:
            anchor = traveler_reference_date
            start_date = anchor + timedelta(days=offset) if anchor else None
            relative_field = _known(
                RelativeStartDateValue(
                    offset_days=offset, anchor_date=start_date,
                    timezone=traveler_timezone,
                ), _span(request_text, *relative_match.span()),
            )
        else:
            relative_field = _missing()
    else:
        relative_field = _missing()

    duration_match, _ = _find_first(request_text, [
        rf"(?:سفر|مدت|به\s*مدت)\s*{_NUMBER}\s*[-\u200c\s]*(?:روزه|روز)",
        rf"{_NUMBER}\s*[-\u200c\s]*(?:روزه|روز)\s*(?:سفر|اقامت)",
        rf"(?:trip|stay|travel)\s+(?:for\s+)?{_NUMBER}\s+days?\b",
        rf"for\s+{_NUMBER}\s+days?\b",
        rf"{_NUMBER}\s*[-\u2010-\u2015]?\s*day\s+(?:trip|stay)\b",
    ])
    duration = _number(duration_match.group("number")) if duration_match else None
    if duration is not None and 1 <= duration <= 365:
        duration_field = _known(duration, _span(request_text, *duration_match.span()))
    elif duration_match:
        # The value is explicitly outside the supported contract; preserve its
        # text for clarification without inventing an alternative duration.
        duration_field = RequirementValue(
            status="missing", evidence_span=_span(request_text, *duration_match.span()),
            source="traveler",
        )
    else:
        duration_field = _missing()

    amount_pattern = (
        r"(?P<amount>\d+(?:[،,.]\d+)?|یک|يهك|دو|سه|چهار|پنج|شش|هفت|هشت|نه|ده|"
        r"one|two|three|four|five|six|seven|eight|nine|ten)\s*"
        r"(?P<scale>میلیون|مليون|million|هزار|thousand|میلیارد|billion)?\s*"
        r"(?P<currency>تومان|ریال|ريال|IRR|دلار|USD|یورو|EUR|درهم|AED)?"
    )
    amount_matches = list(re.finditer(amount_pattern, request_text, re.IGNORECASE | re.UNICODE))
    budget_markers = list(re.finditer(r"هزینه|بودجه|خرج|cost|budget|spend", request_text, re.I | re.U))
    budget_match = None
    if amount_matches and budget_markers:
        nearby = [
            (min(abs(amount.start() - marker.start()), abs(amount.end() - marker.start())), amount)
            for amount in amount_matches for marker in budget_markers
            if min(abs(amount.start() - marker.start()), abs(amount.end() - marker.start())) <= 48
        ]
        if nearby:
            budget_match = min(nearby, key=lambda item: item[0])[1]
    if budget_match:
        raw_amount = budget_match.group("amount").translate(_DIGIT_TRANSLATION).replace("،", ".").replace(",", "")
        amount_raw = str(_number(raw_amount)) if not raw_amount.isdecimal() else raw_amount
        scale_raw = budget_match.group("scale")
        scale = (
            "million" if scale_raw and scale_raw.casefold() in {"میلیون", "مليون", "million"}
            else "thousand" if scale_raw and scale_raw.casefold() in {"هزار", "thousand"}
            else "billion" if scale_raw and scale_raw.casefold() in {"میلیارد", "billion"}
            else "unit"
        )
        currency_raw = budget_match.group("currency")
        currency = None
        if currency_raw:
            currency = (
                "TOMAN" if currency_raw.casefold() == "تومان" else
                "IRR" if currency_raw.casefold() in {"ریال", "ريال", "irr"} else
                "USD" if currency_raw.casefold() in {"دلار", "usd"} else
                "EUR" if currency_raw.casefold() in {"یورو", "eur"} else "AED"
            )
        budget_value = BudgetValue(
            amount=amount_raw, scale=scale, currency=currency,
            currency_status="known" if currency else "unknown",
            raw=request_text[budget_match.start():budget_match.end()].strip(),
        )
        amount_start, amount_end = budget_match.span()
        while amount_end > amount_start and request_text[amount_end - 1].isspace():
            amount_end -= 1
        budget_field = _known(budget_value, _span(request_text, amount_start, amount_end))
    else:
        budget_field = _missing()

    history_match = _find_first(request_text, [
        r"مناطق\s*تاریخی", r"جاهای\s*تاریخی", r"اماکن\s*تاریخی",
        r"\bhistoric(?:al)?\s+(?:areas|places|sites|attractions)\b",
        r"\bhistory\b", r"المناطق\s+التاريخية", r"المعالم\s+التاريخية",
    ])[0]
    interests_field = (
        _known(["historical_attractions"], _span(request_text, *history_match.span()))
        if history_match else _missing()
    )

    # The first safe slice keeps candidate extraction observable while unknown
    # categories remain explicitly missing instead of being model-filled.
    origin = _missing()
    travel_dates = _missing()
    hard_constraints = _missing()
    accessibility = _missing()

    missing_fields = [
        name for name, field in (
            ("destination", destination), ("duration_days", duration_field),
        ) if field.status == "missing"
    ]
    ambiguous_fields = [
        name for name, field in (
            ("destination", destination), ("duration_days", duration_field),
            ("travelers", travelers_field),
        ) if field.status == "ambiguous"
    ]
    question_fields = list(missing_fields) + list(ambiguous_fields)
    if budget_field.status == "known" and budget_field.value.currency_status != "known":
        question_fields.append("budget.currency")
    return TripRequirementsV1(
        original_text=request_text, locale=locale,
        fields=TripRequirementFields(
            destination=destination, origin=origin,
            relative_start_date=relative_field, duration_days=duration_field,
            travel_dates=travel_dates, travelers=travelers_field, budget=budget_field,
            interests=interests_field, hard_constraints=hard_constraints,
            accessibility=accessibility,
        ),
        clarification=TripClarification(
            missing_fields=missing_fields, ambiguous_fields=ambiguous_fields,
            question_fields=question_fields,
        ),
    )


def trip_requirements_storage_view(value: TripRequirementsV1) -> dict[str, object]:
    """Persist the versioned source/evidence contract plus legacy profile views.

    Existing consumers continue to read the camel-case fields. The canonical
    contract remains alongside them so history/reopen can recover evidence and
    correction provenance without reparsing the original request.
    """

    def json_safe(item: object) -> object:
        if isinstance(item, BaseModel):
            return json.loads(item.model_dump_json())
        if isinstance(item, (date, datetime)):
            return item.isoformat()
        if isinstance(item, dict):
            return {str(key): json_safe(nested) for key, nested in item.items()}
        if isinstance(item, (list, tuple)):
            return [json_safe(nested) for nested in item]
        return item

    def field_view(field: RequirementValue) -> dict[str, object]:
        evidence = field.evidence_span.text if field.evidence_span else None
        mapped_status = {"known": "extracted", "missing": "unknown", "ambiguous": "ambiguous"}[field.status]
        result: dict[str, object] = {
            "value": json_safe(field.value),
            "status": mapped_status,
            "evidence": evidence,
        }
        if field.candidates:
            result["candidates"] = field.candidates
        return result

    fields = value.fields
    budget = fields.budget.value
    budget_view: dict[str, object] | None = None
    if budget is not None:
        amount: int | float
        number = float(budget.amount)
        amount = int(number) if number.is_integer() else number
        budget_view = {
            "amount": amount,
            "currency": budget.currency,
            "unit": budget.scale or "unit",
            "scale": budget.scale,
            "raw": budget.raw,
            "currency_status": budget.currency_status,
        }

    requirements: dict[str, object] = {
        "requestText": value.original_text,
        "locale": value.locale,
        "destinations": field_view(fields.destination),
        "origin": field_view(fields.origin),
        "relativeStartDate": field_view(fields.relative_start_date),
        "durationDays": field_view(fields.duration_days),
        "travelDates": field_view(fields.travel_dates),
        "travelerCount": field_view(fields.travelers),
        "budget": {"status": "extracted", "evidence": fields.budget.evidence_span.text if fields.budget.evidence_span else None,
                   "value": budget_view} if budget_view is not None else field_view(fields.budget),
        "interests": field_view(fields.interests),
        "softPreferences": {"value": None, "status": "unknown", "evidence": None},
        "constraints": field_view(fields.hard_constraints),
        "accessibility": field_view(fields.accessibility),
        "extractionStatus": "needs_clarification" if value.clarification.question_fields else "ready",
        "missingRequired": [
            {"duration_days": "duration", "destination": "destination"}[name]
            for name in value.clarification.missing_fields if name in {"duration_days", "destination"}
        ],
        "ambiguousRequired": [
            {"duration_days": "duration", "destination": "destination"}[name]
            for name in value.clarification.ambiguous_fields if name in {"duration_days", "destination"}
        ],
        "clarificationFields": value.clarification.question_fields,
        "confirmationRequired": [],
        "destinationVerification": "user_input_unverified",
        "requirements_v1": value.model_dump(mode="json"),
    }
    destination_value = fields.destination.value
    if destination_value:
        requirements["destinations"] = {
            "value": [destination_value], "status": "extracted",
            "evidence": fields.destination.evidence_span.text if fields.destination.evidence_span else None,
        }
    else:
        requirements["destinations"] = field_view(fields.destination)
    return requirements
