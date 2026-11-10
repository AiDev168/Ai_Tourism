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
from app.modules.trip.repository import (
    TravelerConflict, TravelerInvalidState, TravelerNotFound, TravelerRepository,
)
from app.modules.trip.schemas import ConversationDetail, MessageResponse, TripResponse, _bounded_json

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
    candidate_requirements: dict[str, str | int | None]
    clarification: str | None
    replayed: bool


def get_assistant_turn_repository(
    traveler: Annotated[TravelerRepository, Depends(get_traveler_repository)],
) -> AssistantTurnRepository:
    return AssistantTurnRepository(traveler)


def get_chat_gateway(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AiProviderGateway[ChatRequest, ChatReply]:
    return make_chat_gateway(settings)


def _error(status: int, code: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={'error': {'code': code}},
                        headers={'Cache-Control': 'no-store'})


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
    if not settings.internal_chat_enabled or settings.app_env.lower() not in {'development', 'test'}:
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
            await run_in_threadpool(
                repository.complete, user_id=principal.user_id,
                turn_id=reservation.turn_id, reply=reply.reply,
                requirements=reply.requirements, clarification=reply.clarification,
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
