"""Portable AES-256-GCM vault for server-managed provider credentials.

The key is injected as a protected file by the deployment secret manager. Vault
files contain versioned authenticated ciphertext only; PostgreSQL stores opaque
references. The file backend is deliberately small and can be replaced by a
KMS adapter without changing provider registry contracts.
"""

from __future__ import annotations

import os
import re
import secrets
import json
from collections import Counter
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.modules.provider_admin.vault import VaultUnavailable


class AesGcmSecretVault:
    _NAME = re.compile(r"^[a-f0-9]{32}\.agcm$")
    _VERSION = b"\x01"
    _KEY_ID = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
    _MAX_SECRET_BYTES = 16_384
    _AAD_PREFIX = b"rahgard:provider-secret:v1\x00"

    def __init__(self, directory: Path, key_file: Path) -> None:
        self.directory = directory
        self.key_file = key_file

    def _keyring(self) -> tuple[str, dict[str, bytes]]:
        try:
            if self.directory.is_symlink() or not self.directory.is_dir():
                raise OSError
            if os.name != "nt" and self.directory.stat().st_mode & 0o077:
                raise OSError
            if self.key_file.parent.is_symlink() or not self.key_file.parent.is_dir():
                raise OSError
            if os.name != "nt" and self.key_file.parent.stat().st_mode & 0o077:
                raise OSError
            if self.key_file.is_symlink() or not self.key_file.is_file():
                raise OSError
            metadata = self.key_file.stat()
            if os.name != "nt" and metadata.st_mode & 0o077:
                raise OSError
            encoded = self.key_file.read_bytes()
            if not encoded or len(encoded) > 8192:
                raise OSError
            data = json.loads(encoded.decode("utf-8"))
            if (not isinstance(data, dict) or data.get("format_version") != 1
                    or not isinstance(data.get("active_key_id"), str)
                    or not self._KEY_ID.fullmatch(data["active_key_id"])
                    or not isinstance(data.get("keys"), dict) or not 1 <= len(data["keys"]) <= 8):
                raise OSError
            keys = {}
            for key_id, hex_key in data["keys"].items():
                if (not isinstance(key_id, str) or not self._KEY_ID.fullmatch(key_id)
                        or not isinstance(hex_key, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", hex_key)):
                    raise OSError
                keys[key_id] = bytes.fromhex(hex_key)
            active = data["active_key_id"]
            if active not in keys:
                raise OSError
            return active, keys
        except (OSError, UnicodeError, ValueError):
            raise VaultUnavailable from None

    def put(self, secret: bytes) -> str:
        if not isinstance(secret, bytes) or not 1 <= len(secret) <= self._MAX_SECRET_BYTES:
            raise VaultUnavailable
        key_id, keys = self._keyring()
        reference = f"{uuid4().hex}.agcm"
        nonce = secrets.token_bytes(12)
        key_id_bytes = key_id.encode("ascii")
        payload = self._VERSION + bytes((len(key_id_bytes),)) + key_id_bytes + nonce + AESGCM(keys[key_id]).encrypt(
            nonce, secret, self._AAD_PREFIX + reference.encode("ascii") + b"\x00" + key_id_bytes
        )
        target = self.directory / reference
        temporary = self.directory / f".{uuid4().hex}.tmp"
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            if os.name != "nt":
                os.chmod(target, 0o600)
            return reference
        except OSError:
            temporary.unlink(missing_ok=True)
            raise VaultUnavailable from None

    def get(self, reference: str) -> bytes:
        if not isinstance(reference, str) or not self._NAME.fullmatch(reference):
            raise VaultUnavailable
        try:
            target = self.directory / reference
            if target.is_symlink() or not target.is_file():
                raise OSError
            metadata = target.stat()
            if (os.name != "nt" and metadata.st_mode & 0o077) or not 30 <= metadata.st_size <= self._MAX_SECRET_BYTES + 64:
                raise OSError
            payload = target.read_bytes()
            if payload[:1] != self._VERSION or len(payload) < 31:
                raise OSError
            id_length = payload[1]
            if not 1 <= id_length <= 32 or len(payload) < 2 + id_length + 12 + 16:
                raise OSError
            key_id_bytes = payload[2:2 + id_length]
            key_id = key_id_bytes.decode("ascii")
            if not self._KEY_ID.fullmatch(key_id):
                raise OSError
            _active, keys = self._keyring()
            key = keys.get(key_id)
            if key is None:
                raise OSError
            nonce_start = 2 + id_length
            nonce = payload[nonce_start:nonce_start + 12]
            ciphertext = payload[nonce_start + 12:]
            return AESGCM(key).decrypt(
                nonce, ciphertext, self._AAD_PREFIX + reference.encode("ascii") + b"\x00" + key_id_bytes
            )
        except Exception:
            raise VaultUnavailable from None

    def delete(self, reference: str) -> None:
        if not isinstance(reference, str) or not self._NAME.fullmatch(reference):
            raise VaultUnavailable
        try:
            target = self.directory / reference
            if target.is_symlink():
                raise OSError
            target.unlink(missing_ok=True)
        except OSError:
            raise VaultUnavailable from None

    def reencrypt_all(self) -> int:
        """Re-encrypt all stored references with the keyring's active version.

        Operators must stop the API and keep previous key versions in the
        protected keyring until verification finishes. This operation is
        restartable: mixed key versions remain decryptable during rotation.
        """
        active, keys = self._keyring()
        changed = 0
        for path in self.directory.glob("*.agcm"):
            reference = path.name
            clear = self.get(reference)
            payload = path.read_bytes()
            id_length = payload[1]
            key_id = payload[2:2 + id_length].decode("ascii")
            if key_id == active:
                continue
            key_id_bytes = active.encode("ascii")
            nonce = secrets.token_bytes(12)
            encrypted = self._VERSION + bytes((len(key_id_bytes),)) + key_id_bytes + nonce + AESGCM(keys[active]).encrypt(
                nonce, clear, self._AAD_PREFIX + reference.encode("ascii") + b"\x00" + key_id_bytes
            )
            temporary = self.directory / f".{uuid4().hex}.rotate"
            try:
                descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(encrypted)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, path)
                if os.name != "nt":
                    os.chmod(path, 0o600)
            except OSError:
                temporary.unlink(missing_ok=True)
                raise VaultUnavailable from None
            changed += 1
        return changed

    def key_usage(self) -> dict[str, int]:
        """Verify every ciphertext and report counts by key version only."""
        self._keyring()
        usage: Counter[str] = Counter()
        for path in self.directory.glob("*.agcm"):
            reference = path.name
            if not self._NAME.fullmatch(reference) or path.is_symlink():
                raise VaultUnavailable
            payload = path.read_bytes()
            if len(payload) < 31 or payload[:1] != self._VERSION:
                raise VaultUnavailable
            size = payload[1]
            try:
                key_id = payload[2:2 + size].decode("ascii")
            except UnicodeDecodeError:
                raise VaultUnavailable from None
            if not self._KEY_ID.fullmatch(key_id):
                raise VaultUnavailable
            self.get(reference)
            usage[key_id] += 1
        return dict(usage)

    def rotate_key(self, key_id: str) -> None:
        """Add a new active key while retaining versions needed by old files."""
        if not isinstance(key_id, str) or not self._KEY_ID.fullmatch(key_id):
            raise VaultUnavailable
        _active, keys = self._keyring()
        if key_id in keys or len(keys) >= 8:
            raise VaultUnavailable
        keys[key_id] = secrets.token_bytes(32)
        self._write_keyring(key_id, keys)

    def prune_key(self, key_id: str) -> None:
        """Remove an inactive key only after no stored envelope references it."""
        active, keys = self._keyring()
        if key_id == active or key_id not in keys or self.key_usage().get(key_id, 0):
            raise VaultUnavailable
        del keys[key_id]
        self._write_keyring(active, keys)

    def _write_keyring(self, active: str, keys: dict[str, bytes]) -> None:
        temporary = self.key_file.with_name(f".{self.key_file.name}.{uuid4().hex}.tmp")
        try:
            data = {
                "format_version": 1,
                "active_key_id": active,
                "keys": {key_id: value.hex() for key_id, value in sorted(keys.items())},
            }
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(data, stream, sort_keys=True, separators=(",", ":"))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.key_file)
            if os.name != "nt":
                os.chmod(self.key_file, 0o600)
        except OSError:
            temporary.unlink(missing_ok=True)
            raise VaultUnavailable from None
