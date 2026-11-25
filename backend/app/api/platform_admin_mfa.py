"""TOTP step-up for platform governance, separate from AI-provider administration."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Response
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import authenticated_user, require_authenticated_csrf
from app.core.config import Settings, get_settings
from app.modules.identity.auth_repository import AuthRepository
from app.modules.identity.auth_service import AuthenticatedUser
from app.modules.identity.platform_admin_mfa import (
    current_totp_counter,
    decrypt_totp_secret,
    encrypt_totp_secret,
    enrollment_material,
    generate_recovery_codes,
    recovery_code_hash,
)

router = APIRouter(prefix="/api/v1/admin/mfa", tags=["platform-admin-mfa"])
_ATTEMPT_LIMIT = 5
_STEP_UP_TTL = timedelta(minutes=5)


class TotpBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")


class RecoveryBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=12, max_length=64)


def _connection(settings: Settings):
    return psycopg.connect(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password.get_secret_value(),
        connect_timeout=settings.database_connect_timeout_seconds,
        application_name="rahgard-platform-admin-mfa",
        row_factory=dict_row,
    )


def _runtime(settings: Settings) -> tuple[bytes, bytes]:
    if (settings.app_env.lower() not in {"staging", "production"} or not settings.auth_enabled
            or not settings.auth_cookie_secure or settings.auth_rate_limit_secret is None
            or settings.platform_admin_mfa_encryption_key_hex is None
            or settings.platform_admin_recovery_pepper is None):
        raise HTTPException(status_code=503, detail="platform_admin_mfa_unavailable")
    try:
        key = bytes.fromhex(settings.platform_admin_mfa_encryption_key_hex.get_secret_value())
        pepper = settings.platform_admin_recovery_pepper.get_secret_value().encode("utf-8")
    except ValueError:
        raise HTTPException(status_code=503, detail="platform_admin_mfa_unavailable") from None
    if len(key) != 32 or len(pepper) < 32:
        raise HTTPException(status_code=503, detail="platform_admin_mfa_unavailable")
    return key, pepper


def _actor(cur, user: AuthenticatedUser) -> None:
    cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
    allowed = cur.execute(
        "SELECT identity.has_platform_admin_capability(%s) AS allowed", (user.user_id,)
    ).fetchone()["allowed"]
    if not allowed:
        raise HTTPException(status_code=403, detail="admin_capability_required")


def _audit(cur, action: str, session_id: UUID) -> None:
    cur.execute("SELECT identity.record_platform_admin_mfa_event(%s,%s)", (action, session_id))


def _no_store(response: Response) -> None:
    # Enrollment includes a TOTP seed and verification returns recovery codes.
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Pragma"] = "no-cache"


def _consume_attempt(settings: Settings, user: AuthenticatedUser, now: datetime) -> None:
    secret = settings.auth_rate_limit_secret
    if secret is None:
        raise HTTPException(status_code=503, detail="platform_admin_mfa_unavailable")
    digest = hmac.new(
        secret.get_secret_value().encode("utf-8"),
        b"rahgard:platform-admin-mfa:v1\x00" + user.user_id.bytes,
        hashlib.sha256,
    ).digest()
    try:
        allowed = AuthRepository(settings).allow_verification_attempt(
            [("verify_challenge", digest, _ATTEMPT_LIMIT)], now,
            settings.auth_rate_window_seconds,
        )
    except Exception:
        raise HTTPException(status_code=503, detail="platform_admin_mfa_unavailable") from None
    if not allowed:
        raise HTTPException(status_code=429, detail="mfa_rate_limited")


def _step_up_sql(cur, user: AuthenticatedUser, now: datetime) -> datetime:
    expires = now + _STEP_UP_TTL
    cur.execute(
        """INSERT INTO identity.platform_admin_step_up(user_id,session_id,verified_at,expires_at)
           VALUES (%s,%s,%s,%s) ON CONFLICT (user_id,session_id) DO UPDATE
           SET verified_at=EXCLUDED.verified_at,expires_at=EXCLUDED.expires_at,revoked_at=NULL""",
        (user.user_id, user.session_id, now, expires),
    )
    return expires


def platform_mfa_status(settings: Settings, user: AuthenticatedUser) -> dict[str, object]:
    """Return only the caller's MFA state; missing migration/config fails closed."""
    configured = bool(
        settings.auth_enabled and settings.auth_cookie_secure
        and settings.platform_admin_mfa_encryption_key_hex is not None
        and settings.platform_admin_recovery_pepper is not None
    )
    if not configured:
        return {"available": False, "required": True, "enrolled": False, "step_up_expires_at": None}
    try:
        with _connection(settings) as conn, conn.cursor() as cur:
            _actor(cur, user)
            row = cur.execute(
                """SELECT m.enabled_at,
                          (SELECT s.expires_at FROM identity.platform_admin_step_up s
                           WHERE s.user_id=m.user_id AND s.session_id=%s AND s.revoked_at IS NULL
                             AND s.expires_at>now()) AS step_up_expires_at
                   FROM identity.platform_admin_mfa m WHERE m.user_id=%s""",
                (user.session_id, user.user_id),
            ).fetchone()
            return {"available": True, "required": True, "enrolled": bool(row and row["enabled_at"]),
                    "step_up_expires_at": row["step_up_expires_at"].isoformat()
                    if row and row["step_up_expires_at"] else None}
    except HTTPException as exc:
        if exc.status_code == 403:
            return {"available": True, "required": True, "enrolled": False, "step_up_expires_at": None}
        raise
    except psycopg.Error:
        return {"available": False, "required": True, "enrolled": False, "step_up_expires_at": None}


@router.post("/enroll")
def enroll(
    response: Response,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    _no_store(response)
    key, _pepper = _runtime(settings)
    now = datetime.now(UTC)
    _consume_attempt(settings, user, now)
    secret, _uri, encoded = enrollment_material(user.user_id)
    encrypted = encrypt_totp_secret(secret, key, user.user_id)
    try:
        with _connection(settings) as conn, conn.transaction(), conn.cursor() as cur:
            _actor(cur, user)
            result = cur.execute(
                """INSERT INTO identity.platform_admin_mfa(user_id,pending_secret_ciphertext)
                   VALUES (%s,%s) ON CONFLICT(user_id) DO UPDATE
                   SET pending_secret_ciphertext=EXCLUDED.pending_secret_ciphertext,
                       version=identity.platform_admin_mfa.version+1,updated_at=now()
                   WHERE identity.platform_admin_mfa.enabled_at IS NULL
                   RETURNING user_id""", (user.user_id, encrypted),
            ).fetchone()
            if not result:
                raise HTTPException(status_code=409, detail="mfa_already_enrolled")
            _audit(cur, "enrollment_started", user.session_id)
    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="platform_admin_mfa_unavailable") from None
    return {"secret": encoded}


@router.post("/verify")
def verify_enrollment(
    body: TotpBody,
    response: Response,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    _no_store(response)
    key, pepper = _runtime(settings)
    now = datetime.now(UTC)
    _consume_attempt(settings, user, now)
    recovery_codes = generate_recovery_codes(10)
    hashes = [recovery_code_hash(code, pepper) for code in recovery_codes]
    try:
        with _connection(settings) as conn, conn.transaction(), conn.cursor() as cur:
            _actor(cur, user)
            row = cur.execute(
                "SELECT pending_secret_ciphertext FROM identity.platform_admin_mfa WHERE user_id=%s FOR UPDATE",
                (user.user_id,),
            ).fetchone()
            if not row or not row["pending_secret_ciphertext"]:
                raise HTTPException(status_code=409, detail="mfa_enrollment_missing")
            try:
                secret = decrypt_totp_secret(row["pending_secret_ciphertext"], key, user.user_id)
            except Exception:
                raise HTTPException(status_code=503, detail="platform_admin_mfa_unavailable") from None
            counter = current_totp_counter(secret, body.code, now.timestamp())
            if counter is None:
                raise HTTPException(status_code=401, detail="mfa_code_invalid")
            changed = cur.execute(
                """UPDATE identity.platform_admin_mfa SET secret_ciphertext=pending_secret_ciphertext,
                     pending_secret_ciphertext=NULL,enabled_at=%s,last_totp_counter=%s,recovery_hashes=%s,
                     version=version+1,updated_at=%s WHERE user_id=%s AND enabled_at IS NULL
                     AND last_totp_counter<%s RETURNING user_id""",
                (now, counter, hashes, now, user.user_id, counter),
            ).fetchone()
            if not changed:
                raise HTTPException(status_code=409, detail="mfa_enrollment_changed")
            expires = _step_up_sql(cur, user, now)
            _audit(cur, "mfa_enrolled", user.session_id)
    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="platform_admin_mfa_unavailable") from None
    return {"mfa_enrolled": True, "recovery_codes": list(recovery_codes),
            "step_up_expires_at": expires.isoformat()}


@router.post("/step-up")
def step_up(
    body: TotpBody,
    response: Response,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    _no_store(response)
    key, _pepper = _runtime(settings)
    now = datetime.now(UTC)
    _consume_attempt(settings, user, now)
    try:
        with _connection(settings) as conn, conn.transaction(), conn.cursor() as cur:
            _actor(cur, user)
            row = cur.execute(
                """SELECT secret_ciphertext,last_totp_counter FROM identity.platform_admin_mfa
                   WHERE user_id=%s AND enabled_at IS NOT NULL FOR UPDATE""", (user.user_id,)
            ).fetchone()
            if not row:
                raise HTTPException(status_code=403, detail="mfa_required")
            try:
                secret = decrypt_totp_secret(row["secret_ciphertext"], key, user.user_id)
            except Exception:
                raise HTTPException(status_code=503, detail="platform_admin_mfa_unavailable") from None
            counter = current_totp_counter(secret, body.code, now.timestamp())
            if counter is None or counter <= row["last_totp_counter"]:
                raise HTTPException(status_code=401, detail="mfa_code_invalid_or_replayed")
            updated = cur.execute(
                """UPDATE identity.platform_admin_mfa SET last_totp_counter=%s,version=version+1,updated_at=%s
                   WHERE user_id=%s AND last_totp_counter<%s RETURNING user_id""",
                (counter, now, user.user_id, counter),
            ).fetchone()
            if not updated:
                raise HTTPException(status_code=401, detail="mfa_code_invalid_or_replayed")
            expires = _step_up_sql(cur, user, now)
            _audit(cur, "totp_step_up", user.session_id)
    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="platform_admin_mfa_unavailable") from None
    return {"step_up_expires_at": expires.isoformat()}


@router.post("/recovery")
def recovery_step_up(
    body: RecoveryBody,
    response: Response,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    _no_store(response)
    _key, pepper = _runtime(settings)
    now = datetime.now(UTC)
    _consume_attempt(settings, user, now)
    verifier = recovery_code_hash(body.code, pepper)
    try:
        with _connection(settings) as conn, conn.transaction(), conn.cursor() as cur:
            _actor(cur, user)
            row = cur.execute(
                """UPDATE identity.platform_admin_mfa SET recovery_hashes=array_remove(recovery_hashes,%s),
                     version=version+1,updated_at=%s WHERE user_id=%s AND enabled_at IS NOT NULL
                     AND %s=ANY(recovery_hashes) RETURNING user_id""",
                (verifier, now, user.user_id, verifier),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=401, detail="recovery_code_invalid")
            expires = _step_up_sql(cur, user, now)
            _audit(cur, "recovery_step_up", user.session_id)
    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="platform_admin_mfa_unavailable") from None
    return {"step_up_expires_at": expires.isoformat()}


@router.post("/reset")
def reset_enrollment(
    response: Response,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Reset MFA only after a fresh step-up, typically obtained by recovery code.

    The recovery code is consumed by /recovery first. A separate same-origin
    request is required to clear the lost authenticator and its session step-up.
    """
    _no_store(response)
    _runtime(settings)
    now = datetime.now(UTC)
    try:
        with _connection(settings) as conn, conn.transaction(), conn.cursor() as cur:
            _actor(cur, user)
            fresh = cur.execute(
                """SELECT EXISTS(SELECT 1 FROM identity.platform_admin_step_up
                     WHERE user_id=%s AND session_id=%s AND revoked_at IS NULL
                       AND expires_at>%s
                       AND EXISTS(SELECT 1 FROM identity.web_sessions w
                                  WHERE w.user_id=%s AND w.session_id=%s AND w.revoked_at IS NULL
                                    AND w.idle_expires_at>%s AND w.absolute_expires_at>%s)) AS fresh""",
                (user.user_id, user.session_id, now, user.user_id, user.session_id, now, now),
            ).fetchone()["fresh"]
            if not fresh:
                raise HTTPException(status_code=403, detail="privileged_admin_step_up_required")
            _audit(cur, "recovery_reset", user.session_id)
            cur.execute("DELETE FROM identity.platform_admin_mfa WHERE user_id=%s", (user.user_id,))
    except HTTPException:
        raise
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="platform_admin_mfa_unavailable") from None
    return {"mfa_enrolled": False, "reset": True}
