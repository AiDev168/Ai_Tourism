from __future__ import annotations

import os
import json

import pytest

from app.modules.provider_admin.server_vault import AesGcmSecretVault
from app.modules.provider_admin.vault import VaultUnavailable


def _vault(tmp_path):
    directory = tmp_path / "vault"
    directory.mkdir(mode=0o700)
    key = tmp_path / "key"
    key.write_text(json.dumps({"format_version": 1, "active_key_id": "key-v1", "keys": {"key-v1": "a5" * 32}}), encoding="ascii")
    if os.name != "nt":
        directory.chmod(0o700)
        key.chmod(0o600)
    return AesGcmSecretVault(directory, key), directory, key


def test_server_vault_round_trip_and_delete(tmp_path):
    vault, directory, _key = _vault(tmp_path)
    secret = b"provider-credential-test-only"
    reference = vault.put(secret)
    stored = (directory / reference).read_bytes()
    assert secret not in stored
    assert vault.get(reference) == secret
    vault.delete(reference)
    with pytest.raises(VaultUnavailable):
        vault.get(reference)


def test_server_vault_rejects_tampering_and_path_references(tmp_path):
    vault, directory, _key = _vault(tmp_path)
    reference = vault.put(b"opaque")
    path = directory / reference
    data = bytearray(path.read_bytes())
    data[-1] ^= 0x80
    path.write_bytes(data)
    with pytest.raises(VaultUnavailable):
        vault.get(reference)
    with pytest.raises(VaultUnavailable):
        vault.get("../outside")


def test_server_vault_fails_closed_on_permissive_secret_permissions(tmp_path):
    vault, _directory, key = _vault(tmp_path)
    if os.name == "nt":
        pytest.skip("POSIX secret mode check is not available on Windows")
    key.chmod(0o644)
    with pytest.raises(VaultUnavailable):
        vault.put(b"must-not-store")


def test_server_vault_key_rotation_is_restartable_and_versioned(tmp_path):
    vault, directory, key_file = _vault(tmp_path)
    reference = vault.put(b"rotate-me")
    key_file.write_text(json.dumps({
        "format_version": 1,
        "active_key_id": "key-v2",
        "keys": {"key-v1": "a5" * 32, "key-v2": "b6" * 32},
    }), encoding="ascii")
    if os.name != "nt":
        key_file.chmod(0o600)
    assert vault.get(reference) == b"rotate-me"
    assert vault.reencrypt_all() == 1
    assert vault.get(reference) == b"rotate-me"
    assert vault.reencrypt_all() == 0
    assert b"key-v2" in (directory / reference).read_bytes()


def test_key_rotation_cli_operations_preserve_ciphertexts_until_verified(tmp_path):
    from argparse import Namespace

    from scripts.manage_provider_vault import run

    vault, directory, key_file = _vault(tmp_path)
    reference = vault.put(b"rotation-secret-test-only")
    args = Namespace(action="rotate", vault_dir=directory, key_file=key_file)
    assert run(args).startswith("ROTATED active_key_id=k")
    assert vault.get(reference) == b"rotation-secret-test-only"
    assert vault.key_usage() == {"key-v1": 1}

    args.action = "reencrypt"
    assert "changed=1" in run(args)
    active, _keys = vault._keyring()
    assert vault.key_usage() == {active: 1}

    args.action = "prune"
    args.key_id = "key-v1"
    assert run(args) == "PRUNED key_id=key-v1"
    assert vault.get(reference) == b"rotation-secret-test-only"


def test_key_version_cannot_be_pruned_while_ciphertexts_reference_it(tmp_path):
    vault, _directory, _key_file = _vault(tmp_path)
    vault.put(b"still-encrypted-with-v1")
    with pytest.raises(VaultUnavailable):
        vault.prune_key("key-v1")
