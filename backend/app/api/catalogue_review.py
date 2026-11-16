"""Authenticated archive staging and human identity-review queue."""

from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

import psycopg
import json
from fastapi import APIRouter, Depends, HTTPException, Request
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.api.auth import authenticated_user, require_authenticated_csrf
from app.core.config import Settings, get_settings
from app.modules.catalog.archive_ingest import stage_archive
from app.modules.identity.auth_service import AuthenticatedUser

router = APIRouter(prefix="/api/v1/catalogue-review", tags=["catalogue-review"])
MAX_UPLOAD_BYTES = 256 * 1024 * 1024
CandidateKind = Literal["destination_identity", "discovery_lead"]


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["accept", "approve_new_identity", "reject", "defer", "request_evidence"]
    identity_relation: Literal["same_entity", "part_of_or_within", "nearby_distinct", "unresolved"]
    target_destination_id: int | None = Field(default=None, ge=1)
    reason: str = Field(min_length=1, max_length=2000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=30)
    policy_version: str = Field(default="catalogue-review-v1", min_length=1, max_length=80)

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason_required")
        return value.strip()

    @field_validator("evidence_refs")
    @classmethod
    def normalize_evidence_refs(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 1000 for value in normalized) or len(set(normalized)) != len(normalized):
            raise ValueError("evidence_refs_must_be_nonempty_unique_references")
        return normalized


class SourceReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["register_pending", "reject", "defer", "request_evidence"]
    reason: str = Field(min_length=1, max_length=2000)
    evidence_refs: list[str] = Field(default_factory=list, max_length=30)
    policy_version: str = Field(default="source-review-v1", min_length=1, max_length=80)

    @field_validator("reason")
    @classmethod
    def nonblank_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reason_required")
        return value.strip()

    @field_validator("evidence_refs")
    @classmethod
    def normalize_evidence_refs(cls, values: list[str]) -> list[str]:
        normalized = [value.strip() for value in values]
        if any(not value or len(value) > 1000 for value in normalized) or len(set(normalized)) != len(normalized):
            raise ValueError("evidence_refs_must_be_nonempty_unique_references")
        return normalized


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
    kind: CandidateKind | None = None,
    q: str | None = None,
):
    if not 1 <= limit <= 100 or (q is not None and (not q.strip() or len(q) > 120)):
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
                raw_record,raw_name,raw_province,raw_city,raw_coordinate_role,proposed_name_fa,candidate_kind,
                proposed_destination_type,proposed_latitude,proposed_longitude,candidate_status,created_at
                FROM knowledge.destination_candidates
                WHERE (%s::uuid IS NULL OR candidate_id>%s::uuid)
                  AND candidate_status IN ('needs_review','in_review','conflict')
                  AND (%s::text IS NULL OR candidate_kind=%s)
                  AND (%s::text IS NULL OR proposed_name_fa ILIKE '%%'||%s||'%%'
                       OR raw_province ILIKE '%%'||%s||'%%' OR raw_city ILIKE '%%'||%s||'%%')
                ORDER BY candidate_id LIMIT %s""",
                (after, after, kind, kind, q, q, q, q, limit + 1),
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
    if body.decision == "accept" and (
        body.identity_relation == "unresolved" or body.target_destination_id is None or not body.evidence_refs
    ):
        raise HTTPException(422, "accepted_identity_requires_relation_target_and_evidence")
    if body.decision == "approve_new_identity" and (
        body.identity_relation != "unresolved"
        or body.target_destination_id is not None
        or not body.evidence_refs
    ):
        raise HTTPException(422, "new_identity_approval_requires_evidence_without_target")
    if body.decision in {"reject", "defer", "request_evidence"} and body.target_destination_id is not None:
        raise HTTPException(422, "nonaccept_decision_cannot_have_target")
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
                "SELECT candidate_status FROM knowledge.destination_candidates WHERE candidate_id=%s FOR UPDATE",
                (candidate_id,),
            )
            candidate = cur.fetchone()
            if candidate is None:
                raise HTTPException(404, "candidate_not_found")
            if candidate["candidate_status"] not in {"needs_review", "in_review", "conflict"}:
                raise HTTPException(409, "candidate_already_reviewed")
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
            if body.decision == "accept":
                status = "resolved_existing" if body.identity_relation == "same_entity" else "approved_new_identity"
            else:
                status = {
                    "approve_new_identity": "approved_new_identity",
                    "reject": "rejected",
                    "defer": "needs_review",
                    "request_evidence": "needs_review",
                }[body.decision]
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


@router.get("/sources")
def list_source_candidates(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = 50,
    after: UUID | None = None,
    q: str | None = None,
):
    if not 1 <= limit <= 100 or (q is not None and (not q.strip() or len(q) > 120)):
        raise HTTPException(422, "invalid_source_queue_filter")
    try:
        with _connect(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                "SELECT identity.has_catalogue_review_capability(%s,'source_review') AS allowed",
                (user.user_id,),
            )
            if not cur.fetchone()["allowed"]:
                raise HTTPException(403, "source_review_not_granted")
            cur.execute(
                """SELECT source_candidate_id,dataset_import_batch_id,file_id,source_record_key,raw_record,
                proposed_source_key,proposed_source_name,proposed_publisher,proposed_source_type,proposed_url,
                proposed_license,candidate_status,created_at
                FROM knowledge.source_candidates WHERE (%s::uuid IS NULL OR source_candidate_id>%s::uuid)
                  AND candidate_status IN ('needs_review','conflict')
                  AND (%s::text IS NULL OR proposed_source_name ILIKE '%%'||%s||'%%'
                       OR proposed_publisher ILIKE '%%'||%s||'%%')
                ORDER BY source_candidate_id LIMIT %s""",
                (after, after, q, q, q, limit + 1),
            )
            rows = cur.fetchall()
    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(503, "source_review_queue_unavailable") from None
    next_cursor = str(rows[limit - 1]["source_candidate_id"]) if len(rows) > limit else None
    return {"items": rows[:limit], "next_cursor": next_cursor}


@router.post("/sources/{source_candidate_id}/decision")
def decide_source_candidate(
    source_candidate_id: UUID,
    body: SourceReviewDecision,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    if body.decision == "register_pending" and not body.evidence_refs:
        raise HTTPException(422, "source_registration_requires_review_evidence")
    try:
        with _connect(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                "SELECT identity.has_catalogue_review_capability(%s,'source_review') AS allowed",
                (user.user_id,),
            )
            if not cur.fetchone()["allowed"]:
                raise HTTPException(403, "source_review_not_granted")
            cur.execute(
                """SELECT proposed_source_name,proposed_source_type,proposed_url,proposed_license,
                candidate_status FROM knowledge.source_candidates WHERE source_candidate_id=%s FOR UPDATE""",
                (source_candidate_id,),
            )
            candidate = cur.fetchone()
            if candidate is None:
                raise HTTPException(404, "source_candidate_not_found")
            if candidate["candidate_status"] not in {"needs_review", "conflict"}:
                raise HTTPException(409, "source_candidate_already_reviewed")
            source_id = None
            if body.decision == "register_pending":
                name = (candidate["proposed_source_name"] or "").strip()
                url = (candidate["proposed_url"] or "").strip()
                if not name or not url or len(name) > 500 or len(url) > 2048:
                    raise HTTPException(422, "source_candidate_lacks_name_or_url")
                if not url.startswith("https://"):
                    raise HTTPException(422, "source_candidate_requires_https_url")
                proposed_type = candidate["proposed_source_type"] or "research_pending"
                if len(proposed_type) > 80:
                    raise HTTPException(422, "source_type_exceeds_registry_limit")
                cur.execute(
                    """SELECT source_id,source_name,url FROM knowledge.knowledge_sources
                    WHERE url=%s OR source_name=%s ORDER BY source_id LIMIT 2""",
                    (url, name),
                )
                existing = cur.fetchall()
                if len(existing) > 1 or (
                    existing and (existing[0]["url"] != url or existing[0]["source_name"] != name)
                ):
                    raise HTTPException(409, "source_registry_identity_conflict")
                if existing:
                    cur.execute(
                        "SELECT verification_status,is_synthetic FROM knowledge.knowledge_sources WHERE source_id=%s",
                        (existing[0]["source_id"],),
                    )
                    existing_status = cur.fetchone()
                    if existing_status["verification_status"] != "pending" or existing_status["is_synthetic"]:
                        raise HTTPException(409, "source_registry_existing_status_conflict")
                    source_id = existing[0]["source_id"]
                else:
                    notes = "Imported as pending from owner archive; not verified or published."
                    if candidate["proposed_license"]:
                        notes += " Stated license requires independent review."
                    cur.execute(
                        """INSERT INTO knowledge.knowledge_sources
                        (source_name,source_type,verification_status,url,notes,is_synthetic)
                        VALUES (%s,%s,'pending',%s,%s,FALSE) RETURNING source_id""",
                        (name, proposed_type, url, notes),
                    )
                    source_id = cur.fetchone()["source_id"]
            cur.execute(
                """INSERT INTO knowledge.source_candidate_reviews
                (source_candidate_id,decision,source_id,reason,evidence_refs,reviewer_user_id,policy_version)
                VALUES (%s,%s,%s,%s,%s::jsonb,%s,%s) RETURNING source_review_id""",
                (
                    source_candidate_id,
                    body.decision,
                    source_id,
                    body.reason,
                    json.dumps(body.evidence_refs),
                    user.user_id,
                    body.policy_version,
                ),
            )
            review_id = cur.fetchone()["source_review_id"]
            status = {
                "register_pending": "registered_pending",
                "reject": "rejected",
                "defer": "needs_review",
                "request_evidence": "needs_review",
            }[body.decision]
            cur.execute(
                """UPDATE knowledge.source_candidates SET candidate_status=%s,registered_source_id=%s,updated_at=now()
                WHERE source_candidate_id=%s""",
                (status, source_id, source_candidate_id),
            )
    except HTTPException:
        raise
    except psycopg.errors.InsufficientPrivilege:
        raise HTTPException(403, "source_review_not_granted") from None
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "source_registry_identity_conflict") from None
    except psycopg.Error:
        raise HTTPException(503, "source_review_unavailable") from None
    return {
        "source_review_id": review_id,
        "source_candidate_id": source_candidate_id,
        "source_id": source_id,
        "status": status,
        "source_verification_status": "pending" if source_id is not None else None,
        "published": False,
    }
