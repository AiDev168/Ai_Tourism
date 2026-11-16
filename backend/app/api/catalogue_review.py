"""Authenticated archive staging and human identity-review queue."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

import psycopg
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import authenticated_user, require_authenticated_csrf
from app.core.config import Settings, get_settings
from app.modules.catalog.archive_ingest import stage_archive
from app.modules.identity.auth_service import AuthenticatedUser

router = APIRouter(prefix="/api/v1/catalogue-review", tags=["catalogue-review"])
MAX_UPLOAD_BYTES = 256 * 1024 * 1024


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["accept", "reject", "defer", "request_evidence"]
    identity_relation: Literal["same_entity", "part_of_or_within", "nearby_distinct", "unresolved"]
    target_destination_id: int | None = Field(default=None, ge=1)
    reason: str = Field(min_length=1, max_length=2000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=30)
    policy_version: str = Field(default="catalogue-review-v1", min_length=1, max_length=80)


def _connect(settings: Settings):
    return psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password.get_secret_value(),
        connect_timeout=settings.database_connect_timeout_seconds,
        application_name="rahgard-catalogue-review",
        row_factory=dict_row,
    )


@router.post("/archives", status_code=202)
async def upload_archive(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    filename = request.headers.get("x-archive-filename", "")
    if not filename or not filename.lower().endswith(".zip"):
        raise HTTPException(422, "invalid_archive")
    chunks = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "archive_too_large")
        chunks.append(chunk)
    raw = b"".join(chunks)
    try:
        result = stage_archive(raw, user, settings)
    except PermissionError:
        raise HTTPException(403, "catalogue_review_not_granted") from None
    except Exception:
        raise HTTPException(422, "archive_rejected_or_unavailable") from None
    return {**result, "status": "needs_review", "publication_approved": False}


@router.get("/candidates")
def list_candidates(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = 50,
    after: UUID | None = None,
):
    if not 1 <= limit <= 100:
        raise HTTPException(422, "invalid_limit")
    try:
        with _connect(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                "SELECT identity.has_catalogue_review_capability(%s,'candidate_review') AS allowed",
                (user.user_id,),
            )
            if not cur.fetchone()["allowed"]:
                raise HTTPException(403, "catalogue_review_not_granted")
            cur.execute(
                """SELECT candidate_id,dataset_import_batch_id,file_id,source_record_key,
                raw_record,raw_name,raw_province,raw_city,raw_coordinate_role,proposed_name_fa,
                proposed_destination_type,proposed_latitude,proposed_longitude,candidate_status,created_at
                FROM knowledge.destination_candidates
                WHERE (%s::uuid IS NULL OR candidate_id>%s::uuid) AND candidate_status IN ('needs_review','in_review','conflict')
                ORDER BY candidate_id LIMIT %s""",
                (after, after, limit + 1),
            )
            rows = cur.fetchall()
    except psycopg.Error:
        raise HTTPException(503, "review_queue_unavailable") from None
    next_cursor = str(rows[limit - 1]["candidate_id"]) if len(rows) > limit else None
    items = rows[:limit]
    return {"items": items, "next_cursor": next_cursor}


@router.post("/candidates/{candidate_id}/decision")
def decide_candidate(
    candidate_id: UUID,
    body: ReviewDecision,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    if (
        body.decision == "accept"
        and body.identity_relation != "unresolved"
        and body.target_destination_id is None
    ):
        raise HTTPException(422, "target_required_for_identity_match")
    if body.identity_relation == "unresolved" and body.target_destination_id is not None:
        raise HTTPException(422, "unresolved_identity_cannot_have_target")
    try:
        with _connect(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                "SELECT identity.has_catalogue_review_capability(%s,'candidate_review') AS allowed",
                (user.user_id,),
            )
            if not cur.fetchone()["allowed"]:
                raise HTTPException(403, "catalogue_review_not_granted")
            cur.execute(
                """INSERT INTO knowledge.destination_candidate_reviews
                (candidate_id,identity_relation,target_destination_id,decision,reason,evidence_refs,reviewer_user_id,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s,%s) RETURNING review_id""",
                (
                    candidate_id,
                    body.identity_relation,
                    body.target_destination_id,
                    body.decision,
                    body.reason,
                    json.dumps(body.evidence_refs),
                    user.user_id,
                    body.policy_version,
                ),
            )
            review_id = cur.fetchone()["review_id"]
            status = (
                (
                    "resolved_existing"
                    if body.identity_relation == "same_entity"
                    else "approved_new_identity"
                )
                if body.decision == "accept"
                else {
                    "reject": "rejected",
                    "defer": "needs_review",
                    "request_evidence": "needs_review",
                }[body.decision]
            )
            cur.execute(
                """UPDATE knowledge.destination_candidates
                SET candidate_status=%s, canonical_destination_id=CASE WHEN %s='same_entity' THEN %s ELSE NULL END,updated_at=now()
                WHERE candidate_id=%s RETURNING candidate_id""",
                (status, body.identity_relation, body.target_destination_id, candidate_id),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "candidate_not_found")
    except HTTPException:
        raise
    except psycopg.errors.InsufficientPrivilege:
        raise HTTPException(403, "catalogue_review_not_granted") from None
    except psycopg.errors.ForeignKeyViolation:
        raise HTTPException(422, "unknown_canonical_destination") from None
    except psycopg.Error:
        raise HTTPException(503, "review_unavailable") from None
    return {
        "review_id": review_id,
        "candidate_id": candidate_id,
        "status": status,
        "published": False,
    }
