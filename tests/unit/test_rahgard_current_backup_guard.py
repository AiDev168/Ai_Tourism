import json
from pathlib import Path
import subprocess
import sys
import hashlib
import hmac
import secrets
from types import SimpleNamespace

import pytest
from cryptography.hazmat.primitives import hashes, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ops"))

from check_rahgard_v2_ledger import check_current_snapshot  # noqa: E402
from capture_rahgard_0023_backup import MAX_ENCRYPTED_BYTES, REMOTE, _private_paths  # noqa: E402
from rehearse_rahgard_v2_migrations import (  # noqa: E402
    assert_catalog_preserved,
    decrypt,
    render_guard_inputs,
)


SNAPSHOT = ROOT / "docs/operations/evidence/issue27/R3-live-snapshot-2026-11-25.json"


def _source_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _manifest() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def test_current_0023_snapshot_matches_exact_historical_ledger_and_pending_sql():
    report = check_current_snapshot(_manifest(), _source_sha())
    assert report["verified_base_entries"] == 22
    assert [item["id"] for item in report["pending"]] == [
        "0024_partner_review_audit_actions",
        "0025_owner_control_center",
        "0026_platform_reviewer_mfa",
    ]
    assert all(len(item["sha256"]) == 64 for item in report["pending"])


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("vps", "database", "volume"), "unexpected-volume"),
        (("vps", "database", "name"), "ai_tourism_dev"),
        (("vps", "api_image"), "rahgard-api:other"),
        (("vps", "legacy_release_marker"), "0" * 40),
    ],
)
def test_snapshot_identity_drift_fails_closed(path, value):
    manifest = _manifest()
    target = manifest
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        check_current_snapshot(manifest, _source_sha())


def test_missing_or_changed_ledger_row_fails_closed():
    manifest = _manifest()
    manifest["vps"]["database"]["migration_ledger"].pop()
    with pytest.raises(ValueError, match="exact known 0023 baseline"):
        check_current_snapshot(manifest, _source_sha())
    manifest = _manifest()
    manifest["vps"]["database"]["migration_ledger"][-1]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="checksum differs"):
        check_current_snapshot(manifest, _source_sha())


def test_backup_stream_is_bound_to_exact_topology_and_read_only_snapshot():
    assert "rahgard-staging-db-1" in REMOTE
    assert "rahgard_staging_pgdata" in REMOTE
    assert "default_transaction_read_only=on" in REMOTE
    assert "pg_dump" in REMOTE and "system.schema_migrations" in REMOTE
    assert "rahgard-pilot-db" not in REMOTE
    assert MAX_ENCRYPTED_BYTES == 1024 * 1024 * 1024


def test_backup_dirs_must_be_private_separate_and_outside_checkout(tmp_path):
    backup = tmp_path / "backup"
    keys = tmp_path / "keys"
    backup.mkdir()
    keys.mkdir()
    # Private ACL validation is Windows-specific; this assertion checks path separation.
    if sys.platform == "win32":
        pytest.skip("NTFS ACL test requires the explicit owner/SYSTEM ACL harness")
    # The script's shared secure-storage verifier accepts only private POSIX directories.
    backup.chmod(0o700)
    keys.chmod(0o700)
    result = _private_paths(backup, keys)
    assert result == (backup.resolve(), keys.resolve())
    with pytest.raises(ValueError, match="outside the repository"):
        _private_paths(ROOT, keys)


def _write_encrypted_test_archive(tmp_path: Path) -> tuple[Path, Path]:
    archive_dir = tmp_path / "archive"
    key_dir = tmp_path / "key"
    archive_dir.mkdir()
    key_dir.mkdir()
    archive = archive_dir / "test.dump.enc"
    password = secrets.token_bytes(32)
    salt = secrets.token_bytes(8)
    material = PBKDF2HMAC(algorithm=hashes.SHA256(), length=48, salt=salt, iterations=600_000).derive(password)
    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded = padder.update(b"PGDMP-test-archive") + padder.finalize()
    encryptor = Cipher(algorithms.AES(material[:32]), modes.CBC(material[32:])).encryptor()
    encrypted = b"Salted__" + salt + encryptor.update(padded) + encryptor.finalize()
    key = secrets.token_bytes(32)
    digest = hashlib.sha256(encrypted).hexdigest()
    archive.write_bytes(encrypted)
    archive.with_name(archive.name + ".sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    archive.with_name(archive.name + ".hmac").write_text(
        f"{hmac.digest(key, encrypted, 'sha256').hex()}  {archive.name}\n", encoding="ascii"
    )
    (key_dir / (archive.name + ".hmac-key")).write_bytes(key)
    (key_dir / (archive.name + ".passphrase")).write_text(password.hex() + "\n", encoding="ascii")
    return archive, key_dir


def test_current_backup_decryption_authenticates_and_verifies_custom_archive(tmp_path):
    archive, key_dir = _write_encrypted_test_archive(tmp_path)
    plain, digest = decrypt(SimpleNamespace(backup=archive, key_dir=key_dir))
    assert plain == b"PGDMP-test-archive"
    assert digest == hashlib.sha256(archive.read_bytes()).hexdigest()


def test_current_backup_rejects_corrupt_checksum_before_decryption(tmp_path):
    archive, key_dir = _write_encrypted_test_archive(tmp_path)
    archive.write_bytes(archive.read_bytes()[:-1] + bytes([archive.read_bytes()[-1] ^ 1]))
    with pytest.raises(ValueError, match="checksum mismatch"):
        decrypt(SimpleNamespace(backup=archive, key_dir=key_dir))


def test_current_backup_rejects_bad_hmac_even_when_sha_sidecar_is_recomputed(tmp_path):
    archive, key_dir = _write_encrypted_test_archive(tmp_path)
    corrupted = archive.read_bytes()[:-1] + bytes([archive.read_bytes()[-1] ^ 1])
    archive.write_bytes(corrupted)
    digest = hashlib.sha256(corrupted).hexdigest()
    archive.with_name(archive.name + ".sha256").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    with pytest.raises(ValueError, match="authentication failed"):
        decrypt(SimpleNamespace(backup=archive, key_dir=key_dir))


def test_guard_input_rendering_changes_only_declared_placeholders():
    sql = b"\\getenv marker RAHGARD_PILOT_DATABASE_MARKER\n\\getenv migration_hash RAHGARD_PILOT_MIGRATION_0026_SHA256\nSELECT :'marker', :'migration_hash';\n"
    rendered = render_guard_inputs(sql, {
        "RAHGARD_PILOT_DATABASE_MARKER": "a" * 32,
        "RAHGARD_PILOT_MIGRATION_0026_SHA256": "b" * 64,
    })
    assert rendered == b"SELECT '" + b"a" * 32 + b"', '" + b"b" * 64 + b"';\n"
    with pytest.raises(ValueError, match="Missing guarded migration input"):
        render_guard_inputs(sql, {})


def test_catalog_comparison_allows_only_additive_constraints_indexes_and_foreign_keys():
    before = {
        "indexes": ["travel.trips|trips_pk"],
        "constraints": ["travel.trips|trips_pk|p|old"],
        "foreign_keys": ["travel.trips|trip_user_fk|old"],
        "policies": ["travel.trips|owner_policy|old"],
        "extensions": ["postgis|3.6|public"],
        "roles": ["ai_tourism_app|True|False"],
        "application_grants": ["travel.trips|SELECT|NO"],
        "rls_relations": ["travel.trips|True|True"],
    }
    after = {
        **before,
        "indexes": [*before["indexes"], "identity.platform_admin_mfa|mfa_pk"],
        "constraints": [*before["constraints"], "identity.platform_admin_mfa|mfa_pk|p|new"],
        "foreign_keys": [*before["foreign_keys"], "identity.platform_admin_mfa|user_fk|new"],
        "policies": [*before["policies"], "identity.platform_admin_mfa|owner_policy|new"],
        "application_grants": [*before["application_grants"], "identity.platform_admin_mfa|INSERT|NO"],
        "rls_relations": [*before["rls_relations"], "identity.platform_admin_mfa|True|True"],
    }
    counts = assert_catalog_preserved(before, after)
    assert counts["foreign_keys"] == 2
    assert counts["indexes_after"] == 2

    after["foreign_keys"] = []
    with pytest.raises(RuntimeError, match="pre-existing foreign-key"):
        assert_catalog_preserved(before, after)
