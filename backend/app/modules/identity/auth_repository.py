"""PostgreSQL persistence for authentication primitives."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

from app.core.config import Settings


class AuthRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection[Any]]:
        with psycopg.connect(
            host=self.settings.database_host,
            port=self.settings.database_port,
            dbname=self.settings.database_name,
            user=self.settings.database_user,
            password=self.settings.database_password.get_secret_value(),
            connect_timeout=self.settings.database_connect_timeout_seconds,
            application_name="ai-tourism-auth",
            row_factory=dict_row,
        ) as connection:
            yield connection

    def create_challenge(
        self,
        *,
        challenge_id: UUID,
        phone: str,
        verifier: bytes,
        now: datetime,
        expires_at: datetime,
        resend_after: datetime,
        limits: list[tuple[str, bytes, int]],
        window_seconds: int,
    ) -> bool:
        with self.connection() as conn, conn.transaction():
            # Serialize requests for the same phone across application workers.
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (phone,))
            allowed = True
            epoch = int(now.timestamp())
            window = epoch - epoch % window_seconds
            conn.execute(
                "DELETE FROM identity.auth_rate_limits WHERE window_started_at < to_timestamp(%s)",
                (window - 2 * window_seconds,),
            )
            for dimension, digest, maximum in limits:
                row = conn.execute(
                    """INSERT INTO identity.auth_rate_limits
                       (dimension, subject_digest, window_started_at, hit_count)
                       VALUES (%s, %s, to_timestamp(%s), 1)
                       ON CONFLICT (dimension, subject_digest, window_started_at)
                       DO UPDATE SET hit_count = identity.auth_rate_limits.hit_count + 1
                       RETURNING hit_count""",
                    (dimension, digest, window),
                ).fetchone()
                allowed = allowed and row["hit_count"] <= maximum
            previous = conn.execute(
                """SELECT challenge_id, resend_after FROM identity.otp_challenges
                   WHERE phone_e164 = %s AND consumed_at IS NULL AND superseded_at IS NULL
                   ORDER BY created_at DESC LIMIT 1 FOR UPDATE""",
                (phone,),
            ).fetchone()
            if previous and previous["resend_after"] > now:
                allowed = False
            if not allowed:
                return False
            conn.execute(
                """UPDATE identity.otp_challenges SET superseded_at = %s
                   WHERE phone_e164 = %s AND consumed_at IS NULL AND superseded_at IS NULL""",
                (now, phone),
            )
            conn.execute(
                """INSERT INTO identity.otp_challenges
                   (challenge_id, phone_e164, purpose, verifier_hmac, key_version,
                    created_at, expires_at, resend_after)
                   VALUES (%s, %s, 'login', %s, 'v1', %s, %s, %s)""",
                (challenge_id, phone, verifier, now, expires_at, resend_after),
            )
            return True

    def mark_delivery_failed(self, challenge_id: UUID) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE identity.otp_challenges SET delivery_status='failed' WHERE challenge_id=%s",
                (challenge_id,),
            )

    def mark_delivery_sent(self, challenge_id: UUID) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE identity.otp_challenges SET delivery_status='sent' WHERE challenge_id=%s",
                (challenge_id,),
            )

    def challenge_phone(self, challenge_id: UUID) -> str | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT phone_e164 FROM identity.otp_challenges WHERE challenge_id=%s",
                (challenge_id,),
            ).fetchone()
            return row["phone_e164"] if row else None

    def allow_verification_attempt(
        self, limits: list[tuple[str, bytes, int]], now: datetime, window_seconds: int
    ) -> bool:
        epoch = int(now.timestamp())
        window = epoch - epoch % window_seconds
        allowed = True
        with self.connection() as conn, conn.transaction():
            conn.execute(
                "DELETE FROM identity.auth_rate_limits WHERE window_started_at < to_timestamp(%s)",
                (window - 2 * window_seconds,),
            )
            for dimension, digest, maximum in limits:
                row = conn.execute(
                    """INSERT INTO identity.auth_rate_limits
                       (dimension, subject_digest, window_started_at, hit_count)
                       VALUES (%s, %s, to_timestamp(%s), 1)
                       ON CONFLICT (dimension, subject_digest, window_started_at)
                       DO UPDATE SET hit_count = identity.auth_rate_limits.hit_count + 1
                       RETURNING hit_count""",
                    (dimension, digest, window),
                ).fetchone()
                allowed = allowed and row["hit_count"] <= maximum
        return allowed

    def verify_and_create_session(
        self,
        *,
        challenge_id: UUID,
        candidate_verifier: bytes,
        now: datetime,
        max_attempts: int,
        token_hash: bytes,
        csrf_hash: bytes,
        idle_expires_at: datetime,
        absolute_expires_at: datetime,
    ) -> dict[str, Any] | None:
        with self.connection() as conn, conn.transaction():
            challenge = conn.execute(
                """SELECT * FROM identity.otp_challenges
                   WHERE challenge_id=%s FOR UPDATE""",
                (challenge_id,),
            ).fetchone()
            if (
                challenge is None
                or challenge["purpose"] != "login"
                or challenge["consumed_at"] is not None
                or challenge["superseded_at"] is not None
                or challenge["locked_at"] is not None
                or challenge["expires_at"] <= now
                or challenge["delivery_status"] != "sent"
            ):
                return None
            import hmac

            if not hmac.compare_digest(bytes(challenge["verifier_hmac"]), candidate_verifier):
                attempts = challenge["failed_attempts"] + 1
                conn.execute(
                    """UPDATE identity.otp_challenges
                       SET failed_attempts=%s, locked_at=%s
                       WHERE challenge_id=%s""",
                    (attempts, now if attempts >= max_attempts else None, challenge_id),
                )
                return None

            # Reconcile every old row, including synthetic/disabled rows. Never guess
            # which legacy identity should inherit a verified phone.
            matches = conn.execute(
                """SELECT user_id, account_status, is_synthetic
                   FROM identity.users WHERE phone_e164=%s FOR UPDATE""",
                (challenge["phone_e164"],),
            ).fetchall()
            if len(matches) > 1 or (matches and (matches[0]["is_synthetic"] or matches[0]["account_status"] != "active")):
                conn.execute(
                    "UPDATE identity.otp_challenges SET locked_at=%s WHERE challenge_id=%s",
                    (now, challenge_id),
                )
                return None

            known_verification = conn.execute(
                "SELECT user_id FROM identity.verified_phones WHERE phone_e164=%s FOR UPDATE",
                (challenge["phone_e164"],),
            ).fetchone()
            if known_verification and (not matches or known_verification["user_id"] != matches[0]["user_id"]):
                conn.execute(
                    "UPDATE identity.otp_challenges SET locked_at=%s WHERE challenge_id=%s",
                    (now, challenge_id),
                )
                return None
            user_id = matches[0]["user_id"] if matches else conn.execute(
                """INSERT INTO identity.users(phone_e164, account_status, is_synthetic)
                   VALUES (%s, 'active', FALSE) RETURNING user_id""",
                (challenge["phone_e164"],),
            ).fetchone()["user_id"]

            verification_result = conn.execute(
                """INSERT INTO identity.verified_phones(phone_e164,user_id,verified_at,challenge_id)
                   VALUES (%s,%s,%s,%s)
                   ON CONFLICT (phone_e164) DO UPDATE SET
                     user_id=EXCLUDED.user_id, verified_at=EXCLUDED.verified_at,
                     challenge_id=EXCLUDED.challenge_id
                   WHERE identity.verified_phones.user_id=EXCLUDED.user_id""",
                (challenge["phone_e164"], user_id, now, challenge_id),
            )
            verification = conn.execute(
                "SELECT user_id FROM identity.verified_phones WHERE phone_e164=%s",
                (challenge["phone_e164"],),
            ).fetchone()
            if verification_result.rowcount != 1:
                conn.execute(
                    "UPDATE identity.otp_challenges SET locked_at=%s WHERE challenge_id=%s",
                    (now, challenge_id),
                )
                return None
            if verification is None or verification["user_id"] != user_id:
                conn.execute(
                    "UPDATE identity.otp_challenges SET locked_at=%s WHERE challenge_id=%s",
                    (now, challenge_id),
                )
                return None
            conn.execute(
                "UPDATE identity.otp_challenges SET consumed_at=%s WHERE challenge_id=%s",
                (now, challenge_id),
            )
            session = conn.execute(
                """INSERT INTO identity.web_sessions
                   (token_hash,user_id,csrf_hash,created_at,last_seen_at,idle_expires_at,absolute_expires_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)
                   RETURNING session_id""",
                (token_hash, user_id, csrf_hash, now, now, idle_expires_at, absolute_expires_at),
            ).fetchone()
            return {
                "user_id": user_id,
                "phone_e164": challenge["phone_e164"],
                "session_id": session["session_id"],
            }

    def resolve_session(self, token_hash: bytes, now: datetime, idle_seconds: int) -> dict[str, Any] | None:
        with self.connection() as conn, conn.transaction():
            row = conn.execute(
                """SELECT s.session_id, s.user_id, u.phone_e164
                   FROM identity.web_sessions s
                   JOIN identity.users u ON u.user_id=s.user_id
                   JOIN identity.verified_phones v ON v.user_id=u.user_id
                   WHERE s.token_hash=%s AND s.revoked_at IS NULL
                     AND s.idle_expires_at>%s AND s.absolute_expires_at>%s
                     AND u.account_status='active' AND u.is_synthetic=FALSE
                     AND v.phone_e164=u.phone_e164
                   FOR UPDATE OF s""",
                (token_hash, now, now),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                """UPDATE identity.web_sessions
                   SET last_seen_at=%s, idle_expires_at=LEAST(absolute_expires_at,%s)
                   WHERE session_id=%s""",
                (now, now + timedelta(seconds=idle_seconds), row["session_id"]),
            )
            return {"user_id": row["user_id"], "phone_e164": row["phone_e164"], "session_id": row["session_id"]}

    def refresh_csrf(self, session_id: UUID, csrf_hash: bytes) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE identity.web_sessions SET csrf_hash=%s WHERE session_id=%s AND revoked_at IS NULL",
                (csrf_hash, session_id),
            )

    def validate_csrf(self, session_id: UUID, csrf_hash: bytes) -> bool:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM identity.web_sessions WHERE session_id=%s AND csrf_hash=%s AND revoked_at IS NULL",
                (session_id, csrf_hash),
            ).fetchone()
            return row is not None

    def revoke_session(self, token_hash: bytes, now: datetime) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE identity.web_sessions SET revoked_at=%s WHERE token_hash=%s AND revoked_at IS NULL",
                (now, token_hash),
            )
