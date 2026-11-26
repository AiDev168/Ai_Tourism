"""Build a fail-closed Compose argument list for the staging runtime overlays.

This helper never shells out or prints secret values. It reads only the small
set of non-secret deployment switches and validates the host directories used
for the Owner MFA and server-side provider vault overlays.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path


_KEYS = {
    "RAHGARD_PLATFORM_ADMIN_MFA_ENABLED",
    "RAHGARD_PROVIDER_ADMIN_ENABLED",
    "RAHGARD_ADMIN_SECRET_DIR",
    "RAHGARD_PROVIDER_KEYRING_DIR",
    "RAHGARD_PROVIDER_VAULT_VOLUME",
}
_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}\Z")


class ConfigurationError(ValueError):
    pass


def _read_config(path: Path) -> dict[str, str]:
    values: dict[str, list[str]] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ConfigurationError("deployment config is unavailable") from exc
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in _KEYS:
            values.setdefault(key, []).append(value)
    duplicates = [key for key, rows in values.items() if len(rows) != 1]
    if duplicates:
        raise ConfigurationError("duplicate runtime overlay setting")
    return {key: rows[0] for key, rows in values.items()}


def _flag(config: dict[str, str], key: str) -> bool:
    value = config.get(key, "false").lower()
    if value not in {"true", "false"}:
        raise ConfigurationError("runtime overlay switch must be true or false")
    return value == "true"


def _private_dir(config: dict[str, str], key: str, files: tuple[str, ...]) -> Path:
    raw = config.get(key, "")
    path = Path(raw)
    if not raw or not path.is_absolute() or "\n" in raw or "\r" in raw:
        raise ConfigurationError("enabled runtime overlay requires an absolute private directory")
    try:
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or (os.name != "nt" and stat.S_IMODE(info.st_mode) != 0o700):
            raise ConfigurationError("runtime overlay directory must be a real mode-0700 directory")
        for name in files:
            file = path / name
            fstat = file.lstat()
            if not stat.S_ISREG(fstat.st_mode) or (os.name != "nt" and stat.S_IMODE(fstat.st_mode) not in {0o400, 0o600}):
                raise ConfigurationError("runtime overlay credential file is missing or has unsafe type/mode")
    except OSError as exc:
        raise ConfigurationError("enabled runtime overlay directory or credential is unavailable") from exc
    return path


def compose_args(env_file: Path, release: Path) -> tuple[list[str], dict[str, bool | str]]:
    env_file = env_file.resolve(strict=True)
    release = release.resolve(strict=True)
    config = _read_config(env_file)
    mfa = _flag(config, "RAHGARD_PLATFORM_ADMIN_MFA_ENABLED")
    provider = _flag(config, "RAHGARD_PROVIDER_ADMIN_ENABLED")
    if provider and not mfa:
        raise ConfigurationError("provider administration requires the MFA overlay")
    base = release / "deploy" / "staging" / "compose.yaml"
    if not base.is_file():
        raise ConfigurationError("release Compose file is missing")
    args = ["docker", "compose", "--env-file", str(env_file), "-f", str(base)]
    if mfa:
        _private_dir(
            config,
            "RAHGARD_ADMIN_SECRET_DIR",
            ("platform_admin_mfa_encryption_key_hex", "platform_admin_recovery_pepper"),
        )
        overlay = release / "deploy" / "staging" / "compose.platform-admin-mfa.yaml"
        if not overlay.is_file():
            raise ConfigurationError("release is missing the MFA Compose overlay")
        args += ["-f", str(overlay)]
    if provider:
        keyring_dir = _private_dir(config, "RAHGARD_PROVIDER_KEYRING_DIR", ("ai_provider_vault_keyring.json",))
        volume = config.get("RAHGARD_PROVIDER_VAULT_VOLUME", "rahgard_provider_vault")
        if not _NAME.fullmatch(volume):
            raise ConfigurationError("provider vault volume name is invalid")
        overlay = release / "deploy" / "staging" / "compose.server-provider-admin.yaml"
        if not overlay.is_file():
            raise ConfigurationError("release is missing the provider Compose overlay")
        args += ["-f", str(overlay)]
    else:
        keyring_dir = Path(config.get("RAHGARD_PROVIDER_KEYRING_DIR", "/unused"))
        volume = config.get("RAHGARD_PROVIDER_VAULT_VOLUME", "rahgard_provider_vault")
    details: dict[str, bool | str] = {
        "mfa_enabled": mfa,
        "provider_admin_enabled": provider,
        "provider_vault_volume": volume,
        "admin_secret_dir": config.get("RAHGARD_ADMIN_SECRET_DIR", ""),
    }
    if provider:
        details["provider_keyring_dir"] = str(keyring_dir)
    return args, details


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--format", choices=("json", "nul", "settings"), default="json")
    args = parser.parse_args()
    try:
        command, details = compose_args(args.env_file, args.release)
    except ConfigurationError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    if args.format == "nul":
        sys.stdout.buffer.write(b"\0".join(item.encode() for item in command) + b"\0")
    elif args.format == "settings":
        print(json.dumps({
            "mfa_enabled": details["mfa_enabled"],
            "provider_admin_enabled": details["provider_admin_enabled"],
            "admin_secret_dir": details.get("admin_secret_dir", ""),
            "provider_vault_volume": details["provider_vault_volume"],
            "provider_keyring_dir": details.get("provider_keyring_dir"),
        }))
    else:
        print(json.dumps({"compose_args": command[2:], "mfa_enabled": details["mfa_enabled"],
                          "provider_admin_enabled": details["provider_admin_enabled"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
