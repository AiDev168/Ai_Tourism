"""Offline restore guard tests; no PostgreSQL process or service is contacted."""

import hashlib
from contextlib import contextmanager
from io import BytesIO
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from persistent_backup import BackupBlocked, _verify_windows_acl, _write_dpapi_envelope
from persistent_restore_rehearsal import (
    _GUARD_SQL, _filter_extension_toc, _unlinked_spool, rehearse, validate_config,
)

_TEST_TOC = (
    b"; archive header\n"
    b"1; 0 0 EXTENSION - postgis\n"
    b"2; 0 0 COMMENT - EXTENSION postgis\n"
    b"3; 0 0 EXTENSION - vector\n"
    b"4; 0 0 COMMENT - EXTENSION vector\n"
    b"5; 0 0 EXTENSION - fuzzystrmatch\n"
    b"6; 0 0 EXTENSION - postgis_topology\n"
    b"7; 0 0 EXTENSION - postgis_tiger_geocoder\n"
    b"8; 2615 2200 SCHEMA - tiger ai_tourism_owner\n"
    b"9; 2615 2200 SCHEMA - topology ai_tourism_owner\n"
    b"10; 0 0 COMMENT - SCHEMA tiger ai_tourism_owner\n"
    b"11; 0 0 ACL - SCHEMA topology ai_tourism_owner\n"
    b"12; 0 0 TABLE DATA public spatial_ref_sys ai_tourism_owner\n"
    b"13; 1259 42 TABLE public sample owner\n"
)


def _guard_row(env, *, public_objects="0", postgis="3.6.3"):
    return "\t".join([
        env["RAHGARD_RESTORE_DATABASE"], "ai_tourism_restore", "170005", "1",
        env["RAHGARD_RESTORE_MARKER"], *(["f"] * 5), "0", public_objects, "0", "0",
        postgis, "0.8.7", "1.0", "1.2", "3.6.3", "3.6.3", "t",
    ])


@pytest.fixture
def restore_env(tmp_path, monkeypatch):
    monkeypatch.setattr("persistent_restore_rehearsal._private_storage", lambda path: Path(path).resolve(strict=True))
    @contextmanager
    def memory_spool(_directory):
        yield BytesIO()
    monkeypatch.setattr("persistent_restore_rehearsal._unlinked_spool", memory_spool)
    def test_dpapi(data, _entropy, *, decrypt):
        return data[::-1]
    monkeypatch.setattr("persistent_backup._dpapi_transform", test_dpapi)
    archive = tmp_path / "test.dump"
    if os.name == "nt":
        envelope = BytesIO()
        _write_dpapi_envelope(BytesIO(b"test-only archive"), envelope,
                              protector=lambda data, _entropy: data[::-1])
        archive_bytes = envelope.getvalue()
    else:
        archive_bytes = b"test-only archive"
    archive.write_bytes(archive_bytes)
    cert = tmp_path / "root.crt"
    cert.write_text("test only", encoding="utf-8")
    return {
        "RAHGARD_RESTORE_PGHOST": "private-db.example.invalid",
        "RAHGARD_RESTORE_PGPORT": "5432",
        "RAHGARD_RESTORE_DATABASE": "rahgard_restore_0123456789ab",
        "RAHGARD_RESTORE_MARKER": "ab" * 24,
        "RAHGARD_RESTORE_ARCHIVE": str(archive),
        "RAHGARD_RESTORE_ARCHIVE_SHA256": hashlib.sha256(archive_bytes).hexdigest(),
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
    row = _guard_row(restore_env, public_objects="1")

    def fake_run(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(stdout=row.encode())

    monkeypatch.setattr("persistent_restore_rehearsal._run", fake_run)
    with pytest.raises(BackupBlocked):
        rehearse(validate_config(restore_env), restore_env, confirmed=True)
    assert [command[0] for command in calls] == ["psql"]


def test_restore_uses_transaction_and_verifies_migration_count(restore_env, monkeypatch):
    calls = []
    guard = _guard_row(restore_env)
    verified = "\t".join([restore_env["RAHGARD_RESTORE_DATABASE"], "13", "t", "t", "t"])

    def fake_run(command, *, env, stdout=None, stdin=None):
        calls.append(command)
        assert env["PGSSLMODE"] == "verify-full"
        assert restore_env["RAHGARD_RESTORE_MARKER"] not in " ".join(command)
        if command[0] == "psql":
            return SimpleNamespace(stdout=(guard if sum(c[0] == "psql" for c in calls) == 1 else verified).encode())
        if "--list" in command:
            return SimpleNamespace(stdout=_TEST_TOC)
        assert stdin.read() == b"test-only archive"
        # Replacing the original after validation cannot change the spool.
        Path(restore_env["RAHGARD_RESTORE_ARCHIVE"]).write_bytes(b"replacement")
        return SimpleNamespace(stdout=b"")

    monkeypatch.setattr("persistent_restore_rehearsal._run", fake_run)
    rehearse(validate_config(restore_env), restore_env, confirmed=True)
    assert [command[0] for command in calls] == ["psql", "pg_restore", "pg_restore", "psql"]
    restore_command = calls[2]
    assert "--single-transaction" in restore_command
    assert "--no-owner" in restore_command and "--no-acl" in restore_command
    assert "--use-list" in restore_command
    assert "--clean" not in restore_command and "--create" not in restore_command


def test_extension_toc_filter_skips_only_approved_extensions():
    source = (
        b"; archive header\n"
        b"1; 0 0 EXTENSION - postgis\n"
        b"2; 0 0 COMMENT - EXTENSION postgis\n"
        b"3; 0 0 EXTENSION - vector\n"
        b"4; 0 0 COMMENT - EXTENSION vector\n"
        b"5; 0 0 EXTENSION - fuzzystrmatch\n"
        b"6; 0 0 EXTENSION - postgis_topology\n"
        b"7; 0 0 EXTENSION - postgis_tiger_geocoder\n"
        b"8; 2615 2200 SCHEMA - tiger ai_tourism_owner\n"
        b"9; 2615 2200 SCHEMA - topology ai_tourism_owner\n"
        b"10; 0 0 COMMENT - SCHEMA tiger ai_tourism_owner\n"
        b"11; 0 0 ACL - SCHEMA topology ai_tourism_owner\n"
        b"12; 0 0 TABLE DATA public spatial_ref_sys ai_tourism_owner\n"
        b"13; 1259 42 TABLE public sample owner\n"
    )
    filtered = _filter_extension_toc(source)
    assert b"EXTENSION - postgis" not in filtered
    assert b"COMMENT - EXTENSION vector" not in filtered
    assert b"SCHEMA - tiger" not in filtered
    assert b"SCHEMA - topology" not in filtered
    assert b"COMMENT - SCHEMA tiger" not in filtered
    assert b"TABLE DATA public spatial_ref_sys" not in filtered
    assert b"TABLE public sample" in filtered


def test_extension_toc_filter_rejects_unapproved_or_missing_extensions():
    with pytest.raises(BackupBlocked, match="unapproved database extension"):
        _filter_extension_toc(
            b"1; 0 0 EXTENSION - postgis\n2; 0 0 EXTENSION - vector\n"
            b"3; 0 0 EXTENSION - fuzzystrmatch\n4; 0 0 EXTENSION - postgis_topology\n"
            b"5; 0 0 EXTENSION - postgis_tiger_geocoder\n6; 0 0 EXTENSION - plpython3u\n"
        )
    with pytest.raises(BackupBlocked, match="missing a required approved database extension"):
        _filter_extension_toc(b"1; 0 0 EXTENSION - postgis\n2; 0 0 EXTENSION - vector\n")


def test_restore_guard_requires_expected_operator_prepared_extensions(restore_env, monkeypatch):
    guard = _guard_row(restore_env)
    calls = []

    verified = "\t".join([restore_env["RAHGARD_RESTORE_DATABASE"], "13", "t", "t", "t"])

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[0] == "psql":
            result = guard if sum(item[0] == "psql" for item in calls) == 1 else verified
            return SimpleNamespace(stdout=result.encode())
        if "--list" in command:
            return SimpleNamespace(stdout=_TEST_TOC)
        return SimpleNamespace(stdout=b"")

    monkeypatch.setattr("persistent_restore_rehearsal._run", fake_run)
    rehearse(validate_config(restore_env), restore_env, confirmed=True)
    assert "postgis" in _GUARD_SQL and "vector" in _GUARD_SQL and "plpgsql" in _GUARD_SQL
    assert "pg_namespace" in _GUARD_SQL and "deptype='e'" in _GUARD_SQL
    assert len(calls) == 4


def test_restore_rejects_wrong_extension_versions_before_restore(restore_env, monkeypatch):
    guard = _guard_row(restore_env, postgis="3.5.2")
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command[0])
        return SimpleNamespace(stdout=guard.encode())

    monkeypatch.setattr("persistent_restore_rehearsal._run", fake_run)
    with pytest.raises(BackupBlocked, match="not empty, isolated, or correctly marked"):
        rehearse(validate_config(restore_env), restore_env, confirmed=True)
    assert calls == ["psql"]


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI spool cleanup")
def test_windows_spool_cleanup_failure_is_reported_and_residue_removed(tmp_path, monkeypatch):
    original_unlink = os.unlink
    residue = None
    with pytest.raises(BackupBlocked, match="spool cleanup failed"):
        with _unlinked_spool(tmp_path) as spool:
            residue = Path(spool.name)
            spool.write(b"private plaintext test data")
            spool.flush()
            def deny_target(path, *args, **kwargs):
                if os.fspath(path) == os.fspath(residue):
                    raise PermissionError("test cleanup denial")
                return original_unlink(path, *args, **kwargs)
            monkeypatch.setattr(os, "unlink", deny_target)
    monkeypatch.setattr(os, "unlink", original_unlink)
    assert residue is not None and residue.is_file()
    original_unlink(residue)
    assert not residue.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI rejection")
def test_windows_dpapi_unprotect_failure_blocks_restore_before_pg_restore(restore_env, monkeypatch):
    guard = _guard_row(restore_env)
    calls = []
    def fake_run(command, **kwargs):
        calls.append(command[0])
        return SimpleNamespace(stdout=guard.encode())
    monkeypatch.setattr("persistent_restore_rehearsal._run", fake_run)
    monkeypatch.setattr("persistent_backup._dpapi_transform",
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(BackupBlocked("DPAPI rejected user")))
    with pytest.raises(BackupBlocked, match="DPAPI rejected"):
        rehearse(validate_config(restore_env), restore_env, confirmed=True)
    assert calls == ["psql"]


@pytest.mark.skipif(os.name != "nt", reason="Windows ACL gate")
def test_windows_restore_spool_is_acl_protected_and_removed_after_use(tmp_path):
    spool_path = None
    with _unlinked_spool(tmp_path) as spool:
        spool.write(b"test-only archive")
        spool.flush()
        spool_path = Path(spool.name)
        _verify_windows_acl(spool_path, directory=False)
        assert spool_path.is_file()
    assert spool_path is not None and not spool_path.exists()
