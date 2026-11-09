"""Small deny-by-default authorization seam for later protected modules."""

from dataclasses import dataclass, field
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request

from app.api.auth import authenticated_user
from app.modules.identity.auth_service import AuthenticatedUser


class AuthorizationDenied(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Principal:
    """Constructed from a validated server session and server-side grants only."""

    user_id: UUID
    session_id: UUID
    capabilities: frozenset[str] = field(default_factory=frozenset)


def get_principal(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
) -> Principal:
    """Derive identity from the validated session; no client fields are consulted."""
    return Principal(user_id=user.user_id, session_id=user.session_id)


def require_owner(principal: Principal, owner_id: UUID) -> None:
    if principal.user_id != owner_id:
        raise AuthorizationDenied


def require_capability(principal: Principal, capability: str) -> None:
    if capability not in principal.capabilities:
        raise AuthorizationDenied


def require_owner_dependency(owner_id_parameter: str = "owner_id"):
    """FastAPI dependency for UUID path parameters bound to the principal owner."""

    def dependency(
        request: Request,
        principal: Annotated[Principal, Depends(get_principal)],
    ) -> Principal:
        raw_owner_id = request.path_params.get(owner_id_parameter)
        try:
            owner_id = UUID(str(raw_owner_id))
            require_owner(principal, owner_id)
        except (ValueError, AuthorizationDenied):
            raise HTTPException(status_code=403, detail="forbidden") from None
        return principal

    return dependency


def require_capability_dependency(capability: str):
    """Fail-closed FastAPI dependency for a server-granted capability."""

    def dependency(principal: Annotated[Principal, Depends(get_principal)]) -> Principal:
        try:
            require_capability(principal, capability)
        except AuthorizationDenied:
            raise HTTPException(status_code=403, detail="forbidden") from None
        return principal

    return dependency
