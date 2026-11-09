"""Owner-scoped authenticated conversation, trip, recommendation and itinerary API."""

import logging
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import JSONResponse

from app.core.config import Settings, get_settings
from app.api.auth import require_authenticated_csrf
from app.modules.catalog.repository import (
    CatalogueUnavailableError,
    list_production_destination_sources,
    list_production_destination_tags,
    list_production_destinations,
)
from app.modules.catalog.schemas import ProductionDestinationItem
from app.modules.identity.authorization import Principal, get_principal
from app.modules.itinerary.service import generate_itinerary
from app.modules.recommendation.contracts import EvidenceSource
from app.modules.recommendation.contracts import RecommendationOutcome
from app.modules.recommendation.service import recommend_trip
from app.modules.recommendation.retrieval import StructuredDestinationMetadata
from app.modules.trip.repository import (
    TravelerConflict,
    TravelerInvalidState,
    TravelerNotFound,
    TravelerRepository,
    localized_recommendation_explanation,
)
from app.modules.trip.schemas import (
    AppendMessageRequest,
    ConversationDeleteResponse,
    ConversationDetail,
    ConversationListResponse,
    ConfirmTripProfileRequest,
    CreateItineraryRequest,
    CreateRecommendationRequest,
    ItineraryResponse,
    MessageAppendResponse,
    RecommendationResponse,
    StartConversationRequest,
    StartConversationResponse,
    TripDeleteResponse,
    TripResponse,
    UpdateItineraryRequest,
)

logger = logging.getLogger("ai_tourism.traveler")
router = APIRouter(prefix="/api/v1", tags=["traveler"])


def get_traveler_repository(settings: Annotated[Settings, Depends(get_settings)]) -> TravelerRepository:
    return TravelerRepository(settings)


def production_catalogue_bundle(
    settings: Annotated[Settings, Depends(get_settings)],
) -> tuple[
    list[ProductionDestinationItem],
    dict[str, list[EvidenceSource]],
    dict[str, StructuredDestinationMetadata],
]:
    """Read only approved spatial candidates and their approved source view."""
    candidates = list_production_destinations(settings)
    if not candidates:
        return [], {}, {}
    destination_ids = [item.destination_id for item in candidates]
    source_rows = list_production_destination_sources(
        settings, destination_ids
    )
    sources = {
        str(destination_id): [EvidenceSource.model_validate(source.model_dump()) for source in rows]
        for destination_id, rows in source_rows.items()
    }
    tag_rows = list_production_destination_tags(settings, destination_ids)
    metadata = {
        destination_id: StructuredDestinationMetadata(tags=tags)
        for destination_id, tags in tag_rows.items()
    }
    return candidates, sources, metadata


def _error(status: int, code: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code}})


def _mark_no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def _owner_missing() -> JSONResponse:
    # A foreign identifier and a nonexistent identifier have the same response.
    return _error(404, "resource_not_found")


def _database_unavailable() -> JSONResponse:
    logger.warning("traveler.persistence_unavailable")
    return _error(503, "service_unavailable")


def _trip_id_from_payload(trip: dict) -> UUID:
    return trip["trip_id"] if isinstance(trip["trip_id"], UUID) else UUID(str(trip["trip_id"]))


@router.post("/conversations", response_model=StartConversationResponse, status_code=201)
def create_conversation(
    body: StartConversationRequest,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
):
    _mark_no_store(response)
    try:
        conversation_id, trip_id, message_id, _created = repository.create_conversation(
            user_id=principal.user_id,
            locale=body.locale,
            request_text=body.request_text,
            extracted_requirements=body.extracted_requirements,
            # Extraction and resolver output are untrusted until the traveler
            # reviews and submits the explicit profile-confirmation request.
            confirmed_requirements={},
            destination_ids=[],
            idempotency_key=body.idempotency_key,
        )
        conversation = repository.conversation(principal.user_id, conversation_id)
        trip = repository.trip(principal.user_id, trip_id)
        if conversation is None or trip is None:
            return _database_unavailable()
        message = next((item for item in conversation["messages"] if item["message_id"] == message_id), None)
        if message is None:
            return _database_unavailable()
        return {"conversation": conversation, "trip": trip, "initial_message": message}
    except TravelerConflict:
        return _error(409, "idempotency_conflict")
    except Exception:
        return _database_unavailable()


@router.post(
    "/conversations/{conversation_id}/trips",
    response_model=StartConversationResponse,
    status_code=201,
)
def create_trip_in_conversation(
    conversation_id: UUID,
    body: StartConversationRequest,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
):
    _mark_no_store(response)
    try:
        resolved_conversation_id, trip_id, message_id, _created = repository.create_trip_in_conversation(
            user_id=principal.user_id,
            conversation_id=conversation_id,
            locale=body.locale,
            request_text=body.request_text,
            extracted_requirements=body.extracted_requirements,
            # A new trip draft starts unconfirmed; only PATCH /trips/{id}
            # records user-reviewed requirements and canonical destination IDs.
            confirmed_requirements={},
            destination_ids=[],
            idempotency_key=body.idempotency_key,
        )
        conversation = repository.conversation(principal.user_id, resolved_conversation_id)
        trip = repository.trip(principal.user_id, trip_id)
        if conversation is None or trip is None:
            return _database_unavailable()
        message = next((item for item in conversation["messages"] if item["message_id"] == message_id), None)
        if message is None:
            return _database_unavailable()
        return {"conversation": conversation, "trip": trip, "initial_message": message}
    except TravelerNotFound:
        return _owner_missing()
    except TravelerConflict:
        return _error(409, "idempotency_conflict")
    except Exception:
        return _database_unavailable()


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
    limit: int = Query(default=20, ge=1, le=50),
    cursor: UUID | None = None,
):
    _mark_no_store(response)
    try:
        items, next_cursor = repository.list_conversations(principal.user_id, limit, cursor)
        return {"items": items, "next_cursor": next_cursor}
    except TravelerNotFound:
        return _error(400, "invalid_cursor")
    except Exception:
        return _database_unavailable()


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: UUID,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
):
    _mark_no_store(response)
    try:
        result = repository.conversation(principal.user_id, conversation_id)
    except Exception:
        return _database_unavailable()
    return result if result is not None else _owner_missing()


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageAppendResponse,
    status_code=201,
)
def append_message(
    conversation_id: UUID,
    body: AppendMessageRequest,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
):
    _mark_no_store(response)
    try:
        message_id, _created = repository.append_message(
            user_id=principal.user_id,
            conversation_id=conversation_id,
            trip_id=body.trip_id,
            content=body.content,
            extracted_requirements=body.extracted_requirements,
            idempotency_key=body.idempotency_key,
            expected_version=body.expected_version,
            replace_previous_request=body.replace_previous_request,
        )
        conversation = repository.conversation(principal.user_id, conversation_id)
        trip = repository.trip(principal.user_id, body.trip_id)
        if conversation is None or trip is None:
            return _owner_missing()
        message = next((item for item in conversation["messages"] if item["message_id"] == message_id), None)
        if message is None:
            return _database_unavailable()
        return {"conversation": conversation, "trip": trip, "message": message}
    except TravelerNotFound:
        return _owner_missing()
    except TravelerConflict:
        return _error(409, "version_or_idempotency_conflict")
    except TravelerInvalidState:
        return _error(413, "conversation_limit_reached")
    except Exception:
        return _database_unavailable()


@router.get("/trips/{trip_id}", response_model=TripResponse)
def get_trip(
    trip_id: UUID,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
):
    _mark_no_store(response)
    try:
        result = repository.trip(principal.user_id, trip_id)
    except Exception:
        return _database_unavailable()
    return result if result is not None else _owner_missing()


@router.patch("/trips/{trip_id}", response_model=TripResponse)
def confirm_trip_profile(
    trip_id: UUID,
    body: ConfirmTripProfileRequest,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
):
    _mark_no_store(response)
    try:
        repository.confirm_trip_profile(
            user_id=principal.user_id,
            trip_id=trip_id,
            expected_version=body.expected_version,
            confirmed_requirements=body.confirmed_requirements,
            destination_ids=body.destination_ids,
            requirement_consent=(
                body.requirement_consent.model_dump(mode="json")
                if body.requirement_consent is not None else None
            ),
        )
        result = repository.trip(principal.user_id, trip_id)
        return result if result is not None else _owner_missing()
    except TravelerNotFound:
        return _owner_missing()
    except TravelerConflict:
        return _error(409, "version_conflict")
    except Exception:
        return _database_unavailable()


@router.delete("/trips/{trip_id}", response_model=TripDeleteResponse)
def delete_trip(
    trip_id: UUID,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
):
    _mark_no_store(response)
    try:
        result = repository.delete_trip(principal.user_id, trip_id)
    except Exception:
        return _database_unavailable()
    return {"deleted": True} if result is not None else _owner_missing()


@router.delete("/conversations/{conversation_id}", response_model=ConversationDeleteResponse)
def delete_conversation(
    conversation_id: UUID,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
):
    _mark_no_store(response)
    try:
        deleted = repository.delete_conversation(principal.user_id, conversation_id)
    except Exception:
        return _database_unavailable()
    return {"deleted": True} if deleted else _owner_missing()


def _recommendation_outcome(
    settings: Settings,
    trip: dict,
    selected_destination_ids: list[str],
) -> tuple[Any, dict[str, ProductionDestinationItem]]:
    candidates, all_evidence, metadata_by_destination = production_catalogue_bundle(settings)
    by_id = {item.destination_id: item for item in candidates}
    selected = list(selected_destination_ids)
    # The structured retriever may expand an explicitly selected area to exact
    # same-city published candidates; provide provenance for the full approved
    # catalogue projection so each returned child is independently evidenced.
    evidence_by_destination = all_evidence
    requirements = dict(trip.get("confirmed_requirements") or {})
    requirements["destination_ids"] = selected
    outcome = recommend_trip(
        requirements=requirements,
        selected_destination_ids=selected,
        catalogue=candidates,
        evidence_by_destination=evidence_by_destination,
        locale=trip["locale"],
        metadata_by_destination=metadata_by_destination,
        profile_version=trip["version"],
    )
    return outcome, by_id


def _recommendation_response(
    outcome: Any,
    by_id: dict[str, ProductionDestinationItem],
    request_id: UUID,
    trip_version: int,
    recommendation_ids: dict[str, UUID],
    persisted_scores: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    items = []
    for item in outcome.items:
        destination = by_id.get(item.destination_id)
        if destination is None:
            continue
        item_data = item.model_dump(mode="python")
        if persisted_scores is not None:
            item_data["score_components"] = persisted_scores.get(item.destination_id, [])
        items.append({
            **item_data,
            "recommendation_id": recommendation_ids[item.destination_id],
            "canonical_name": destination.canonical_name,
            "localized_names": destination.localized_names,
            "explanation_by_locale": localized_recommendation_explanation(item.explanation_key),
            "city_name": destination.city_name,
            "province_name": destination.province_name,
            "destination_type": destination.destination_type,
        })
    return {
        "recommendation_request_id": request_id,
        "status": outcome.status,
        "reason_code": outcome.reason_code,
        "algorithm_version": outcome.algorithm_version,
        "retrieval_version": outcome.retrieval_version,
        "trip_version": trip_version,
        "unresolved_fields": list(outcome.unresolved_fields),
        "requirement_assessments": [item.model_dump(mode="json") for item in outcome.requirement_assessments],
        "waived_fields": list(outcome.waived_fields),
        "not_evaluated_fields": list(outcome.not_evaluated_fields),
        "items": items,
    }


@router.post("/trips/{trip_id}/recommendations", response_model=RecommendationResponse, status_code=201)
def create_recommendations(
    trip_id: UUID,
    body: CreateRecommendationRequest,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    _mark_no_store(response)
    try:
        trip = repository.trip(principal.user_id, trip_id)
        if trip is None:
            return _owner_missing()
        selected_ids = body.selected_destination_ids or trip["destination_ids"]
        if selected_ids != trip["destination_ids"]:
            return _error(409, "trip_profile_not_confirmed")
        outcome, by_id = _recommendation_outcome(settings, trip, selected_ids)
        request_id, version = repository.create_recommendation_run(
            user_id=principal.user_id,
            trip_id=trip_id,
            expected_trip_version=trip["version"],
            outcome=outcome,
            selected_destination_ids=selected_ids,
        )
        # Attach the database-assigned recommendation IDs to the response in rank order.
        context = repository.recommendation_context(principal.user_id, trip_id, request_id)
        rec_ids = {str(row["destination_id"]): row["recommendation_id"] for row in context["items"]} if context else {}
        stored_scores = {
            str(row["destination_id"]): row.get("score_components", [])
            for row in context["items"]
        } if context else {}
        return _recommendation_response(outcome, by_id, request_id, version, rec_ids, stored_scores)
    except CatalogueUnavailableError:
        return _error(503, "catalogue_unavailable")
    except TravelerNotFound:
        return _owner_missing()
    except Exception:
        return _database_unavailable()


@router.get("/trips/{trip_id}/recommendations", response_model=RecommendationResponse)
def get_latest_recommendations(
    trip_id: UUID,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    _mark_no_store(response)
    try:
        trip = repository.trip(principal.user_id, trip_id)
        if trip is None:
            return _owner_missing()
        request_id = trip["latest_recommendation_request_id"]
        if request_id is None:
            return _error(404, "recommendation_not_found")
        context = repository.recommendation_context(principal.user_id, trip_id, request_id)
        if context is None:
            return _error(409, "recommendation_outdated")
        snapshot = context["input_snapshot"] or {}
        saved_status = snapshot.get("outcome_status")
        if saved_status in {"empty", "needs_confirmation"}:
            outcome = RecommendationOutcome(
                status=saved_status,
                reason_code=snapshot.get("reason_code"),
                unresolved_fields=snapshot.get("unresolved_fields", []),
                requirement_assessments=snapshot.get("requirement_assessments", []),
                waived_fields=snapshot.get("waived_fields", []),
                not_evaluated_fields=snapshot.get("not_evaluated_fields", []),
                items=[],
            )
            return _recommendation_response(outcome, {}, request_id, trip["version"], {})
        outcome, by_id, recommendation_ids, persisted_scores = _current_recommendations(
            settings, repository, principal.user_id, trip_id, request_id
        )
        return _recommendation_response(
            outcome, by_id, request_id, trip["version"], recommendation_ids, persisted_scores
        )
    except CatalogueUnavailableError:
        return _error(503, "catalogue_unavailable")
    except TravelerNotFound:
        return _owner_missing()
    except TravelerConflict:
        return _error(409, "recommendation_outdated")
    except TravelerInvalidState:
        return _error(409, "no_eligible_recommendations")
    except Exception:
        return _database_unavailable()


def _current_recommendations(
    settings: Settings,
    repository: TravelerRepository,
    user_id: UUID,
    trip_id: UUID,
    request_id: UUID,
) -> tuple[Any, dict[str, ProductionDestinationItem], dict[str, UUID], dict[str, list[dict[str, Any]]]]:
    context = repository.recommendation_context(user_id, trip_id, request_id)
    if context is None:
        raise TravelerConflict
    trip = repository.trip(user_id, trip_id)
    if trip is None:
        raise TravelerNotFound
    selected = (context["input_snapshot"] or {}).get("selected_destination_ids", [])
    outcome, by_id = _recommendation_outcome(settings, trip, selected)
    rec_ids = {str(row["destination_id"]): row["recommendation_id"] for row in context["items"]}
    persisted_scores = {
        str(row["destination_id"]): row.get("score_components", []) for row in context["items"]
    }
    if outcome.status != "available" or not outcome.items:
        raise TravelerInvalidState
    if any(item.destination_id not in rec_ids for item in outcome.items):
        raise TravelerConflict
    return outcome, by_id, rec_ids, persisted_scores


_ITINERARY_TITLES = {
    "fa-IR": "پیشنهاد برنامه سفر",
    "en-US": "Suggested itinerary",
    "ar": "خطة سفر مقترحة",
}


def _draft_stops(draft: Any, recommendation_ids: dict[str, UUID]) -> list[dict[str, Any]]:
    return [
        {
            "destination_id": stop.destination_id,
            "recommendation_id": recommendation_ids[stop.destination_id],
            "day_number": stop.day_number,
            "stop_order": stop.stop_order,
            "notes_by_locale": stop.user_notes_by_locale,
        }
        for stop in draft.stops
    ]


@router.post("/trips/{trip_id}/itineraries", response_model=ItineraryResponse, status_code=201)
def create_itinerary(
    trip_id: UUID,
    body: CreateItineraryRequest,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    _mark_no_store(response)
    try:
        trip = repository.trip(principal.user_id, trip_id)
        if trip is None:
            return _owner_missing()
        confirmed_duration = trip.get("duration_days")
        if confirmed_duration is None:
            return _error(409, "trip_duration_not_confirmed")
        if body.day_count > confirmed_duration:
            return _error(409, "itinerary_exceeds_confirmed_duration")
        outcome, by_id, rec_ids, _persisted_scores = _current_recommendations(
            settings, repository, principal.user_id, trip_id, body.recommendation_request_id
        )
        draft = generate_itinerary(recommendation=outcome, day_count=body.day_count, locale=body.locale)
        if draft is None or not draft.stops:
            return _error(409, "no_eligible_recommendations")
        itinerary_id = repository.create_itinerary(
            user_id=principal.user_id,
            trip_id=trip_id,
            recommendation_request_id=body.recommendation_request_id,
            day_count=draft.day_count,
            title_by_locale=_ITINERARY_TITLES,
            stops=_draft_stops(draft, rec_ids),
        )
        result = repository.itinerary(principal.user_id, itinerary_id)
        if result is None:
            return _database_unavailable()
        return _enrich_itinerary(result, by_id)
    except CatalogueUnavailableError:
        return _error(503, "catalogue_unavailable")
    except TravelerNotFound:
        return _owner_missing()
    except TravelerConflict:
        return _error(409, "recommendation_outdated")
    except TravelerInvalidState:
        return _error(409, "no_eligible_recommendations")
    except Exception:
        return _database_unavailable()


def _enrich_itinerary(row: dict[str, Any], by_id: dict[str, ProductionDestinationItem]) -> dict[str, Any]:
    enriched_stops = []
    for stop in row["stops"]:
        destination = by_id.get(str(stop["destination_id"]))
        if destination is None:
            raise TravelerConflict
        enriched_stops.append({
            **stop,
            "destination_id": str(stop["destination_id"]),
            "localized_names": destination.localized_names,
            "canonical_name": destination.canonical_name,
        })
    planned_days = {stop["day_number"] for stop in enriched_stops}
    unplanned_days = [day for day in range(1, row["day_count"] + 1) if day not in planned_days]
    return {
        **row,
        "stops": enriched_stops,
        "status": "partial" if unplanned_days else "complete",
        "unplanned_days": unplanned_days,
    }


@router.get("/itineraries/{itinerary_id}", response_model=ItineraryResponse)
def get_itinerary(
    itinerary_id: UUID,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    _mark_no_store(response)
    try:
        result = repository.itinerary(principal.user_id, itinerary_id)
        if result is None:
            return _owner_missing()
        context = repository.recommendation_context(
            principal.user_id, result["trip_id"], result["recommendation_request_id"]
        )
        if context is None:
            return _error(409, "itinerary_evidence_stale")
        candidates, _, _ = production_catalogue_bundle(settings)
        by_id = {item.destination_id: item for item in candidates}
        return _enrich_itinerary(result, by_id)
    except CatalogueUnavailableError:
        return _error(503, "catalogue_unavailable")
    except TravelerConflict:
        return _error(409, "itinerary_evidence_stale")
    except Exception:
        return _database_unavailable()


@router.put("/itineraries/{itinerary_id}", response_model=ItineraryResponse)
def update_itinerary(
    itinerary_id: UUID,
    body: UpdateItineraryRequest,
    response: Response,
    principal: Annotated[Principal, Depends(get_principal)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    repository: Annotated[TravelerRepository, Depends(get_traveler_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    _mark_no_store(response)
    try:
        existing = repository.itinerary(principal.user_id, itinerary_id)
        if existing is None:
            return _owner_missing()
        trip = repository.trip(principal.user_id, existing["trip_id"])
        if trip is None:
            return _owner_missing()
        confirmed_duration = trip.get("duration_days")
        if confirmed_duration is None:
            return _error(409, "trip_duration_not_confirmed")
        if existing["day_count"] > confirmed_duration:
            return _error(409, "itinerary_exceeds_confirmed_duration")
        # Revalidate every referenced destination against the current publication view.
        outcome, by_id, current_rec_ids, _persisted_scores = _current_recommendations(
            settings, repository, principal.user_id, existing["trip_id"],
            existing["recommendation_request_id"],
        )
        valid_by_rec = {str(rec_id): destination_id for destination_id, rec_id in current_rec_ids.items()}
        stops = []
        for stop in body.stops:
            destination_id = valid_by_rec.get(str(stop.recommendation_id))
            if destination_id is None or destination_id not in by_id:
                return _error(409, "itinerary_item_not_eligible")
            stops.append({
                "recommendation_id": stop.recommendation_id,
                "destination_id": destination_id,
                "day_number": stop.day_number,
                "stop_order": stop.stop_order,
                "notes_by_locale": stop.notes_by_locale,
            })
        repository.update_itinerary(
            user_id=principal.user_id,
            itinerary_id=itinerary_id,
            expected_revision=body.expected_revision,
            title_by_locale=body.title_by_locale,
            stops=stops,
        )
        result = repository.itinerary(principal.user_id, itinerary_id)
        if result is None:
            return _owner_missing()
        return _enrich_itinerary(result, by_id)
    except CatalogueUnavailableError:
        return _error(503, "catalogue_unavailable")
    except TravelerNotFound:
        return _owner_missing()
    except TravelerConflict:
        return _error(409, "version_conflict")
    except TravelerInvalidState:
        return _error(409, "itinerary_item_not_eligible")
    except Exception:
        return _database_unavailable()

