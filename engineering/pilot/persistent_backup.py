"""Operator-triggered backup of a separately provisioned private pilot database.

This tool does not provision a database, schedule backups, choose retention, or
restore into any database. It needs the operator's explicit confirmation, a
PG17 database bearing the private-pilot marker, verify-full TLS, and a
separately provisioned non-superuser ai_tourism_backup role. Secrets are read
only from the process environment. Never point this tool at a shared DB.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import struct
import stat
import subprocess
import sys
import threading
from typing import BinaryIO, Mapping
from uuid import uuid4

_DATABASE = re.compile(r"rahgard_pilot_[a-z0-9_]{3,40}\Z")
_MARKER = re.compile(r"[a-fA-F0-9]{32,128}\Z")
_HOST = re.compile(r"[a-zA-Z0-9.-]{1,253}\Z")
_LOCAL_CONTAINER = re.compile(r"rahgard-local-pg17-[a-f0-9]{12}\Z")
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DPAPI_MAGIC = b"RAHGARD-DPAPI-BACKUP\x00\x01\n"
_DPAPI_SCHEMA = "rahgard.dpapi-backup.v2"
_DPAPI_CHUNK_SIZE = 1024 * 1024
_MARKER_SQL = """SELECT current_database(), current_user,
current_setting('server_version_num'),
(SELECT count(*) FROM public.rahgard_private_pilot_marker),
(SELECT min(marker_value) FROM public.rahgard_private_pilot_marker),
rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls,
(SELECT count(*) FROM pg_roles r WHERE pg_has_role(current_user, r.oid, 'MEMBER')
 AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR r.rolbypassrls)),
has_database_privilege(current_user, current_database(), 'CREATE')
FROM pg_roles WHERE rolname=current_user"""


class BackupBlocked(ValueError):
    """A safety precondition or a database tool invocation failed."""


_WINDOWS_ACL_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$path = $env:RAHGARD_ACL_PATH
$mode = $env:RAHGARD_ACL_MODE
$item = Get-Item -LiteralPath $path -Force
if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'reparse' }
$currentSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
if ($mode -eq 'secure-file') {
    if ($item.PSIsContainer) { throw 'not-file' }
    $acl = Get-Acl -LiteralPath $path
    if ($acl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $currentSid) { throw 'owner' }
    $acl.SetAccessRuleProtection($true, $false)
    foreach ($rule in @($acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]))) {
        [void]$acl.RemoveAccessRuleAll($rule)
    }
    foreach ($sidText in @($currentSid, 'S-1-5-18')) {
        $sid = [Security.Principal.SecurityIdentifier]::new($sidText)
        $rule = [Security.AccessControl.FileSystemAccessRule]::new(
            $sid, [Security.AccessControl.FileSystemRights]::FullControl,
            [Security.AccessControl.AccessControlType]::Allow)
        [void]$acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $path -AclObject $acl
}
$acl = Get-Acl -LiteralPath $path
$owner = $acl.GetOwner([Security.Principal.SecurityIdentifier]).Value
$rules = @($acl.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier]) | ForEach-Object {
    [ordered]@{
        sid = $_.IdentityReference.Value
        type = $_.AccessControlType.ToString()
        rights = [int]$_.FileSystemRights
        inherited = [bool]$_.IsInherited
        inheritance = [int]$_.InheritanceFlags
        propagation = [int]$_.PropagationFlags
    }
})
[ordered]@{
    owner = $owner
    current_sid = $currentSid
    protected = [bool]$acl.AreAccessRulesProtected
    canonical = [bool]$acl.AreAccessRulesCanonical
    is_directory = [bool]$item.PSIsContainer
    rules = $rules
} | ConvertTo-Json -Depth 5 -Compress
"""


def _windows_attributes(path: Path) -> int:
    """Read attributes without following the final reparse point."""
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_attributes = kernel32.GetFileAttributesW
    get_attributes.argtypes = [wintypes.LPCWSTR]
    get_attributes.restype = wintypes.DWORD
    attributes = get_attributes(str(path))
    if attributes == 0xFFFFFFFF:
        raise BackupBlocked("private storage path could not be inspected")
    return int(attributes)


def _windows_is_remote_drive(anchor: str) -> bool:
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    get_drive_type = kernel32.GetDriveTypeW
    get_drive_type.argtypes = [wintypes.LPCWSTR]
    get_drive_type.restype = wintypes.UINT
    return get_drive_type(anchor) == 4  # DRIVE_REMOTE


def _reject_windows_reparse_components(path: Path) -> None:
    absolute = Path(os.path.abspath(path))
    if absolute.anchor.startswith("\\\\"):
        raise BackupBlocked("network share storage is not permitted")
    if _windows_is_remote_drive(absolute.anchor):
        raise BackupBlocked("mapped network drive storage is not permitted")
    for component in reversed((absolute, *absolute.parents)):
        try:
            attributes = _windows_attributes(component)
        except BackupBlocked:
            # A missing component cannot resolve through a reparse point. The
            # requested leaf itself is checked separately as an existing dir.
            if component == absolute:
                raise
            continue
        if attributes & 0x00000400:  # FILE_ATTRIBUTE_REPARSE_POINT
            raise BackupBlocked("private storage path contains a reparse point")


def _powershell_acl(path: Path, mode: str = "inspect") -> dict:
    if mode not in {"inspect", "secure-file"}:
        raise BackupBlocked("private storage ACL operation is invalid")
    child_env = {"SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
                 "WINDIR": os.environ.get("WINDIR", r"C:\Windows"),
                 "PATH": os.environ.get("PATH", ""),
                 "RAHGARD_ACL_PATH": str(path), "RAHGARD_ACL_MODE": mode}
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", _WINDOWS_ACL_SCRIPT],
            env=child_env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=True, timeout=15, text=True, encoding="utf-8",
        )
        import json
        payload = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError, TypeError):
        raise BackupBlocked("NTFS ACL could not be verified") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("rules"), list):
        raise BackupBlocked("NTFS ACL inspection returned an invalid result")
    return payload


def _windows_current_sid() -> str:
    child_env = {"SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
                 "WINDIR": os.environ.get("WINDIR", r"C:\Windows"),
                 "PATH": os.environ.get("PATH", "")}
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command",
             "[Security.Principal.WindowsIdentity]::GetCurrent().User.Value"],
            env=child_env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=True, timeout=15, text=True, encoding="utf-8",
        )
        sid = result.stdout.strip()
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise BackupBlocked("current Windows security identity could not be verified") from None
    if not re.fullmatch(r"S-1-[0-9-]{4,100}", sid):
        raise BackupBlocked("current Windows security identity is invalid")
    return sid


def _verify_windows_acl(path: Path, *, directory: bool) -> None:
    audit = _powershell_acl(path)
    owner = audit.get("owner")
    current_sid = audit.get("current_sid")
    if (not isinstance(owner, str) or owner != current_sid
            or audit.get("protected") is not True or audit.get("canonical") is not True
            or audit.get("is_directory") is not directory):
        raise BackupBlocked("NTFS ACL owner, inheritance, or object type is unsafe")
    entries = audit["rules"]
    if not entries:
        raise BackupBlocked("NTFS ACL has no explicit private access rules")
    allowed_sids = {current_sid, "S-1-5-18"}  # current operator and LocalSystem only
    found = set()
    for entry in entries:
        if (not isinstance(entry, dict) or entry.get("sid") not in allowed_sids
                or entry.get("type") != "Allow" or entry.get("inherited") is not False
                or entry.get("propagation") != 0 or type(entry.get("rights")) is not int):
            raise BackupBlocked("NTFS ACL grants access outside the operator and LocalSystem")
        if directory and entry.get("inheritance") != 3:  # ObjectInherit | ContainerInherit
            raise BackupBlocked("NTFS directory ACL does not safely protect child files")
        if not directory and entry.get("inheritance") != 0:
            raise BackupBlocked("NTFS backup file ACL unexpectedly inherits access")
        if entry["rights"] != 2032127:  # FileSystemRights.FullControl
            raise BackupBlocked("NTFS ACL contains an unexpected or partial access mask")
        found.add(entry["sid"])
    if not allowed_sids.issubset(found):
        raise BackupBlocked("NTFS ACL must explicitly allow only the operator and LocalSystem")


def _dpapi_transform(data: bytes, entropy: bytes, *, decrypt: bool) -> bytes:
    """Protect/unprotect one bounded frame with DPAPI CurrentUser scope."""
    if os.name != "nt":
        raise BackupBlocked("Windows DPAPI CurrentUser is unavailable on this platform")
    import ctypes
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    def make_blob(value: bytes):
        buffer = (ctypes.c_ubyte * len(value)).from_buffer_copy(value)
        return DataBlob(len(value), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))), buffer

    source, source_buffer = make_blob(data)
    entropy_blob, entropy_buffer = make_blob(entropy)
    output = DataBlob()
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    local_free = kernel32.LocalFree
    local_free.argtypes = [ctypes.c_void_p]
    local_free.restype = ctypes.c_void_p
    if decrypt:
        description = wintypes.LPWSTR()
        function = crypt32.CryptUnprotectData
        function.argtypes = [ctypes.POINTER(DataBlob), ctypes.POINTER(wintypes.LPWSTR),
                             ctypes.POINTER(DataBlob), ctypes.c_void_p, ctypes.c_void_p,
                             wintypes.DWORD, ctypes.POINTER(DataBlob)]
        function.restype = wintypes.BOOL
        succeeded = function(ctypes.byref(source), ctypes.byref(description), ctypes.byref(entropy_blob),
                             None, None, 0x1, ctypes.byref(output))
    else:
        function = crypt32.CryptProtectData
        function.argtypes = [ctypes.POINTER(DataBlob), wintypes.LPCWSTR, ctypes.POINTER(DataBlob),
                             ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DataBlob)]
        function.restype = wintypes.BOOL
        succeeded = function(ctypes.byref(source), "Rahgard private pilot backup",
                             ctypes.byref(entropy_blob), None, None, 0x1, ctypes.byref(output))
    if not succeeded:
        error = ctypes.get_last_error()
        raise BackupBlocked(f"Windows DPAPI CurrentUser operation failed (code {error})")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        local_free(output.pbData)
        if decrypt and description:
            local_free(description)
        # Keep the input buffers alive through the native call.
        _ = source_buffer, entropy_buffer


def _dpapi_header(chunk_size: int = _DPAPI_CHUNK_SIZE) -> tuple[dict, bytes]:
    if type(chunk_size) is not int or not 4096 <= chunk_size <= 4 * 1024 * 1024:
        raise BackupBlocked("backup envelope bounds are invalid")
    header = {
        "schema": _DPAPI_SCHEMA,
        "protection": "Windows DPAPI CurrentUser",
        "chunk_size": chunk_size,
        "created_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    encoded = json.dumps(header, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > 4096:
        raise BackupBlocked("backup envelope metadata exceeds its bound")
    return header, encoded


def _frame_entropy(header_bytes: bytes, index: int, *, footer: bool = False) -> bytes:
    kind = b"manifest" if footer else b"frame"
    return hashlib.sha256(b"rahgard-dpapi-envelope-v2\x00" + kind
                         + hashlib.sha256(header_bytes).digest() + index.to_bytes(8, "big")).digest()


def _write_dpapi_envelope(source: BinaryIO, target: BinaryIO, *, protector=None,
                          chunk_size: int = _DPAPI_CHUNK_SIZE) -> dict:
    protector = protector or (lambda data, entropy: _dpapi_transform(data, entropy, decrypt=False))
    header, header_bytes = _dpapi_header(chunk_size)
    target.write(_DPAPI_MAGIC)
    target.write(struct.pack(">I", len(header_bytes)))
    target.write(header_bytes)
    digest = hashlib.sha256()
    written = 0
    count = 0
    while plaintext := source.read(chunk_size):
        if len(plaintext) > chunk_size:
            raise BackupBlocked("backup source returned an oversized frame")
        digest.update(plaintext)
        protected = protector(plaintext, _frame_entropy(header_bytes, count))
        if not isinstance(protected, bytes) or not protected or len(protected) > chunk_size + 65536:
            raise BackupBlocked("Windows DPAPI returned an invalid protected frame")
        target.write(struct.pack(">I", len(protected)))
        target.write(protected)
        written += len(plaintext)
        count += 1
    manifest = {"plaintext_bytes": written, "record_count": count,
                "plaintext_sha256": digest.hexdigest()}
    manifest_bytes = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    protected_manifest = protector(manifest_bytes, _frame_entropy(header_bytes, count, footer=True))
    if not isinstance(protected_manifest, bytes) or not protected_manifest or len(protected_manifest) > 8192:
        raise BackupBlocked("Windows DPAPI returned an invalid encrypted manifest")
    target.write(struct.pack(">I", 0))  # frame terminator
    target.write(struct.pack(">I", len(protected_manifest)))
    target.write(protected_manifest)
    target.flush()
    return {**header, **manifest}


def _read_dpapi_header(source: BinaryIO) -> tuple[dict, bytes]:
    if source.read(len(_DPAPI_MAGIC)) != _DPAPI_MAGIC:
        raise BackupBlocked("backup archive is not a Rahgard DPAPI envelope")
    raw_length = source.read(4)
    if len(raw_length) != 4:
        raise BackupBlocked("backup envelope header is truncated")
    header_length = struct.unpack(">I", raw_length)[0]
    if not 1 <= header_length <= 4096:
        raise BackupBlocked("backup envelope header length is invalid")
    header_bytes = source.read(header_length)
    if len(header_bytes) != header_length:
        raise BackupBlocked("backup envelope header is truncated")
    try:
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate field")
                result[key] = value
            return result
        header = json.loads(header_bytes.decode("utf-8"), object_pairs_hook=unique_pairs)
    except (UnicodeError, ValueError):
        raise BackupBlocked("backup envelope metadata is invalid") from None
    expected_keys = {"schema", "protection", "chunk_size", "created_at"}
    if (not isinstance(header, dict) or set(header) != expected_keys
            or header["schema"] != _DPAPI_SCHEMA
            or header["protection"] != "Windows DPAPI CurrentUser"
            or type(header["chunk_size"]) is not int or not 4096 <= header["chunk_size"] <= 4 * 1024 * 1024
            or not isinstance(header["created_at"], str) or len(header["created_at"]) > 40):
        raise BackupBlocked("backup envelope metadata failed validation")
    return header, header_bytes


def _decrypt_dpapi_envelope(source: BinaryIO, target: BinaryIO, *, unprotector=None) -> dict:
    unprotector = unprotector or (lambda data, entropy: _dpapi_transform(data, entropy, decrypt=True))
    header, header_bytes = _read_dpapi_header(source)
    try:
        frame_offset = source.tell()
        source.seek(0, os.SEEK_END)
        envelope_length = source.tell()
        source.seek(frame_offset)
        maximum_frames = max(0, (envelope_length - frame_offset - 8) // 5)
    except BackupBlocked:
        raise
    except (OSError, ValueError):
        raise BackupBlocked("backup envelope source is not seekable") from None
    digest = hashlib.sha256()
    written = 0
    count = 0
    while True:
        raw_length = source.read(4)
        if len(raw_length) != 4:
            raise BackupBlocked("encrypted backup frame is truncated")
        frame_length = struct.unpack(">I", raw_length)[0]
        if frame_length == 0:
            break
        if count >= maximum_frames or not 1 <= frame_length <= header["chunk_size"] + 65536:
            raise BackupBlocked("encrypted backup frame count or length is invalid")
        protected = source.read(frame_length)
        if len(protected) != frame_length:
            raise BackupBlocked("encrypted backup frame is truncated")
        plaintext = unprotector(protected, _frame_entropy(header_bytes, count))
        if not isinstance(plaintext, bytes) or not 1 <= len(plaintext) <= header["chunk_size"]:
            raise BackupBlocked("DPAPI could not authenticate this backup for the current Windows user")
        digest.update(plaintext)
        target.write(plaintext)
        written += len(plaintext)
        count += 1
    manifest_length_raw = source.read(4)
    if len(manifest_length_raw) != 4:
        raise BackupBlocked("encrypted backup manifest is missing")
    manifest_length = struct.unpack(">I", manifest_length_raw)[0]
    if not 1 <= manifest_length <= 8192:
        raise BackupBlocked("encrypted backup manifest length is invalid")
    protected_manifest = source.read(manifest_length)
    if len(protected_manifest) != manifest_length or source.read(1):
        raise BackupBlocked("encrypted backup manifest is truncated or has trailing bytes")
    try:
        manifest_bytes = unprotector(protected_manifest, _frame_entropy(header_bytes, count, footer=True))
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError("duplicate field")
                result[key] = value
            return result
        manifest = json.loads(manifest_bytes.decode("utf-8"), object_pairs_hook=unique_pairs)
    except (BackupBlocked, UnicodeError, ValueError, TypeError):
        raise BackupBlocked("DPAPI could not authenticate the backup manifest") from None
    if (not isinstance(manifest, dict)
            or set(manifest) != {"plaintext_bytes", "record_count", "plaintext_sha256"}
            or type(manifest["plaintext_bytes"]) is not int or manifest["plaintext_bytes"] != written
            or type(manifest["record_count"]) is not int or manifest["record_count"] != count
            or not isinstance(manifest["plaintext_sha256"], str)
            or not hmac.compare_digest(manifest["plaintext_sha256"], digest.hexdigest())):
        raise BackupBlocked("encrypted backup manifest failed integrity verification")
    target.flush()
    return {**header, **manifest}


def _verify_dpapi_envelope(source: BinaryIO, expected_size: int, expected_sha256: str,
                           *, unprotector=None) -> dict:
    class Sink:
        def __init__(self):
            self.digest = hashlib.sha256()
            self.length = 0
        def write(self, chunk):
            self.digest.update(chunk)
            self.length += len(chunk)
            return len(chunk)
        def flush(self):
            return None
    sink = Sink()
    metadata = _decrypt_dpapi_envelope(source, sink, unprotector=unprotector)
    if sink.length != expected_size or not hmac.compare_digest(sink.digest.hexdigest(), expected_sha256):
        raise BackupBlocked("encrypted backup verification did not match source archive")
    return metadata


def _dpapi_envelope_metadata(source: BinaryIO) -> dict:
    class Sink:
        def write(self, chunk):
            return len(chunk)
        def flush(self):
            return None
    return _decrypt_dpapi_envelope(source, Sink())


def _timeout_kill(process: subprocess.Popen) -> threading.Timer:
    def kill_if_running():
        try:
            if process.poll() is None:
                process.kill()
        except OSError:
            pass
    timer = threading.Timer(3600, kill_if_running)
    timer.daemon = True
    timer.start()
    return timer


def _pipe_pg_dump_to_dpapi(command: list[str], child_env: Mapping[str, str], target: BinaryIO) -> dict:
    """Stream pg_dump directly into encrypted frames; never stage plaintext on disk."""
    try:
        process = subprocess.Popen(_database_tool_command(command, child_env), env=dict(child_env), stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL)
    except OSError:
        raise BackupBlocked("database dump process could not be started") from None
    timer = _timeout_kill(process)
    try:
        if process.stdout is None:
            raise BackupBlocked("database dump output stream is unavailable")
        metadata = _write_dpapi_envelope(process.stdout, target)
        process.stdout.close()
        return_code = process.wait(timeout=3605)
        if return_code != 0:
            raise BackupBlocked("database dump process failed before archive completion")
        return metadata
    except Exception:
        try:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass
        raise
    finally:
        timer.cancel()
        if process.stdout is not None and not process.stdout.closed:
            process.stdout.close()


def _pg_restore_list_dpapi(path: Path, child_env: Mapping[str, str]) -> dict:
    """Validate a DPAPI archive through an OS pipe, with no plaintext file."""
    try:
        process = subprocess.Popen(_database_tool_command(["pg_restore", "--list"], child_env), env=dict(child_env),
                                   stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
    except OSError:
        raise BackupBlocked("archive verification process could not be started") from None
    timer = _timeout_kill(process)
    try:
        if process.stdin is None:
            raise BackupBlocked("archive verification input stream is unavailable")
        with path.open("rb") as source:
            metadata = _decrypt_dpapi_envelope(source, process.stdin)
        process.stdin.close()
        return_code = process.wait(timeout=3605)
        if return_code != 0:
            raise BackupBlocked("pg_restore rejected the decrypted private backup")
        return metadata
    except Exception:
        try:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
        except (OSError, subprocess.SubprocessError):
            pass
        raise
    finally:
        timer.cancel()
        if process.stdin is not None and not process.stdin.closed:
            process.stdin.close()


def _private_storage(path: str) -> Path:
    """Require verifiably private, owner-controlled storage outside the repo."""
    requested = Path(path).absolute()
    if os.name == "nt":
        _reject_windows_reparse_components(requested)
    directory = requested.resolve(strict=True)
    if os.name == "nt":
        _reject_windows_reparse_components(directory)
    if directory == _REPOSITORY_ROOT or _REPOSITORY_ROOT in directory.parents:
        raise BackupBlocked("private data storage must be outside the repository")
    if os.name == "nt":
        _verify_windows_acl(directory, directory=True)
        return directory
    if not hasattr(os, "geteuid"):
        raise BackupBlocked("private directory permissions cannot be verified on this platform")
    info = directory.stat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise BackupBlocked("private directory must be owned by the operator and mode 0700 or stricter")
    return directory


def validate_config(env: Mapping[str, str]) -> dict[str, str]:
    host = env.get("RAHGARD_PILOT_PGHOST", "")
    port = env.get("RAHGARD_PILOT_PGPORT", "")
    database = env.get("RAHGARD_PILOT_DATABASE", "")
    marker = env.get("RAHGARD_PILOT_DATABASE_MARKER", "")
    backup_dir = env.get("RAHGARD_PILOT_BACKUP_DIR", "")
    root_cert = env.get("PGSSLROOTCERT", "")
    docker_container = env.get("RAHGARD_PILOT_DOCKER_CONTAINER", "")
    if (
        not _HOST.fullmatch(host)
        or not port.isascii() or not port.isdigit()
        or not 1024 <= int(port) <= 65535 or int(port) == 55433
        or not _DATABASE.fullmatch(database)
        or not _MARKER.fullmatch(marker)
        or not backup_dir or not root_cert
            or (not docker_container and not (env.get("PGPASSWORD") or env.get("PGPASSFILE")))
            or (docker_container and not _LOCAL_CONTAINER.fullmatch(docker_container))
    ):
        raise BackupBlocked("private pilot backup configuration is incomplete or unsafe")
    directory = _private_storage(backup_dir)
    certificate = Path(root_cert).resolve(strict=True)
    if not directory.is_dir() or not certificate.is_file():
        raise BackupBlocked("backup directory or TLS root certificate is invalid")
    return {"host": host, "port": port, "database": database,
            "marker": marker.lower(), "backup_dir": str(directory), "root_cert": str(certificate),
            "docker_container": docker_container}


def _run(command: list[str], *, env: Mapping[str, str], stdout=subprocess.PIPE, stdin=None) -> subprocess.CompletedProcess:
    tool = Path(command[0]).name
    command = _database_tool_command(command, env)
    try:
        return subprocess.run(command, env=dict(env), stdout=stdout, stdin=stdin, stderr=subprocess.PIPE,
                              check=True, timeout=3600)
    except OSError as exc:
        raise BackupBlocked(f"required database tool unavailable: {tool}") from exc
    except subprocess.CalledProcessError as exc:
        diagnostic = _safe_database_tool_diagnostic(exc.stderr)
        suffix = f"; {diagnostic}" if diagnostic else ""
        raise BackupBlocked(f"database verification command failed: {tool} (exit {exc.returncode}){suffix}") from exc
    except subprocess.SubprocessError as exc:
        raise BackupBlocked(f"database verification command failed: {tool}") from exc


def _safe_database_tool_diagnostic(stderr: bytes | None) -> str:
    """Return one bounded PostgreSQL error line with literals/URLs masked."""
    if not stderr:
        return ""
    try:
        lines = stderr.decode("utf-8", errors="replace").splitlines()
    except Exception:
        return ""
    line = next((value for value in lines if "ERROR:" in value), "")
    if not line:
        return ""
    line = line.split("ERROR:", 1)[-1].strip()
    line = re.sub(r"'[^']{0,512}'", "'<value>'", line)
    line = re.sub(r"(?i)(postgres(?:ql)?://)\S+", "<database-uri>", line)
    line = re.sub(r"(?i)(password\s*[=:]\s*)\S+", r"\1<redacted>", line)
    return line[:180]


def _database_tool_command(command: list[str], env: Mapping[str, str]) -> list[str]:
    """Use the PostgreSQL clients in the already-validated private container."""
    container = env.get("RAHGARD_PILOT_DOCKER_CONTAINER", "")
    if not container:
        return command
    if not _LOCAL_CONTAINER.fullmatch(container) or Path(command[0]).name not in {"psql", "pg_dump", "pg_restore"}:
        raise BackupBlocked("private local database tool binding is invalid")
    # The runner verifies this exact task-owned container, marker, loopback
    # port and persistent bind mount. The client connects through its local
    # Unix socket, so Windows needs no separately installed PostgreSQL tools.
    # No password is put on docker's command line or sent in its environment.
    return ["docker", "exec", "-i", container, *command]


def backup(config: Mapping[str, str], env: Mapping[str, str], *, confirmed: bool) -> Path:
    if not confirmed:
        raise BackupBlocked("explicit private-pilot backup confirmation is required")
    child_env = {key: value for key, value in env.items() if key in {
        "PATH", "SystemRoot", "SYSTEMROOT", "WINDIR", "TEMP", "TMP",
        "PGPASSWORD", "PGPASSFILE", "RAHGARD_PILOT_DOCKER_CONTAINER",
    }}
    child_env.update({"PGSSLMODE": "verify-full", "PGSSLROOTCERT": config["root_cert"],
                      "PGAPPNAME": "rahgard-private-pilot-backup"})
    endpoint = (["-U", "ai_tourism_backup", "-d", config["database"], "-w"] if config["docker_container"]
                else ["-h", config["host"], "-p", config["port"], "-U", "ai_tourism_backup",
                      "-d", config["database"], "-w"])
    check = _run(["psql", *endpoint, "-X", "-q", "-t", "-A", "-F", "\t", "-c", _MARKER_SQL], env=child_env)
    fields = check.stdout.decode("utf-8").strip().split("\t")
    if (len(fields) != 12 or fields[0] != config["database"] or fields[1] != "ai_tourism_backup"
            or not fields[2].isdigit() or not 170000 <= int(fields[2]) < 180000
            or fields[3] != "1" or fields[4].lower() != config["marker"]
            or fields[5:10] != ["f"] * 5 or fields[10:] != ["0", "f"]):
        raise BackupBlocked("private pilot database marker, engine, or backup role did not match")
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    directory = _private_storage(config["backup_dir"])
    windows = os.name == "nt"
    suffix = ".dump.dpapi" if windows else ".dump"
    final = directory / f"rahgard-pilot-{timestamp}-{uuid4().hex}{suffix}"
    partial = final.with_name(final.name + ".partial")
    created_partial = False
    try:
        if final.exists() or partial.exists():
            raise BackupBlocked("exclusive backup archive path already exists")
        if os.name == "nt":
            descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created_partial = True
            os.close(descriptor)
            _powershell_acl(partial, mode="secure-file")
            _verify_windows_acl(partial, directory=False)
            with partial.open("wb") as target:
                written_metadata = _pipe_pg_dump_to_dpapi(
                    ["pg_dump", *endpoint, "--format=custom"], child_env, target,
                )
            with partial.open("rb") as envelope:
                verified_metadata = _verify_dpapi_envelope(
                    envelope, written_metadata["plaintext_bytes"], written_metadata["plaintext_sha256"],
                )
            if written_metadata != verified_metadata:
                raise BackupBlocked("DPAPI backup envelope metadata did not verify")
            if _pg_restore_list_dpapi(partial, child_env) != written_metadata:
                raise BackupBlocked("pg_restore envelope validation did not match backup metadata")
        else:
            descriptor = os.open(partial, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            created_partial = True
            with os.fdopen(descriptor, "wb") as output:
                _run(["pg_dump", *endpoint, "--format=custom"], env=child_env, stdout=output)
            _run(["pg_restore", "--list", str(partial)], env=child_env, stdout=subprocess.DEVNULL)
        partial.rename(final)
        created_partial = False
        return final
    except Exception:
        if created_partial and partial.exists():
            partial.unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm-private-pilot", action="store_true")
    args = parser.parse_args(argv)
    try:
        config = validate_config(os.environ)
        path = backup(config, os.environ, confirmed=args.confirm_private_pilot)
    except BackupBlocked as exc:
        # These are fixed, secret-free operator diagnostics. Never include a
        # psycopg exception string, connection URL, or environment value.
        print(f"Private pilot backup blocked: {exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as exc:
        print(f"Private pilot backup blocked: {type(exc).__name__}", file=sys.stderr)
        return 1
    if os.name == "nt":
        with path.open("rb") as archive:
            metadata = _dpapi_envelope_metadata(archive)
        print(json.dumps({"status": "backup_created", "path": str(path), **metadata}, sort_keys=True))
    else:
        print(f"Verified archive created: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
