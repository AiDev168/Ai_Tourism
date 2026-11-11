"""Local-only single-owner password credential verification.

There are intentionally no HTTP handlers or session database writes here. A
caller must provide a server-side, owner-scoped session issuer and a limiter;
the private pilot integration persists only the salt and PBKDF2 verifier.
"""

from __future__ import annotations

import base64
from collections import deque
from dataclasses import dataclass
import hashlib
import hmac
import ipaddress
import json
import secrets
import threading
import time
from typing import Callable, TypeVar
from urllib.parse import urlsplit
from uuid import UUID

_VERSION = 1
_ALGORITHM = "pbkdf2-sha256"
_ITERATIONS = 600_000
_SALT_BYTES = 32
_VERIFIER_BYTES = 32
_MAX_PASSWORD_CHARS = 256
_DUMMY_SALT = bytes.fromhex("a6" * _SALT_BYTES)
_DUMMY_VERIFIER = bytes.fromhex("59" * _VERIFIER_BYTES)
_OWNER_ID = TypeVar("_OWNER_ID")
_SESSION = TypeVar("_SESSION")


class LocalOwnerCredentialError(ValueError):
    """Credential material or local request context is not safe to accept."""


@dataclass(frozen=True, slots=True)
class LocalOwnerCredential:
    owner_id: UUID
    salt_b64: str
    verifier_b64: str
    iterations: int = _ITERATIONS
    version: int = _VERSION
    algorithm: str = _ALGORITHM

    def as_record(self) -> dict[str, str | int]:
        """Serialize only a one-way verifier and random salt, never a password."""
        return {
            "version": self.version,
            "algorithm": self.algorithm,
            "owner_id": str(self.owner_id),
            "iterations": self.iterations,
            "salt_b64": self.salt_b64,
            "verifier_b64": self.verifier_b64,
        }


class LocalOwnerLoginGuard:
    """Small process-local limiter; production callers may adapt this interface
    to an atomic persistent limiter. The map is bounded against key flooding.
    """

    def __init__(self, *, max_attempts: int = 5, window_seconds: int = 900,
                 maximum_keys: int = 256, clock: Callable[[], float] = time.monotonic) -> None:
        if not 1 <= max_attempts <= 10 or not 60 <= window_seconds <= 3600 or maximum_keys < 8:
            raise ValueError("local owner limiter bounds are invalid")
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.maximum_keys = maximum_keys
        self._clock = clock
        self._attempts: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allowed(self, key: str) -> bool:
        now = self._clock()
        with self._lock:
            self._expire(now)
            if key not in self._attempts and len(self._attempts) >= self.maximum_keys:
                return False
            entries = self._attempts.setdefault(key, deque())
            return len(entries) < self.max_attempts

    def failed(self, key: str) -> None:
        now = self._clock()
        with self._lock:
            self._expire(now)
            if key not in self._attempts and len(self._attempts) >= self.maximum_keys:
                return
            entries = self._attempts.setdefault(key, deque())
            if len(entries) < self.max_attempts:
                entries.append(now)

    def succeeded(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)

    def _expire(self, now: float) -> None:
        cutoff = now - self.window_seconds
        for key in tuple(self._attempts):
            entries = self._attempts[key]
            while entries and entries[0] <= cutoff:
                entries.popleft()
            if not entries:
                del self._attempts[key]


def _decode_b64(value: object, expected_bytes: int) -> bytes:
    if not isinstance(value, str) or len(value) > 128:
        raise LocalOwnerCredentialError("local owner credential is malformed")
    try:
        encoded = value.encode("ascii")
        decoded = base64.b64decode(encoded + b"=" * (-len(encoded) % 4), altchars=b"-_", validate=True)
    except (UnicodeError, ValueError):
        raise LocalOwnerCredentialError("local owner credential is malformed") from None
    if len(decoded) != expected_bytes:
        raise LocalOwnerCredentialError("local owner credential is malformed")
    return decoded


def parse_credential(value: object) -> LocalOwnerCredential:
    """Parse strict DB/JSON data and reject unknown fields or weak KDF settings."""
    if isinstance(value, str | bytes):
        try:
            def no_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
                result: dict[str, object] = {}
                for key, item in pairs:
                    if key in result:
                        raise ValueError("duplicate key")
                    result[key] = item
                return result
            value = json.loads(value, object_pairs_hook=no_duplicates)
        except (UnicodeError, ValueError, TypeError):
            raise LocalOwnerCredentialError("local owner credential is malformed") from None
    expected = {"version", "algorithm", "owner_id", "iterations", "salt_b64", "verifier_b64"}
    if not isinstance(value, dict) or set(value) != expected:
        raise LocalOwnerCredentialError("local owner credential is malformed")
    try:
        if (type(value["version"]) is not int or value["version"] != _VERSION or value["algorithm"] != _ALGORITHM
                or type(value["iterations"]) is not int or value["iterations"] != _ITERATIONS):
            raise ValueError
        owner_id = UUID(str(value["owner_id"]))
        salt = _decode_b64(value["salt_b64"], _SALT_BYTES)
        verifier = _decode_b64(value["verifier_b64"], _VERIFIER_BYTES)
    except (ValueError, TypeError, LocalOwnerCredentialError):
        raise LocalOwnerCredentialError("local owner credential is malformed") from None
    return LocalOwnerCredential(owner_id, base64.urlsafe_b64encode(salt).decode().rstrip("="),
                                base64.urlsafe_b64encode(verifier).decode().rstrip("="))


def create_credential(owner_id: UUID, password: str) -> LocalOwnerCredential:
    """One-time bootstrap primitive; the caller must enforce owner approval and
    persist the returned verifier using the pilot's protected credential store.
    """
    if not isinstance(owner_id, UUID):
        raise LocalOwnerCredentialError("owner identity is invalid")
    if (not isinstance(password, str) or not 16 <= len(password) <= _MAX_PASSWORD_CHARS
            or password != password.strip() or len(set(password)) < 8
            or any(ord(char) < 32 for char in password)):
        raise LocalOwnerCredentialError("owner password does not meet local pilot requirements")
    salt = secrets.token_bytes(_SALT_BYTES)
    verifier = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _ITERATIONS, _VERIFIER_BYTES)
    return LocalOwnerCredential(
        owner_id=owner_id,
        salt_b64=base64.urlsafe_b64encode(salt).decode().rstrip("="),
        verifier_b64=base64.urlsafe_b64encode(verifier).decode().rstrip("="),
    )


def _is_local_https_request(peer: str, host: str, origin: str, allowed_origin: str,
                            forwarded_for: str | None) -> bool:
    if forwarded_for is not None:
        return False
    try:
        if not ipaddress.ip_address(peer).is_loopback:
            return False
        parsed_host = urlsplit("https://" + host)
        parsed_origin = urlsplit(origin)
        allowed = urlsplit(allowed_origin)
        if (parsed_host.username or parsed_host.password or not parsed_host.hostname
                or parsed_host.path or parsed_host.query or parsed_host.fragment
                or parsed_origin.scheme != "https" or allowed.scheme != "https"
                or not parsed_origin.hostname or parsed_origin.username or parsed_origin.password
                or parsed_origin.path or parsed_origin.query or parsed_origin.fragment
                or allowed.username or allowed.password or allowed.path or allowed.query or allowed.fragment
                or origin != allowed_origin or parsed_host.netloc.lower() != parsed_origin.netloc.lower()
                or parsed_host.port != parsed_origin.port):
            return False
        for candidate in (parsed_host.hostname, parsed_origin.hostname, allowed.hostname):
            if candidate is None or candidate.endswith("."):
                return False
            try:
                if not ipaddress.ip_address(candidate).is_loopback:
                    return False
            except ValueError:
                if candidate.lower() != "localhost":
                    return False
        return True
    except (ValueError, TypeError):
        return False


def verify_and_issue(
    credential: LocalOwnerCredential | None,
    password: str,
    *,
    limiter: LocalOwnerLoginGuard,
    request_peer: str,
    host: str,
    origin: str,
    allowed_origin: str,
    session_issuer: Callable[[UUID], _SESSION],
    forwarded_for: str | None = None,
) -> _SESSION | None:
    """Verify a local owner password and delegate actual session creation.

    No session is issued for a non-loopback peer, non-HTTPS/non-local origin,
    forwarded client identity, malformed credential, or locked attempt key.
    `session_issuer` must create a normal revocable, expiring owner session.
    """
    if not _is_local_https_request(request_peer, host, origin, allowed_origin, forwarded_for):
        return None
    peer = ipaddress.ip_address(request_peer).compressed
    owner_key = str(credential.owner_id) if credential else "unknown-owner"
    limit_key = hashlib.sha256((peer + "\0" + owner_key).encode("utf-8")).hexdigest()
    allowed = limiter.allowed(limit_key)
    salt = _DUMMY_SALT
    expected = _DUMMY_VERIFIER
    valid_credential = credential is not None
    if valid_credential:
        try:
            salt = _decode_b64(credential.salt_b64, _SALT_BYTES)
            expected = _decode_b64(credential.verifier_b64, _VERIFIER_BYTES)
            valid_credential = credential.iterations == _ITERATIONS and credential.version == _VERSION and credential.algorithm == _ALGORITHM
        except LocalOwnerCredentialError:
            valid_credential = False
            salt = _DUMMY_SALT
            expected = _DUMMY_VERIFIER
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8", errors="replace")[:_MAX_PASSWORD_CHARS], salt,
        _ITERATIONS, _VERIFIER_BYTES,
    ) if isinstance(password, str) else hashlib.pbkdf2_hmac(
        "sha256", b"invalid-password-input", salt, _ITERATIONS, _VERIFIER_BYTES,
    )
    matched = hmac.compare_digest(candidate, expected)
    if not allowed or not valid_credential or not matched:
        limiter.failed(limit_key)
        return None
    limiter.succeeded(limit_key)
    return session_issuer(credential.owner_id)


# Backward-compatible short name for application adapters implementing the
# same limiter surface.
AttemptLimiter = LocalOwnerLoginGuard
