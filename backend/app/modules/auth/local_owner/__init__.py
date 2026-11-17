"""Local-only owner authentication primitives.

This module deliberately has no HTTP routes and does not create application
sessions itself. The application must connect its session issuer to the
existing owner-scoped session system after confirming the returned owner ID.
"""

from app.modules.auth.local_owner.credentials import (
    LocalOwnerCredential,
    LocalOwnerCredentialError,
    LocalOwnerLoginGuard,
    create_credential,
    parse_credential,
    verify_and_issue,
)

__all__ = [
    "LocalOwnerCredential",
    "LocalOwnerCredentialError",
    "LocalOwnerLoginGuard",
    "create_credential",
    "parse_credential",
    "verify_and_issue",
]
