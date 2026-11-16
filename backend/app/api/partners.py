"""Organization-scoped private partner data-entry API; publication is not exposed."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import authenticated_user, require_authenticated_csrf
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


class ServiceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service_type: str = Field(min_length=1, max_length=80)
    service_key: str = Field(min_length=1, max_length=160, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    locale: Literal["fa-IR", "en-US", "ar"] = "fa-IR"
    display_name: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    branch_id: UUID | None = None


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


@router.get("/organizations")
def organizations(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            cur.execute(
                "SELECT organization_id,display_name,organization_type,verification_status,participation_status,application_status FROM partner.organizations ORDER BY created_at DESC LIMIT 100"
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
                    body.service_key,
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


@router.get("/organizations/{organization_id}/workspace")
def workspace(
    organization_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            result = {}
            for name, sql in {
                "services": "SELECT service_id,service_key,service_type,status,public_fields FROM partner.services WHERE organization_id=%s ORDER BY created_at DESC LIMIT 100",
                "schedules": "SELECT schedule_id,service_id,schedule_type,timezone,starts_at,ends_at,status,observed_at,valid_until FROM partner.schedules WHERE organization_id=%s ORDER BY created_at DESC LIMIT 200",
                "offers": "SELECT offer_id,service_id,schedule_id,offer_type,status,valid_from,valid_until,capacity_limit FROM partner.offers WHERE organization_id=%s ORDER BY created_at DESC LIMIT 200",
                "prices": "SELECT price_id,offer_id,price_state,amount,currency,denomination,unit,observed_at,valid_until FROM partner.prices WHERE organization_id=%s ORDER BY created_at DESC LIMIT 200",
                "availability": "SELECT snapshot_id,offer_id,schedule_id,occurrence_starts_at,availability_state,observed_at,valid_until FROM partner.availability_snapshots WHERE organization_id=%s ORDER BY created_at DESC LIMIT 200",
            }.items():
                cur.execute(sql, (organization_id,))
                result[name] = cur.fetchall()
            return result
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
