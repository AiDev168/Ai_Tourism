"""Fail-closed guards for privileged platform writes.

Public staging/production reviewers require a fresh TOTP step-up bound to the
current authenticated session. Local development and isolated acceptance keep
the existing capability-audited workflow without weakening public checks.
"""

import psycopg
from fastapi import HTTPException
from psycopg.rows import dict_row

from app.core.config import Settings
from app.modules.identity.auth_service import AuthenticatedUser

PUBLIC_RUNTIME_ENVS = frozenset({"staging", "production", "prod", "preview"})


def privileged_admin_writes_available(app_env: str) -> bool:
    return app_env.strip().lower() not in PUBLIC_RUNTIME_ENVS


def require_privileged_admin_step_up(settings: Settings, user: AuthenticatedUser) -> None:
    if privileged_admin_writes_available(settings.app_env):
        return
    if (not settings.auth_enabled or not settings.auth_cookie_secure
            or settings.platform_admin_mfa_encryption_key_hex is None
            or settings.platform_admin_recovery_pepper is None):
        raise HTTPException(status_code=403, detail="privileged_admin_mfa_not_configured")
    try:
        with psycopg.connect(
            host=settings.database_host,
            port=settings.database_port,
            dbname=settings.database_name,
            user=settings.database_user,
            password=settings.database_password.get_secret_value(),
            connect_timeout=settings.database_connect_timeout_seconds,
            application_name="rahgard-privileged-step-up-check",
            row_factory=dict_row,
        ) as conn, conn.cursor() as cur:
            cur.execute("SELECT set_config('app.actor_id',%s,true)", (str(user.user_id),))
            fresh = cur.execute(
                """SELECT EXISTS(SELECT 1 FROM identity.platform_admin_step_up s
                     WHERE s.user_id=%s AND s.session_id=%s AND s.revoked_at IS NULL
                       AND s.expires_at>now()
                       AND EXISTS(SELECT 1 FROM identity.web_sessions w
                                 WHERE w.user_id=s.user_id AND w.session_id=s.session_id
                                   AND w.revoked_at IS NULL
                                   AND w.idle_expires_at>now() AND w.absolute_expires_at>now())
                       AND identity.has_platform_admin_capability(s.user_id)) AS fresh""",
                (user.user_id, user.session_id),
            ).fetchone()["fresh"]
    except psycopg.Error:
        raise HTTPException(status_code=503, detail="privileged_admin_step_up_unavailable") from None
    if not fresh:
        raise HTTPException(status_code=403, detail="privileged_admin_step_up_required")
