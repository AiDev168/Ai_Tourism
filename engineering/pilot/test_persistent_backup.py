"""Offline guard tests; no database or external process is contacted."""

from types import SimpleNamespace
from pathlib import Path
import os

import pytest

from persistent_backup import BackupBlocked, backup, validate_config


@pytest.fixture
def pilot_env(tmp_path, monkeypatch):
    # Mock only the storage guard on Windows; that platform is otherwise
    # deliberately blocked until native ACL verification is implemented.
    monkeypatch.setattr("persistent_backup._private_storage", lambda path: Path(path).resolve(strict=True))
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
def test_windows_storage_fails_closed_without_acl_verification(tmp_path, monkeypatch):
    import persistent_backup

    monkeypatch.setattr(persistent_backup, "_REPOSITORY_ROOT", tmp_path / "other-repository")
    with pytest.raises(BackupBlocked, match="cannot be verified"):
        persistent_backup._private_storage(str(tmp_path))


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

    monkeypatch.setattr("persistent_backup._run", fake_run)
    result = backup(validate_config(pilot_env), pilot_env, confirmed=True)
    assert calls == ["psql", "pg_dump", "pg_restore"]
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
    with pytest.raises(BackupBlocked):
        backup(validate_config(pilot_env), pilot_env, confirmed=True)
    assert sentinel.read_bytes() == b"preserve"
    assert not list(tmp_path.glob("*.partial"))
