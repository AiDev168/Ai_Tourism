"""Offline guard tests; no database or external process is contacted."""

from types import SimpleNamespace
from io import BytesIO
from pathlib import Path
import os
import json
import sys
import struct

import pytest

from persistent_backup import (
    BackupBlocked, _decrypt_dpapi_envelope, _powershell_acl, _private_storage,
    _verify_windows_acl, _windows_attributes, _windows_current_sid, backup,
    _database_tool_command,
    validate_config, _write_dpapi_envelope,
    _pipe_pg_dump_to_dpapi,
)


@pytest.fixture
def pilot_env(tmp_path, monkeypatch):
    # Mock only the storage guard on Windows; that platform is otherwise
    # deliberately blocked until native ACL verification is implemented.
    monkeypatch.setattr("persistent_backup._private_storage", lambda path: Path(path).resolve(strict=True))
    monkeypatch.setattr("persistent_backup._powershell_acl", lambda *args, **kwargs: None)
    monkeypatch.setattr("persistent_backup._verify_windows_acl", lambda *args, **kwargs: None)
    monkeypatch.setattr("persistent_backup._dpapi_transform",
                        lambda data, entropy, *, decrypt: data[::-1])
    cert = tmp_path / "root.crt"
    cert.write_text("test only", encoding="utf-8")
    return {
        "RAHGARD_PILOT_PGHOST": "private-db.example.invalid",
        "RAHGARD_PILOT_PGPORT": "5432",
        "RAHGARD_PILOT_DATABASE": "rahgard_pilot_example",
        "RAHGARD_PILOT_DATABASE_MARKER": "ab" * 24,
        "RAHGARD_PILOT_BACKUP_DIR": str(tmp_path),
        "PGSSLROOTCERT": str(cert),
        "PGPASSWORD": "test-only-password",
    }


def test_repository_storage_is_rejected():
    import persistent_backup

    with pytest.raises(BackupBlocked):
        persistent_backup._private_storage(str(persistent_backup._REPOSITORY_ROOT))


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL gate")
def test_windows_private_acl_accepts_only_operator_and_system(tmp_path, monkeypatch):
    monkeypatch.setattr("persistent_backup._REPOSITORY_ROOT", tmp_path.parent / "unrelated-repository")
    directory = tmp_path / "private"
    directory.mkdir()
    sid = _windows_current_sid()
    result = __import__("subprocess").run(
        ["icacls.exe", str(directory), "/inheritance:r", "/grant:r",
         f"*{sid}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"],
        stdout=__import__("subprocess").DEVNULL,
        stderr=__import__("subprocess").DEVNULL, check=False, timeout=15,
    )
    assert result.returncode == 0
    assert _private_storage(str(directory)) == directory.resolve()

    backup_file = directory / "new.dump"
    descriptor = os.open(backup_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    _powershell_acl(backup_file, mode="secure-file")
    _verify_windows_acl(backup_file, directory=False)


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL gate")
def test_windows_acl_rejects_broad_allow_and_reparse_path(tmp_path, monkeypatch):
    monkeypatch.setattr("persistent_backup._REPOSITORY_ROOT", tmp_path.parent / "unrelated-repository")
    directory = tmp_path / "private-broad"
    directory.mkdir()
    sid = _windows_current_sid()
    subprocess = __import__("subprocess")
    secured = subprocess.run(
        ["icacls.exe", str(directory), "/inheritance:r", "/grant:r",
         f"*{sid}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=15,
    )
    assert secured.returncode == 0
    broad = subprocess.run(
        ["icacls.exe", str(directory), "/grant", "*S-1-1-0:(OI)(CI)R"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=15,
    )
    assert broad.returncode == 0
    with pytest.raises(BackupBlocked, match="outside the operator"):
        _private_storage(str(directory))

    clean = tmp_path / "private-clean"
    clean.mkdir()
    assert subprocess.run(
        ["icacls.exe", str(clean), "/inheritance:r", "/grant:r",
         f"*{sid}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=15,
    ).returncode == 0
    real_attributes = _windows_attributes
    monkeypatch.setattr("persistent_backup._windows_attributes", lambda path: (
        real_attributes(path) | 0x00000400 if path == clean else real_attributes(path)
    ))
    with pytest.raises(BackupBlocked, match="reparse point"):
        _private_storage(str(clean))

    monkeypatch.setattr("persistent_backup._windows_attributes", lambda path: (
        real_attributes(path) | 0x00000400 if path == clean.parent else real_attributes(path)
    ))
    with pytest.raises(BackupBlocked, match="reparse point"):
        _private_storage(str(clean))


@pytest.mark.skipif(os.name != "nt", reason="Windows network path gate")
def test_windows_storage_rejects_unc_and_mapped_network_paths(monkeypatch):
    import persistent_backup

    with pytest.raises(BackupBlocked, match="network share"):
        persistent_backup._reject_windows_reparse_components(Path(r"\\server\share\backup"))
    monkeypatch.setattr(persistent_backup, "_windows_is_remote_drive", lambda _anchor: True)
    with pytest.raises(BackupBlocked, match="mapped network drive"):
        persistent_backup._reject_windows_reparse_components(Path(r"Z:\backup"))


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL gate")
def test_windows_storage_rejects_inherited_entries(tmp_path, monkeypatch):
    monkeypatch.setattr("persistent_backup._REPOSITORY_ROOT", tmp_path.parent / "unrelated-repository")
    subprocess = __import__("subprocess")
    parent = tmp_path / "inherited-parent"
    child = parent / "backup"
    parent.mkdir()
    assert subprocess.run(
        ["icacls.exe", str(parent), "/grant", "*S-1-1-0:(OI)(CI)R"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=15,
    ).returncode == 0
    child.mkdir()
    audit = _powershell_acl(child)
    assert any(rule["inherited"] is True for rule in audit["rules"])
    with pytest.raises(BackupBlocked, match="inheritance"):
        _private_storage(str(child))


@pytest.mark.parametrize("field,value", [
    ("RAHGARD_PILOT_PGPORT", "55433"),
    ("RAHGARD_PILOT_DATABASE", "ai_tourism_dev"),
    ("RAHGARD_PILOT_DATABASE_MARKER", "too-short"),
    ("RAHGARD_PILOT_PGHOST", "bad host"),
])
def test_rejects_unsafe_target(pilot_env, field, value):
    pilot_env[field] = value
    with pytest.raises(BackupBlocked):
        validate_config(pilot_env)


def test_docker_client_binding_is_exact_and_never_forwards_arbitrary_commands():
    env = {"RAHGARD_PILOT_DOCKER_CONTAINER": "rahgard-local-pg17-ed735a549bba"}
    assert _database_tool_command(["pg_dump", "--format=custom"], env) == [
        "docker", "exec", "-i", "rahgard-local-pg17-ed735a549bba", "pg_dump", "--format=custom"
    ]
    with pytest.raises(BackupBlocked):
        _database_tool_command(["powershell", "-Command", "..."], env)
    env["RAHGARD_PILOT_DOCKER_CONTAINER"] = "unrelated-container"
    with pytest.raises(BackupBlocked):
        _database_tool_command(["psql", "-V"], env)


def test_backup_requires_explicit_confirmation_without_connecting(pilot_env, monkeypatch):
    monkeypatch.setattr("persistent_backup._run", lambda *args, **kwargs: pytest.fail("unexpected process"))
    with pytest.raises(BackupBlocked):
        backup(validate_config(pilot_env), pilot_env, confirmed=False)


def test_backup_checks_marker_and_role_before_dump_and_checks_archive(pilot_env, monkeypatch):
    calls = []

    def fake_run(command, *, env, stdout=None):
        calls.append(command[0])
        assert env["PGSSLMODE"] == "verify-full"
        assert pilot_env["RAHGARD_PILOT_DATABASE_MARKER"] not in " ".join(command)
        if command[0] == "psql":
            row = "\t".join(["rahgard_pilot_example", "ai_tourism_backup", "170005", "1",
                             pilot_env["RAHGARD_PILOT_DATABASE_MARKER"], "f", "f", "f", "f", "f", "0", "f"])
            return SimpleNamespace(stdout=row.encode())
        if command[0] == "pg_dump":
            stdout.write(b"test-only archive")
        return SimpleNamespace(stdout=b"")

    if os.name == "nt":
        def fake_stream(command, env, target):
            calls.append("pg_dump")
            return _write_dpapi_envelope(BytesIO(b"test-only archive"), target,
                                         protector=lambda data, _entropy: data[::-1])
        def fake_list(path, _env):
            calls.append("pg_restore")
            output = BytesIO()
            with path.open("rb") as source:
                return _decrypt_dpapi_envelope(source, output, unprotector=lambda data, _entropy: data[::-1])
        monkeypatch.setattr("persistent_backup._pipe_pg_dump_to_dpapi", fake_stream)
        monkeypatch.setattr("persistent_backup._pg_restore_list_dpapi", fake_list)

    monkeypatch.setattr("persistent_backup._run", fake_run)
    result = backup(validate_config(pilot_env), pilot_env, confirmed=True)
    assert calls == ["psql", "pg_dump", "pg_restore"]
    if os.name == "nt":
        decrypted = BytesIO()
        _decrypt_dpapi_envelope(BytesIO(result.read_bytes()), decrypted,
                                unprotector=lambda data, _entropy: data[::-1])
        assert decrypted.getvalue() == b"test-only archive"
        assert result.name.endswith(".dump.dpapi")
    else:
        assert result.read_bytes() == b"test-only archive"
        assert result.suffix == ".dump"
    assert not list(result.parent.glob("*.partial"))


def test_wrong_marker_blocks_dump(pilot_env, monkeypatch):
    row = "\t".join(["rahgard_pilot_example", "ai_tourism_backup", "170005", "1",
                     "ff" * 24, "f", "f", "f", "f", "f", "0", "f"])
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command[0])
        return SimpleNamespace(stdout=row.encode())

    monkeypatch.setattr("persistent_backup._run", fake_run)
    with pytest.raises(BackupBlocked):
        backup(validate_config(pilot_env), pilot_env, confirmed=True)
    assert calls == ["psql"]


def test_privileged_role_flags_block_dump(pilot_env, monkeypatch):
    row = "\t".join(["rahgard_pilot_example", "ai_tourism_backup", "170005", "1",
                     pilot_env["RAHGARD_PILOT_DATABASE_MARKER"], "t", "f", "f", "f", "f", "0", "f"])
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command[0])
        return SimpleNamespace(stdout=row.encode())

    monkeypatch.setattr("persistent_backup._run", fake_run)
    with pytest.raises(BackupBlocked):
        backup(validate_config(pilot_env), pilot_env, confirmed=True)
    assert calls == ["psql"]


def test_failed_archive_verification_removes_only_new_partial(pilot_env, monkeypatch, tmp_path):
    sentinel = tmp_path / "existing.dump"
    sentinel.write_bytes(b"preserve")

    def fake_run(command, *, env, stdout=None):
        if command[0] == "psql":
            row = "\t".join(["rahgard_pilot_example", "ai_tourism_backup", "170005", "1",
                             pilot_env["RAHGARD_PILOT_DATABASE_MARKER"], "f", "f", "f", "f", "f", "0", "f"])
            return SimpleNamespace(stdout=row.encode())
        if command[0] == "pg_dump":
            stdout.write(b"test only")
            return SimpleNamespace(stdout=b"")
        raise BackupBlocked("invalid archive")

    monkeypatch.setattr("persistent_backup._run", fake_run)
    if os.name == "nt":
        def fake_stream(_command, _env, target):
            return _write_dpapi_envelope(BytesIO(b"test-only archive"), target,
                                         protector=lambda data, _entropy: data[::-1])
        monkeypatch.setattr("persistent_backup._pipe_pg_dump_to_dpapi", fake_stream)
        monkeypatch.setattr("persistent_backup._pg_restore_list_dpapi",
                            lambda *_args: (_ for _ in ()).throw(BackupBlocked("invalid archive")))
    with pytest.raises(BackupBlocked):
        backup(validate_config(pilot_env), pilot_env, confirmed=True)
    assert sentinel.read_bytes() == b"preserve"
    assert not list(tmp_path.glob("*.partial"))
    assert not list(tmp_path.glob(".*.partial"))


def test_dpapi_envelope_protect_failure_is_fail_closed():
    output = BytesIO()
    with pytest.raises(BackupBlocked, match="provider unavailable"):
        _write_dpapi_envelope(BytesIO(b"test-only database archive"), output,
                              protector=lambda *_: (_ for _ in ()).throw(BackupBlocked("DPAPI provider unavailable")),
                              chunk_size=4096)
    assert b"test-only database archive" not in output.getvalue()


def test_dpapi_envelope_rejects_record_metadata_in_untrusted_header():
    envelope = BytesIO()
    _write_dpapi_envelope(BytesIO(b"test-only"), envelope,
                          protector=lambda data, _entropy: data[::-1], chunk_size=4096)
    raw = envelope.getvalue()
    magic = b"RAHGARD-DPAPI-BACKUP\x00\x01\n"
    header_length = struct.unpack(">I", raw[len(magic):len(magic) + 4])[0]
    header_start = len(magic) + 4
    header = json.loads(raw[header_start:header_start + header_length])
    header["record_count"] = 100_000
    header["plaintext_bytes"] = 100_000 * header["chunk_size"]
    encoded = json.dumps(header, sort_keys=True, separators=(",", ":")).encode()
    malformed = BytesIO(magic + struct.pack(">I", len(encoded)) + encoded + raw[header_start + header_length:])
    with pytest.raises(BackupBlocked, match="metadata failed validation"):
        _decrypt_dpapi_envelope(malformed, BytesIO(), unprotector=lambda *_: pytest.fail("must not decrypt"))


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI CurrentUser round trip")
def test_windows_dpapi_current_user_round_trip_and_entropy_binding():
    import persistent_backup

    plaintext = b"owner-only isolated backup payload"
    entropy = b"test-only envelope context"
    protected = persistent_backup._dpapi_transform(plaintext, entropy, decrypt=False)
    assert protected != plaintext
    assert persistent_backup._dpapi_transform(protected, entropy, decrypt=True) == plaintext
    with pytest.raises(BackupBlocked):
        persistent_backup._dpapi_transform(protected, b"wrong envelope context", decrypt=True)


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI streaming subprocess")
def test_windows_dump_stream_is_encrypted_without_plaintext_file():
    payload = b"test-only pg_dump bytes; never real traveler data"
    target = BytesIO()
    _pipe_pg_dump_to_dpapi(
        [sys.executable, "-c", f"import sys;sys.stdout.buffer.write({payload!r})"],
        {"SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
         "PATH": os.environ.get("PATH", "")}, target,
    )
    envelope = target.getvalue()
    assert payload not in envelope
    plaintext = BytesIO()
    metadata = _decrypt_dpapi_envelope(BytesIO(envelope), plaintext)
    assert plaintext.getvalue() == payload
    assert metadata["plaintext_bytes"] == len(payload)
