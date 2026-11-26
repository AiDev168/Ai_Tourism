from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "ops" / "rahgard_runtime_compose.py"
SPEC = importlib.util.spec_from_file_location("rahgard_runtime_compose", MODULE_PATH)
assert SPEC and SPEC.loader
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


def _config(path: Path, **values: str) -> Path:
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
    return path


def _credential_dir(path: Path, files: tuple[str, ...]) -> Path:
    path.mkdir(mode=0o700)
    path.chmod(0o700)
    for name in files:
        target = path / name
        target.write_text("test-only-not-a-secret", encoding="ascii")
        target.chmod(0o600)
    return path


def test_default_compose_plan_uses_only_base_file(tmp_path: Path) -> None:
    config = _config(tmp_path / "runtime.env")
    args, details = runtime.compose_args(config, MODULE_PATH.parents[2])
    assert details["mfa_enabled"] is False
    assert details["provider_admin_enabled"] is False
    assert [part for part in args if part == "-f"] == ["-f"]
    assert args[-1].replace("\\", "/").endswith("deploy/staging/compose.yaml")


def test_provider_overlay_requires_mfa_and_mount_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    release = MODULE_PATH.parents[2]
    config = _config(tmp_path / "runtime.env", RAHGARD_PROVIDER_ADMIN_ENABLED="true")
    with pytest.raises(runtime.ConfigurationError, match="requires the MFA overlay"):
        runtime.compose_args(config, release)

    admin = _credential_dir(tmp_path / "admin", ("platform_admin_mfa_encryption_key_hex", "platform_admin_recovery_pepper"))
    keyring = _credential_dir(tmp_path / "keyring", ("ai_provider_vault_keyring.json",))
    # Windows ACLs are validated by the Windows local-pilot launcher; the
    # server Compose contract is POSIX and is exercised in Linux CI.
    monkeypatch.setattr(runtime, "_private_dir", lambda config, key, files: Path(config[key]))
    config = _config(
        config,
        RAHGARD_PLATFORM_ADMIN_MFA_ENABLED="true",
        RAHGARD_PROVIDER_ADMIN_ENABLED="true",
        RAHGARD_ADMIN_SECRET_DIR=str(admin),
        RAHGARD_PROVIDER_KEYRING_DIR=str(keyring),
        RAHGARD_PROVIDER_VAULT_VOLUME="rahgard_provider_vault_test",
    )
    args, details = runtime.compose_args(config, release)
    assert details["mfa_enabled"] is True
    assert details["provider_admin_enabled"] is True
    assert details["provider_vault_volume"] == "rahgard_provider_vault_test"
    assert args.count("-f") == 3
    assert args[-1].endswith("compose.server-provider-admin.yaml")


@pytest.mark.parametrize("bad_volume", ["../outside", "has space", "", "x" * 64])
def test_provider_volume_name_is_constrained(tmp_path: Path, bad_volume: str, monkeypatch: pytest.MonkeyPatch) -> None:
    admin = _credential_dir(tmp_path / "admin", ("platform_admin_mfa_encryption_key_hex", "platform_admin_recovery_pepper"))
    keyring = _credential_dir(tmp_path / "keyring", ("ai_provider_vault_keyring.json",))
    monkeypatch.setattr(runtime, "_private_dir", lambda config, key, files: Path(config[key]))
    config = _config(
        tmp_path / "runtime.env",
        RAHGARD_PLATFORM_ADMIN_MFA_ENABLED="true",
        RAHGARD_PROVIDER_ADMIN_ENABLED="true",
        RAHGARD_ADMIN_SECRET_DIR=str(admin),
        RAHGARD_PROVIDER_KEYRING_DIR=str(keyring),
        RAHGARD_PROVIDER_VAULT_VOLUME=bad_volume,
    )
    with pytest.raises(runtime.ConfigurationError, match="volume name is invalid"):
        runtime.compose_args(config, MODULE_PATH.parents[2])


def test_duplicate_switch_fails_closed_without_echoing_values(tmp_path: Path) -> None:
    config = tmp_path / "runtime.env"
    config.write_text("RAHGARD_PROVIDER_ADMIN_ENABLED=true\nRAHGARD_PROVIDER_ADMIN_ENABLED=false\n", encoding="utf-8")
    with pytest.raises(runtime.ConfigurationError, match="duplicate runtime overlay"):
        runtime.compose_args(config, MODULE_PATH.parents[2])


def test_private_directory_rejects_symlink(tmp_path: Path) -> None:
    actual = _credential_dir(tmp_path / "actual", ("platform_admin_mfa_encryption_key_hex", "platform_admin_recovery_pepper"))
    link = tmp_path / "linked"
    try:
        link.symlink_to(actual, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable in this environment")
    config = _config(
        tmp_path / "runtime.env",
        RAHGARD_PLATFORM_ADMIN_MFA_ENABLED="true",
        RAHGARD_ADMIN_SECRET_DIR=str(link),
    )
    with pytest.raises(runtime.ConfigurationError):
        runtime.compose_args(config, MODULE_PATH.parents[2])
