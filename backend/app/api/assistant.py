"""Internal authenticated Chat endpoint; never a public provider control plane."""
from __future__ import annotations

import logging
from typing import Annotated, Any, Literal
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
    remote_processing_consent: Literal[True]
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
        'interest': 'interests', 'relative_start_date': 'relative_start_date',
        'travel_start': 'travel_dates', 'travel_end': 'travel_dates',
        'hard_constraint': 'hard_constraints', 'accessibility': 'accessibility',
    }
    for key, field_name in key_to_field.items():
        current = getattr(profile.fields, field_name)
        raw_value = hints.get(key)
        quote = evidence.get(key)
        if current.status != 'missing' or raw_value is None or not isinstance(quote, str):
            continue
        start = text.find(quote)
        if start < 0 or not quote or len(quote) > 200:
            continue
        # Parse the quoted source with the same deterministic contract. This
        # allows useful multilingual extraction while refusing unsupported
        # conversions (especially dates, money and numeric quantities).
        parsed_quote = interpret_trip_requirements(quote, locale)
        quoted_field_name = {'traveler_count': 'travelers', 'budget_text': 'budget',
                             'interest': 'interests', 'hard_constraint': 'hard_constraints',
                             'travel_start': 'travel_dates', 'travel_end': 'travel_dates'}.get(key, key)
        quoted_field = getattr(parsed_quote.fields, quoted_field_name, None)
        value = quoted_field.value if quoted_field is not None and quoted_field.status == 'known' else None
        if key in {'duration_days', 'traveler_count'}:
            if type(raw_value) is not int or quoted_field is None or quoted_field.status != 'known' or value != raw_value:
                continue
        elif key in {'destination', 'origin', 'interest', 'hard_constraint', 'accessibility'}:
            if not isinstance(raw_value, str) or raw_value.strip() not in quote:
                continue
        elif key == 'budget_text':
            if (not isinstance(raw_value, str) or quoted_field is None
                    or quoted_field.status != 'known' or not quote):
                continue
        elif key in {'relative_start_date', 'travel_start', 'travel_end'}:
            if quoted_field is None or quoted_field.status != 'known':
                continue
            if key == 'relative_start_date' and (
                type(raw_value) is not int or quoted_field.value.offset_days != raw_value
            ):
                continue
            if key in {'travel_start', 'travel_end'}:
                expected = quoted_field.value.get('start' if key == 'travel_start' else 'end')
                if not isinstance(raw_value, str) or expected is None or expected.isoformat() != raw_value:
                    continue
        span = EvidenceSpan(start=start, end=start + len(quote), text=quote)
        if key in {'destination', 'origin'}:
            candidate_value = raw_value.strip()
        elif key == 'interest':
            candidate_value = [raw_value.strip()]
        elif key in {'hard_constraint', 'accessibility'}:
            candidate_value = [raw_value.strip()]
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
    except Exception:
        logger.warning('assistant.reservation_unavailable')
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
                # history window rolls forward. The current turn's explicit
                # processing consent covers this same-trip context; the latest
                # correction remains the newest message in the retained tail.
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
        except Exception:
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
    except Exception:
        return _error(503, 'assistant_unavailable')
