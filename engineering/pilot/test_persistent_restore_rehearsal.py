"""Offline restore guard tests; no PostgreSQL process or service is contacted."""

import hashlib
from contextlib import nullcontext
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

import pytest

from persistent_backup import BackupBlocked
from persistent_restore_rehearsal import rehearse, validate_config


@pytest.fixture
def restore_env(tmp_path, monkeypatch):
    monkeypatch.setattr("persistent_restore_rehearsal._private_storage", lambda path: Path(path).resolve(strict=True))
    monkeypatch.setattr("persistent_restore_rehearsal._unlinked_spool", lambda directory: nullcontext(BytesIO()))
    archive = tmp_path / "test.dump"
    archive.write_bytes(b"test-only archive")
    cert = tmp_path / "root.crt"
    cert.write_text("test only", encoding="utf-8")
    return {
        "RAHGARD_RESTORE_PGHOST": "private-db.example.invalid",
        "RAHGARD_RESTORE_PGPORT": "5432",
        "RAHGARD_RESTORE_DATABASE": "rahgard_restore_0123456789ab",
        "RAHGARD_RESTORE_MARKER": "ab" * 24,
        "RAHGARD_RESTORE_ARCHIVE": str(archive),
        "RAHGARD_RESTORE_ARCHIVE_SHA256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "RAHGARD_RESTORE_SPOOL_DIR": str(tmp_path),
        "RAHGARD_RESTORE_EXPECTED_MIGRATIONS": "13",
        "PGSSLROOTCERT": str(cert), "PGPASSWORD": "test-only-password",
    }


@pytest.mark.parametrize("field,value", [
    ("RAHGARD_RESTORE_DATABASE", "rahgard_pilot_example"),
    ("RAHGARD_RESTORE_DATABASE", "ai_tourism_dev"),
    ("RAHGARD_RESTORE_PGPORT", "55433"),
    ("RAHGARD_RESTORE_MARKER", "bad"),
    ("RAHGARD_RESTORE_EXPECTED_MIGRATIONS", "12"),
])
def test_rejects_non_rehearsal_targets(restore_env, field, value):
    restore_env[field] = value
    with pytest.raises(BackupBlocked):
        validate_config(restore_env)


def test_confirmation_and_archive_hash_are_required_before_processes(restore_env, monkeypatch):
    monkeypatch.setattr("persistent_restore_rehearsal._run", lambda *args, **kwargs: pytest.fail("unexpected process"))
    config = validate_config(restore_env)
    with pytest.raises(BackupBlocked):
        rehearse(config, restore_env, confirmed=False)
    config["sha256"] = "f" * 64
    with pytest.raises(BackupBlocked):
        rehearse(config, restore_env, confirmed=True)


def test_dirty_or_privileged_target_blocks_restore(restore_env, monkeypatch):
    calls = []
    row = "\t".join([restore_env["RAHGARD_RESTORE_DATABASE"], "ai_tourism_restore", "170005", "1",
                     restore_env["RAHGARD_RESTORE_MARKER"], "f", "f", "f", "f", "f", "1", "0", "0", "t"])

    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(stdout=row.encode())

    monkeypatch.setattr("persistent_restore_rehearsal._run", fake_run)
    with pytest.raises(BackupBlocked):
        rehearse(validate_config(restore_env), restore_env, confirmed=True)
    assert [command[0] for command in calls] == ["pg_restore", "psql"]


def test_restore_uses_transaction_and_verifies_migration_count(restore_env, monkeypatch):
    calls = []
    guard = "\t".join([restore_env["RAHGARD_RESTORE_DATABASE"], "ai_tourism_restore", "170005", "1",
                       restore_env["RAHGARD_RESTORE_MARKER"], "f", "f", "f", "f", "f", "0", "0", "0", "t"])
    verified = "\t".join([restore_env["RAHGARD_RESTORE_DATABASE"], "13", "t", "t", "t"])

    def fake_run(command, *, env, stdout=None, stdin=None):
        calls.append(command)
        assert env["PGSSLMODE"] == "verify-full"
        assert restore_env["RAHGARD_RESTORE_MARKER"] not in " ".join(command)
        if command[0] == "psql":
            return SimpleNamespace(stdout=(guard if sum(c[0] == "psql" for c in calls) == 1 else verified).encode())
        assert stdin.read() == b"test-only archive"
        if "--list" in command:
            # Replacing the original after validation cannot change the spool.
            Path(restore_env["RAHGARD_RESTORE_ARCHIVE"]).write_bytes(b"replacement")
        return SimpleNamespace(stdout=b"")

    monkeypatch.setattr("persistent_restore_rehearsal._run", fake_run)
    rehearse(validate_config(restore_env), restore_env, confirmed=True)
    assert [command[0] for command in calls] == ["pg_restore", "psql", "pg_restore", "psql"]
    restore_command = calls[2]
    assert "--single-transaction" in restore_command
    assert "--no-owner" in restore_command and "--no-acl" in restore_command
    assert "--clean" not in restore_command and "--create" not in restore_command
