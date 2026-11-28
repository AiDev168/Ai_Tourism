"""Internal authenticated Chat endpoint; never a public provider control plane."""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import date, timedelta
from time import monotonic
from typing import Annotated, Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator
from starlette.concurrency import run_in_threadpool

from app.api.auth import require_authenticated_csrf
from app.api.traveler import get_traveler_repository
from app.core.config import Settings, get_settings
from app.modules.identity.authorization import Principal, get_principal
from app.modules.integrations.ai_gateway import AiProviderGateway
from app.modules.integrations.chat_adapter import (
    ChatRequest, ChatReply, ProvisionalItinerary, make_chat_adapter, make_chat_gateway,
)
from app.modules.trip.assistant_turns import AssistantTurnRepository, ChatBudgetExceeded
from app.modules.trip.requirements_interpretation import (
    EvidenceSpan, RelativeStartDateValue, RequirementValue, TripClarification, TripRequirementsV1,
    interpret_trip_requirements,
    parse_explicit_budget_text,
)
from app.modules.trip.repository import (
    TravelerConflict, TravelerInvalidState, TravelerNotFound, TravelerRepository,
)
from app.modules.trip.schemas import ConversationDetail, MessageResponse, TripResponse, _bounded_json
from app.modules.provider_admin.runtime import make_admin_chat_gateway, provider_registry

router = APIRouter(prefix='/api/v1', tags=['traveler'])
logger = logging.getLogger('ai_tourism.assistant')
_model_readiness: tuple[Settings, float, asyncio.Task[bool]] | None = None


class AssistantTurnRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    trip_id: UUID
    content: str = Field(min_length=1, max_length=1200)
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r'^[A-Za-z0-9._:-]+$')
    expected_version: int = Field(ge=1)
    provisional_itinerary_days: StrictInt | None = Field(default=None, ge=1, le=15)
    extracted_requirements: dict[str, Any] | None = None
    existing_user_message_id: UUID | None = None

    @field_validator('content')
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip() or '\0' in value:
            raise ValueError('Invalid text')
        return value

    @field_validator('extracted_requirements')
    @classmethod
    def bounded(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return _bounded_json(value) if value is not None else None


class AssistantTurnResponse(BaseModel):
    model_config = ConfigDict(extra='forbid')
    conversation: ConversationDetail
    trip: TripResponse
    message: MessageResponse
    candidate_requirements: TripRequirementsV1 | dict[str, str | int | None]
    extraction_path: Literal['llm', 'fallback']
    provisional_itinerary: ProvisionalItinerary | None = None
    clarification: str | None
    replayed: bool


def get_assistant_turn_repository(
    traveler: Annotated[TravelerRepository, Depends(get_traveler_repository)],
) -> AssistantTurnRepository:
    return AssistantTurnRepository(traveler)


def get_chat_gateway(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AiProviderGateway[ChatRequest, ChatReply]:
    if settings.ai_provider_admin_enabled:
        return make_admin_chat_gateway(settings)
    return make_chat_gateway(settings)


def _error(status: int, code: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={'error': {'code': code}},
                        headers={'Cache-Control': 'no-store'})


_NUMBER_WORDS = {
    'a': 1, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'یک': 1, 'دو': 2, 'سه': 3, 'چهار': 4, 'پنج': 5,
    'شش': 6, 'هفت': 7, 'هشت': 8, 'نه': 9, 'ده': 10,
    'واحد': 1, 'واحده': 1, 'اثنان': 2, 'اثنين': 2, 'اثنتان': 2,
    'ثلاثة': 3, 'ثلاث': 3, 'أربعة': 4, 'اربعة': 4, 'أربع': 4,
    'خمسة': 5, 'خمس': 5, 'ستة': 6, 'ست': 6, 'سبعة': 7, 'سبع': 7,
    'ثمانية': 8, 'ثمان': 8, 'تسعة': 9, 'تسع': 9, 'عشرة': 10,
}
_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def _explicit_integer_evidence(quote: str, value: int, field: str) -> bool:
    """Check current-turn unit evidence, not whether the regex parser extracted it."""
    normalized = quote.translate(_DIGITS)
    tokens = [re.escape(token) for token in sorted(_NUMBER_WORDS, key=len, reverse=True)]
    token_pattern = r"(?P<number>\d{1,3}|" + '|'.join(tokens) + r")"
    for match in re.finditer(token_pattern, normalized, re.IGNORECASE | re.UNICODE):
        raw_number = match.group('number').casefold()
        try:
            number = int(raw_number) if raw_number.isdecimal() else _NUMBER_WORDS[raw_number]
        except KeyError:
            continue
        before = normalized[max(0, match.start() - 48):match.start()].casefold()
        after = normalized[match.end():min(len(normalized), match.end() + 48)].casefold()
        if field == 'duration_days':
            unit = re.match(
                r"\s*[-\u2010-\u2015]?\s*(?P<unit>days?|weeks?|\u0631\u0648\u0632(?:\u0647)?|"
                r"\u0623\u064a\u0627\u0645|\u0627\u064a\u0627\u0645|\u064a\u0648\u0645|"
                r"\u0647\u0641\u062a(?:\u0647)?)(?!\w)", after,
            )
            if unit is None:
                continue
            multiplier = 7 if unit.group('unit').startswith(('week', '\u0647\u0641\u062a')) else 1
            if number * multiplier != value:
                continue
            if re.search(r"\b(?:in|after|within|from)\s*$|(?:\u0628\u0639\u062f|\u062f\u064a\u06af\u0647|\u062f\u064a\u06af\u0631)\s*$", before, re.I):
                continue
            if re.search(r"(?:from\s+now|later|(?:\u0628\u0639\u062f|\u062f\u064a\u06af\u0647|\u062f\u064a\u06af\u0631))", after, re.I):
                continue
            return True
        elif field in {'traveler_count', 'travelers'}:
            if number != value:
                continue
            direct_unit = re.match(
                r"\s*(?:people|persons?|travelers?|travellers?|passengers?|\u0646\u0641\u0631(?:\u064a\u0645|\u0627\u062a)?|"
                r"\u0645\u0633\u0627\u0641\u0631(?:\u0627\u0646)?|\u0623\u0634\u062e\u0627\u0635|\u0627\u0634\u062e\u0627\u0635|"
                r"\u0627\u0641\u0631\u0627\u062f|\u0623\u0641\u0631\u0627\u062f|\u0634\u062e\u0635)(?!\w)",
                after, re.I | re.UNICODE,
            )
            after_words = after.strip()
            before_words = before.strip()
            if (direct_unit or after_words.startswith('of us') or before_words.endswith((
                'party of', 'group of', 'family of', 'a family of', 'we are', "we're", 'there are',
                '\u0645\u0627', '\u0646\u062d\u0646', '\u0628\u0627', '\u0647\u0645\u0631\u0627\u0647 \u0628\u0627',
            ))):
                return True
    return False


def _explicit_correction_context(quote: str) -> bool:
    return re.search(
        r"\b(?:actually|instead|rather\s+than|make\s+it|set\s+it|correction)\b|"
        r"(?:در\s+واقع|اصلاح|منظورم|به\s+جای|نه)|"
        r"(?:بل|أقصد|اقصد|بدلاً|بدلا|اجعلها)",
        quote, re.I | re.UNICODE,
    ) is not None


def _explicit_soft_preference(quote: str) -> bool:
    return re.search(
        r"\bprefer(?:s|red)?\b|\bwould\s+prefer\b|"
        r"ترجیح\s+می(?:‌|\s)?دهم|ترجیح\s+می(?:‌|\s)?دهیم|دوست\s+دارم|"
        r"أفضل|أفضّل|افضل|يفضل|تفضيل",
        quote, re.I | re.UNICODE,
    ) is not None


def _has_relative_date_cue(quote: str) -> bool:
    """Validate that a quoted turn describes a relative date, without parsing its offset.

    The LLM determines the semantic offset. This lexical guard only prevents a
    stay length such as "five days" from being relabeled as departure timing.
    """
    value = quote.translate({
        0x064A: 0x06CC, 0x0649: 0x06CC, 0x0643: 0x06A9,
        0x0629: 0x0647, 0x06C0: 0x0647, 0x0623: 0x0627,
        0x0625: 0x0627, 0x0671: 0x0627,
    }).replace("\u200c", " ").casefold()
    value = re.sub(r"\s+", " ", value).strip()
    return re.search(
        r"\b(?:today|tomorrow|yesterday|day after tomorrow|the day after tomorrow|"
        r"next (?:day|morning|afternoon|evening|week|month)|"
        r"in (?:\d+|one|two|three|four|five|six|seven|eight|nine|ten) (?:days?|weeks?)|"
        r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten) (?:days?|weeks?) (?:from now|later))\b|"
        r"\b(?:today|tomorrow) morning\b|"
        r"\u0627\u0645\u0631\u0648\u0632|\u0641\u0631\u062f\u0627|"
        r"\u067e\u0633\s*\u0641\u0631\u062f\u0627|\u0627\u0645\u0634\u0628|"
        r"(?:\d+|\u06cc\u06a9|\u062f\u0648|\u0633\u0647|\u0686\u0647\u0627\u0631|\u067e\u0646\u062c)\s*"
        r"\u0631\u0648\u0632\s*(?:\u062f\u06cc\u06af\u0647|\u062f\u06cc\u06af\u0631|\u0628\u0639\u062f)|"
        r"\u0628\u0639\u062f\s*(?:\d+|\u06cc\u06a9|\u062f\u0648|\u0633\u0647|\u0686\u0647\u0627\u0631|\u067e\u0646\u062c)\s*"
        r"(?:\u0631\u0648\u0632|\u0627\u064a\u0627\u0645|\u0623\u064a\u0627\u0645)|"
        r"\u0627\u0644\u064a\u0648\u0645|\u063a\u062f\u0627|\u0628\u0639\u062f\s*\u063a\u062f|"
        r"\u0628\u0639\u062f\s*(?:\d+|\u064a\u0648\u0645\u064a\u0646|\u062b\u0644\u0627\u062b\u0629)\s*"
        r"(?:\u0627\u064a\u0627\u0645|\u0623\u064a\u0627\u0645)",
        value, re.I | re.U,
    ) is not None


def _chat_route_state(settings: Settings) -> str:
    """Report configured route readiness only; never probes or calls a model."""
    if settings.app_env.lower() not in {'development', 'test', 'local_pilot', 'staging'}:
        return 'disabled'
    if settings.ai_provider_admin_enabled:
        if settings.ai_provider_vault_dir is None:
            return 'disabled'
        try:
            registry = provider_registry(settings)
            active = registry.active_snapshot('chat')
            if active.revision_id is not None:
                eligible = registry.validated_snapshot('chat', active.revision_id)
                return 'configured' if eligible.revision_id == active.revision_id else 'unavailable'
            fallback = registry.get_fallback('chat')
            if fallback.get('enabled'):
                for revision_id in fallback.get('ordered_revision_ids', []):
                    try:
                        eligible = registry.validated_snapshot('chat', revision_id)
                    except Exception:
                        continue
                    if eligible.revision_id == revision_id:
                        return 'configured'
            return 'disabled'
        except Exception:
            return 'unavailable'
    if settings.internal_chat_enabled and settings.internal_chat_token is not None:
        return 'configured'
    return 'disabled'


@router.get('/assistant/status')
async def assistant_status(
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[AssistantTurnRepository, Depends(get_assistant_turn_repository)],
):
    """Return safe route/quota facts without spending an assistant invocation."""
    global _model_readiness
    response.headers['Cache-Control'] = 'no-store'
    try:
        route_state = await run_in_threadpool(_chat_route_state, settings)
        budget = await run_in_threadpool(repository.budget_status,
            user_id=principal.user_id,
            per_user_limit=settings.internal_chat_daily_user_limit,
            global_limit=settings.internal_chat_daily_global_limit,
        )
        state = route_state
        if state == 'configured' and (
            budget['user_remaining'] == 0 or budget['global_remaining'] == 0
        ):
            state = 'quota_exhausted'
        if state == 'configured' and not settings.ai_provider_admin_enabled:
            now = monotonic()
            if (_model_readiness is None or _model_readiness[0] is not settings
                    or _model_readiness[1] <= now):
                probe = asyncio.create_task(make_chat_adapter(settings).check_model_available())
                _model_readiness = (settings, now + 30, probe)
            if await asyncio.shield(_model_readiness[2]):
                state = 'connected'
        return {'state': state, **budget}
    except Exception:
        return _error(503, 'assistant_status_unavailable')


def _normalize_evidence(value: str) -> str:
    """Normalize common Arabic/Persian spelling variants for evidence checks."""
    value = value.translate({
        0x064A: 0x06CC, 0x0649: 0x06CC, 0x0643: 0x06A9,
        0x0629: 0x0647, 0x06C0: 0x0647, 0x0623: 0x0627,
        0x0625: 0x0627, 0x0671: 0x0627,
    })
    return re.sub(r"[\s\u200c\u200d\u0640]+", "", value).casefold()


def _interest_source_span(text: str, phrases: list[str]) -> tuple[int, str] | None:
    """Locate model-selected interest phrases in the original traveler text."""
    normalized_text, indexes = _normalized_evidence_map(text)
    spans = []
    for phrase in phrases:
        normalized = _normalize_evidence(phrase)
        if len(normalized) < 2:
            return None
        start = normalized_text.find(normalized)
        if start < 0:
            return None
        spans.append((indexes[start], indexes[start + len(normalized) - 1] + 1))
    start = min(left for left, _ in spans)
    end = max(right for _, right in spans)
    return (start, text[start:end]) if end - start <= 200 else None


def _normalized_evidence_map(text: str) -> tuple[str, list[int]]:
    """Map normalized evidence code points back to offsets in the original text."""
    characters: list[str] = []
    indexes: list[int] = []
    for index, char in enumerate(text):
        normalized = _normalize_evidence(char)
        characters.extend(normalized)
        indexes.extend([index] * len(normalized))
    return ''.join(characters), indexes


def _evidence_span(text: str, quote: str) -> tuple[int, int, str] | None:
    """Resolve a model quote despite harmless Persian/Arabic spelling or ZWNJ differences.

    Validation uses normalized text, while the persisted evidence span always
    points into and returns the untouched original traveler message.
    """
    if not isinstance(quote, str) or not quote or len(quote) > 200:
        return None
    normalized = _normalize_evidence(quote)
    if len(normalized) < 2:
        return None
    normalized_text, indexes = _normalized_evidence_map(text)
    start = normalized_text.find(normalized)
    if start < 0:
        return None
    original_start = indexes[start]
    original_end = indexes[start + len(normalized) - 1] + 1
    if original_end - original_start > 200:
        return None
    return original_start, original_end, text[original_start:original_end]


def _candidate_profile(text: str, locale: str, hints: dict[str, Any], evidence: dict[str, str],
                       ambiguous: dict[str, list[str]] | None = None, *,
                       traveler_timezone: str | None = None,
                       traveler_reference_date: date | None = None,
                       model_only: bool = False) -> TripRequirementsV1:
    """Use evidenced LLM semantics first; deterministic extraction only fills gaps.

    The result is an advisory review candidate, never a confirmed profile.
    """
    profile = interpret_trip_requirements(
        text, locale, traveler_timezone=traveler_timezone,
        traveler_reference_date=traveler_reference_date,
    )
    fields = profile.fields.model_dump()
    key_to_field = {
        'destination': 'destination', 'origin': 'origin', 'duration_days': 'duration_days',
        'traveler_count': 'travelers', 'budget_text': 'budget', 'interest': 'interests',
        'soft_preference': 'soft_preferences', 'relative_start_date': 'relative_start_date',
        'travel_start': 'travel_dates', 'travel_end': 'travel_dates',
        'hard_constraint': 'hard_constraints', 'accessibility': 'accessibility',
        'travel_difficulty': 'travel_difficulty', 'weather_preference': 'weather_preferences',
        'local_cuisine': 'local_cuisine',
    }
    ambiguous = ambiguous or {}
    for key, options in ambiguous.items():
        field_name, quote = key_to_field.get(key), evidence.get(key)
        if (field_name not in {'destination', 'origin'} or not isinstance(options, list)
                or not 2 <= len(options) <= 5 or not isinstance(quote, str)):
            continue
        span = _evidence_span(text, quote)
        if (span is None or any(not isinstance(option, str) or not option.strip()
                or _normalize_evidence(option.strip()) not in _normalize_evidence(span[2])
                for option in options)):
            continue
        try:
            fields[field_name] = RequirementValue(
                status='ambiguous', candidates=[option.strip() for option in options],
                evidence_span=EvidenceSpan(start=span[0], end=span[1], text=span[2]), source='llm',
            ).model_dump()
        except Exception:
            continue

    for key, field_name in key_to_field.items():
        raw_value, quote = hints.get(key), evidence.get(key)
        if raw_value is None or not isinstance(quote, str) or len(quote) > 200:
            continue
        span = _evidence_span(text, quote)
        start = span[0] if span is not None else -1
        source_quote = span[2] if span is not None else quote
        interests = []
        if key == 'interest' and isinstance(raw_value, str) and raw_value.strip():
            interests = [raw_value.strip()]
            if start < 0 or _normalize_evidence(raw_value.strip()) not in _normalize_evidence(source_quote):
                interests = [item.strip() for item in re.split(r'[,،;؛]|\s+و\s+', raw_value) if item.strip()]
                interest_span = _interest_source_span(text, interests) if interests else None
                if interest_span is not None:
                    start, source_quote = interest_span
        if start < 0:
            continue
        current = getattr(profile.fields, field_name)
        parsed_quote = interpret_trip_requirements(
            source_quote, locale, traveler_timezone=traveler_timezone,
            traveler_reference_date=traveler_reference_date,
        )
        quoted_field_name = {'traveler_count': 'travelers', 'budget_text': 'budget',
            'interest': 'interests', 'hard_constraint': 'hard_constraints',
            'soft_preference': 'soft_preferences', 'travel_start': 'travel_dates',
            'travel_end': 'travel_dates'}.get(key, key)
        quoted_field = getattr(parsed_quote.fields, quoted_field_name, None)
        value = quoted_field.value if quoted_field and quoted_field.status == 'known' else None
        if key in {'destination', 'origin'}:
            if (not isinstance(raw_value, str) or not raw_value.strip()
                    or _normalize_evidence(raw_value.strip()) not in _normalize_evidence(source_quote)):
                continue
            value = raw_value.strip()
        elif key in {'duration_days', 'traveler_count'}:
            maximum = 365 if key == 'duration_days' else 50
            if (type(raw_value) is not int or not 1 <= raw_value <= maximum
                    or not _explicit_integer_evidence(source_quote, raw_value, key)):
                continue
            # A provider may not turn a relative departure offset into the
            # requested stay length. A separate explicit duration hint in the
            # same current turn makes the intended distinction unambiguous.
            relative = hints.get('relative_start_date')
            relative_quote = evidence.get('relative_start_date')
            relative_span = (_evidence_span(text, relative_quote)
                             if isinstance(relative_quote, str) else None)
            if (key == 'duration_days' and type(relative) is int
                    and relative_span is not None
                    and _normalize_evidence(relative_span[2]) in _normalize_evidence(source_quote)
                    and raw_value == relative and not _explicit_correction_context(quote)
                    and not any(marker in quote.casefold() for marker in (
                        'trip for', 'stay for', 'duration', 'for ', 'به مدت', 'برای', 'اقامت',
                    ))):
                continue
            value = raw_value
        elif key == 'budget_text':
            if (not isinstance(raw_value, str) or not raw_value.strip()
                    or _normalize_evidence(raw_value.strip()) not in _normalize_evidence(source_quote)
                    ):
                continue
            # LLM intent classification selects the quoted budget. This strict
            # amount/unit parser validates its syntax only; it does not require
            # regex recognition of surrounding sentence structure. No currency
            # or denomination conversion is performed.
            value = parse_explicit_budget_text(raw_value.strip())
            if value is None:
                continue
        elif key == 'interest':
            if not interests or any(
                _normalize_evidence(item) not in _normalize_evidence(source_quote) for item in interests
            ):
                continue
            value = list(dict.fromkeys(interests))
        elif key == 'soft_preference':
            if (not isinstance(raw_value, str) or not raw_value.strip()
                    or _normalize_evidence(raw_value.strip()) not in _normalize_evidence(source_quote)):
                continue
            if (not _explicit_soft_preference(source_quote) or quoted_field is None
                    or quoted_field.status != 'known'):
                continue
            value = list(dict.fromkeys([*(current.value or []), *(quoted_field.value or [])]))
        elif key in {'travel_difficulty', 'weather_preference', 'local_cuisine'}:
            if (not isinstance(raw_value, str) or not raw_value.strip()
                    or _normalize_evidence(raw_value.strip()) not in _normalize_evidence(source_quote)):
                continue
            value = list(dict.fromkeys([*(current.value or []), raw_value.strip()]))
        elif key in {'hard_constraint', 'accessibility'}:
            if (not isinstance(raw_value, str)
                    or _normalize_evidence(raw_value.strip()) != _normalize_evidence(source_quote.strip())):
                continue
            value = list(dict.fromkeys([*(current.value or []), raw_value.strip()]))
        elif key == 'relative_start_date':
            if (type(raw_value) is not int or not 0 <= raw_value <= 365
                    or not _has_relative_date_cue(source_quote)):
                continue
            anchor = (traveler_reference_date + timedelta(days=raw_value)
                      if traveler_reference_date is not None else None)
            value = RelativeStartDateValue(
                offset_days=raw_value, anchor_date=anchor, timezone=traveler_timezone,
            )
        elif key in {'travel_start', 'travel_end'}:
            # The typed contract requires an explicit pair. A single endpoint
            # is retained only as an unresolved clarification, never as a date
            # object in the pair field.
            continue
        if value is None:
            continue
        # A valid, evidence-backed model interpretation is an advisory
        # candidate and may correct a deterministic fallback guess. The UI
        # still protects manual edits and confirmed traveler values.
        try:
            fields[field_name] = RequirementValue(
                status='known', value=value,
                evidence_span=EvidenceSpan(start=start, end=start + len(source_quote), text=source_quote),
                source='llm',
            ).model_dump()
        except Exception:
            continue

    # Explicit ISO start/end pair only. A known duration never implies an end.
    if 'travel_start' in hints and 'travel_end' in hints:
        start_quote, end_quote = evidence.get('travel_start'), evidence.get('travel_end')
        start_value, end_value = hints['travel_start'], hints['travel_end']
        start_span = _evidence_span(text, start_quote) if isinstance(start_quote, str) else None
        end_span = _evidence_span(text, end_quote) if isinstance(end_quote, str) else None
        if (start_span is not None and end_span is not None
                and isinstance(start_value, str) and isinstance(end_value, str)
                and start_value in start_span[2] and end_value in end_span[2]
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", start_value)
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", end_value)):
            try:
                parsed_start, parsed_end = date.fromisoformat(start_value), date.fromisoformat(end_value)
            except ValueError:
                pass
            else:
                if parsed_start <= parsed_end:
                    left = min(start_span[0], end_span[0])
                    right = max(start_span[1], end_span[1])
                    fields['travel_dates'] = RequirementValue(
                        status='known', value={'start': parsed_start, 'end': parsed_end},
                        evidence_span=EvidenceSpan(start=left, end=right, text=text[left:right]), source='llm',
                    ).model_dump()
    if model_only:
        for field_name, field in fields.items():
            # Keep the deterministic safety detector for explicit restrictions.
            # For other fields, partial inference leaves an unanswered slot.
            if field_name not in {'hard_constraints', 'accessibility'} and field['source'] != 'llm':
                fields[field_name] = RequirementValue(status='missing', source='llm').model_dump()
    interpreted = profile.fields.model_validate(fields)
    required = ('destination', 'duration_days')
    missing = [name for name in required if getattr(interpreted, name).status == 'missing']
    ambiguous_fields = [name for name in required if getattr(interpreted, name).status == 'ambiguous']
    questions = [*missing, *ambiguous_fields]
    if interpreted.budget.value is not None and interpreted.budget.value.currency_status != 'known':
        questions.append('budget.currency')
    return profile.model_copy(update={
        'fields': interpreted,
        'clarification': TripClarification(
            missing_fields=missing, ambiguous_fields=ambiguous_fields, question_fields=questions,
        ),
    })


def _reviewed_profile_context(trip: dict[str, Any] | None) -> str | None:
    reviewed = trip.get('confirmed_requirements') if trip else None
    if not isinstance(reviewed, dict) or reviewed.get('confirmation_source') != 'traveler_reviewed':
        return None
    context: dict[str, Any] = {}
    for name in (
        'destinations', 'duration_days', 'travel_dates', 'traveler_count', 'budget',
        'constraints', 'accessibility', 'interests', 'travel_difficulty',
        'weather_preferences', 'local_cuisine', 'soft_preferences',
    ):
        value = reviewed.get(name)
        if value is not None and len(json.dumps({**context, name: value}, ensure_ascii=False)) <= 2000:
            context[name] = value
    return json.dumps(context, ensure_ascii=False) if context else None


@router.post('/conversations/{conversation_id}/assistant-turns', response_model=AssistantTurnResponse)
async def assistant_turn(
    conversation_id: UUID,
    body: AssistantTurnRequest,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[AssistantTurnRepository, Depends(get_assistant_turn_repository)],
    traveler: Annotated[TravelerRepository, Depends(get_traveler_repository)],
    gateway: Annotated[AiProviderGateway[ChatRequest, ChatReply], Depends(get_chat_gateway)],
):
    response.headers['Cache-Control'] = 'no-store'
    if (not settings.internal_chat_enabled and not settings.ai_provider_admin_enabled) or settings.app_env.lower() not in {'development', 'test', 'local_pilot', 'staging'}:
        logger.warning('assistant.turn.failed phase=configuration error_type=ChatDisabled')
        return _error(503, 'assistant_unavailable')
    confirmed_trip = None
    if body.provisional_itinerary_days is not None:
        try:
            confirmed_trip = await run_in_threadpool(
                traveler.trip, principal.user_id, body.trip_id,
            )
        except Exception:
            return _error(503, 'assistant_unavailable')
        confirmed = confirmed_trip.get('confirmed_requirements', {}) if confirmed_trip else {}
        duration = confirmed.get('duration_days') if isinstance(confirmed, dict) else None
        destinations = confirmed.get('destinations') if isinstance(confirmed, dict) else None
        if (not isinstance(confirmed, dict)
                or confirmed.get('confirmation_source') != 'traveler_reviewed'
                or duration != body.provisional_itinerary_days
                or not isinstance(destinations, list) or not destinations):
            return _error(409, 'trip_profile_not_ready_for_itinerary')
    try:
        reservation = await run_in_threadpool(
            repository.reserve,
            user_id=principal.user_id, conversation_id=conversation_id,
            trip_id=body.trip_id, idempotency_key=body.idempotency_key,
            expected_version=body.expected_version, content=body.content,
            extracted_requirements=body.extracted_requirements,
            per_user_limit=settings.internal_chat_daily_user_limit,
            global_limit=settings.internal_chat_daily_global_limit,
            existing_user_message_id=body.existing_user_message_id,
        )
    except TravelerNotFound:
        return _error(404, 'resource_not_found')
    except TravelerConflict:
        return _error(409, 'version_or_idempotency_conflict')
    except TravelerInvalidState:
        return _error(413, 'conversation_limit_reached')
    except ChatBudgetExceeded:
        return _error(429, 'assistant_daily_limit')
    except Exception as exc:
        logger.warning('assistant.turn.failed phase=reservation error_type=%s', type(exc).__name__)
        return _error(503, 'assistant_unavailable')

    replayed = reservation.status == 'completed'
    if not replayed and (reservation.status != 'reserved' or not reservation.created):
        # Never auto-retry an unknown-cost in-flight or failed provider call.
        return _error(409, 'assistant_turn_not_retryable')
    if not replayed:
        try:
            history = await run_in_threadpool(
                repository.history, user_id=principal.user_id,
                conversation_id=conversation_id, trip_id=body.trip_id,
                exclude_message_id=reservation.user_message_id,
            )
            trip_context = await run_in_threadpool(
                traveler.trip, principal.user_id, body.trip_id,
            )
            original_request = trip_context.get('original_request') if trip_context else None
            if (isinstance(original_request, str) and original_request.strip()
                    and original_request != body.content
                    and not any(
                        item.get('role') == 'user' and item.get('content') == original_request
                        for item in history if isinstance(item, dict)
                    )):
                # Keep the initial request in scope after the bounded recent
                # history window rolls forward. This is limited to the same
                # authenticated trip; the latest correction remains the newest
                # message in the retained tail.
                history = [
                    {'role': 'user', 'content': original_request[:1200]},
                    *history[-11:],
                ]
            locale = {'fa': 'fa-IR', 'en': 'en-US', 'ar': 'ar'}.get(
                reservation.locale, reservation.locale,
            )
            extracted = (trip_context.get('extracted_requirements', {})
                         if isinstance(trip_context, dict) else {})
            traveler_context = (extracted.get('_traveler_context', {})
                                if isinstance(extracted, dict) else {})
            traveler_timezone = None
            traveler_reference_date = None
            if isinstance(traveler_context, dict):
                raw_timezone = traveler_context.get('timezone')
                raw_reference_date = traveler_context.get('reference_date')
                if isinstance(raw_timezone, str):
                    try:
                        ZoneInfo(raw_timezone)
                        traveler_timezone = raw_timezone
                    except (ZoneInfoNotFoundError, ValueError):
                        traveler_timezone = None
                if isinstance(raw_reference_date, str):
                    try:
                        traveler_reference_date = date.fromisoformat(raw_reference_date)
                    except ValueError:
                        traveler_reference_date = None
            contract = extracted.get('requirements_v1', {}) if isinstance(extracted, dict) else {}
            contract_fields = contract.get('fields', {}) if isinstance(contract, dict) else {}
            relative = contract_fields.get('relative_start_date', {}) if isinstance(contract_fields, dict) else {}
            relative_value = relative.get('value', {}) if isinstance(relative, dict) else {}
            if traveler_timezone is None and isinstance(relative_value, dict):
                candidate_timezone = relative_value.get('timezone')
                if isinstance(candidate_timezone, str):
                    try:
                        ZoneInfo(candidate_timezone)
                        traveler_timezone = candidate_timezone
                    except (ZoneInfoNotFoundError, ValueError):
                        traveler_timezone = None
            if traveler_reference_date is None and isinstance(relative_value, dict) and relative_value.get('anchor_date'):
                try:
                    # anchor_date is the already-resolved local departure date;
                    # reconstruct the original reference day without using the
                    # server clock.
                    traveler_reference_date = date.fromisoformat(relative_value['anchor_date']) - timedelta(
                        days=int(relative_value.get('offset_days', 0)),
                    )
                except (TypeError, ValueError, OverflowError):
                    traveler_reference_date = None
            itinerary_days = body.provisional_itinerary_days
            reply = await gateway.invoke(ChatRequest(
                locale=locale,
                text=(
                    'Generate a provisional itinerary from the confirmed profile.'
                    if itinerary_days is not None else body.content
                ),
                history=history if itinerary_days is None else [],
                traveler_timezone=traveler_timezone if isinstance(traveler_timezone, str) else None,
                traveler_reference_date=traveler_reference_date,
                reviewed_profile=_reviewed_profile_context(trip_context),
                provisional_itinerary_days=itinerary_days,
            ))
            if itinerary_days is not None and isinstance(extracted, dict):
                try:
                    # Planning does not re-extract or overwrite requirements.
                    # Return the existing persisted requirements snapshot as the
                    # turn's context, while planning itself uses the confirmed
                    # profile supplied by the server above.
                    candidate_profile = TripRequirementsV1.model_validate(
                        extracted.get('requirements_v1')
                    )
                except Exception:
                    candidate_profile = _candidate_profile(
                        body.content, locale, {}, {}, {}, model_only=True,
                    )
            else:
                candidate_profile = _candidate_profile(
                    body.content, locale, reply.requirements, reply.requirement_evidence,
                    reply.ambiguous_requirements,
                    traveler_timezone=traveler_timezone if isinstance(traveler_timezone, str) else None,
                    traveler_reference_date=traveler_reference_date,
                    model_only=True,
                )
            await run_in_threadpool(
                repository.complete, user_id=principal.user_id,
                turn_id=reservation.turn_id, reply=reply.reply,
                requirements=candidate_profile.model_dump(mode='json'), clarification=reply.clarification,
                provisional_itinerary=(reply.provisional_itinerary.model_dump(mode='json')
                                       if reply.provisional_itinerary else None),
            )
        except Exception as exc:
            logger.warning('assistant.turn.failed phase=provider_or_completion error_type=%s', type(exc).__name__)
            try:
                await run_in_threadpool(
                    repository.fail, user_id=principal.user_id, turn_id=reservation.turn_id,
                )
            except Exception:
                logger.warning('assistant.failure_record_unavailable')
            return _error(503, 'assistant_unavailable')
    try:
        message = await run_in_threadpool(
            repository.result, user_id=principal.user_id,
            conversation_id=conversation_id, trip_id=body.trip_id,
            turn_id=reservation.turn_id,
        )
        conversation = await run_in_threadpool(traveler.conversation, principal.user_id, conversation_id)
        trip = await run_in_threadpool(traveler.trip, principal.user_id, body.trip_id)
        if not message or not conversation or not trip:
            return _error(503, 'assistant_unavailable')
        metadata = message.pop('metadata', {}) or {}
        candidate = metadata.get('requirements_candidate') or {}
        return {
            'conversation': conversation, 'trip': trip, 'message': message,
            'candidate_requirements': candidate,
            # A completed provider turn may only have asked a question.
            # Field-level sources report what was actually extracted.
            'extraction_path': 'llm',
            'provisional_itinerary': metadata.get('provisional_itinerary'),
            'clarification': metadata.get('clarification'), 'replayed': replayed,
        }
    except Exception as exc:
        logger.warning('assistant.turn.failed phase=result_load error_type=%s', type(exc).__name__)
        return _error(503, 'assistant_unavailable')
