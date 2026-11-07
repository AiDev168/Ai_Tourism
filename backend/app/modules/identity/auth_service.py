"""Deterministic OTP/session application service."""

import hashlib
import hmac
import secrets
import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.core.config import Settings
from app.modules.identity.auth_repository import AuthRepository
from app.modules.identity.phone import normalize_iranian_mobile
from app.modules.identity.sms import SmsDeliveryError, SmsMessage, SmsPort


class AuthenticationUnavailable(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ChallengeResult:
    challenge_id: UUID | None
    accepted: bool = True


@dataclass(frozen=True, slots=True)
class AuthenticatedUser:
    user_id: UUID
    phone_e164: str
    session_id: UUID


class AuthenticationService:
    def __init__(self, settings: Settings, sms: SmsPort, repository: AuthRepository | None = None) -> None:
        self.settings = settings
        self.sms = sms
        self.repository = repository or AuthRepository(settings)

    def _enabled(self) -> None:
        if not self.settings.auth_enabled:
            raise AuthenticationUnavailable

    def _hmac(self, key_name: str, data: bytes) -> bytes:
        secret = getattr(self.settings, key_name)
        if secret is None:
            raise AuthenticationUnavailable
        return hmac.new(secret.get_secret_value().encode(), data, hashlib.sha256).digest()

    def _otp_verifier(self, challenge_id: UUID, phone: str, code: str) -> bytes:
        payload = b"rahgard:otp:v1\0" + challenge_id.bytes + b"\0login\0" + phone.encode() + b"\0" + code.encode()
        return self._hmac("auth_otp_hmac_secret", payload)

    def _digest(self, dimension: str, value: str) -> bytes:
        return self._hmac("auth_rate_limit_secret", (dimension + "\0" + value).encode())

    def issue(self, raw_phone: str, client_ip: str, locale: str = "fa-IR") -> ChallengeResult:
        self._enabled()
        phone = normalize_iranian_mobile(raw_phone)
        challenge_id = uuid4()
        code = f"{secrets.randbelow(10 ** self.settings.auth_otp_length):0{self.settings.auth_otp_length}d}"
        now = datetime.now(UTC)
        limits = [
            ("phone", self._digest("phone", phone), self.settings.auth_phone_issue_limit),
            ("ip", self._digest("ip", client_ip or "unknown"), self.settings.auth_ip_issue_limit),
            ("global", self._digest("global", "issuance"), self.settings.auth_global_issue_limit),
        ]
        allowed = self.repository.create_challenge(
            challenge_id=challenge_id,
            phone=phone,
            verifier=self._otp_verifier(challenge_id, phone, code),
            now=now,
            expires_at=now + timedelta(seconds=self.settings.auth_otp_ttl_seconds),
            resend_after=now + timedelta(seconds=self.settings.auth_otp_resend_cooldown_seconds),
            limits=limits,
            window_seconds=self.settings.auth_rate_window_seconds,
        )
        if not allowed:
            return ChallengeResult(challenge_id=None, accepted=False)
        sms_text = {
            "fa-IR": f"کد ورود راه‌گرد: {code}",
            "en-US": f"Rahgard sign-in code: {code}",
            "ar": f"رمز تسجيل الدخول إلى راه‌گرد: {code}",
        }
        message = SmsMessage(
            recipient=phone,
            verification_code=code,
            purpose="login",
            locale=locale,
            body=sms_text.get(locale, sms_text["fa-IR"]),
        )
        try:
            self.sms.send(message, timeout_seconds=3.0)
            self.repository.mark_delivery_sent(challenge_id)
        except (SmsDeliveryError, TimeoutError):
            self.repository.mark_delivery_failed(challenge_id)
            return ChallengeResult(challenge_id=None, accepted=False)
        except Exception:
            self.repository.mark_delivery_failed(challenge_id)
            return ChallengeResult(challenge_id=None, accepted=False)
        finally:
            del code
            del message
        return ChallengeResult(challenge_id=challenge_id)

    def verify(
        self, challenge_id: UUID, code: str, client_ip: str = "unknown"
    ) -> tuple[AuthenticatedUser, str, str] | None:
        self._enabled()
        raw_session = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_session.encode()).digest()
        csrf = self._csrf_for_session(raw_session)
        csrf_hash = hashlib.sha256(csrf.encode()).digest()
        now = datetime.now(UTC)
        phone = self.repository.challenge_phone(challenge_id)
        if phone is None:
            return None
        if not self.repository.allow_verification_attempt(
            [
                ("verify_challenge", self._digest("verify_challenge", str(challenge_id)), self.settings.auth_otp_max_attempts),
                ("verify_phone", self._digest("verify_phone", phone), self.settings.auth_phone_verify_limit),
                ("verify_ip", self._digest("verify_ip", client_ip or "unknown"), self.settings.auth_ip_verify_limit),
            ],
            now,
            self.settings.auth_rate_window_seconds,
        ):
            return None
        absolute = now + timedelta(seconds=self.settings.auth_session_absolute_seconds or 0)
        row = self.repository.verify_and_create_session(
            challenge_id=challenge_id,
            candidate_verifier=self._otp_verifier(challenge_id, phone, code),
            now=now,
            max_attempts=self.settings.auth_otp_max_attempts,
            token_hash=token_hash,
            csrf_hash=csrf_hash,
            idle_expires_at=now + timedelta(seconds=self.settings.auth_session_idle_seconds or 0),
            absolute_expires_at=absolute,
        )
        if row is None:
            return None
        return AuthenticatedUser(row["user_id"], row["phone_e164"], row["session_id"]), raw_session, csrf

    def authenticate(self, raw_session: str) -> AuthenticatedUser | None:
        self._enabled()
        if not raw_session or len(raw_session) > 128:
            return None
        token_hash = hashlib.sha256(raw_session.encode()).digest()
        row = self.repository.resolve_session(
            token_hash, datetime.now(UTC), self.settings.auth_session_idle_seconds or 0
        )
        if row is None:
            return None
        return AuthenticatedUser(row["user_id"], row["phone_e164"], row["session_id"])

    def _csrf_for_session(self, raw_session: str) -> str:
        digest = self._hmac("auth_csrf_secret", b"rahgard:csrf:v1\0" + raw_session.encode())
        return base64.urlsafe_b64encode(digest).decode().rstrip("=")

    def csrf_token(self, raw_session: str) -> str:
        return self._csrf_for_session(raw_session)

    def validate_csrf(self, user: AuthenticatedUser, token: str | None) -> bool:
        if not token or len(token) > 128:
            return False
        return self.repository.validate_csrf(user.session_id, hashlib.sha256(token.encode()).digest())

    def logout(self, raw_session: str | None) -> None:
        if raw_session and len(raw_session) <= 128:
            self.repository.revoke_session(hashlib.sha256(raw_session.encode()).digest(), datetime.now(UTC))
