"""Small deny-by-default authorization seam for later protected modules."""

from dataclasses import dataclass, field
from uuid import UUID


class AuthorizationDenied(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Principal:
    """Construct only from a validated server-side session and server grants."""

    user_id: UUID
    capabilities: frozenset[str] = field(default_factory=frozenset)


def require_owner(principal: Principal, owner_id: UUID) -> None:
    if principal.user_id != owner_id:
        raise AuthorizationDenied


def require_capability(principal: Principal, capability: str) -> None:
    if capability not in principal.capabilities:
        raise AuthorizationDenied
