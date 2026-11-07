"""Same-origin phone OTP authentication endpoints."""

import logging
import string
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
from app.modules.identity.phone import InvalidPhoneNumber, normalize_iranian_mobile
from app.modules.identity.sms import DisabledSmsAdapter

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
    phone_e164: str
    phone_verified: bool = True


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


@router.post("/otp/challenges", response_model=ChallengeResponse, status_code=202)
def request_challenge(
    body: ChallengeRequest,
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
):
    if not settings.auth_enabled:
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
    if not settings.auth_enabled:
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


@router.get("/me", response_model=SessionResponse)
def current_user(
    request: Request,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    service: Annotated[AuthenticationService, Depends(get_auth_service)],
):
    try:
        raw_session = request.cookies.get(HOST_SESSION_COOKIE) or request.cookies.get(SESSION_COOKIE) or ""
        csrf_token = service.csrf_token(raw_session)
    except AuthenticationUnavailable:
        return _unavailable()
    return SessionResponse(
        user=PublicUser(user_id=user.user_id, phone_e164=user.phone_e164), csrf_token=csrf_token
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


