"""Internal authenticated Chat endpoint; never a public provider control plane."""
from __future__ import annotations

import logging
import re
from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from starlette.concurrency import run_in_threadpool

from app.api.auth import require_authenticated_csrf
from app.api.traveler import get_traveler_repository
from app.core.config import Settings, get_settings
from app.modules.identity.authorization import Principal, get_principal
from app.modules.integrations.ai_gateway import AiProviderGateway
from app.modules.integrations.chat_adapter import ChatRequest, ChatReply, make_chat_gateway
from app.modules.trip.assistant_turns import AssistantTurnRepository, ChatBudgetExceeded
from app.modules.trip.requirements_interpretation import (
    EvidenceSpan, RequirementValue, TripRequirementsV1, interpret_trip_requirements,
)
from app.modules.trip.repository import (
    TravelerConflict, TravelerInvalidState, TravelerNotFound, TravelerRepository,
)
from app.modules.trip.schemas import ConversationDetail, MessageResponse, TripResponse, _bounded_json
from app.modules.provider_admin.runtime import make_admin_chat_gateway, provider_registry

router = APIRouter(prefix='/api/v1', tags=['traveler'])
logger = logging.getLogger('ai_tourism.assistant')


class AssistantTurnRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    trip_id: UUID
    content: str = Field(min_length=1, max_length=1200)
    idempotency_key: str = Field(min_length=8, max_length=128, pattern=r'^[A-Za-z0-9._:-]+$')
    expected_version: int = Field(ge=1)
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
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
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
    """Require a literal number, its field-specific unit, and nonrelative context."""
    normalized = quote.translate(_DIGITS)
    tokens = [re.escape(token) for token in sorted(_NUMBER_WORDS, key=len, reverse=True)]
    token_pattern = r"(?P<number>\d{1,3}|" + '|'.join(tokens) + r")"
    for match in re.finditer(token_pattern, normalized, re.IGNORECASE | re.UNICODE):
        raw_number = match.group('number').casefold()
        try:
            number = int(raw_number) if raw_number.isdecimal() else _NUMBER_WORDS[raw_number]
        except KeyError:
            continue
        if number != value:
            continue
        before = normalized[max(0, match.start() - 36):match.start()].casefold()
        after = normalized[match.end():min(len(normalized), match.end() + 36)].casefold()
        if field == 'duration_days':
            duration_unit = re.match(
                r"\s*[-\u2010-\u2015]?\s*(?:days?|روز(?:ه)?|أيام|ايام|يوم)(?!\w)", after,
            )
            if duration_unit is None:
                continue
            if re.search(r"\b(?:in|after|within)\s*$|(?:بعد|دیگه|دیگر)\s*$", before, re.I):
                continue
            if re.search(r"(?:from\s+now|later|(?:بعد|دیگه|دیگر))", after, re.I):
                continue
            return True
        elif field in {'travelers', 'traveler_count'}:
            direct_unit = re.match(
                r"\s*(?:people|persons?|travelers?|travellers?|passengers?|نفر(?:یم|ات)?|مسافر(?:ان)?|"
                r"أشخاص|اشخاص|افراد|أفراد|شخص)(?!\w)", after, re.I | re.UNICODE,
            )
            after_words = after.strip().casefold()
            before_words = before.strip().casefold()
            of_us = after_words.startswith('of us')
            context = before_words.endswith((
                'party of', 'group of', 'we are', "we're", 'there are',
                'ما', 'نحن', 'با', 'همراه با',
            ))
            if direct_unit or of_us or context:
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
def assistant_status(
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    settings: Annotated[Settings, Depends(get_settings)],
    repository: Annotated[AssistantTurnRepository, Depends(get_assistant_turn_repository)],
):
    """Return safe route/quota facts without spending an assistant invocation."""
    response.headers['Cache-Control'] = 'no-store'
    try:
        route_state = _chat_route_state(settings)
        budget = repository.budget_status(
            user_id=principal.user_id,
            per_user_limit=settings.internal_chat_daily_user_limit,
            global_limit=settings.internal_chat_daily_global_limit,
        )
        state = route_state
        if state == 'configured' and (
            budget['user_remaining'] == 0 or budget['global_remaining'] == 0
        ):
            state = 'quota_exhausted'
        return {'state': state, **budget}
    except Exception:
        return _error(503, 'assistant_status_unavailable')


def _candidate_profile(
    text: str, locale: str, hints: dict[str, Any], evidence: dict[str, str],
) -> TripRequirementsV1:
    """Build a typed profile; model hints need exact current-turn evidence."""
    profile = interpret_trip_requirements(text, locale)
    fields = profile.fields.model_dump()
    key_to_field = {
        'destination': 'destination', 'origin': 'origin', 'duration_days': 'duration_days',
        'traveler_count': 'travelers', 'budget_text': 'budget',
        'interest': 'interests', 'soft_preference': 'soft_preferences',
        'relative_start_date': 'relative_start_date',
        'travel_start': 'travel_dates', 'travel_end': 'travel_dates',
        'hard_constraint': 'hard_constraints', 'accessibility': 'accessibility',
    }
    for key, field_name in key_to_field.items():
        current = getattr(profile.fields, field_name)
        raw_value = hints.get(key)
        quote = evidence.get(key)
        if raw_value is None or not isinstance(quote, str):
            continue
        start = text.find(quote)
        if start < 0 or not quote or len(quote) > 200:
            continue
        end = start + len(quote)
        if current.status != 'missing':
            # Existing values came from the same traveler turn's deterministic
            # fallback. A model may refine a heuristic only when its exact
            # quote covers that fallback evidence. Confirmed trip state is not
            # modified here; this endpoint persists only an advisory candidate.
            span = current.evidence_span
            additive_field = field_name in {
                'interests', 'soft_preferences', 'hard_constraints', 'accessibility',
            }
            if (current.source != 'fallback'
                    or (not additive_field and (
                        span is None or start > span.start or end < span.end
                    ))):
                continue
        # Parse the quoted source with the same deterministic contract. This
        # allows useful multilingual extraction while refusing unsupported
        # conversions (especially dates, money and numeric quantities).
        parsed_quote = interpret_trip_requirements(quote, locale)
        quoted_field_name = {'traveler_count': 'travelers', 'budget_text': 'budget',
                             'interest': 'interests', 'hard_constraint': 'hard_constraints',
                             'soft_preference': 'soft_preferences',
                             'travel_start': 'travel_dates', 'travel_end': 'travel_dates'}.get(key, key)
        quoted_field = getattr(parsed_quote.fields, quoted_field_name, None)
        value = quoted_field.value if quoted_field is not None and quoted_field.status == 'known' else None
        if key in {'duration_days', 'traveler_count'}:
            if (type(raw_value) is not int
                    or not _explicit_integer_evidence(quote, raw_value, key)):
                continue
            value = raw_value
        elif key in {'destination', 'origin', 'interest', 'soft_preference',
                     'hard_constraint', 'accessibility'}:
            if not isinstance(raw_value, str) or raw_value.strip() not in quote:
                continue
            if key == 'soft_preference' and (
                raw_value.strip() != quote.strip() or not _explicit_soft_preference(quote)
            ):
                continue
            if key in {'hard_constraint', 'accessibility'} and raw_value.strip() != quote.strip():
                # Never let the model paraphrase or weaken safety/access text.
                continue
        elif key == 'budget_text':
            if (not isinstance(raw_value, str) or raw_value.strip() not in quote
                    or quoted_field is None or quoted_field.status != 'known'):
                continue
            if current.status == 'known' and quoted_field.value != current.value:
                # Keep the denomination/currency exactly as the traveler stated.
                continue
        elif key in {'relative_start_date', 'travel_start', 'travel_end'}:
            if key == 'relative_start_date':
                if (quoted_field is None or quoted_field.status != 'known'
                        or type(raw_value) is not int or quoted_field.value.offset_days != raw_value):
                    continue
            elif key in {'travel_start', 'travel_end'}:
                if (not isinstance(raw_value, str)
                        or re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw_value) is None
                        or raw_value not in quote):
                    continue
                try:
                    value = date.fromisoformat(raw_value)
                except ValueError:
                    continue
            elif quoted_field is None or quoted_field.status != 'known':
                continue
        if key in {'duration_days', 'traveler_count'} and current.status == 'known' and current.value != value:
            if not _explicit_correction_context(quote):
                continue
        if key == 'relative_start_date' and current.status == 'known' and current.value.offset_days != value.offset_days:
            continue
        if key == 'budget_text' and current.status == 'known' and current.value != value:
            continue
        span = EvidenceSpan(start=start, end=end, text=quote)
        if key in {'destination', 'origin'}:
            candidate_value = raw_value.strip()
        elif key == 'interest':
            candidate_value = list(dict.fromkeys([*(current.value or []), raw_value.strip()]))
        elif key == 'soft_preference':
            # The exact quote can include the preference marker ("I prefer …").
            # Store the parsed preference itself, not that full sentence alongside
            # the fallback's already extracted value.
            candidate_value = list(dict.fromkeys([*(current.value or []), *(quoted_field.value or [])]))
        elif key in {'hard_constraint', 'accessibility'}:
            candidate_value = list(dict.fromkeys([*(current.value or []), raw_value.strip()]))
        elif key in {'travel_start', 'travel_end'}:
            # Date candidates are merged below only when both endpoints were
            # stated and independently evidenced in this exact current turn.
            continue
        else:
            candidate_value = value
        try:
            fields[field_name] = RequirementValue(
                status='known', value=candidate_value, evidence_span=span, source='llm',
            )
        except Exception:
            # Invalid/unrepresentable provider candidates are omitted; they do
            # not weaken the deterministic interpretation.
            continue
    # The wire contract requires a complete start/end pair; never infer an end
    # date from a duration or silently accept only one endpoint.
    if 'travel_start' in hints and 'travel_end' in hints:
        start_quote = evidence.get('travel_start')
        end_quote = evidence.get('travel_end')
        start_value, end_value = hints['travel_start'], hints['travel_end']
        existing_dates = profile.fields.travel_dates
        if (isinstance(start_quote, str) and isinstance(end_quote, str)
                and start_quote and end_quote and start_quote in text and end_quote in text
                and isinstance(start_value, str) and isinstance(end_value, str)
                and start_value in start_quote and end_value in end_quote
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", start_value)
                and re.fullmatch(r"\d{4}-\d{2}-\d{2}", end_value)):
            try:
                parsed_start, parsed_end = date.fromisoformat(start_value), date.fromisoformat(end_value)
            except ValueError:
                pass
            else:
                if parsed_start <= parsed_end:
                    combined_start = min(text.index(start_quote), text.index(end_quote))
                    combined_end = max(text.index(start_quote) + len(start_quote),
                                       text.index(end_quote) + len(end_quote))
                    pair_allowed = True
                    if existing_dates.status != 'missing':
                        existing_span = existing_dates.evidence_span
                        if (existing_dates.source != 'fallback' or existing_span is None
                                or combined_start > existing_span.start or combined_end < existing_span.end
                                or existing_dates.value != {'start': parsed_start, 'end': parsed_end}):
                            pair_allowed = False
                    if pair_allowed:
                        combined_span = EvidenceSpan(
                            start=combined_start, end=combined_end,
                            text=text[combined_start:combined_end],
                        )
                        fields['travel_dates'] = RequirementValue(
                            status='known', value={'start': parsed_start, 'end': parsed_end},
                            evidence_span=combined_span, source='llm',
                        ).model_dump()
    return profile.model_copy(update={'fields': profile.fields.model_validate(fields)})


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
            reply = await gateway.invoke(ChatRequest(
                locale=locale, text=body.content, history=history,
            ))
            candidate_profile = _candidate_profile(
                body.content, locale, reply.requirements, reply.requirement_evidence,
            )
            await run_in_threadpool(
                repository.complete, user_id=principal.user_id,
                turn_id=reservation.turn_id, reply=reply.reply,
                requirements=candidate_profile.model_dump(mode='json'), clarification=reply.clarification,
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
        return {
            'conversation': conversation, 'trip': trip, 'message': message,
            'candidate_requirements': metadata.get('requirements_candidate') or {},
            'clarification': metadata.get('clarification'), 'replayed': replayed,
        }
    except Exception as exc:
        logger.warning('assistant.turn.failed phase=result_load error_type=%s', type(exc).__name__)
        return _error(503, 'assistant_unavailable')
