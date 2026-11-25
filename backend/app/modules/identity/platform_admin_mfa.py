"""Cryptographic primitives for session-bound platform-reviewer MFA."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.modules.provider_admin.security import (
    generate_recovery_codes,
    new_totp_secret,
    totp_provisioning_uri,
    verify_totp,
)

_ENVELOPE_VERSION = b"\x01"
_AAD_PREFIX = b"rahgard:platform-reviewer-totp:v1\x00"


def encrypt_totp_secret(secret: bytes, key: bytes, user_id: UUID) -> bytes:
    if len(secret) != 20 or len(key) != 32:
        raise ValueError("invalid_platform_mfa_material")
    nonce = secrets.token_bytes(12)
    return _ENVELOPE_VERSION + nonce + AESGCM(key).encrypt(nonce, secret, _AAD_PREFIX + user_id.bytes)


def decrypt_totp_secret(envelope: bytes, key: bytes, user_id: UUID) -> bytes:
    if len(key) != 32 or len(envelope) != 1 + 12 + 20 + 16 or envelope[:1] != _ENVELOPE_VERSION:
        raise ValueError("invalid_platform_mfa_envelope")
    secret = AESGCM(key).decrypt(envelope[1:13], envelope[13:], _AAD_PREFIX + user_id.bytes)
    if len(secret) != 20:
        raise ValueError("invalid_platform_mfa_secret")
    return secret


def recovery_code_hash(code: str, pepper: bytes) -> bytes:
    normalized = "".join(character for character in code.upper() if character not in " -")
    if (not 12 <= len(normalized) <= 32 or not normalized.isascii()
            or not normalized.isalnum() or len(pepper) < 32):
        # Do equivalent HMAC work for malformed candidates before returning a
        # value that cannot match a generated code.
        normalized = "invalid-platform-recovery-code"
    return hmac.new(pepper, b"rahgard:platform-admin:recovery:v1\x00" + normalized.encode("ascii"), hashlib.sha256).digest()


def current_totp_counter(secret: bytes, code: str, now: float | None = None) -> int | None:
    if not isinstance(code, str) or len(code) != 6 or not code.isascii() or not code.isdigit():
        return None
    timestamp = time.time() if now is None else now
    center = int(timestamp // 30)
    for counter in range(max(0, center - 1), center + 2):
        if verify_totp(secret, code, now=counter * 30, window=0):
            return counter
    return None


def enrollment_material(user_id: UUID) -> tuple[bytes, str, str]:
    secret = new_totp_secret()
    uri = totp_provisioning_uri(secret, f"platform-reviewer-{user_id}")
    encoded = base64.b32encode(secret).decode("ascii").rstrip("=")
    return secret, uri, encoded


__all__ = [
    "current_totp_counter", "decrypt_totp_secret", "encrypt_totp_secret",
    "enrollment_material", "generate_recovery_codes", "recovery_code_hash",
]
