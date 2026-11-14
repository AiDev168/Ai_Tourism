"""Invitation-only password authentication for the isolated VPS staging app."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from app.core.config import Settings
from app.modules.identity.auth_repository import AuthRepository

_ITERATIONS = 600_000
_SALT_BYTES = 32
_KEY_BYTES = 32
_DUMMY_SALT = bytes.fromhex("a1" * 32)
_DUMMY_VERIFIER = bytes.fromhex("b2" * 32)


def normalize_login(value: str) -> str:
    normalized = value.strip().lower()
    if (len(normalized) > 254 or len(normalized) < 5 or "@" not in normalized
            or any(ord(ch) < 33 or ord(ch) > 126 for ch in normalized)
            or normalized.count("@") != 1 or "." not in normalized.rsplit("@", 1)[-1]):
        raise ValueError("invalid login")
    return normalized


def password_bytes(value: str) -> bytes:
    if not isinstance(value, str) or not 16 <= len(value) <= 256 or "\0" in value:
        raise ValueError("invalid password")
    encoded = value.encode("utf-8", errors="strict")
    if len(encoded) > 1024:
        raise ValueError("invalid password")
    return encoded


def derive_password(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password_bytes(password), salt, _ITERATIONS, _KEY_BYTES)


class StagingAuthRepository:
    """DB operations only; no invitation or password material is logged."""

    def __init__(self, settings: Settings) -> None:
        self._auth = AuthRepository(settings)

    @staticmethod
    def _open_invites(conn, now: datetime) -> None:
        conn.execute("DELETE FROM identity.staging_auth_limits WHERE window_started_at < %s", (now - timedelta(hours=2),))

    def allow_attempt(self, *, dimension: str, digest: bytes, now: datetime,
                      window_seconds: int = 900, maximum: int = 12) -> bool:
        window_epoch = int(now.timestamp())
        window = datetime.fromtimestamp(window_epoch - window_epoch % window_seconds, now.tzinfo)
        with self._auth.connection() as conn, conn.transaction():
            self._open_invites(conn, now)
            row = conn.execute(
                """INSERT INTO identity.staging_auth_limits(dimension,subject_digest,window_started_at,hit_count)
                   VALUES (%s,%s,%s,1)
                   ON CONFLICT(dimension,subject_digest,window_started_at)
                   DO UPDATE SET hit_count=identity.staging_auth_limits.hit_count+1
                   RETURNING hit_count""", (dimension, digest, window),
            ).fetchone()
            return int(row["hit_count"]) <= maximum

    def create_invite(self, token_digest: bytes, now: datetime, expires_at: datetime) -> None:
        with self._auth.connection() as conn, conn.transaction():
            conn.execute("INSERT INTO identity.staging_invites(token_digest,created_at,expires_at) VALUES (%s,%s,%s)",
                         (token_digest, now, expires_at))

    def load_credential(self, login_name: str) -> dict[str, Any] | None:
        with self._auth.connection() as conn:
            return conn.execute(
                """SELECT c.user_id,c.salt,c.verifier,c.iterations,u.account_status,u.is_synthetic
                   FROM identity.staging_password_credentials c
                   JOIN identity.users u ON u.user_id=c.user_id
                   WHERE c.login_name=%s""", (login_name,),
            ).fetchone()

    def create_session(self, *, user_id: UUID, expected_verifier: bytes, token_hash: bytes,
                       csrf_hash: bytes, now: datetime, idle_seconds: int, absolute_seconds: int):
        with self._auth.connection() as conn, conn.transaction():
            row = conn.execute(
                """SELECT u.user_id,u.email FROM identity.users u
                   JOIN identity.staging_password_credentials c ON c.user_id=u.user_id
                   WHERE u.user_id=%s AND u.auth_subject='staging_invite'
                     AND u.account_status='active' AND u.is_synthetic=FALSE
                     AND c.verifier=%s FOR UPDATE OF u""", (user_id, expected_verifier),
            ).fetchone()
            if row is None:
                return None
            session = conn.execute(
                """INSERT INTO identity.web_sessions
                   (token_hash,user_id,csrf_hash,created_at,last_seen_at,idle_expires_at,absolute_expires_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING session_id""",
                (token_hash, user_id, csrf_hash, now, now, now + timedelta(seconds=idle_seconds),
                 now + timedelta(seconds=absolute_seconds)),
            ).fetchone()
            return {"user_id": user_id, "email": row["email"], "session_id": session["session_id"]}

    def redeem_invite(self, *, token_digest: bytes, login_name: str, salt: bytes, verifier: bytes,
                      token_hash: bytes, csrf_hash: bytes, now: datetime,
                      idle_seconds: int, absolute_seconds: int):
        with self._auth.connection() as conn, conn.transaction():
            invite = conn.execute(
                """SELECT invite_id,expires_at,consumed_at FROM identity.staging_invites
                   WHERE token_digest=%s FOR UPDATE""", (token_digest,),
            ).fetchone()
            if invite is None or invite["expires_at"] <= now or invite["consumed_at"] is not None:
                return None
            user = conn.execute(
                """INSERT INTO identity.users(auth_subject,email,account_status,is_synthetic)
                   VALUES ('staging_invite',%s,'active',FALSE) RETURNING user_id""", (login_name,),
            ).fetchone()
            conn.execute(
                """INSERT INTO identity.staging_password_credentials(user_id,login_name,salt,verifier,iterations)
                   VALUES (%s,%s,%s,%s,%s)""",
                (user["user_id"], login_name, salt, verifier, _ITERATIONS),
            )
            conn.execute("UPDATE identity.staging_invites SET consumed_at=%s,consumed_by=%s WHERE invite_id=%s",
                         (now, user["user_id"], invite["invite_id"]))
            session = conn.execute(
                """INSERT INTO identity.web_sessions
                   (token_hash,user_id,csrf_hash,created_at,last_seen_at,idle_expires_at,absolute_expires_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING session_id""",
                (token_hash, user["user_id"], csrf_hash, now, now, now + timedelta(seconds=idle_seconds),
                 now + timedelta(seconds=absolute_seconds)),
            ).fetchone()
            return {"user_id": user["user_id"], "email": login_name, "session_id": session["session_id"]}


def _dummy_work(password: str) -> None:
    try:
        value = password_bytes(password)
    except (ValueError, UnicodeError):
        value = b"invalid-password-input"
    candidate = hashlib.pbkdf2_hmac("sha256", value, _DUMMY_SALT, _ITERATIONS, _KEY_BYTES)
    hmac.compare_digest(candidate, _DUMMY_VERIFIER)


def hash_invite(token: str) -> bytes:
    return hashlib.sha256(token.encode("ascii", errors="strict")).digest()


def password_material(password: str) -> tuple[bytes, bytes]:
    password_bytes(password)
    salt = secrets.token_bytes(_SALT_BYTES)
    return salt, derive_password(password, salt)
