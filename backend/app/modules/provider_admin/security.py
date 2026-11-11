"""Small, provider-independent security primitives for AI provider administration.

Persistence, authorization grants, TOTP-secret encryption, and atomic recovery-code
consumption belong to the protected control-plane repository/API. These helpers do
not infer an administrator grant from a traveler identity.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from datetime import UTC, datetime, timedelta
from typing import Collection, Sequence
from urllib.parse import quote

AI_PROVIDER_ADMIN = "ai_provider_admin"
TOTP_PERIOD_SECONDS = 30
TOTP_DIGITS = 6


def has_ai_provider_admin_capability(grants: Collection[str]) -> bool:
    """Return true only for an explicit server-derived provider-admin grant."""
    # A bare string is itself a Collection[str]; substring membership would
    # accidentally authorize values such as "not_ai_provider_admin".
    if isinstance(grants, str):
        return False
    return AI_PROVIDER_ADMIN in grants


def new_totp_secret() -> bytes:
    """Generate a 160-bit TOTP secret; callers must encrypt it before persistence."""
    return secrets.token_bytes(20)


def _base32_secret(secret: bytes) -> str:
    if not isinstance(secret, bytes) or len(secret) < 20:
        raise ValueError("TOTP secret must contain at least 160 bits")
    return base64.b32encode(secret).decode("ascii").rstrip("=")


def totp_provisioning_uri(secret: bytes, account: str, issuer: str = "Rahgard") -> str:
    """Build an otpauth URI for a private enrollment response, never for logs."""
    account = account.strip()
    issuer = issuer.strip()
    if not account or len(account) > 254 or not issuer or len(issuer) > 64:
        raise ValueError("Invalid TOTP account or issuer")
    label = quote(f"{issuer}:{account}", safe="")
    return (
        f"otpauth://totp/{label}?secret={_base32_secret(secret)}"
        f"&issuer={quote(issuer, safe='')}&algorithm=SHA1&digits={TOTP_DIGITS}"
        f"&period={TOTP_PERIOD_SECONDS}"
    )


def totp_code(secret: bytes, timestamp: int | float | None = None) -> str:
    """Return the current RFC 6238 code (exposed for deterministic tests/tools)."""
    if not isinstance(secret, bytes) or len(secret) < 20:
        raise ValueError("TOTP secret must contain at least 160 bits")
    current = time.time() if timestamp is None else timestamp
    if not isinstance(current, (int, float)) or isinstance(current, bool) or current < 0:
        raise ValueError("Invalid timestamp")
    counter = int(current) // TOTP_PERIOD_SECONDS
    digest = hmac.new(secret, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{binary % (10 ** TOTP_DIGITS):0{TOTP_DIGITS}d}"


def verify_totp(
    secret: bytes,
    code: str,
    *,
    now: int | float | None = None,
    window: int = 1,
) -> bool:
    """Verify a six-digit TOTP within a small bounded clock-skew window."""
    if (not isinstance(code, str) or len(code) != TOTP_DIGITS
            or not code.isascii() or not code.isdigit()
            or type(window) is not int or not 0 <= window <= 2):
        return False
    timestamp = time.time() if now is None else now
    if (not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool)
            or timestamp < 0):
        return False
    try:
        for offset in range(-window, window + 1):
            expected = totp_code(secret, timestamp + offset * TOTP_PERIOD_SECONDS)
            if hmac.compare_digest(expected, code):
                return True
    except (TypeError, ValueError, OverflowError):
        return False
    return False


def normalize_recovery_code(code: str) -> str:
    """Canonicalize presentation separators while rejecting ambiguous input."""
    if not isinstance(code, str) or len(code) > 64:
        return ""
    normalized = "".join(char for char in code.upper() if char not in " -")
    if not (12 <= len(normalized) <= 32) or not normalized.isascii() or not normalized.isalnum():
        return ""
    return normalized


def hash_recovery_code(code: str, pepper: bytes) -> bytes:
    """Domain-separated keyed verifier; the pepper must remain outside the DB."""
    normalized = normalize_recovery_code(code)
    if not normalized or not isinstance(pepper, bytes) or len(pepper) < 32:
        raise ValueError("Invalid recovery material")
    return hmac.new(pepper, b"rahgard:ai-provider-admin:recovery:v1\0" + normalized.encode("ascii"), hashlib.sha256).digest()


def consume_recovery_code(code: str, verifiers: Sequence[bytes], pepper: bytes) -> int | None:
    """Locate a matching verifier for an atomic DB consume operation.

    All stored verifiers are checked in constant-time; callers must atomically mark
    the returned row used (e.g. UPDATE ... WHERE used_at IS NULL) before granting.
    """
    try:
        candidate = hash_recovery_code(code, pepper)
    except ValueError:
        candidate = bytes(32)
    match: int | None = None
    for index, verifier in enumerate(verifiers):
        equal = isinstance(verifier, bytes) and hmac.compare_digest(candidate, verifier)
        if equal and match is None:
            match = index
    return match if normalize_recovery_code(code) else None

def generate_recovery_codes(count: int = 10) -> tuple[str, ...]:
    """Generate bounded one-use high-entropy recovery codes for one-time display."""
    if type(count) is not int or not 1 <= count <= 20:
        raise ValueError("Recovery code count must be between 1 and 20")
    output: list[str] = []
    for _ in range(count):
        raw = base64.b32encode(secrets.token_bytes(10)).decode("ascii").rstrip("=")
        output.append(f"{raw[:8]}-{raw[8:]}")
    return tuple(output)


def step_up_is_fresh(
    verified_at: datetime | None,
    *,
    now: datetime | None = None,
    max_age: timedelta = timedelta(minutes=5),
) -> bool:
    """Fail closed for missing, naive, future, or expired step-up timestamps."""
    if verified_at is None or verified_at.tzinfo is None or verified_at.utcoffset() is None:
        return False
    current = now or datetime.now(UTC)
    if current.tzinfo is None or current.utcoffset() is None:
        return False
    if max_age <= timedelta(0) or max_age > timedelta(minutes=15):
        return False
    age = current.astimezone(UTC) - verified_at.astimezone(UTC)
    return timedelta(0) <= age <= max_age
