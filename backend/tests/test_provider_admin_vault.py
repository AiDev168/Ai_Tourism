from __future__ import annotations

import os

import pytest

from app.modules.provider_admin.vault import DpapiSecretVault, VaultUnavailable


@pytest.mark.skipif(os.name != "nt", reason="the production vault requires Windows DPAPI")
def test_windows_dpapi_secret_round_trip_is_opaque_and_deletable(tmp_path):
    secret = b"test-only provider credential material"
    protected_directory = tmp_path / "protected-vault"
    protected_directory.mkdir()
    vault = DpapiSecretVault(protected_directory)
    reference = vault.put(secret)
    stored = (protected_directory / reference).read_bytes()
    assert secret not in stored
    assert vault.get(reference) == secret
    vault.delete(reference)
    with pytest.raises(VaultUnavailable):
        vault.get(reference)


def test_vault_fails_closed_for_invalid_references(tmp_path):
    with pytest.raises(VaultUnavailable):
        DpapiSecretVault(tmp_path).get("../../secret")
