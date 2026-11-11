"""Windows CurrentUser DPAPI vault for provider and TOTP secrets.

PostgreSQL stores only opaque references. The files contain DPAPI-protected
bytes and are intended to live in the local pilot's operator-only ACL folder.
This deliberately fails closed outside Windows rather than weakening storage.
"""

from __future__ import annotations

import ctypes
import os
import re
from ctypes import wintypes
from pathlib import Path
from uuid import uuid4


class VaultUnavailable(RuntimeError):
    pass


class DpapiSecretVault:
    _NAME = re.compile(r"^[a-f0-9]{32}\.dpapi$")
    _ENTROPY = b"Rahgard:AIProviderAdmin:secret-v1"
    _MAX_SECRET_BYTES = 16_384

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def put(self, secret: bytes) -> str:
        if (
            os.name != "nt"
            or not isinstance(secret, bytes)
            or not 1 <= len(secret) <= self._MAX_SECRET_BYTES
        ):
            raise VaultUnavailable
        # The pilot runner must create and ACL-protect this directory before
        # enabling the admin API. Do not implicitly create an unreviewed path.
        if not self.directory.is_dir():
            raise VaultUnavailable
        reference = f"{uuid4().hex}.dpapi"
        encrypted = _dpapi(secret, self._ENTROPY, decrypt=False)
        path = self.directory / reference
        try:
            with path.open("xb") as stream:
                stream.write(encrypted)
        except OSError:
            raise VaultUnavailable from None
        return reference

    def get(self, reference: str) -> bytes:
        if os.name != "nt" or not isinstance(reference, str) or not self._NAME.fullmatch(reference):
            raise VaultUnavailable
        try:
            encrypted = (self.directory / reference).read_bytes()
            if not 1 <= len(encrypted) <= self._MAX_SECRET_BYTES + 4096:
                raise VaultUnavailable
            clear = _dpapi(encrypted, self._ENTROPY, decrypt=True)
            if not 1 <= len(clear) <= self._MAX_SECRET_BYTES:
                raise VaultUnavailable
            return clear
        except (OSError, ValueError):
            raise VaultUnavailable from None

    def delete(self, reference: str) -> None:
        if os.name != "nt" or not isinstance(reference, str) or not self._NAME.fullmatch(reference):
            raise VaultUnavailable
        try:
            (self.directory / reference).unlink(missing_ok=True)
        except OSError:
            raise VaultUnavailable from None


def _dpapi(data: bytes, entropy: bytes, *, decrypt: bool) -> bytes:
    if os.name != "nt":
        raise VaultUnavailable

    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    def blob(value: bytes):
        buf = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
        return DataBlob(len(value), ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte))), buf

    source, source_buffer = blob(data)
    entropy_blob, entropy_buffer = blob(entropy)
    output = DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    local_free = kernel32.LocalFree
    local_free.argtypes = [ctypes.c_void_p]
    local_free.restype = ctypes.c_void_p
    if decrypt:
        description = wintypes.LPWSTR()
        fn = crypt32.CryptUnprotectData
        fn.argtypes = [
            ctypes.POINTER(DataBlob),
            ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DataBlob),
        ]
        fn.restype = wintypes.BOOL
        ok = fn(
            ctypes.byref(source),
            ctypes.byref(description),
            ctypes.byref(entropy_blob),
            None,
            None,
            0x1,
            ctypes.byref(output),
        )
    else:
        description = None
        fn = crypt32.CryptProtectData
        fn.argtypes = [
            ctypes.POINTER(DataBlob),
            wintypes.LPCWSTR,
            ctypes.POINTER(DataBlob),
            ctypes.c_void_p,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(DataBlob),
        ]
        fn.restype = wintypes.BOOL
        ok = fn(
            ctypes.byref(source),
            "Rahgard AI provider secret",
            ctypes.byref(entropy_blob),
            None,
            None,
            0x1,
            ctypes.byref(output),
        )
    if not ok:
        raise VaultUnavailable
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        local_free(output.pbData)
        if description:
            local_free(description)
        _ = source_buffer, entropy_buffer
