"""Capability-driven, read-only owner control-center overview.

Company and catalogue decisions remain on their existing APIs, which retain
their own database capability checks and audit records. This router exposes
only the sections the authenticated actor is explicitly granted to see.
"""

from __future__ import annotations

import os
import re
from typing import Annotated

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from psycopg.rows import dict_row

from app.api.auth import authenticated_user
from app.api.admin_guards import privileged_admin_writes_available
from app.api.platform_admin_mfa import platform_mfa_status
from app.core.config import Settings, get_settings
from app.modules.identity.auth_service import AuthenticatedUser

router = APIRouter(prefix="/api/v1/admin", tags=["owner-control-center"])

PARTNER_CAPABILITIES = ("organization_review", "service_review", "offer_review")
CATALOGUE_CAPABILITIES = ("candidate_review", "source_review", "catalogue_publish")
_SHA = re.compile(r"^[0-9a-f]{40}$")


def _connection(settings: Settings):
    return psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password.get_secret_value(),
        connect_timeout=settings.database_connect_timeout_seconds,
        application_name="rahgard-admin-control-center",
        row_factory=dict_row,
    )


def _capabilities(cur, actor_id) -> dict[str, bool]:
    partner = {
        key: bool(value)
        for key, value in cur.execute(
            """SELECT
                partner.has_platform_capability(%s,'organization_review') AS company_review,
                partner.has_platform_capability(%s,'service_review') AS service_review,
                partner.has_platform_capability(%s,'offer_review') AS offer_review,
                partner.has_platform_capability(%s,'admin_overview_read') AS admin_overview""",
            (actor_id, actor_id, actor_id, actor_id),
        ).fetchone().items()
    }
    catalogue = {
        key: bool(value)
        for key, value in cur.execute(
            """SELECT
                identity.has_catalogue_review_capability(%s,'candidate_review') AS candidate_review,
                identity.has_catalogue_review_capability(%s,'source_review') AS source_review,
                identity.has_catalogue_review_capability(%s,'catalogue_publish') AS catalogue_publish""",
            (actor_id, actor_id, actor_id),
        ).fetchone().items()
    }
    provider = cur.execute(
        "SELECT identity.has_ai_provider_admin_capability(%s) AS ai_provider_admin",
        (actor_id,),
    ).fetchone()
    return {**partner, **catalogue, "ai_provider_admin": bool(provider["ai_provider_admin"])}


def _load_capabilities(settings: Settings, actor_id) -> dict[str, bool]:
    with _connection(settings) as conn, conn.cursor() as cur:
        cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(actor_id),))
        return _capabilities(cur, actor_id)


@router.get("/capabilities")
def admin_capabilities(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        capabilities = _load_capabilities(settings, user.user_id)
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="admin_capabilities_unavailable") from None
    sections = {
        "companies": any(capabilities[key] for key in ("company_review", "service_review", "offer_review")),
        "destinations": any(capabilities[key] for key in CATALOGUE_CAPABILITIES),
        "users": capabilities["admin_overview"],
        "system": capabilities["admin_overview"],
        "ai_providers": capabilities["ai_provider_admin"],
    }
    if not any(sections.values()):
        raise HTTPException(status_code=403, detail="admin_capability_required")
    if privileged_admin_writes_available(settings.app_env):
        mfa = {"available": True, "required": False, "enrolled": False, "step_up_expires_at": None}
    else:
        mfa = platform_mfa_status(settings, user)
    privileged_writes = bool(
        privileged_admin_writes_available(settings.app_env)
        or (mfa["available"] and mfa["step_up_expires_at"] is not None)
    )
    return {
        "sections": sections,
        "company_capabilities": {
            "organization_review": capabilities["company_review"],
            "service_review": capabilities["service_review"],
            "offer_review": capabilities["offer_review"],
        },
        "catalogue_capabilities": {
            key: capabilities[key] for key in CATALOGUE_CAPABILITIES
        },
        "privileged_writes_available": privileged_writes,
        "privileged_step_up": mfa,
        # Provider administration is visible only with its independent grant.
        # Its own API still enforces server configuration, HTTPS session,
        # shared platform MFA step-up and provider-specific capability checks.
        "ai_admin": {
            "authorized": capabilities["ai_provider_admin"],
            "available": capabilities["ai_provider_admin"] and settings.ai_provider_admin_enabled,
            "scope": "server" if settings.ai_provider_admin_enabled else "server_not_configured",
        },
    }


@router.get("/overview")
def admin_overview(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            capabilities = _capabilities(cur, user.user_id)
            if not any((
                capabilities["company_review"], capabilities["service_review"],
                capabilities["offer_review"], capabilities["candidate_review"],
                capabilities["source_review"], capabilities["catalogue_publish"],
                capabilities["admin_overview"], capabilities["ai_provider_admin"],
            )):
                raise HTTPException(status_code=403, detail="admin_capability_required")

            result: dict[str, object] = {
                "release": {"commit": "unavailable"},
                "ai_admin": {
                    "authorized": capabilities["ai_provider_admin"],
                    "available": capabilities["ai_provider_admin"] and settings.ai_provider_admin_enabled,
                    "scope": "server" if settings.ai_provider_admin_enabled else "server_not_configured",
                },
            }
            commit = os.environ.get("RAHGARD_RELEASE_COMMIT", "").strip().lower()
            if _SHA.fullmatch(commit):
                result["release"] = {"commit": commit}

            if capabilities["admin_overview"]:
                db = cur.execute(
                    """SELECT current_setting('server_version_num')::integer AS server_version_num,
                              (SELECT count(*) FROM system.schema_migrations) AS migration_count,
                              (SELECT max(migration_id) FROM system.schema_migrations) AS latest_migration"""
                ).fetchone()
                users = cur.execute("SELECT count(*) AS count FROM identity.users").fetchone()
                companies = cur.execute(
                    """SELECT count(*) AS total,
                              count(*) FILTER (WHERE application_status='submitted') AS awaiting_application,
                              count(*) FILTER (WHERE verification_status='pending') AS awaiting_verification
                       FROM partner.organizations"""
                ).fetchone()
                destinations = cur.execute(
                    "SELECT count(*) AS count FROM knowledge.production_destinations"
                ).fetchone()
                eligible = cur.execute(
                    "SELECT count(*) AS count FROM partner.share_eligible_organizations"
                ).fetchone()
                result["system"] = {
                    "api": "responding",
                    "database": "connected",
                    "postgres_major": int(db["server_version_num"]) // 10000,
                    "migration_count": int(db["migration_count"]),
                    "latest_migration": db["latest_migration"],
                    "backup_evidence": "not_available_from_application",
                }
                result["users"] = {"account_count": int(users["count"])}
                result["access"] = {
                    "grant_counts": [
                        {
                            "domain": row["grant_domain"],
                            "capability": row["capability"],
                            "active_count": int(row["active_grant_count"]),
                        }
                        for row in cur.execute("SELECT * FROM partner.admin_grant_counts()").fetchall()
                    ]
                }
                result["companies"] = {
                    "organization_count": int(companies["total"]),
                    "awaiting_application": int(companies["awaiting_application"]),
                    "awaiting_verification": int(companies["awaiting_verification"]),
                    "share_eligible_count": int(eligible["count"]),
                }
                result["destinations"] = {"published_count": int(destinations["count"])}
            elif capabilities["company_review"]:
                counts = cur.execute(
                    """SELECT count(*) AS total,
                              count(*) FILTER (WHERE application_status='submitted') AS awaiting_application,
                              count(*) FILTER (WHERE verification_status='pending') AS awaiting_verification
                       FROM partner.organizations"""
                ).fetchone()
                result["companies"] = {
                    "organization_count": int(counts["total"]),
                    "awaiting_application": int(counts["awaiting_application"]),
                    "awaiting_verification": int(counts["awaiting_verification"]),
                }
            if any(capabilities[key] for key in CATALOGUE_CAPABILITIES):
                published = cur.execute(
                    "SELECT count(*) AS count FROM knowledge.production_destinations"
                ).fetchone()
                result["destinations"] = {"published_count": int(published["count"])}
            return result
    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="admin_overview_unavailable") from None
