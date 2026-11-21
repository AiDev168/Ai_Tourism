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
    source: Literal["traveler", "llm", "fallback", "correction"] = "traveler"
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


def parse_explicit_budget_text(raw: str) -> BudgetValue | None:
    """Parse an already semantically identified budget string without conversion.

    The LLM chooses whether a quoted phrase is a budget; this helper validates
    only its bounded numeric/unit/currency syntax. It does not require the
    deterministic parser to recognize surrounding wording such as "our limit
    is" or "we can spend".
    """
    if not raw or len(raw) > 120 or any(ord(char) < 32 or ord(char) == 127 for char in raw):
        return None
    normalized = raw.translate(_DIGIT_TRANSLATION).strip()
    amount_words = "|".join(re.escape(value) for value in sorted(_NUMBER_WORDS, key=len, reverse=True))
    pattern = re.compile(
        rf"(?P<amount>\d{{1,3}}(?:[,٬]\d{{3}})+(?:\.\d+)?|\d+(?:\.\d+)?|{amount_words})"
        rf"(?:\s*(?P<scale>million|billion|thousand|میلیون|مليون|میلیارد|هزار))?"
        rf"(?:\s*(?P<currency>TOMAN|IRR|USD|EUR|AED|ریال|ريال|تومان|تومنه?|دلار|یورو|درهم))?",
        re.IGNORECASE | re.UNICODE,
    )
    match = pattern.fullmatch(normalized)
    if match is None:
        return None
    amount_token = match.group("amount").replace(",", "").replace("٬", "")
    if amount_token.replace(".", "", 1).isdecimal():
        amount = amount_token
    else:
        number = _number(amount_token)
        if number is None:
            return None
        amount = str(number)
    scale_token = (match.group("scale") or "").casefold()
    scale = (
        "million" if scale_token in {"million", "میلیون", "مليون"} else
        "billion" if scale_token in {"billion", "میلیارد"} else
        "thousand" if scale_token in {"thousand", "هزار"} else "unit"
    )
    currency_token = (match.group("currency") or "").casefold()
    currency = (
        "TOMAN" if currency_token in {"toman", "تومان", "تومن", "تومنه"} else
        "IRR" if currency_token in {"irr", "ریال", "ريال"} else
        "USD" if currency_token in {"usd", "دلار"} else
        "EUR" if currency_token in {"eur", "یورو"} else
        "AED" if currency_token in {"aed", "درهم"} else None
    )
    return BudgetValue(
        amount=amount, scale=scale, currency=currency,
        currency_status="known" if currency else "unknown", raw=raw.strip(),
    )


class TripRequirementFields(_StrictModel):
    destination: RequirementValue[str]
    origin: RequirementValue[str]
    relative_start_date: RequirementValue[RelativeStartDateValue]
    duration_days: RequirementValue[StrictInt]
    travel_dates: RequirementValue[dict[str, date]]
    travelers: RequirementValue[StrictInt]
    budget: RequirementValue[BudgetValue]
    interests: RequirementValue[list[str]]
    soft_preferences: RequirementValue[list[str]] = Field(
        default_factory=lambda: RequirementValue[list[str]](status="missing", source="fallback")
    )
    hard_constraints: RequirementValue[list[str]]
    accessibility: RequirementValue[list[str]]
    travel_difficulty: RequirementValue[list[str]] = Field(
        default_factory=lambda: RequirementValue[list[str]](status="missing", source="fallback")
    )
    weather_preferences: RequirementValue[list[str]] = Field(
        default_factory=lambda: RequirementValue[list[str]](status="missing", source="fallback")
    )
    local_cuisine: RequirementValue[list[str]] = Field(
        default_factory=lambda: RequirementValue[list[str]](status="missing", source="fallback")
    )


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


_DIGIT_TRANSLATION = str.maketrans({
    **{ord(chr(start + offset)): str(offset) for start in (0x06F0, 0x0660) for offset in range(10)},
})
_NUMBER_WORDS: dict[str, int] = {
    "\u06cc\u06a9": 1, "\u06cc\u06a9\u06cc": 1,
    "\u062f\u0648": 2, "\u0633\u0647": 3, "\u0686\u0647\u0627\u0631": 4,
    "\u067e\u0646\u062c": 5, "\u0634\u0634": 6, "\u0647\u0641\u062a": 7,
    "\u0647\u0634\u062a": 8, "\u0646\u0647": 9, "\u062f\u0647": 10,
    "\u0648\u0627\u062d\u062f": 1, "\u0627\u062b\u0646\u0627\u0646": 2,
    "\u062b\u0644\u0627\u062b\u0629": 3, "\u0623\u0631\u0628\u0639\u0629": 4,
    "\u062e\u0645\u0633\u0629": 5, "\u0633\u062a\u0629": 6,
    "\u0633\u0628\u0639\u0629": 7, "\u062b\u0645\u0627\u0646\u064a\u0629": 8,
    "\u062a\u0633\u0639\u0629": 9, "\u0639\u0634\u0631\u0629": 10,
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_NUMBER = r"(?P<number>\d{1,3}|" + "|".join(
    re.escape(value) for value in sorted(_NUMBER_WORDS, key=len, reverse=True)
) + r")"


def _number(value: str) -> int | None:
    normalized = value.translate(_DIGIT_TRANSLATION).casefold().strip()
    if normalized.isdecimal():
        return int(normalized)
    return _NUMBER_WORDS.get(normalized)


def _span(text: str, start: int, end: int) -> EvidenceSpan:
    return EvidenceSpan(start=start, end=end, text=text[start:end])


def _known(value: T, span: EvidenceSpan | None) -> RequirementValue[T]:
    return RequirementValue(status="known", value=value, evidence_span=span, source="fallback")


def _missing() -> RequirementValue[T]:
    return RequirementValue(status="missing", value=None, source="fallback")


def _find_first(text: str, patterns: list[str]) -> tuple[re.Match[str] | None, str | None]:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.UNICODE)
        if match:
            return match, match.group(0)
    return None, None


def _duration_field(text: str) -> tuple[RequirementValue[int], re.Match[str] | None]:
    patterns = [
        rf"(?:\u0633\u0641\u0631|\u0645\u062f\u062a(?:\s+\u0633\u0641\u0631)?|\u0628\u0647\s*\u0645\u062f\u062a|\u0628\u0631\u0627\u06cc)\s*{_NUMBER}\s*[-\u200c\s]*(?:\u0631\u0648\u0632\u0647|\u0631\u0648\u0632)",
        rf"{_NUMBER}\s*[-\u200c\s]*(?:\u0631\u0648\u0632\u0647|\u0631\u0648\u0632)\s*(?:\u0633\u0641\u0631|\u0627\u0642\u0627\u0645\u062a)",
        rf"(?:\u0644\u0645\u062f\u0629\s+)?(?:\u0631\u062d\u0644\u0629\s+)?\u0644\u0645\u062f\u0629\s*{_NUMBER}\s*(?:\u0623\u064a\u0627\u0645|\u0627\u064a\u0627\u0645|\u064a\u0648\u0645)",
        rf"(?:trip|stay|travel)\s+(?:for\s+)?{_NUMBER}\s+days?\b",
        rf"for\s+{_NUMBER}\s+days?\b",
        rf"{_NUMBER}\s*[-\u2010-\u2015]?\s*day\s+(?:trip|stay)\b",
    ]
    match, _ = _find_first(text, patterns)
    count = _number(match.group("number")) if match else None
    if count is not None and 1 <= count <= 365:
        return _known(count, _span(text, *match.span())), match
    if match:
        return RequirementValue(status="missing", evidence_span=_span(text, *match.span()), source="fallback"), match
    return _missing(), None


def interpret_trip_requirements(
    request_text: str,
    locale: Locale,
    *,
    traveler_timezone: str | None = None,
    traveler_reference_date: date | None = None,
) -> TripRequirementsV1:
    """Interpret explicit supported facts without consulting the host clock."""
    if not request_text.strip() or len(request_text) > 1200:
        raise ValueError("request_text must contain 1 to 1200 characters")
    if traveler_timezone is not None:
        ZoneInfo(traveler_timezone)

    destination_match, _ = _find_first(request_text, [
        r"\u0634\u06cc\u0631\u0627\u0632", r"\u0634\u064a\u0631\u0627\u0632", r"\bshiraz\b",
    ])
    destination = _known(destination_match.group(0), _span(request_text, *destination_match.span())) if destination_match else _missing()

    traveler_match = re.search(
        rf"(?:\u0628\u0627|\u0647\u0645\u0631\u0627\u0647\s+\u0628\u0627|\u0628\u0631\u0627\u06cc|with|for)\s*{_NUMBER}\s*(?:\u0646\u0641\u0631|\u0645\u0633\u0627\u0641\u0631(?:\u0627\u0646)?|people|persons?|travelers?|travellers?)(?!\w)",
        request_text, re.IGNORECASE | re.UNICODE,
    )
    if traveler_match is None:
        traveler_match = re.search(
            rf"{_NUMBER}\s*(?:\u0646\u0641\u0631|\u0645\u0633\u0627\u0641\u0631(?:\u0627\u0646)?|people|persons?|travelers?|travellers?)",
            request_text, re.IGNORECASE | re.UNICODE,
        )
    travelers = _number(traveler_match.group("number")) if traveler_match else None
    travelers_field = _known(travelers, _span(request_text, *traveler_match.span())) if travelers and 1 <= travelers <= 50 else _missing()

    duration_field, duration_match = _duration_field(request_text)
    # Relative departure is deliberately independent from duration. A relative
    # expression must include its marker; plain "three days" can only be a stay.
    relative_patterns = [
        rf"(?:\u0627\u0632\s*)?{_NUMBER}\s*(?:\u0631\u0648\u0632|days?)\s*(?:\u062f\u06cc\u06af\u0647|\u062f\u06cc\u06af\u0631|\u0628\u0639\u062f|later|from\s+now|after)",
        rf"(?:\u0628\u0639\u062f|\u062e\u0644\u0627\u0644)\s*{_NUMBER}\s*(?:\u0623\u064a\u0627\u0645|\u0627\u064a\u0627\u0645|\u064a\u0648\u0645)",
        rf"in\s+{_NUMBER}\s+days?\b",
    ]
    relative_match, _ = _find_first(request_text, relative_patterns)
    if relative_match and not (duration_match and relative_match.start() == duration_match.start()):
        offset = _number(relative_match.group("number"))
        if offset is not None and 0 <= offset <= 365:
            anchor = traveler_reference_date + timedelta(days=offset) if traveler_reference_date else None
            relative_field = _known(RelativeStartDateValue(offset_days=offset, anchor_date=anchor,
                                                          timezone=traveler_timezone),
                                    _span(request_text, *relative_match.span()))
        else:
            relative_field = _missing()
    else:
        today = r"(?:\u0627\u0645\u0631\u0648\u0632|\u0627\u0644\u064a\u0648\u0645|today|\u0627\u0644\u064a\u0648\u0645)"
        after_tomorrow = r"(?:\u067e\u0633[\s\u200c-]*\u0641\u0631\u062f\u0627|day\s+after\s+tomorrow|\u0628\u0639\u062f\s+\u063a\u062f)"
        tomorrow = r"(?:\u0641\u0631\u062f\u0627|tomorrow|\u063a\u062f(?:\u0627\u064b|\u0627)?)"
        day_match = re.search(rf"(?<!\w)(?:\u0627\u0632\s+)?(?P<phrase>{after_tomorrow}|{today}|{tomorrow})(?!\w)", request_text, re.I | re.U)
        if day_match:
            phrase = day_match.group("phrase")
            offset = 0 if re.fullmatch(today, phrase, re.I | re.U) else 2 if re.fullmatch(after_tomorrow, phrase, re.I | re.U) else 1
            anchor = traveler_reference_date + timedelta(days=offset) if traveler_reference_date else None
            relative_field = _known(RelativeStartDateValue(offset_days=offset, anchor_date=anchor,
                                                          timezone=traveler_timezone),
                                    _span(request_text, *day_match.span()))
        else:
            relative_field = _missing()

    date_matches = list(re.finditer(r"(?P<date>\d{4}-\d{2}-\d{2})", request_text))
    travel_dates = _missing()
    if len(date_matches) >= 2:
        start_markers = re.compile(
            r"\b(?:departure|depart|start|leave|outbound)\b|"
            r"\u0627\u0644\u0645\u063a\u0627\u062f\u0631\u0629|\u0627\u0644\u0628\u062f\u0621|"
            r"\u0634\u0631\u0648\u0639|\u0639\u0632\u06cc\u0645\u062a",
            re.I | re.U,
        )
        end_markers = re.compile(
            r"\b(?:return|back|end|until|inbound)\b|"
            r"\u0627\u0644\u0639\u0648\u062f\u0629|\u0627\u0644\u0646\u0647\u0627\u064a\u0629|"
            r"\u0628\u0627\u0632\u06af\u0634\u062a|\u067e\u0627\u06cc\u0627\u0646",
            re.I | re.U,
        )
        labelled_start: tuple[re.Match[str], date] | None = None
        labelled_end: tuple[re.Match[str], date] | None = None
        has_date_label = False
        parsed_dates: list[tuple[re.Match[str], date]] = []
        for index, match in enumerate(date_matches):
            try:
                parsed = date.fromisoformat(match.group("date"))
            except ValueError:
                continue
            segment_start = date_matches[index - 1].end() if index else 0
            label_context = request_text[segment_start:match.start()]
            start_match = start_markers.search(label_context)
            end_match = end_markers.search(label_context)
            has_date_label = has_date_label or bool(start_match or end_match)
            if start_match:
                labelled_start = (match, parsed)
            if end_match:
                labelled_end = (match, parsed)
            parsed_dates.append((match, parsed))

        pair: tuple[tuple[re.Match[str], date], tuple[re.Match[str], date]] | None = None
        if has_date_label:
            if labelled_start and labelled_end and labelled_start[1] <= labelled_end[1]:
                pair = (labelled_start, labelled_end)
        elif len(parsed_dates) >= 2 and parsed_dates[0][1] <= parsed_dates[1][1]:
            pair = (parsed_dates[0], parsed_dates[1])
        if pair:
            first_match, first_date = pair[0]
            second_match, second_date = pair[1]
            span_start = min(first_match.start(), second_match.start())
            span_end = max(first_match.end(), second_match.end())
            travel_dates = _known(
                {"start": first_date, "end": second_date},
                _span(request_text, span_start, span_end),
            )

    amount_pattern = (
        r"(?<!\w)(?P<amount>\d+(?:[.,]\d+)?|" + "|".join(
            re.escape(word) for word in sorted(_NUMBER_WORDS, key=len, reverse=True)
        ) + r")\s*"
        r"(?P<scale>\u0645\u06cc\u0644\u06cc\u0648\u0646|\u0645\u0644\u064a\u0648\u0646|million|\u0647\u0632\u0627\u0631|thousand|\u0645\u06cc\u0644\u06cc\u0627\u0631\u062f|billion)?\s*"
        r"(?P<currency>\u062a\u0648\u0645\u0627\u0646|toman|\u0631\u06cc\u0627\u0644|\u0631\u064a\u0627\u0644|IRR|\u062f\u0644\u0627\u0631|USD|\u064a\u0648\u0631\u0648|EUR|\u062f\u0631\u0647\u0645|AED)?(?!\w)"
    )
    amount_matches = list(re.finditer(amount_pattern, request_text, re.I | re.U))
    budget_markers = list(re.finditer(
        r"\u0647\u0632\u06cc\u0646\u0647|\u0628\u0648\u062f\u062c\u0647|\u062e\u0631\u062c|cost|budget|spend|\u062a\u0643\u0644\u0641\u0629|\u0645\u064a\u0632\u0627\u0646\u064a\u0629",
        request_text, re.I | re.U,
    ))
    budget_match = None
    if amount_matches and budget_markers:
        nearby = [(min(abs(amount.start() - marker.start()), abs(amount.end() - marker.start())), amount)
                  for amount in amount_matches for marker in budget_markers
                  if min(abs(amount.start() - marker.start()), abs(amount.end() - marker.start())) <= 60]
        if nearby:
            budget_match = min(nearby, key=lambda item: item[0])[1]
    if budget_match:
        amount_text = budget_match.group("amount").translate(_DIGIT_TRANSLATION).replace(",", "").replace("?", ".")
        amount_raw = str(_number(amount_text)) if not amount_text.replace(".", "", 1).isdecimal() else amount_text
        scale_raw = (budget_match.group("scale") or "").casefold()
        scale = "million" if scale_raw in {"million", "\u0645\u06cc\u0644\u06cc\u0648\u0646", "\u0645\u0644\u064a\u0648\u0646"} else (
            "thousand" if scale_raw in {"thousand", "\u0647\u0632\u0627\u0631"} else
            "billion" if scale_raw in {"billion", "\u0645\u06cc\u0644\u06cc\u0627\u0631\u062f"} else "unit"
        )
        currency_raw = (budget_match.group("currency") or "").casefold()
        currency = (
            "TOMAN" if currency_raw in {"toman", "\u062a\u0648\u0645\u0627\u0646"} else
            "IRR" if currency_raw in {"irr", "\u0631\u06cc\u0627\u0644", "\u0631\u064a\u0627\u0644"} else
            "USD" if currency_raw in {"usd", "\u062f\u0644\u0627\u0631"} else
            "EUR" if currency_raw in {"eur", "\u064a\u0648\u0631\u0648"} else
            "AED" if currency_raw in {"aed", "\u062f\u0631\u0647\u0645"} else None
        )
        budget_value = BudgetValue(amount=amount_raw, scale=scale, currency=currency,
                                   currency_status="known" if currency else "unknown",
                                   raw=request_text[budget_match.start():budget_match.end()].strip())
        budget_field = _known(budget_value, _span(request_text, *budget_match.span()))
    else:
        budget_field = _missing()

    history_match = _find_first(request_text, [
        r"\u0645\u0646\u0627\u0637\u0642\s*\u062a\u0627\u0631\u06cc\u062e\u06cc",
        r"\u062c\u0627\u0647\u0627\u06cc?\s*\u062a\u0627\u0631\u06cc\u062e\u06cc",
        r"\u0627\u0645\u0627\u06a9\u0646\s*\u062a\u0627\u0631\u06cc\u062e\u06cc",
        r"\u0645\u0646\u0627\u0637\u0642\s*\u062a\u0627\u0631\u064a\u062e\u064a",
        r"\bhistoric(?:al)?\s+(?:areas|places|sites|attractions)\b", r"\bhistory\b",
        r"\u0627\u0644\u0645\u0646\u0627\u0637\u0642\s+\u0627\u0644\u062a\u0627\u0631\u064a\u062e\u064a\u0629",
        r"\u0627\u0644\u0645\u0639\u0627\u0644\u0645\s+\u0627\u0644\u062a\u0627\u0631\u064a\u062e\u064a\u0629",
    ])[0]
    garden_match = _find_first(request_text, [
        r"\u0628\u0627\u063a(?:[\s\u200c]*\u0647\u0627)?",
        r"\bgardens?\b", r"\bparks?\b", r"\u062d\u062f\u0627\u0626\u0642",
    ])[0]
    interest_matches = [match for match in (history_match, garden_match) if match]
    if interest_matches:
        interest_values = []
        if history_match:
            interest_values.append("historical_attractions")
        if garden_match:
            interest_values.append("gardens")
        interests_field = _known(
            interest_values,
            _span(request_text, min(match.start() for match in interest_matches),
                  max(match.end() for match in interest_matches)),
        )
    else:
        interests_field = _missing()

    origin_match = _find_first(request_text, [
        # Spoken Persian requests may place date and duration clauses between
        # the origin and destination verb: "from Mashhad ... in five days ... go".
        r"(?<!\w)\u0627\u0632\s+(?P<place>[\u0600-\u06ff][\u0600-\u06ff\u200c-]{1,45}(?:\s+[\u0600-\u06ff][\u0600-\u06ff\u200c-]{1,45})?)"
        r"\s+\u0645\u06cc[\s\u200c]*(?:\u062e\u0648\u0627\u0645|\u062e\u0648\u0627\u0647\u0645|\u062e\u0648\u0627\u06cc\u0645|\u062e\u0648\u0627\u0647\u06cc\u0645)"
        r"[\s\S]{0,80}?\s+(?:\u0628\u0631\u0645|\u0628\u0631\u0648\u0645|\u0628\u0631\u0648\u06cc\u0645|\u0633\u0641\u0631\s+\u06a9\u0646\u0645)",
        r"(?<!\w)از\s+(?P<place>[\u0600-\u06ff][\u0600-\u06ff\u200c-]{1,45}(?:\s+[\u0600-\u06ff][\u0600-\u06ff\u200c-]{1,45})?)\s+می[\s\u200c]*(?:خوام|خواهم|خوایم|خواهیم)\s+(?:برم|بریم|برویم|سفر)",
        r"(?:\u0627\u0632\s+\u0645\u0628\u062f\u0627\u0621?\s+)(?P<place>[\u0600-\u06ffA-Za-z][\u0600-\u06ffA-Za-z\s\u200c-]{1,50})",
        r"\bfrom\s+(?P<place>[A-Za-z][A-Za-z -]{1,50})",
    ])[0]
    # An explicit relative departure is a date, never a city of origin.
    if origin_match and re.fullmatch(r"(?:امروز|فردا|پس[\s\u200c]*فردا|دیروز)", origin_match.group("place").strip()):
        origin_match = None
    origin = _known(origin_match.group("place").strip(), _span(request_text, *origin_match.span("place"))) if origin_match else _missing()

    soft_patterns = [
        r"(?:\u062a\u0631\u062c\u06cc\u062d[\s\u200c]*\u0645\u06cc[\s\u200c]*\u062f\u0647\u0645|\u062f\u0648\u0633\u062a\s*\u062f\u0627\u0631\u0645|prefer(?:\s+to)?|would\s+prefer|\u0623\u0641\u0636\u0644|\u0627\u0641\u0636\u0644)\s*(?P<value>[^.;!\n\u061b\u061f]{2,100}?)(?=\s+(?:but|however|\u0627\u0645\u0627|\u0648\u0644\u064a|\u0644\u0643\u0646)\b|[.;!\n\u061b\u061f]|$)",
    ]
    hard_patterns = [
        # Explicit prohibitions and mandatory language stay hard requirements.
        # Include common spoken forms so they cannot be mistaken for a soft preference.
        r"(?:\bmust\b|\bmust\s+not\b|\bdo\s+not\b|\bdon't\b|\bwon't\b|\bwill\s+not\b|\bcannot\b|\bcan't\b|\bnever\b|\bavoid\b|"
        r"\u0628\u0627\u06cc\u062f|\u0646\u0628\u0627\u06cc\u062f|\u062d\u062a\u0645\u0627\u064b|\u062d\u062a\u0645\u0627|"
        r"(?:\u0628\u0627|\u0627\u0632)\s+[^.;!\n\u061b\u061f]{1,45}?\s+\u0646\u0645\u06cc\u200c?\u0631\u0648\u06cc\u0645|"
        r"\u0646\u0645\u06cc\u200c?\u0631\u0648\u06cc\u0645|\u0646\u0645\u06cc\u200c?\u062e\u0648\u0627\u0647\u06cc\u0645|\u067e\u0631\u0647\u06cc\u0632\s+\u06a9\u0646|"
        r"\u064a\u062c\u0628|\u06cc\u062c\u0628|\u0644\u0627\s+\u064a\u062c\u0648\u0632|\u0644\u0646\s+|\u0644\u0627\s+\u0623?\u0631\u064a\u062f|\u0644\u0627\s+\u0646\u0633\u062a\u062e\u062f\u0645|\u0644\u0627\s+\u0623\u0630\u0647\u0628|\u062a\u062c\u0646\u0628)[^.;!\n\u061b\u061f]{0,180}",
    ]
    hard_match = re.search(hard_patterns[0], request_text, re.I | re.U)
    soft_match = re.search(soft_patterns[0], request_text, re.I | re.U)
    if soft_match and hard_match and soft_match.start() < hard_match.start() < soft_match.end():
        # Keep only the explicit preference clause; never absorb a subsequent
        # prohibition into an advisory field.
        soft_end = min(soft_match.end(), hard_match.start())
        soft_text = request_text[soft_match.start():soft_end].rstrip(" ;,\u061b")
        soft_match = soft_match if len(soft_text) <= len(soft_match.group(0)) else None
        if soft_match:
            soft_value = soft_text[soft_match.start("value") - soft_match.start():]
            soft_value = soft_value.strip()
        else:
            soft_value = ""
    else:
        soft_value = soft_match.group("value").strip() if soft_match else ""
    soft_preferences = _known([soft_value], _span(request_text, soft_match.start(), soft_match.start() + len(soft_text) if soft_match and hard_match and hard_match.start() < soft_match.end() else soft_match.end())) if soft_match and soft_value else _missing()

    accessibility_match = _find_first(request_text, [
        r"\u0648\u06cc\u0644\u0686\u0631", r"\bwheelchair\b", r"\bwheelchair\s+access\b",
        r"\u0627\u062d\u062a\u064a\u0627\u062c\u0627\u062a?\s+(?:\u062d\u0631\u0643\u064a\u0629|mobility)",
        r"\u0627\u062d\u062a\u064a\u0627\u062c\s+\u0627\u0644\u0649\s+\u0645\u0633\u0627\u0639\u062f\u0629",
    ])[0]
    accessibility = _known(["wheelchair_access"], _span(request_text, *accessibility_match.span())) if accessibility_match else _missing()

    hard_constraints = _known([hard_match.group(0).strip()], _span(request_text, *hard_match.span())) if hard_match else _missing()

    missing_fields = [name for name, field in (("destination", destination), ("duration_days", duration_field)) if field.status == "missing"]
    ambiguous_fields: list[str] = []
    question_fields = [*missing_fields]
    if budget_field.status == "known" and budget_field.value.currency_status != "known":
        question_fields.append("budget.currency")
    return TripRequirementsV1(
        original_text=request_text, locale=locale,
        fields=TripRequirementFields(
            destination=destination, origin=origin, relative_start_date=relative_field,
            duration_days=duration_field, travel_dates=travel_dates, travelers=travelers_field,
            budget=budget_field, interests=interests_field, soft_preferences=soft_preferences,
            hard_constraints=hard_constraints, accessibility=accessibility,
        ),
        clarification=TripClarification(
            missing_fields=missing_fields, ambiguous_fields=ambiguous_fields, question_fields=question_fields,
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
            "source": field.source,
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
        "softPreferences": field_view(fields.soft_preferences),
        "constraints": field_view(fields.hard_constraints),
        "accessibility": field_view(fields.accessibility),
        "travelDifficulty": field_view(fields.travel_difficulty),
        "weatherPreferences": field_view(fields.weather_preferences),
        "localCuisine": field_view(fields.local_cuisine),
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
