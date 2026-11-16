"""Authenticated archive staging and human identity-review queue."""

from __future__ import annotations

from typing import Annotated, Literal
from datetime import UTC, datetime
from uuid import UUID
from urllib.parse import urlsplit

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


class SourceVerificationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    publisher: str = Field(min_length=1, max_length=240)
    page_title: str = Field(min_length=1, max_length=500)
    evidence_excerpt: str = Field(min_length=1, max_length=600)
    inspected_at: datetime
    policy_version: str = Field(default="source-direct-inspection-v1", min_length=1, max_length=80)


class SourceRegistrationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_name: str = Field(min_length=1, max_length=500)
    source_type: str = Field(min_length=1, max_length=80)
    publisher: str = Field(min_length=1, max_length=240)
    page_title: str = Field(min_length=1, max_length=500)
    url: str = Field(min_length=12, max_length=2048)
    license_note: str | None = Field(default=None, max_length=500)
    registration_note: str = Field(min_length=1, max_length=1000)
    policy_version: str = Field(default="direct-source-registration-v1", min_length=1, max_length=80)

    @field_validator("url")
    @classmethod
    def require_https_source_url(cls, value: str) -> str:
        parsed = urlsplit(value.strip())
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.fragment or any(ch.isspace() for ch in value)):
            raise ValueError("source_url_must_be_https_without_credentials_or_fragment")
        return value.strip()


class CandidateEvidenceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: int = Field(ge=1)
    field_key: Literal["identity", "province", "city", "coordinates", "description"]
    claim_value: str = Field(min_length=1, max_length=8000)
    evidence_excerpt: str = Field(min_length=1, max_length=600)
    retrieved_at: datetime
    policy_version: str = Field(default="candidate-field-evidence-v1", min_length=1, max_length=80)


class PublishCandidateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destination_key: str = Field(min_length=3, max_length=240, pattern=r"^[a-z0-9][a-z0-9_-]{2,239}$")
    # Archive-provided coordinates are property/map points. A visitor entrance
    # can only be published after it has its own independently reviewed access
    # point record and evidence; this endpoint does not create one.
    coordinate_role: Literal["property_reference", "representative_point"]
    policy_version: str = Field(default="archive-candidate-publication-v1", min_length=1, max_length=80)


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
    evidence_ids: list[UUID] = []
    if body.decision in {"accept", "approve_new_identity"}:
        try:
            evidence_ids = [UUID(value) for value in body.evidence_refs]
        except ValueError:
            raise HTTPException(422, "review_requires_candidate_evidence_ids") from None
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
            if body.decision in {"accept", "approve_new_identity"}:
                cur.execute(
                    """SELECT count(DISTINCT e.evidence_id) AS n
                    FROM knowledge.destination_candidate_evidence e
                    JOIN knowledge.knowledge_sources s USING(source_id)
                    WHERE e.candidate_id=%s AND e.evidence_id=ANY(%s::uuid[])
                      AND s.verification_status='verified' AND s.is_synthetic=FALSE""",
                    (candidate_id, evidence_ids),
                )
                if int(cur.fetchone()["n"]) != len(evidence_ids):
                    raise HTTPException(422, "review_evidence_not_linked_to_verified_source")
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


@router.get("/sources/pending-verification")
def pending_source_verification(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """List archive source records that were registered pending, not verified."""
    try:
        with _connect(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute("SELECT identity.has_catalogue_review_capability(%s,'source_review') AS allowed", (user.user_id,))
            if not cur.fetchone()["allowed"]:
                raise HTTPException(403, "source_review_not_granted")
            cur.execute(
                """SELECT s.source_id,s.source_name AS proposed_source_name,s.url AS proposed_url,
                    latest.publisher AS proposed_publisher,latest.page_title,
                    latest.license_note AS proposed_license,s.verification_status
                FROM knowledge.knowledge_sources s
                JOIN LATERAL (
                  SELECT e.publisher,e.page_title,e.license_note,e.created_at
                  FROM knowledge.source_registry_registration_events e WHERE e.source_id=s.source_id
                  UNION ALL
                  SELECT sc.proposed_publisher,sc.proposed_source_name,NULL::text,sc.created_at
                  FROM knowledge.source_candidates sc WHERE sc.registered_source_id=s.source_id
                ) latest ON TRUE
                WHERE s.verification_status IN ('pending','stale') AND NOT s.is_synthetic
                ORDER BY latest.created_at,s.source_id LIMIT 100"""
            )
            return {"items": cur.fetchall()}
    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(503, "pending_source_verification_unavailable") from None


@router.post("/sources/register", status_code=201)
def register_direct_source(
    body: SourceRegistrationInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Register a directly inspected source as pending; registration is not verification."""
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
                """SELECT source_id FROM knowledge.knowledge_sources
                WHERE url=%s OR source_name=%s LIMIT 1""",
                (body.url, body.source_name.strip()),
            )
            if cur.fetchone() is not None:
                raise HTTPException(409, "source_registry_identity_already_exists")
            cur.execute(
                """INSERT INTO knowledge.knowledge_sources
                (source_name,source_type,verification_status,url,notes,is_synthetic)
                VALUES (%s,%s,'pending',%s,%s,FALSE) RETURNING source_id""",
                (body.source_name.strip(),body.source_type.strip(),body.url,
                 "Manually registered for direct inspection; not verified or published."),
            )
            source_id = cur.fetchone()["source_id"]
            cur.execute(
                """INSERT INTO knowledge.source_registry_registration_events
                (source_id,publisher,page_title,registered_url,license_note,registration_note,
                 registrar_user_id,policy_version)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING registration_id""",
                (source_id,body.publisher.strip(),body.page_title.strip(),body.url,
                 body.license_note,body.registration_note.strip(),user.user_id,body.policy_version),
            )
            return {"source_id":source_id,"registration_id":cur.fetchone()["registration_id"],
                    "verification_status":"pending","published":False}
    except HTTPException:
        raise
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "source_registry_identity_already_exists") from None
    except psycopg.errors.InsufficientPrivilege:
        raise HTTPException(403, "source_review_not_granted") from None
    except psycopg.Error:
        raise HTTPException(503, "source_registration_unavailable") from None


@router.post("/sources/{source_id}/verification", status_code=201)
def verify_source(
    source_id: int,
    body: SourceVerificationInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Verify the source record after direct inspection; claims remain separate."""
    if body.inspected_at.tzinfo is None or body.inspected_at > datetime.now(UTC):
        raise HTTPException(422, "source_inspection_timestamp_invalid")
    if len(body.evidence_excerpt.split()) > 25:
        raise HTTPException(422, "source_excerpt_exceeds_25_words")
    try:
        with _connect(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """SELECT knowledge.verify_archive_source(%s,%s,%s,%s,%s,%s,%s) AS verification_id""",
                (source_id, body.publisher, body.page_title, body.evidence_excerpt,
                 body.inspected_at, body.policy_version, user.user_id),
            )
            result = cur.fetchone()
    except psycopg.errors.InsufficientPrivilege:
        raise HTTPException(403, "source_review_not_granted") from None
    except psycopg.errors.RaiseException:
        raise HTTPException(422, "source_verification_rejected") from None
    except psycopg.Error:
        raise HTTPException(503, "source_verification_unavailable") from None
    return {"verification_id": result["verification_id"], "source_id": source_id,
            "verification_status": "verified", "claim_status": "claims_still_require_field_evidence"}


@router.get("/candidates/{candidate_id}/evidence")
def list_candidate_evidence(
    candidate_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connect(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute("SELECT identity.has_catalogue_review_capability(%s,'candidate_review') AS allowed", (user.user_id,))
            if not cur.fetchone()["allowed"]:
                raise HTTPException(403, "catalogue_review_not_granted")
            cur.execute(
                """SELECT e.evidence_id,e.source_id,e.field_key,e.claim_value,e.source_url,
                    e.evidence_excerpt,e.retrieved_at,e.created_at,s.source_name,s.verification_status
                FROM knowledge.destination_candidate_evidence e JOIN knowledge.knowledge_sources s USING(source_id)
                WHERE e.candidate_id=%s ORDER BY e.created_at,e.evidence_id""",
                (candidate_id,),
            )
            return {"items": cur.fetchall()}
    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(503, "candidate_evidence_unavailable") from None


@router.get("/candidates/approved")
def list_approved_candidates(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connect(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute("SELECT identity.has_catalogue_review_capability(%s,'candidate_review') AS allowed", (user.user_id,))
            if not cur.fetchone()["allowed"]:
                raise HTTPException(403, "catalogue_review_not_granted")
            cur.execute(
                """SELECT c.candidate_id,c.candidate_kind,c.proposed_destination_key,c.proposed_name_fa,
                    c.proposed_destination_type,c.raw_province,c.raw_city,c.raw_coordinate_role,
                    c.proposed_latitude,c.proposed_longitude,c.candidate_status,
                    COALESCE(array_agg(DISTINCT e.field_key) FILTER(WHERE e.evidence_id IS NOT NULL),'{}') AS evidence_fields,
                    count(DISTINCT e.evidence_id) AS evidence_count
                FROM knowledge.destination_candidates c
                JOIN knowledge.destination_candidate_reviews r ON r.candidate_id=c.candidate_id
                LEFT JOIN knowledge.destination_candidate_evidence e ON e.candidate_id=c.candidate_id
                WHERE c.candidate_status='approved_new_identity' AND r.decision='approve_new_identity'
                  AND NOT EXISTS(SELECT 1 FROM knowledge.catalogue_publication_events p WHERE p.candidate_id=c.candidate_id)
                GROUP BY c.candidate_id,r.review_id ORDER BY r.decided_at DESC LIMIT 100"""
            )
            return {"items": cur.fetchall()}
    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(503, "approved_candidate_queue_unavailable") from None


@router.get("/sources/verified")
def list_verified_sources(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connect(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute("SELECT identity.has_catalogue_review_capability(%s,'source_review') AS allowed", (user.user_id,))
            if not cur.fetchone()["allowed"]:
                raise HTTPException(403, "source_review_not_granted")
            cur.execute(
                """SELECT s.source_id,s.source_name,s.source_type,s.url,s.verification_status,
                    r.publisher,r.page_title,r.inspected_at
                FROM knowledge.knowledge_sources s JOIN LATERAL
                    (SELECT publisher,page_title,inspected_at FROM knowledge.source_verification_reviews v
                     WHERE v.source_id=s.source_id AND v.decision='verified' ORDER BY decided_at DESC LIMIT 1) r ON TRUE
                WHERE s.verification_status='verified' AND s.is_synthetic=FALSE AND s.url LIKE 'https://%%'
                ORDER BY s.source_name,s.source_id LIMIT 200"""
            )
            return {"items": cur.fetchall()}
    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(503, "verified_source_list_unavailable") from None


@router.post("/candidates/{candidate_id}/evidence", status_code=201)
def record_candidate_evidence(
    candidate_id: UUID,
    body: CandidateEvidenceInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    if body.retrieved_at.tzinfo is None or body.retrieved_at > datetime.now(UTC):
        raise HTTPException(422, "evidence_timestamp_invalid")
    if len(body.evidence_excerpt.split()) > 25:
        raise HTTPException(422, "evidence_excerpt_exceeds_25_words")
    try:
        with _connect(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """SELECT candidate_status FROM knowledge.destination_candidates
                WHERE candidate_id=%s AND candidate_kind='destination_identity' FOR UPDATE""",
                (candidate_id,),
            )
            candidate = cur.fetchone()
            if candidate is None:
                raise HTTPException(404, "destination_candidate_not_found")
            if candidate["candidate_status"] not in {"needs_review", "in_review", "conflict"}:
                raise HTTPException(409, "candidate_already_resolved")
            cur.execute(
                """INSERT INTO knowledge.destination_candidate_evidence
                (candidate_id,source_id,field_key,claim_value,source_url,evidence_excerpt,
                 retrieved_at,reviewer_user_id,policy_version)
                SELECT %s,s.source_id,%s,%s,s.url,%s,%s,%s,%s
                FROM knowledge.knowledge_sources s
                WHERE s.source_id=%s AND s.verification_status='verified' AND s.is_synthetic=FALSE
                  AND s.url LIKE 'https://%%'
                RETURNING evidence_id,source_id,field_key,claim_value,source_url,evidence_excerpt,retrieved_at""",
                (candidate_id, body.field_key, body.claim_value.strip(), body.evidence_excerpt.strip(),
                 body.retrieved_at, user.user_id, body.policy_version, body.source_id),
            )
            evidence = cur.fetchone()
            if evidence is None:
                raise HTTPException(422, "evidence_requires_verified_https_source")
            return evidence
    except HTTPException:
        raise
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "candidate_evidence_already_recorded") from None
    except psycopg.errors.InsufficientPrivilege:
        raise HTTPException(403, "source_review_not_granted") from None
    except psycopg.Error:
        raise HTTPException(503, "candidate_evidence_unavailable") from None


@router.post("/candidates/{candidate_id}/publish", status_code=201)
def publish_candidate(
    candidate_id: UUID,
    body: PublishCandidateInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connect(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                "SELECT knowledge.publish_archive_destination(%s,%s,%s,%s,%s) AS destination_id",
                (candidate_id, body.destination_key, body.coordinate_role, user.user_id, body.policy_version),
            )
            result = cur.fetchone()
            cur.execute("SELECT destination_key FROM knowledge.destinations WHERE destination_id=%s", (result["destination_id"],))
            key_row = cur.fetchone()
            cur.execute("SELECT count(*) AS n FROM knowledge.production_destinations WHERE destination_id=%s", (result["destination_id"],))
            if int(cur.fetchone()["n"]) != 1:
                raise HTTPException(409, "destination_did_not_pass_production_view")
    except HTTPException:
        raise
    except psycopg.errors.InsufficientPrivilege:
        raise HTTPException(403, "catalogue_publish_not_granted") from None
    except psycopg.errors.RaiseException:
        raise HTTPException(422, "candidate_not_publishable") from None
    except psycopg.errors.UniqueViolation:
        raise HTTPException(409, "candidate_already_published_or_key_conflict") from None
    except psycopg.Error:
        raise HTTPException(503, "catalogue_publication_unavailable") from None
    return {"destination_id": result["destination_id"], "destination_key": key_row["destination_key"],
            "publication_status": "published", "published": True}
