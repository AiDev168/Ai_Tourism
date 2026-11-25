"""Organization-scoped private partner data-entry API; publication is not exposed."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID, uuid4

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.api.auth import authenticated_user, require_authenticated_csrf
from app.api.admin_guards import require_privileged_admin_step_up
from app.core.config import Settings, get_settings
from app.modules.identity.auth_service import AuthenticatedUser

router = APIRouter(prefix="/api/v1/partners", tags=["partner-workspace"])


class OrganizationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    legal_name: str = Field(min_length=1, max_length=240)
    display_name: str = Field(min_length=1, max_length=240)
    organization_type: Literal[
        "company", "individual_business", "nonprofit", "public_body", "other"
    ]
    registration_country: str = Field(default="IR", pattern=r"^[A-Z]{2}$")


class OrganizationUpdateInput(OrganizationInput):
    """Editable business profile fields; lifecycle state is never client-set."""


class OrganizationReviewSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence_refs: list[str] = Field(min_length=1, max_length=20)
    policy_version: str = Field(default="partner-verification-v1", min_length=1, max_length=80)

    @field_validator("evidence_refs")
    @classmethod
    def nonempty_refs(cls, values: list[str]) -> list[str]:
        refs = [value.strip() for value in values]
        if any(not value or len(value) > 1000 for value in refs) or len(refs) != len(set(refs)):
            raise ValueError("verification_evidence_refs_invalid")
        return refs


class OrganizationReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["verified", "needs_information", "rejected"]
    reason: str = Field(min_length=10, max_length=2000)

    @field_validator("reason")
    @classmethod
    def nonblank_review_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("review_reason_required")
        return value.strip()


class OrganizationApplicationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["approve", "reject"]
    reason: str = Field(min_length=10, max_length=2000)

    @field_validator("reason")
    @classmethod
    def nonblank_application_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("review_reason_required")
        return value.strip()


class OrganizationParticipationDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["activate", "deactivate", "suspend"]
    reason: str = Field(min_length=10, max_length=2000)

    @field_validator("reason")
    @classmethod
    def nonblank_participation_reason(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("review_reason_required")
        return value.strip()


def _require_platform_capability(cur, user: AuthenticatedUser, capability: str) -> None:
    allowed = cur.execute(
        "SELECT partner.has_platform_capability(%s,%s) AS allowed",
        (user.user_id, capability),
    ).fetchone()
    if not allowed or not allowed["allowed"]:
        raise HTTPException(status_code=403, detail="partner_review_not_granted")


class ServiceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service_type: str = Field(min_length=1, max_length=80)
    locale: Literal["fa-IR", "en-US", "ar"] = "fa-IR"
    display_name: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    branch_id: UUID | None = None


class ServiceUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service_type: str = Field(min_length=1, max_length=80)
    locale: Literal["fa-IR", "en-US", "ar"] = "fa-IR"
    display_name: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)


class ScheduleUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service_id: UUID
    schedule_type: Literal["opening_window", "departure", "appointment", "event", "other"]
    timezone: str | None = Field(default=None, max_length=80)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    recurrence: dict[str, object] | None = None
    observed_at: datetime | None = None
    valid_until: datetime | None = None


class OfferUpdateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service_id: UUID
    schedule_id: UUID | None = None
    offer_type: str = Field(min_length=1, max_length=80)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    capacity_limit: int | None = Field(default=None, ge=0)


class ServiceDestinationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destination_id: int = Field(ge=1)
    relation_type: Literal["at", "serves", "near", "route_endpoint"]
    evidence_note: str | None = Field(default=None, max_length=1000)


class ScheduleInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service_id: UUID
    schedule_type: Literal["opening_window", "departure", "appointment", "event", "other"]
    timezone: str | None = Field(default=None, max_length=80)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    recurrence: dict[str, object] | None = None
    observed_at: datetime | None = None
    valid_until: datetime | None = None


class OfferInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service_id: UUID
    schedule_id: UUID | None = None
    offer_type: str = Field(min_length=1, max_length=80)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    capacity_limit: int | None = Field(default=None, ge=0)


class PriceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    offer_id: UUID
    price_state: Literal["known", "unknown", "not_applicable", "conflicting"]
    amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    denomination: str | None = Field(default=None, max_length=80)
    unit: str | None = Field(default=None, max_length=80)
    tax_included: bool | None = None
    observed_at: datetime | None = None
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class AvailabilityInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    offer_id: UUID
    schedule_id: UUID
    occurrence_starts_at: datetime
    availability_state: Literal["available", "unavailable", "limited", "unknown", "not_applicable"]
    observed_at: datetime
    valid_from: datetime
    valid_until: datetime


class TravelerCompanyShareInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization_ids: list[UUID] = Field(default_factory=list, max_length=10)
    recipient_mode: Literal["selected", "all_eligible"] = "selected"
    consent_confirmed: Literal[True]
    # Extra, explicit opt-in for broad sharing. A selected-recipient consent
    # alone must never silently turn into a broadcast.
    broad_sharing_consent_confirmed: bool = False
    include_original_request: bool = False
    consent_policy_version: str = Field(default="company-request-share-v1", min_length=1, max_length=80)

    @field_validator("organization_ids")
    @classmethod
    def unique_recipients(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("recipient organizations must be unique")
        return value

    @model_validator(mode="after")
    def validate_recipient_mode(self):
        if self.recipient_mode == "selected" and not self.organization_ids:
            raise ValueError("select_at_least_one_company")
        if self.recipient_mode == "all_eligible":
            if self.organization_ids:
                raise ValueError("broadcast_must_not_include_named_recipients")
            if not self.broad_sharing_consent_confirmed:
                raise ValueError("broadcast_requires_explicit_consent")
            if self.include_original_request:
                raise ValueError("broadcast_cannot_include_original_request")
        return self


class CompanyTripResponseInput(BaseModel):
    """Response to an immutable, consented share revision; never edits the trip."""

    model_config = ConfigDict(extra="forbid")
    client_request_id: UUID
    revision_id: UUID
    response_kind: Literal["accepted_as_requested", "counter_offer"]
    message: str = Field(default="", max_length=2000)
    proposed_price_toman: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )
    proposed_start_date: date | None = None
    proposed_end_date: date | None = None
    proposed_schedule_notes: str = Field(default="", max_length=1500)

    @model_validator(mode="after")
    def validate_changes(self):
        dates = self.proposed_start_date is not None, self.proposed_end_date is not None
        if dates[0] != dates[1]:
            raise ValueError("proposed_dates_must_be_a_complete_range")
        if dates[0] and self.proposed_end_date < self.proposed_start_date:
            raise ValueError("proposed_end_must_not_precede_start")
        changed = (self.proposed_price_toman is not None or dates[0]
                   or bool(self.proposed_schedule_notes.strip()))
        if self.response_kind == "accepted_as_requested" and changed:
            raise ValueError("as_requested_cannot_change_price_or_schedule")
        if self.response_kind == "counter_offer" and not changed:
            raise ValueError("counter_offer_requires_a_specific_change")
        return self


class TravelerCompanyDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["accepted", "declined"]


def _connection(settings: Settings):
    return psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password.get_secret_value(),
        connect_timeout=settings.database_connect_timeout_seconds,
        application_name="rahgard-partner-self-service",
        row_factory=dict_row,
    )


def _db_error(error: psycopg.Error) -> None:
    if isinstance(error, psycopg.errors.InsufficientPrivilege):
        # In the guarded disposable acceptance only, include non-sensitive
        # PostgreSQL privilege diagnostics so RLS/GRANT regressions can be
        # distinguished without logging SQL, parameters, or traveler data.
        if __import__("os").environ.get("RAHGARD_NATIONAL_CATALOGUE_E2E") == "1":
            diag = getattr(error, "diag", None)
            object_name = ".".join(filter(None, (
                getattr(diag, "schema_name", None), getattr(diag, "table_name", None),
            )))
            primary = getattr(diag, "message_primary", "") or ""
            match = __import__("re").search(
                r'(?:table|relation|schema|sequence|function) "([A-Za-z0-9_.]+)"', primary,
            )
            if not object_name and match:
                object_name = match.group(1)
            if not __import__("re").fullmatch(r"[A-Za-z0-9_.]{1,128}", object_name or ""):
                object_name = "unknown_object"
            raise HTTPException(403, f"db_privilege_denied_{error.sqlstate or 'unknown'}_{object_name}") from None
        raise HTTPException(403, "organization_access_denied") from None
    if isinstance(
        error,
        (
            psycopg.errors.ForeignKeyViolation,
            psycopg.errors.CheckViolation,
            psycopg.errors.UniqueViolation,
        ),
    ):
        raise HTTPException(422, "partner_record_rejected") from None
    raise HTTPException(503, "partner_workspace_unavailable") from None


@router.get("/trips/{trip_id}/company-share-options")
def company_share_options(
    trip_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Return only verified, active companies; never expose traveler data here."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            trip = cur.execute(
                """SELECT confirmed_requirements,is_synthetic FROM travel.trips
                   WHERE trip_id=%s AND user_id=%s""", (trip_id, user.user_id),
            ).fetchone()
            if trip is None:
                raise HTTPException(404, "trip_not_found")
            if trip["is_synthetic"] or not isinstance(trip["confirmed_requirements"], dict) or not trip["confirmed_requirements"]:
                raise HTTPException(409, "review_trip_before_sharing")
            cur.execute(
                """SELECT organization_id,display_name,organization_type
                   FROM partner.share_eligible_organizations
                   ORDER BY display_name,organization_id LIMIT 100"""
            )
            items = cur.fetchall()
            cur.execute("SELECT count(*) AS total FROM partner.share_eligible_organizations")
            eligible_count = int(cur.fetchone()["total"])
            return {"items": items, "eligible_count": eligible_count,
                    "broadcast_limit": 500, "trip_id": trip_id,
                    "requires_explicit_consent": True}
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/trips/{trip_id}/company-shares", status_code=201)
def share_trip_with_companies(
    trip_id: UUID,
    body: TravelerCompanyShareInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Share a reviewed request with named eligible organizations after consent."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            trip = cur.execute(
                """SELECT confirmed_requirements,is_synthetic FROM travel.trips
                   WHERE trip_id=%s AND user_id=%s FOR UPDATE""", (trip_id, user.user_id),
            ).fetchone()
            if trip is None:
                raise HTTPException(404, "trip_not_found")
            if trip["is_synthetic"] or not isinstance(trip["confirmed_requirements"], dict) or not trip["confirmed_requirements"]:
                raise HTTPException(409, "review_trip_before_sharing")
            if body.recipient_mode == "all_eligible":
                # Cap before writing anything; avoid silently omitting recipients.
                # Only approved/verified/active organizations are included.
                cur.execute(
                    """SELECT organization_id FROM partner.share_eligible_organizations
                       ORDER BY organization_id LIMIT 501"""
                )
                recipient_ids = [row["organization_id"] for row in cur.fetchall()]
                if not recipient_ids:
                    raise HTTPException(409, "no_eligible_companies")
                if len(recipient_ids) > 500:
                    raise HTTPException(409, "too_many_eligible_companies")
            else:
                cur.execute(
                    """SELECT organization_id FROM partner.share_eligible_organizations
                       WHERE organization_id=ANY(%s)""",
                    (body.organization_ids,),
                )
                eligible = {row["organization_id"] for row in cur.fetchall()}
                if eligible != set(body.organization_ids):
                    raise HTTPException(422, "recipient_not_eligible")
                recipient_ids = body.organization_ids
            shares = []
            for organization_id in recipient_ids:
                cur.execute(
                    """INSERT INTO partner.traveler_request_shares
                       (trip_id,traveler_id,organization_id,consent_policy_version,include_original_request)
                       VALUES (%s,%s,%s,%s,%s)
                       ON CONFLICT (trip_id,organization_id) DO NOTHING
                       RETURNING share_id,organization_id,consented_at""",
                    (trip_id,user.user_id,organization_id,body.consent_policy_version,body.include_original_request),
                )
                created = cur.fetchone()
                if created is None:
                    cur.execute(
                        """SELECT share_id,organization_id,consented_at FROM partner.traveler_request_shares
                           WHERE trip_id=%s AND organization_id=%s AND traveler_id=%s AND revoked_at IS NULL""",
                        (trip_id,organization_id,user.user_id),
                    )
                    created = cur.fetchone()
                if created is None:
                    raise HTTPException(409, "share_revoked_requires_new_request")
                shares.append(created)
            return {"trip_id": trip_id, "shares": shares, "shared": True,
                    "recipient_mode": body.recipient_mode,
                    "recipient_count": len(shares),
                    "message": "Only consented eligible organizations can view this request in their protected inbox."}
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.get("/trips/{trip_id}/company-shares")
def list_trip_company_shares(
    trip_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """SELECT s.share_id,s.organization_id,COALESCE(o.display_name,s.organization_id::text) AS display_name,s.consented_at,s.revoked_at,
                          (SELECT MAX(r.revision_number) FROM partner.traveler_request_revisions r WHERE r.share_id=s.share_id) AS latest_revision
                   FROM partner.traveler_request_shares s LEFT JOIN partner.share_eligible_organizations o USING (organization_id)
                   WHERE s.trip_id=%s AND s.traveler_id=%s ORDER BY s.created_at""",
                (trip_id,user.user_id),
            )
            return {"items": cur.fetchall()}
    except psycopg.Error as exc:
        _db_error(exc)


@router.delete("/trips/{trip_id}/company-shares/{share_id}")
def revoke_trip_company_share(
    trip_id: UUID,
    share_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """UPDATE partner.traveler_request_shares SET revoked_at=COALESCE(revoked_at,now())
                   WHERE trip_id=%s AND share_id=%s AND traveler_id=%s RETURNING share_id""",
                (trip_id,share_id,user.user_id),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "share_not_found")
            return {"revoked": True}
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.get("/organizations/{organization_id}/requests")
def traveler_request_inbox(
    organization_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Organization-scoped inbox with immutable request/itinerary revisions."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """SELECT i.inbox_event_id,i.event_kind,i.created_at,i.viewed_at,
                          r.revision_id,r.share_id,r.revision_number,r.trip_version,
                          r.request_snapshot,r.itinerary_snapshot,r.created_at AS revision_created_at
                   FROM partner.traveler_request_inbox i
                   JOIN partner.traveler_request_revisions r USING (revision_id,organization_id)
                   WHERE i.organization_id=%s AND NOT r.is_synthetic
                   ORDER BY i.created_at DESC,r.revision_number DESC LIMIT 200""",
                (organization_id,),
            )
            return {"items": cur.fetchall()}
    except psycopg.Error as exc:
        _db_error(exc)


@router.get("/organizations/{organization_id}/requests/{share_id}/revisions")
def traveler_request_revisions(
    organization_id: UUID,
    share_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """SELECT revision_id,share_id,revision_number,trip_version,event_kind,
                          request_snapshot,itinerary_snapshot,created_at
                   FROM partner.traveler_request_revisions
                   WHERE organization_id=%s AND share_id=%s AND NOT is_synthetic
                   ORDER BY revision_number DESC LIMIT 100""",
                (organization_id,share_id),
            )
            return {"items": cur.fetchall()}
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/organizations/{organization_id}/requests/{inbox_event_id}/viewed")
def mark_traveler_request_viewed(
    organization_id: UUID,
    inbox_event_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """UPDATE partner.traveler_request_inbox SET viewed_at=COALESCE(viewed_at,now())
                   WHERE organization_id=%s AND inbox_event_id=%s RETURNING inbox_event_id""",
                (organization_id,inbox_event_id),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "request_not_found")
            return {"viewed": True}
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.get("/organizations")
def organizations(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                "SELECT organization_id,legal_name,display_name,organization_type,registration_country,verification_status,participation_status,application_status,created_at,updated_at FROM partner.organizations ORDER BY created_at DESC LIMIT 100"
            )
            return {"items": cur.fetchall()}
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/organizations", status_code=201)
def create_organization(
    body: OrganizationInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """INSERT INTO partner.organizations(legal_name,display_name,organization_type,registration_country,created_by)
                VALUES (%s,%s,%s,%s,%s) RETURNING organization_id,display_name,application_status""",
                (
                    body.legal_name.strip(),
                    body.display_name.strip(),
                    body.organization_type,
                    body.registration_country,
                    user.user_id,
                ),
            )
            row = cur.fetchone()
            cur.execute(
                "INSERT INTO partner.memberships(organization_id,user_id,role,status,accepted_at) VALUES (%s,%s,'owner','active',now())",
                (row["organization_id"], user.user_id),
            )
            return row
    except psycopg.Error as exc:
        _db_error(exc)


@router.put("/organizations/{organization_id}")
def update_organization(
    organization_id: UUID,
    body: OrganizationUpdateInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Edit only profile fields; lifecycle and verification remain reviewer-owned."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """UPDATE partner.organizations SET legal_name=%s,display_name=%s,
                          organization_type=%s,registration_country=%s,updated_at=now()
                   WHERE organization_id=%s RETURNING organization_id,legal_name,display_name,
                         organization_type,registration_country,application_status,
                         verification_status,participation_status,updated_at""",
                (body.legal_name.strip(), body.display_name.strip(), body.organization_type,
                 body.registration_country, organization_id),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="organization_not_found")
            return row
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/organizations/{organization_id}/verification-cases", status_code=201)
def submit_organization_for_review(
    organization_id: UUID,
    body: OrganizationReviewSubmission,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Company owner submits evidence; this does not verify or activate it."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            org = cur.execute(
                """SELECT organization_id,created_by,application_status,verification_status
                   FROM partner.organizations WHERE organization_id=%s FOR UPDATE""",
                (organization_id,),
            ).fetchone()
            if org is None:
                raise HTTPException(status_code=404, detail="organization_not_found")
            if org["created_by"] != user.user_id:
                raise HTTPException(status_code=403, detail="organization_owner_required")
            if org["verification_status"] == "verified":
                raise HTTPException(status_code=409, detail="organization_already_verified")
            if org["application_status"] not in {"draft", "needs_information", "withdrawn", "rejected"}:
                raise HTTPException(status_code=409, detail="organization_review_already_pending")
            cur.execute(
                """INSERT INTO partner.verification_cases
                     (organization_id,status,evidence_refs,submitted_by,policy_version,submitted_at)
                   VALUES (%s,'submitted',%s,%s,%s,now())
                   RETURNING case_id,organization_id,status,submitted_at""",
                (organization_id, Jsonb(body.evidence_refs), user.user_id, body.policy_version),
            )
            case = cur.fetchone()
            cur.execute(
                """UPDATE partner.organizations SET application_status='submitted',updated_at=now()
                   WHERE organization_id=%s""",
                (organization_id,),
            )
            return {**case, "verification_status": org["verification_status"],
                    "participation_status": "inactive"}
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.get("/platform/organization-review")
def organization_review_queue(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Private reviewer queue; capability comes only from operator grant state."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            _require_platform_capability(cur, user, "organization_review")
            cur.execute(
                """WITH latest_case AS (
                       SELECT DISTINCT ON (organization_id)
                              case_id,organization_id,status,evidence_refs,submitted_at,
                              policy_version,submitted_by,created_at
                       FROM partner.verification_cases
                       ORDER BY organization_id, submitted_at DESC NULLS LAST,
                                created_at DESC, case_id DESC
                   )
                   SELECT c.case_id,c.organization_id,c.status AS case_status,
                          c.evidence_refs,c.submitted_at,c.policy_version,
                          o.legal_name,o.display_name,o.organization_type,
                          o.registration_country,o.created_by,o.application_status,
                          o.verification_status,o.participation_status
                   FROM latest_case c
                   JOIN partner.organizations o USING (organization_id)
                   WHERE c.status IN ('submitted','needs_information','verified')
                     AND o.application_status IN ('submitted','approved')
                   ORDER BY c.submitted_at,c.case_id LIMIT 100"""
            )
            return {"items": cur.fetchall()}
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.get("/platform/review-events")
def platform_review_events(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    limit: int = Query(default=50, ge=1, le=100),
):
    """Read recent company governance audit history for explicit reviewers."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            _require_platform_capability(cur, user, "organization_review")
            cur.execute(
                """SELECT o.display_name,e.entity_type,e.decision,e.reason,
                          e.policy_version,e.occurred_at
                   FROM partner.review_events e
                   JOIN partner.organizations o USING (organization_id)
                   ORDER BY e.occurred_at DESC,e.review_event_id DESC LIMIT %s""",
                (limit,),
            )
            return {"items": cur.fetchall()}
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/platform/verification-cases/{case_id}/decision")
def decide_organization_verification(
    case_id: UUID,
    body: OrganizationReviewDecision,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Record evidence review separately from application approval/activation."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            _require_platform_capability(cur, user, "organization_review")
            require_privileged_admin_step_up(settings, user)
            case = cur.execute(
                """SELECT c.case_id,c.organization_id,c.submitted_by,c.status,
                          o.created_by,o.application_status,o.verification_status
                   FROM partner.verification_cases c JOIN partner.organizations o USING(organization_id)
                   WHERE c.case_id=%s FOR UPDATE OF c,o""",
                (case_id,),
            ).fetchone()
            if case is None:
                raise HTTPException(status_code=404, detail="verification_case_not_found")
            if case["submitted_by"] == user.user_id or case["created_by"] == user.user_id:
                raise HTTPException(status_code=403, detail="self_review_forbidden")
            if case["status"] not in {"submitted", "needs_information"}:
                raise HTTPException(status_code=409, detail="verification_case_not_reviewable")
            next_status = body.decision
            cur.execute(
                """UPDATE partner.verification_cases
                   SET status=%s,reviewer_user_id=%s,decision_reason=%s,decided_at=now()
                   WHERE case_id=%s RETURNING case_id,organization_id,status,reviewer_user_id,decided_at""",
                (next_status, user.user_id, body.reason, case_id),
            )
            result = cur.fetchone()
            if body.decision == "verified":
                cur.execute(
                    """UPDATE partner.organizations SET verification_status='verified',updated_at=now()
                       WHERE organization_id=%s""", (case["organization_id"],),
                )
            elif body.decision == "needs_information":
                cur.execute(
                    """UPDATE partner.organizations SET application_status='needs_information',updated_at=now()
                       WHERE organization_id=%s""", (case["organization_id"],),
                )
            else:
                cur.execute(
                    """UPDATE partner.organizations SET verification_status='rejected',
                              application_status='rejected',participation_status='inactive',updated_at=now()
                       WHERE organization_id=%s""", (case["organization_id"],),
                )
            audit_decision = {"verified": "approve", "needs_information": "request_changes", "rejected": "reject"}[body.decision]
            cur.execute(
                """INSERT INTO partner.review_events
                     (organization_id,entity_type,entity_id,decision,reviewer_user_id,reason,policy_version)
                   VALUES (%s,'verification_case',%s,%s,%s,%s,'partner-verification-v1')""",
                (case["organization_id"], case_id, audit_decision, user.user_id, body.reason),
            )
            return result
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/platform/organizations/{organization_id}/application-decision")
def decide_organization_application(
    organization_id: UUID,
    body: OrganizationApplicationDecision,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Application approval is a distinct transition after verification."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            _require_platform_capability(cur, user, "organization_review")
            require_privileged_admin_step_up(settings, user)
            org = cur.execute(
                """SELECT organization_id,created_by,verification_status,application_status
                   FROM partner.organizations WHERE organization_id=%s FOR UPDATE""",
                (organization_id,),
            ).fetchone()
            if org is None:
                raise HTTPException(status_code=404, detail="organization_not_found")
            if org["created_by"] == user.user_id:
                raise HTTPException(status_code=403, detail="self_review_forbidden")
            if org["application_status"] != "submitted":
                raise HTTPException(status_code=409, detail="organization_application_not_submitted")
            if body.decision == "approve" and org["verification_status"] != "verified":
                raise HTTPException(status_code=409, detail="organization_not_verified")
            next_state = "approved" if body.decision == "approve" else "rejected"
            cur.execute(
                """UPDATE partner.organizations SET application_status=%s,
                          participation_status=CASE WHEN %s='rejected' THEN 'inactive' ELSE participation_status END,
                          updated_at=now() WHERE organization_id=%s
                   RETURNING organization_id,application_status,verification_status,participation_status""",
                (next_state, next_state, organization_id),
            )
            result = cur.fetchone()
            cur.execute(
                """INSERT INTO partner.review_events
                     (organization_id,entity_type,entity_id,decision,reviewer_user_id,reason,policy_version)
                   VALUES (%s,'organization',%s,%s,%s,%s,'partner-application-v1')""",
                (organization_id, organization_id, body.decision, user.user_id, body.reason),
            )
            return result
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/platform/organizations/{organization_id}/participation-decision")
def decide_organization_participation(
    organization_id: UUID,
    body: OrganizationParticipationDecision,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Activate/deactivate/suspend sharing eligibility with a separate audit."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            _require_platform_capability(cur, user, "organization_review")
            require_privileged_admin_step_up(settings, user)
            org = cur.execute(
                """SELECT organization_id,created_by,verification_status,application_status,participation_status
                   FROM partner.organizations WHERE organization_id=%s FOR UPDATE""",
                (organization_id,),
            ).fetchone()
            if org is None:
                raise HTTPException(status_code=404, detail="organization_not_found")
            if org["created_by"] == user.user_id:
                raise HTTPException(status_code=403, detail="self_review_forbidden")
            if body.decision == "activate" and not (
                org["verification_status"] == "verified" and org["application_status"] == "approved"
            ):
                raise HTTPException(status_code=409, detail="organization_must_be_verified_and_approved")
            next_state = {"activate": "active", "deactivate": "inactive", "suspend": "suspended"}[body.decision]
            cur.execute(
                """UPDATE partner.organizations SET participation_status=%s,updated_at=now()
                   WHERE organization_id=%s RETURNING organization_id,application_status,verification_status,participation_status""",
                (next_state, organization_id),
            )
            result = cur.fetchone()
            cur.execute(
                """INSERT INTO partner.review_events
                     (organization_id,entity_type,entity_id,decision,reviewer_user_id,reason,policy_version)
                   VALUES (%s,'organization',%s,%s,%s,%s,'partner-participation-v1')""",
                (organization_id, organization_id, body.decision, user.user_id, body.reason),
            )
            return result
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/organizations/{organization_id}/services", status_code=201)
def create_service(
    organization_id: UUID,
    body: ServiceInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """INSERT INTO partner.services(organization_id,branch_id,service_type,service_key,created_by)
                VALUES (%s,%s,%s,%s,%s) RETURNING service_id,status""",
                (
                    organization_id,
                    body.branch_id,
                    body.service_type.strip(),
                    f"service-{uuid4().hex}",
                    user.user_id,
                ),
            )
            row = cur.fetchone()
            cur.execute(
                "INSERT INTO partner.service_localizations(organization_id,service_id,locale,display_name,description) VALUES (%s,%s,%s,%s,%s)",
                (
                    organization_id,
                    row["service_id"],
                    body.locale,
                    body.display_name.strip(),
                    body.description,
                ),
            )
            return row
    except psycopg.Error as exc:
        _db_error(exc)


@router.put("/organizations/{organization_id}/services/{service_id}")
def update_service(
    organization_id: UUID,
    service_id: UUID,
    body: ServiceUpdateInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Update a private, unapproved service and its current locale content."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """UPDATE partner.services SET service_type=%s,updated_at=now()
                   WHERE organization_id=%s AND service_id=%s
                   RETURNING service_id,status""",
                (body.service_type.strip(), organization_id, service_id),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="service_not_found")
            cur.execute(
                """INSERT INTO partner.service_localizations
                     (organization_id,service_id,locale,display_name,description)
                   VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (service_id,locale) DO UPDATE SET
                     display_name=EXCLUDED.display_name,description=EXCLUDED.description,updated_at=now()""",
                (organization_id, service_id, body.locale, body.display_name.strip(), body.description),
            )
            return row
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/organizations/{organization_id}/schedules", status_code=201)
def create_schedule(
    organization_id: UUID,
    body: ScheduleInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """INSERT INTO partner.schedules(organization_id,service_id,schedule_type,timezone,starts_at,ends_at,recurrence,observed_at,valid_until)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s) RETURNING schedule_id,status""",
                (
                    organization_id,
                    body.service_id,
                    body.schedule_type,
                    body.timezone,
                    body.starts_at,
                    body.ends_at,
                    Jsonb(body.recurrence) if body.recurrence is not None else None,
                    body.observed_at,
                    body.valid_until,
                ),
            )
            return cur.fetchone()
    except psycopg.Error as exc:
        _db_error(exc)


@router.put("/organizations/{organization_id}/schedules/{schedule_id}")
def update_schedule(
    organization_id: UUID,
    schedule_id: UUID,
    body: ScheduleUpdateInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """UPDATE partner.schedules SET service_id=%s,schedule_type=%s,timezone=%s,
                          starts_at=%s,ends_at=%s,recurrence=%s::jsonb,observed_at=%s,
                          valid_until=%s
                   WHERE organization_id=%s AND schedule_id=%s
                   RETURNING schedule_id,service_id,status""",
                (body.service_id, body.schedule_type, body.timezone, body.starts_at, body.ends_at,
                 Jsonb(body.recurrence) if body.recurrence is not None else None,
                 body.observed_at, body.valid_until, organization_id, schedule_id),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="schedule_not_found")
            return row
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.get("/organizations/{organization_id}/workspace")
def workspace(
    organization_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    locale: Literal["fa-IR", "en-US", "ar"] = Query(default="fa-IR"),
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            result = {}
            for name, sql in {
                "services": "SELECT s.service_id,s.service_type,s.status,l.display_name,l.description FROM partner.services s LEFT JOIN partner.service_localizations l ON l.organization_id=s.organization_id AND l.service_id=s.service_id AND l.locale=%s WHERE s.organization_id=%s ORDER BY s.created_at DESC LIMIT 100",
                "schedules": "SELECT schedule_id,service_id,schedule_type,timezone,starts_at,ends_at,status,observed_at,valid_until FROM partner.schedules WHERE organization_id=%s ORDER BY created_at DESC LIMIT 200",
                "offers": "SELECT offer_id,service_id,schedule_id,offer_type,status,valid_from,valid_until,capacity_limit FROM partner.offers WHERE organization_id=%s ORDER BY created_at DESC LIMIT 200",
                "prices": "SELECT price_id,offer_id,price_state,amount,currency,denomination,unit,observed_at,valid_until FROM partner.prices WHERE organization_id=%s ORDER BY created_at DESC LIMIT 200",
                "availability": "SELECT snapshot_id,offer_id,schedule_id,occurrence_starts_at,availability_state,observed_at,valid_until FROM partner.availability_snapshots WHERE organization_id=%s ORDER BY created_at DESC LIMIT 200",
                # The partner app role intentionally has no direct read grant on
                # canonical storage. The publication view is the authorized
                # source for destination details in the private workspace too.
                "destinations": "SELECT sd.service_id,sd.destination_id,sd.relation_type,sd.status,d.canonical_name,d.province_name,d.city_name FROM partner.service_destinations sd JOIN knowledge.production_destinations d USING(destination_id) WHERE sd.organization_id=%s ORDER BY sd.created_at DESC LIMIT 200",
            }.items():
                cur.execute(sql, (locale, organization_id) if name == "services" else (organization_id,))
                result[name] = cur.fetchall()
            return result
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/organizations/{organization_id}/services/{service_id}/destinations", status_code=201)
def associate_published_destination(
    organization_id: UUID,
    service_id: UUID,
    body: ServiceDestinationInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Link a private draft service only to a currently published canonical POI."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                "SELECT 1 FROM knowledge.production_destinations WHERE destination_id=%s",
                (body.destination_id,),
            )
            if cur.fetchone() is None:
                raise HTTPException(422, "destination_not_published")
            cur.execute(
                """INSERT INTO partner.service_destinations
                (organization_id,service_id,destination_id,relation_type,evidence_note)
                VALUES (%s,%s,%s,%s,%s) RETURNING service_id,destination_id,relation_type,status""",
                (
                    organization_id,
                    service_id,
                    body.destination_id,
                    body.relation_type,
                    body.evidence_note,
                ),
            )
            return cur.fetchone()
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/organizations/{organization_id}/offers", status_code=201)
def create_offer(
    organization_id: UUID,
    body: OfferInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """INSERT INTO partner.offers(organization_id,service_id,schedule_id,offer_type,valid_from,valid_until,capacity_limit,created_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING offer_id,status""",
                (
                    organization_id,
                    body.service_id,
                    body.schedule_id,
                    body.offer_type.strip(),
                    body.valid_from,
                    body.valid_until,
                    body.capacity_limit,
                    user.user_id,
                ),
            )
            return cur.fetchone()
    except psycopg.Error as exc:
        _db_error(exc)


@router.put("/organizations/{organization_id}/offers/{offer_id}")
def update_offer(
    organization_id: UUID,
    offer_id: UUID,
    body: OfferUpdateInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """UPDATE partner.offers SET service_id=%s,schedule_id=%s,offer_type=%s,
                          valid_from=%s,valid_until=%s,capacity_limit=%s,updated_at=now()
                   WHERE organization_id=%s AND offer_id=%s
                   RETURNING offer_id,service_id,schedule_id,status""",
                (body.service_id, body.schedule_id, body.offer_type.strip(), body.valid_from,
                 body.valid_until, body.capacity_limit, organization_id, offer_id),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="offer_not_found")
            return row
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/organizations/{organization_id}/prices", status_code=201)
def create_price(
    organization_id: UUID,
    body: PriceInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    if body.price_state == "known" and any(
        v is None
        for v in (body.amount, body.currency, body.denomination, body.unit, body.observed_at)
    ):
        raise HTTPException(422, "known_price_requires_currency_unit_and_observation")
    if body.price_state != "known" and any(
        v is not None
        for v in (body.amount, body.currency, body.denomination, body.unit, body.tax_included)
    ):
        raise HTTPException(422, "unknown_price_must_not_claim_amount")
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """INSERT INTO partner.prices(organization_id,offer_id,price_state,amount,currency,denomination,unit,tax_included,observed_at,valid_from,valid_until,source_kind)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'partner_asserted') RETURNING price_id,price_state,observed_at""",
                (
                    organization_id,
                    body.offer_id,
                    body.price_state,
                    body.amount,
                    body.currency,
                    body.denomination,
                    body.unit,
                    body.tax_included,
                    body.observed_at,
                    body.valid_from,
                    body.valid_until,
                ),
            )
            return cur.fetchone()
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/organizations/{organization_id}/availability", status_code=201)
def create_availability(
    organization_id: UUID,
    body: AvailabilityInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """INSERT INTO partner.availability_snapshots(organization_id,offer_id,schedule_id,occurrence_starts_at,availability_state,observed_at,valid_from,valid_until,created_by,source_kind)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,'partner_asserted') RETURNING snapshot_id,availability_state,observed_at,valid_until""",
                (
                    organization_id,
                    body.offer_id,
                    body.schedule_id,
                    body.occurrence_starts_at,
                    body.availability_state,
                    body.observed_at,
                    body.valid_from,
                    body.valid_until,
                    user.user_id,
                ),
            )
            return cur.fetchone()
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/organizations/{organization_id}/requests/{share_id}/responses", status_code=201)
def submit_company_trip_response(
    organization_id: UUID,
    share_id: UUID,
    body: CompanyTripResponseInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Submit an authenticated accept-as-requested or a counter-offer.

    A company cannot modify traveler records; it may only respond to a specific
    immutable revision that the traveler actually shared with its organization.
    Delivery is the authenticated in-app traveler response inbox, not SMS/email.
    """
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """SELECT s.trip_id,s.traveler_id FROM partner.traveler_request_shares s
                   WHERE s.share_id=%s AND s.organization_id=%s AND s.revoked_at IS NULL
                   AND EXISTS (SELECT 1 FROM partner.share_eligible_organizations e
                               WHERE e.organization_id=s.organization_id)
                   AND EXISTS (SELECT 1 FROM partner.memberships m
                               WHERE m.organization_id=s.organization_id
                                 AND m.user_id=%s AND m.status='active'
                                 AND m.role IN ('owner','manager','editor'))""",
                (share_id, organization_id, user.user_id),
            )
            shared = cur.fetchone()
            if shared is None:
                raise HTTPException(403, "company_share_access_denied")
            cur.execute(
                """SELECT revision_id FROM partner.traveler_request_revisions
                   WHERE share_id=%s AND organization_id=%s
                   ORDER BY revision_number DESC LIMIT 1""",
                (share_id, organization_id),
            )
            latest = cur.fetchone()
            if latest is None or latest["revision_id"] != body.revision_id:
                raise HTTPException(409, "company_share_revision_stale")
            cur.execute(
                """INSERT INTO partner.trip_company_responses
                   (client_request_id,share_id,organization_id,revision_id,trip_id,
                    traveler_id,submitted_by,response_kind,message,proposed_price_toman,
                    proposed_start_date,proposed_end_date,proposed_schedule_notes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON CONFLICT (share_id,client_request_id) DO NOTHING
                   RETURNING response_id,response_kind,traveler_decision,created_at""",
                (body.client_request_id,share_id,organization_id,body.revision_id,
                 shared["trip_id"],shared["traveler_id"],user.user_id,
                 body.response_kind,body.message,body.proposed_price_toman,
                 body.proposed_start_date,body.proposed_end_date,body.proposed_schedule_notes),
            )
            created = cur.fetchone()
            if created is None:
                cur.execute(
                    """SELECT response_id,response_kind,revision_id,traveler_decision,created_at,
                              message,proposed_price_toman,proposed_start_date,
                              proposed_end_date,proposed_schedule_notes,submitted_by
                       FROM partner.trip_company_responses
                       WHERE share_id=%s AND client_request_id=%s""",
                    (share_id,body.client_request_id),
                )
                created = cur.fetchone()
                if (created is None
                    or created["revision_id"] != body.revision_id
                    or created["response_kind"] != body.response_kind
                    or created["message"] != body.message
                    or created["proposed_price_toman"] != body.proposed_price_toman
                    or created["proposed_start_date"] != body.proposed_start_date
                    or created["proposed_end_date"] != body.proposed_end_date
                    or created["proposed_schedule_notes"] != body.proposed_schedule_notes
                    or created["submitted_by"] != user.user_id):
                    raise HTTPException(409, "company_response_idempotency_conflict")
            return {"response": created, "delivery_channel": "authenticated_traveler_inbox",
                    "contract_status": "nonbinding_proposal_or_confirmation" }
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)


@router.get("/organizations/{organization_id}/requests/{share_id}/responses")
def company_trip_responses(
    organization_id: UUID,
    share_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """SELECT response_id,revision_id,response_kind,message,proposed_price_toman,
                          proposed_start_date,proposed_end_date,proposed_schedule_notes,
                          traveler_decision,created_at,decided_at
                   FROM partner.trip_company_responses
                   WHERE share_id=%s AND organization_id=%s ORDER BY created_at DESC LIMIT 100""",
                (share_id,organization_id),
            )
            return {"items":cur.fetchall()}
    except psycopg.Error as exc:
        _db_error(exc)


@router.get("/trips/{trip_id}/company-responses")
def traveler_company_responses(
    trip_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Traveler can review persistent private replies, including past revisions."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """SELECT r.response_id,r.organization_id,COALESCE(o.display_name,r.organization_id::text) AS display_name,r.share_id,r.revision_id,
                          r.response_kind,r.message,r.proposed_price_toman,r.proposed_start_date,
                          r.proposed_end_date,r.proposed_schedule_notes,r.traveler_decision,
                          r.created_at,r.decided_at
                   FROM partner.trip_company_responses r
                   LEFT JOIN partner.share_eligible_organizations o USING (organization_id)
                   WHERE r.trip_id=%s AND r.traveler_id=%s
                   ORDER BY r.created_at DESC LIMIT 200""",
                (trip_id,user.user_id),
            )
            return {"items":cur.fetchall()}
    except psycopg.Error as exc:
        _db_error(exc)


@router.post("/trips/{trip_id}/company-responses/{response_id}/decision")
def decide_company_response(
    trip_id: UUID,
    response_id: UUID,
    body: TravelerCompanyDecisionInput,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Traveler accepts/declines one current proposal; does not auto-edit itinerary."""
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                """UPDATE partner.trip_company_responses r
                   SET traveler_decision=%s,decided_at=now()
                   WHERE r.response_id=%s AND r.trip_id=%s AND r.traveler_id=%s
                     AND r.traveler_decision='pending'
                     AND EXISTS (
                       SELECT 1 FROM partner.traveler_request_shares s
                       WHERE s.share_id=r.share_id AND s.revoked_at IS NULL)
                     AND r.revision_id=(
                       SELECT rv.revision_id FROM partner.traveler_request_revisions rv
                       WHERE rv.share_id=r.share_id ORDER BY rv.revision_number DESC LIMIT 1)
                   RETURNING r.response_id,r.traveler_decision,r.decided_at""",
                (body.decision,response_id,trip_id,user.user_id),
            )
            result = cur.fetchone()
            if result is None:
                raise HTTPException(409, "company_response_decision_unavailable_or_stale")
            return result
    except HTTPException:
        raise
    except psycopg.Error as exc:
        _db_error(exc)
