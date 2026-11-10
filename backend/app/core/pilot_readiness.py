"""Fail-closed, side-effect-free checks for a proposed internal pilot.

This module intentionally does not start services, inspect environment files,
connect to databases, or make provider calls. It turns owner-approved runtime
facts into explicit blockers before anyone performs a pilot activation.
"""

from __future__ import annotations

from dataclasses import dataclass
from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlsplit


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class PilotReadinessInputs:
    public_origin: str | None = None
    deployment_region_approved: bool = False
    tls_termination_verified: bool = False
    managed_secrets_ready: bool = False
    database_host: str | None = None
    database_port: int | None = None
    database_name: str | None = None
    database_private_network_verified: bool = False
    backup_restore_tested: bool = False
    auth_enabled: bool = False
    production_sms_adapter_ready: bool = False
    production_sms_authorized: bool = False
    auth_recovery_approved: bool = False
    admin_security_approved: bool = False
    owner_rag_origin: str | None = None
    owner_rag_private_transport_verified: bool = False
    approved_content_count: int = 0
    remote_chat_enabled: bool = False
    remote_chat_endpoint: str | None = None
    remote_chat_credential_available: bool = False
    remote_chat_authorized: bool = False
    remote_processing_consent_approved: bool = False
    chat_budget_approved: bool = False
    physical_device_acceptance_complete: bool = False


@dataclass(frozen=True)
class LiveChatSmokeInputs:
    """Preconditions for one separately authorized staging Chat request."""

    app_environment: Literal["development", "test", "production"] = "development"
    gateway_enabled: bool = False
    endpoint: str | None = None
    credential_available: bool = False
    owner_authorized: bool = False
    traveler_processing_consent: bool = False
    budget_approved: bool = False
    max_calls: int = 0
    max_output_tokens: int = 0


def _is_public_https_origin(value: str | None) -> bool:
    if not value:
        return False
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            return False
        try:
            address = ip_address(parsed.hostname)
        except ValueError:
            return parsed.hostname not in {"localhost", "localhost.localdomain"}
        return not address.is_loopback and not address.is_unspecified
    except ValueError:
        return False


def evaluate_pilot_readiness(inputs: PilotReadinessInputs) -> ReadinessResult:
    """Return missing owner/operations gates without performing any action."""

    blockers: list[str] = []
    if not _is_public_https_origin(inputs.public_origin):
        blockers.append("public_https_origin_not_configured")
    if not inputs.deployment_region_approved:
        blockers.append("deployment_region_not_approved")
    if not inputs.tls_termination_verified:
        blockers.append("tls_termination_not_verified")
    if not inputs.managed_secrets_ready:
        blockers.append("managed_secrets_not_ready")

    normalized_host = (inputs.database_host or "").strip().lower()
    normalized_database = (inputs.database_name or "").strip().lower()
    try:
        loopback = bool(normalized_host) and ip_address(normalized_host).is_loopback
    except ValueError:
        loopback = normalized_host in {"localhost", "localhost.localdomain"}
    if (
        loopback
        or inputs.database_port == 55433
        or normalized_database == "ai_tourism_dev"
    ):
        blockers.append("shared_development_database_target_forbidden")
    if not inputs.database_private_network_verified:
        blockers.append("database_private_network_not_verified")
    if not inputs.backup_restore_tested:
        blockers.append("backup_restore_not_tested")

    if not inputs.auth_enabled:
        blockers.append("production_auth_not_enabled")
    if not inputs.production_sms_adapter_ready:
        blockers.append("production_sms_adapter_not_ready")
    if not inputs.production_sms_authorized:
        blockers.append("production_sms_not_authorized")
    if not inputs.auth_recovery_approved:
        blockers.append("auth_recovery_not_approved")
    if not inputs.admin_security_approved:
        blockers.append("admin_security_not_approved")

    if not _is_public_https_origin(inputs.owner_rag_origin):
        blockers.append("production_owner_rag_https_origin_not_configured")
    if not inputs.owner_rag_private_transport_verified:
        blockers.append("owner_rag_private_transport_not_verified")
    if inputs.approved_content_count < 1:
        blockers.append("approved_published_content_missing")

    if not inputs.remote_chat_enabled:
        blockers.append("remote_chat_disabled")
    if not _is_public_https_origin(inputs.remote_chat_endpoint):
        blockers.append("remote_chat_https_endpoint_not_configured")
    if not inputs.remote_chat_credential_available:
        blockers.append("remote_chat_credential_not_configured")
    if not inputs.remote_chat_authorized:
        blockers.append("remote_chat_not_authorized")
    if not inputs.remote_processing_consent_approved:
        blockers.append("remote_processing_consent_not_approved")
    if not inputs.chat_budget_approved:
        blockers.append("remote_chat_budget_not_approved")
    if not inputs.physical_device_acceptance_complete:
        blockers.append("physical_device_acceptance_incomplete")

    result = tuple(blockers)
    return ReadinessResult(ready=not result, blockers=result)


def evaluate_single_chat_smoke(inputs: LiveChatSmokeInputs) -> ReadinessResult:
    """Check a single remote Chat call's prerequisites; never make the call."""

    blockers: list[str] = []
    if inputs.app_environment == "production":
        blockers.append("live_smoke_must_run_in_isolated_staging")
    if not inputs.gateway_enabled:
        blockers.append("chat_gateway_disabled")
    if not _is_public_https_origin(inputs.endpoint):
        blockers.append("chat_endpoint_must_be_credential_free_https_origin")
    if not inputs.credential_available:
        blockers.append("server_side_chat_credential_missing")
    if not inputs.owner_authorized:
        blockers.append("owner_live_call_authorization_missing")
    if not inputs.traveler_processing_consent:
        blockers.append("traveler_remote_processing_consent_missing")
    if not inputs.budget_approved:
        blockers.append("bounded_chat_budget_not_approved")
    if inputs.max_calls != 1:
        blockers.append("chat_smoke_must_be_limited_to_one_call")
    if not 1 <= inputs.max_output_tokens <= 1_000:
        blockers.append("chat_smoke_output_limit_invalid")

    result = tuple(blockers)
    return ReadinessResult(ready=not result, blockers=result)
