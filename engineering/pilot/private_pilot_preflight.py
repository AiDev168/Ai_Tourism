"""Validate proposed private-pilot configuration without starting services.

This process reads only its environment and checks whether named files exist.
It never opens dotenv files, reads secret files, contacts services, or deploys.
Passing syntax checks is not authorization or evidence of runtime readiness.
"""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
import json
import os
from pathlib import Path
import re
from typing import Mapping
from urllib.parse import urlsplit

from persistent_backup import _DATABASE, _HOST

_ENV_REFERENCE = re.compile(r"env:(RAHGARD_PILOT_SECRET_[A-Z0-9_]{1,56})\Z")
_REGION = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{1,79}\Z")
_RUNTIME_GATES = (
    "tls_certificate_and_proxy_enforcement_unverified",
    "database_identity_marker_and_private_network_unverified",
    "production_auth_adapter_not_available",
    "backup_restore_and_operator_authority_unverified",
    "approved_geo_content_and_release_authority_unverified",
)


@dataclass(frozen=True)
class PreflightResult:
    configuration_errors: tuple[str, ...]
    runtime_gates: tuple[str, ...] = _RUNTIME_GATES

    @property
    def ready(self) -> bool:
        return not self.configuration_errors and not self.runtime_gates


def _https_origin(value: str) -> bool:
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.path or parsed.query or parsed.fragment or parsed.hostname.endswith(".")
                or "*" in parsed.hostname or parsed.netloc != parsed.netloc.lower()
                or (parsed.port is not None and not 1 <= parsed.port <= 65535)):
            return False
        try:
            address = ip_address(parsed.hostname)
        except ValueError:
            return (parsed.hostname not in {"localhost", "localhost.localdomain"}
                    and _dns_host(parsed.hostname))
        return not (address.is_loopback or address.is_unspecified or address.is_link_local)
    except ValueError:
        return False


def _dns_host(value: str) -> bool:
    name = value.lower()
    return (bool(_HOST.fullmatch(value)) and len(name) <= 253 and "." in name
            and not all(char.isdigit() or char == "." for char in name)
            and all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                    for label in name.split(".")))


def _reference(env: Mapping[str, str], key: str, minimum_bytes: int) -> str | None:
    match = _ENV_REFERENCE.fullmatch(env.get(key, ""))
    if not match:
        return None
    name = match.group(1)
    secret = env.get(name, "")
    if (not secret or secret != secret.strip() or "\r" in secret or "\n" in secret
            or len(secret.encode("utf-8")) < minimum_bytes):
        return None
    return name


def _existing_absolute_file(value: str) -> bool:
    try:
        path = Path(value)
        return bool(value) and path.is_absolute() and path.is_file()
    except (OSError, ValueError):
        return False


def evaluate(env: Mapping[str, str]) -> PreflightResult:
    """Return stable error codes only; never return values or secret references."""
    errors: list[str] = []
    origin = env.get("RAHGARD_PILOT_HTTPS_ORIGIN", "")
    if not _https_origin(origin):
        errors.append("https_origin_invalid")
    if env.get("AUTH_ALLOWED_ORIGINS", "") != origin or not origin:
        errors.append("auth_origin_mismatch")
    if not _REGION.fullmatch(env.get("RAHGARD_PILOT_DEPLOYMENT_REGION", "")):
        errors.append("deployment_region_missing")
    if env.get("APP_ENV") != "production" or env.get("APP_HOST") != "127.0.0.1":
        errors.append("backend_environment_or_bind_invalid")
    if env.get("AUTH_COOKIE_SECURE", "").lower() != "true":
        errors.append("secure_cookie_required")
    if env.get("RAHGARD_PILOT_TLS_TERMINATION") != "local_pfx_proxy":
        errors.append("tls_termination_model_unsupported")
    if not _existing_absolute_file(env.get("PILOT_TLS_PFX", "")):
        errors.append("tls_pfx_path_missing")
    proxy_ips = env.get("RAHGARD_PILOT_TRUSTED_PROXY_IPS", "").split(",")
    try:
        parsed_ips = [ip_address(item) for item in proxy_ips]
        if not parsed_ips or any(not item.is_loopback for item in parsed_ips) or len(set(parsed_ips)) != len(parsed_ips):
            raise ValueError
    except ValueError:
        errors.append("trusted_proxy_list_invalid")
    db_host, db_port, db_name = (env.get("RAHGARD_PILOT_PGHOST", ""), env.get("RAHGARD_PILOT_PGPORT", ""),
                                env.get("RAHGARD_PILOT_DATABASE", ""))
    if (not _HOST.fullmatch(db_host) or db_host.lower() in {"localhost", "localhost.localdomain"}
            or not db_port.isascii() or not db_port.isdigit()
            or not 1024 <= int(db_port) <= 65535 or int(db_port) == 55433
            or not _DATABASE.fullmatch(db_name) or env.get("DATABASE_USER") != "ai_tourism_app"):
        errors.append("persistent_database_target_invalid")
    else:
        try:
            address = ip_address(db_host)
            if address.is_loopback or address.is_unspecified or not address.is_private:
                errors.append("persistent_database_target_invalid")
        except ValueError:
            if not _dns_host(db_host):
                errors.append("persistent_database_target_invalid")
            # A valid DNS target still requires an independent private-network check.
    if not _existing_absolute_file(env.get("PGSSLROOTCERT", "")):
        errors.append("database_tls_ca_path_missing")
    references = []
    for key, size in (
        ("RAHGARD_PILOT_DB_PASSWORD_REF", 16), ("RAHGARD_PILOT_TLS_PFX_PASSWORD_REF", 16),
        ("RAHGARD_PILOT_OTP_HMAC_REF", 32), ("RAHGARD_PILOT_CSRF_SECRET_REF", 32),
        ("RAHGARD_PILOT_RATE_LIMIT_SECRET_REF", 32),
    ):
        reference = _reference(env, key, size)
        if reference is None:
            errors.append(f"{key.lower()}_invalid")
        else:
            references.append(reference)
    if len(set(references)) != len(references):
        errors.append("secret_references_must_be_distinct")
    return PreflightResult(tuple(errors))


def main() -> int:
    result = evaluate(os.environ)
    print(json.dumps({"ready": result.ready, "configuration_errors": result.configuration_errors,
                      "runtime_gates": result.runtime_gates}, sort_keys=True))
    return 0 if result.ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
