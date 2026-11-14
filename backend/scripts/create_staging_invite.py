"""Create one bounded, single-use private-staging traveler invitation.

Run only inside the protected API container as an operator. The generated
bearer code is printed once; callers must deliver it through a private channel.
"""
from __future__ import annotations

import argparse
import secrets
from datetime import UTC, datetime, timedelta

from app.core.config import get_settings
from app.modules.identity.staging_auth import StagingAuthRepository, hash_invite


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=7, choices=range(1, 15))
    args = parser.parse_args()
    settings = get_settings()
    if settings.app_env.lower() != "staging" or not settings.staging_auth_enabled or not settings.auth_enabled:
        raise SystemExit("Staging invitations are disabled for this environment.")
    token = secrets.token_urlsafe(32)
    now = datetime.now(UTC)
    StagingAuthRepository(settings).create_invite(hash_invite(token), now, now + timedelta(days=args.days))
    print("Create the account at the private staging sign-in page. Invitation code (shown once):")
    print(token)
    print(f"Expires in {args.days} days.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
