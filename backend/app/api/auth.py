"""Same-origin phone OTP authentication endpoints."""

import logging
import string
import base64
from typing import Annotated, Literal
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import Settings, get_settings
from app.modules.identity.auth_service import (
    AuthenticationService,
    AuthenticationUnavailable,
    AuthenticatedUser,
)
from app.modules.auth.local_owner import parse_credential, verify_and_issue
from app.modules.identity.phone import InvalidPhoneNumber, normalize_iranian_mobile
from app.modules.identity.sms import DisabledSmsAdapter
from app.modules.trip.repository import TravelerRepository

logger = logging.getLogger("ai_tourism.auth")
router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
SESSION_COOKIE = "rahgard_session"
HOST_SESSION_COOKIE = "__Host-rahgard_session"


class ChallengeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    phone_number: str = Field(min_length=1, max_length=40)
    locale: Literal["fa-IR", "en-US", "ar"] = "fa-IR"

    @field_validator("phone_number")
    @classmethod
    def valid_phone_shape(cls, value: str) -> str:
        try:
            normalize_iranian_mobile(value)
        except InvalidPhoneNumber as error:
            raise ValueError("Enter a supported Iranian mobile number") from error
        return value


class ChallengeResponse(BaseModel):
    challenge_id: UUID | None
    status: Literal["accepted", "unavailable"]
    message: str = "If sign-in can proceed, a code will be sent."


class AuthMethodResponse(BaseModel):
    methods: list[Literal["otp", "local_owner"]]
    otp_delivery: Literal["available", "unavailable"]


class LocalOwnerLoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    login_name: str = Field(min_length=3, max_length=40, pattern=r"^[a-z][a-z0-9._-]{2,39}$")
    password: str = Field(min_length=1, max_length=256)


class VerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: UUID
    code: str = Field(min_length=4, max_length=8)

    @field_validator("code")
    @classmethod
    def ascii_code(cls, value: str) -> str:
        digits = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
        normalized = value.translate(digits)
        if not normalized or any(char not in string.digits for char in normalized):
            raise ValueError("Invalid verification code")
        return normalized


class PublicUser(BaseModel):
    user_id: UUID
    phone_e164: str | None = None
    phone_verified: bool | None = True
    auth_method: Literal["otp", "local_owner"] = "otp"


class SessionResponse(BaseModel):
    user: PublicUser
    csrf_token: str


def get_auth_service(request: Request, settings: Annotated[Settings, Depends(get_settings)]) -> AuthenticationService:
    adapter = getattr(request.app.state, "sms_adapter", None) or DisabledSmsAdapter()
    return AuthenticationService(settings, adapter)


def _unavailable() -> JSONResponse:
    return JSONResponse(status_code=503, content={"error": {"code": "authentication_unavailable"}})


def _cookie_name(settings: Settings) -> str:
    return HOST_SESSION_COOKIE if settings.auth_cookie_secure else SESSION_COOKIE


def _set_cookie(response: Response, raw_session: str, settings: Settings) -> None:
    response.set_cookie(
        _cookie_name(settings), raw_session,
        secure=settings.auth_cookie_secure, httponly=True, samesite="lax", path="/",
        max_age=settings.auth_session_absolute_seconds,
    )


def _delete_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        _cookie_name(settings), secure=settings.auth_cookie_secure, httponly=True,
        samesite="lax", path="/",
    )


class _PersistentLocalOwnerLimiter:
    """Adapter over the marked pilot DB's durable failed-attempt ledger."""

    def __init__(self, repository):
        self.repository = repository

    def allowed(self, key: str) -> bool:
        from datetime import UTC, datetime
        return self.repository.allow_local_owner_attempt(key, datetime.now(UTC))

    def failed(self, key: str) -> None:
        from datetime import UTC, datetime
        self.repository.record_local_owner_failure(key, datetime.now(UTC))

    def succeeded(self, key: str) -> None:
        self.repository.clear_local_owner_failures(key)


@router.get("/method", response_model=AuthMethodResponse)
def authentication_method(settings: Annotated[Settings, Depends(get_settings)]):
    if not settings.auth_enabled:
        return AuthMethodResponse(methods=[], otp_delivery="unavailable")
    # OTP remains the ordinary traveler capability even when this local pilot
    # has no delivery provider. The client can explain that delivery is
    # unavailable without inventing or exposing a verification code.
    methods: list[Literal["otp", "local_owner"]] = ["otp"]
    if settings.auth_local_owner_enabled:
        methods.append("local_owner")
    return AuthMethodResponse(
        methods=methods,
        otp_delivery="available" if settings.auth_sms_adapter != "disabled" else "unavailable",
    )


@router.post("/local-owner/login", response_model=SessionResponse)
def local_owner_login(
    body: LocalOwnerLoginRequest,
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
):
    if not settings.auth_enabled or not settings.auth_local_owner_enabled:
        return _unavailable()
    origin = request.headers.get("origin", "")
    allowed = [item.strip() for item in settings.auth_allowed_origins.split(",") if item.strip()]
    if len(allowed) != 1:
        return _unavailable()
    if any(header in request.headers for header in (
        "forwarded", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto"
    )):
        return JSONResponse(status_code=401, content={"error": {"code": "unauthenticated"}})
    peer = request.client.host if request.client else ""
    repository = service.repository
    try:
        row = repository.load_local_owner_credential(body.login_name)
        credential = None
        session_issuer = service.issue_local_owner_session
        if row is not None:
            credential = parse_credential({
                "version": 1, "algorithm": "pbkdf2-sha256", "owner_id": str(row["owner_id"]),
                "iterations": row["iterations"],
                "salt_b64": base64.urlsafe_b64encode(bytes(row["salt"])).decode().rstrip("="),
                "verifier_b64": base64.urlsafe_b64encode(bytes(row["verifier"])).decode().rstrip("="),
            })
            expected_salt = bytes(row["salt"])
            expected_verifier = bytes(row["verifier"])
            expected_iterations = int(row["iterations"])
            def session_issuer(owner_id):
                return service.issue_local_owner_session(
                    owner_id, expected_salt, expected_verifier, expected_iterations,
                )
        result = verify_and_issue(
            credential, body.password, limiter=_PersistentLocalOwnerLimiter(repository),
            request_peer=peer, host=request.headers.get("host", ""), origin=origin,
            allowed_origin=allowed[0], session_issuer=session_issuer,
            forwarded_for=request.headers.get("x-forwarded-for") if "x-forwarded-for" in request.headers else None,
        )
    except (AuthenticationUnavailable, psycopg.Error):
        logger.warning("auth.local_owner_unavailable")
        return _unavailable()
    if result is None:
        return JSONResponse(status_code=401, content={"error": {"code": "unauthenticated"}})
    user, raw_session, csrf_token = result
    _set_cookie(response, raw_session, settings)
    return SessionResponse(user=PublicUser(
        user_id=user.user_id, phone_e164=None, phone_verified=None, auth_method="local_owner",
    ), csrf_token=csrf_token)


@router.post("/otp/challenges", response_model=ChallengeResponse, status_code=202)
def request_challenge(
    body: ChallengeRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
):
    if not settings.auth_enabled or settings.auth_sms_adapter == "disabled":
        return _unavailable()
    try:
        result = service.issue(
            body.phone_number, request.client.host if request.client else "unknown", body.locale
        )
    except AuthenticationUnavailable:
        return _unavailable()
    except psycopg.Error:
        logger.warning("auth.challenge_unavailable")
        return _unavailable()
    except InvalidPhoneNumber:
        return JSONResponse(status_code=422, content={"error": {"code": "invalid_phone"}})
    return ChallengeResponse(
        challenge_id=result.challenge_id,
        status="accepted" if result.accepted else "unavailable",
    )


@router.post("/otp/verify", response_model=SessionResponse)
def verify_challenge(
    body: VerifyRequest,
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
):
    if not settings.auth_enabled or settings.auth_sms_adapter == "disabled":
        return _unavailable()
    try:
        result = service.verify(
            body.challenge_id, body.code, request.client.host if request.client else "unknown"
        )
    except (AuthenticationUnavailable, psycopg.Error):
        logger.warning("auth.verification_unavailable")
        return _unavailable()
    if result is None:
        return JSONResponse(status_code=401, content={"error": {"code": "invalid_or_expired_code"}})
    user, raw_session, csrf_token = result
    _set_cookie(response, raw_session, settings)
    return SessionResponse(
        user=PublicUser(user_id=user.user_id, phone_e164=user.phone_e164),
        csrf_token=csrf_token,
    )


def authenticated_user(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
) -> AuthenticatedUser:
    if not settings.auth_enabled:
        raise AuthenticationUnavailable
    token = request.cookies.get(_cookie_name(settings))
    try:
        user = service.authenticate(token or "")
    except (AuthenticationUnavailable, psycopg.Error):
        raise AuthenticationUnavailable from None
    if user is None:
        raise HTTPException(status_code=401, detail="unauthenticated")
    return user


def require_authenticated_csrf(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
) -> None:
    """Require exact same-origin and the CSRF token bound to the server session."""
    origin = request.headers.get("origin")
    allowed = {item.strip() for item in settings.auth_allowed_origins.split(",") if item.strip()}
    token = request.headers.get("x-csrf-token")
    try:
        valid_csrf = service.validate_csrf(user, token)
    except (AuthenticationUnavailable, psycopg.Error):
        raise AuthenticationUnavailable from None
    if origin not in allowed or not valid_csrf:
        raise HTTPException(status_code=403, detail="csrf_rejected")


@router.get("/me", response_model=SessionResponse)
def current_user(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        # Derive the token from the same cookie that authenticated_user used.
        # A stale cookie from another configuration must not override it.
        raw_session = request.cookies.get(_cookie_name(settings)) or ""
        csrf_token = service.csrf_token(raw_session)
    except AuthenticationUnavailable:
        return _unavailable()
    return SessionResponse(
        user=PublicUser(user_id=user.user_id, phone_e164=user.phone_e164,
                        phone_verified=True if user.phone_e164 else None,
                        auth_method=user.auth_method), csrf_token=csrf_token
    )


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
):
    if not settings.auth_enabled:
        _delete_cookie(response, settings)
        response.status_code = 204
        return None
    token = request.cookies.get(_cookie_name(settings))
    if token:
        try:
            user = service.authenticate(token)
        except (AuthenticationUnavailable, psycopg.Error):
            return _unavailable()
        if user is None:
            _delete_cookie(response, settings)
            response.status_code = 204
            return None
        origin = request.headers.get("origin")
        allowed = {item.strip() for item in settings.auth_allowed_origins.split(",") if item.strip()}
        csrf = request.headers.get("x-csrf-token")
        try:
            valid_csrf = service.validate_csrf(user, csrf)
        except (AuthenticationUnavailable, psycopg.Error):
            return _unavailable()
        if origin not in allowed or not valid_csrf:
            return JSONResponse(status_code=403, content={"error": {"code": "csrf_rejected"}})
        try:
            service.logout(token)
        except psycopg.Error:
            return _unavailable()
    _delete_cookie(response, settings)
    response.status_code = 204
    return None


@router.delete("/me", status_code=204)
def delete_current_account(
    request: Request,
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
):
    """Delete the authenticated owner's account and all linked personal data."""
    origin = request.headers.get("origin")
    allowed = {item.strip() for item in settings.auth_allowed_origins.split(",") if item.strip()}
    csrf = request.headers.get("x-csrf-token")
    try:
        valid_csrf = service.validate_csrf(user, csrf)
    except (AuthenticationUnavailable, psycopg.Error):
        return _unavailable()
    if origin not in allowed or not valid_csrf:
        return JSONResponse(status_code=403, content={"error": {"code": "csrf_rejected"}})
    try:
        deleted = TravelerRepository(settings).delete_account_data(user.user_id)
    except psycopg.Error:
        logger.warning("auth.account_delete_unavailable")
        return _unavailable()
    if not deleted:
        return JSONResponse(status_code=401, content={"error": {"code": "unauthenticated"}})
    _delete_cookie(response, settings)
    response.status_code = 204
    return None


