"""Protected local-pilot AI Provider administration control plane."""

from __future__ import annotations

import hashlib
import hmac
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Response
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StrictBool, StrictInt, field_validator, model_validator

from app.api.auth import authenticated_user, require_authenticated_csrf
from app.core.config import Settings, get_settings
from app.modules.identity.auth_repository import AuthRepository
from app.modules.identity.auth_service import AuthenticatedUser
from app.modules.provider_admin.providers import (
    ChatProviderConfig,
    OpenAiCompatibleProviderAdapter,
    ProviderAuthenticationError,
    ProviderConfigurationError,
    ProviderCapabilityUnsupported,
    ProviderTransportError,
    validate_provider_base_config,
)
from app.modules.provider_admin.registry import (
    ProviderRegistry,
    RegistryConflict,
    RegistryNotFound,
    RegistryRejected,
)
from app.modules.provider_admin.security import (
    generate_recovery_codes,
    hash_recovery_code,
    new_totp_secret,
    totp_provisioning_uri,
    verify_totp,
)
from app.modules.provider_admin.vault import DpapiSecretVault, VaultUnavailable

router = APIRouter(prefix="/api/v1/admin/ai-providers", tags=["ai-provider-admin"])
_CAPABILITIES = {"chat", "vision", "embedding", "reranking"}
_MFA_FAILURE_LIMIT = 5


def _consume_admin_mfa_attempt(settings: Settings, user: AuthenticatedUser, now: datetime) -> None:
    """Apply a privacy-preserving, per-admin rolling-window limit to MFA proofs."""
    secret = settings.auth_rate_limit_secret
    if secret is None:
        raise HTTPException(status_code=503, detail="provider_admin_unavailable") from None
    digest = hmac.new(
        secret.get_secret_value().encode("utf-8"),
        b"rahgard:provider-admin-mfa:v1\0" + user.user_id.bytes,
        hashlib.sha256,
    ).digest()
    try:
        allowed = AuthRepository(settings).allow_verification_attempt(
            [("verify_challenge", digest, _MFA_FAILURE_LIMIT)],
            now,
            settings.auth_rate_window_seconds,
        )
    except Exception:
        raise HTTPException(status_code=503, detail="provider_admin_unavailable") from None
    if not allowed:
        raise HTTPException(status_code=429, detail="mfa_rate_limited")


class CapabilityBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: str = Field(min_length=1, max_length=160)
    max_tokens: StrictInt = Field(default=800, ge=1, le=4096)


class ProfileWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    provider_kind: Literal["lm_studio", "openai_compatible"]
    base_url: str = Field(min_length=8, max_length=300)
    auth_mode: Literal["none", "bearer"]
    enabled: StrictBool = True
    capabilities: dict[str, CapabilityBinding] = Field(min_length=1, max_length=4)
    timeout_seconds: StrictInt = Field(default=20, ge=1, le=60)
    concurrency_limit: StrictInt = Field(default=1, ge=1, le=10)
    api_key: SecretStr | None = Field(default=None, max_length=2048)

    @field_validator("name", "base_url")
    @classmethod
    def reject_controls(cls, value: str) -> str:
        if not value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError("Invalid profile value")
        return value.strip()

    @field_validator("capabilities")
    @classmethod
    def supported_capabilities(cls, value):
        if set(value) - _CAPABILITIES:
            raise ValueError("Unsupported capability")
        return value

    @model_validator(mode="after")
    def provider_capability_contract(self):
        # GapGPT's account-specific API capability list has not yet been
        # verified. Keep it Chat-only until the operator has tested and
        # approved its actual account contract. Local LM Studio capabilities
        # are independently tested before activation.
        if self.provider_kind == "openai_compatible" and set(self.capabilities) - {"chat"}:
            raise ValueError("Remote provider capabilities require verified account support")
        return self

    @field_validator("enabled")
    @classmethod
    def disable_only_by_archive(cls, value: bool) -> bool:
        if not value:
            raise ValueError("Use the archive operation to disable a profile")
        return value

    def to_config(self, normalized_url: str) -> dict[str, Any]:
        return {
            "provider_kind": self.provider_kind,
            "base_url": normalized_url,
            "auth_mode": self.auth_mode,
            "timeout_seconds": self.timeout_seconds,
            "concurrency_limit": self.concurrency_limit,
            "capabilities": {key: value.model_dump() for key, value in self.capabilities.items()},
        }


class ProfileUpdate(ProfileWrite):
    expected_version: StrictInt = Field(ge=1)


class StepUpBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")


class RecoveryBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=12, max_length=64)


class RouteChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: UUID
    expected_version: StrictInt = Field(ge=0)


class DeactivateRoute(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: StrictInt = Field(ge=0)


class FallbackPolicyWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: StrictBool
    ordered_revision_ids: list[UUID] = Field(max_length=3)


def _registry(settings: Settings) -> ProviderRegistry:
    def connect():
        return psycopg.connect(
            host=settings.database_host,
            port=settings.database_port,
            dbname=settings.database_name,
            user=settings.database_user,
            password=settings.database_password.get_secret_value(),
            connect_timeout=settings.database_connect_timeout_seconds,
            application_name="rahgard-ai-provider-admin",
            row_factory=dict_row,
        )

    return ProviderRegistry(connect)


def _vault(settings: Settings) -> DpapiSecretVault:
    if settings.ai_provider_vault_dir is None:
        raise VaultUnavailable
    return DpapiSecretVault(settings.ai_provider_vault_dir)


def _admin(settings: Settings, registry: ProviderRegistry, user: AuthenticatedUser) -> None:
    if (
        not settings.ai_provider_admin_enabled
        or settings.app_env.lower() != "local_pilot"
        or user.auth_method != "local_owner"
        or not registry.has_admin_grant(user.user_id)
    ):
        raise HTTPException(status_code=403, detail="admin_required")


def _step_up(registry: ProviderRegistry, user: AuthenticatedUser) -> None:
    if not registry.has_fresh_step_up(user.user_id, user.session_id):
        raise HTTPException(status_code=403, detail="step_up_required")


def _totp_counter(secret: bytes, code: str, now: datetime) -> int | None:
    timestamp = now.timestamp()
    center = int(timestamp // 30)
    for counter in range(max(0, center - 1), center + 2):
        if verify_totp(secret, code, now=counter * 30, window=0):
            return counter
    return None


def _translate_registry_errors(call):
    try:
        return call()
    except RegistryNotFound:
        raise HTTPException(status_code=404, detail="resource_not_found") from None
    except RegistryConflict:
        raise HTTPException(status_code=409, detail="version_conflict") from None
    except (RegistryRejected, ProviderConfigurationError):
        raise HTTPException(status_code=422, detail="configuration_rejected") from None
    except VaultUnavailable:
        raise HTTPException(status_code=503, detail="secret_storage_unavailable") from None


def _public_profile(profile: dict[str, Any], revision: dict[str, Any] | None) -> dict[str, Any]:
    config = revision.get("config", {}) if revision else {}
    return {
        "id": str(profile["profile_id"]),
        "name": profile["name"],
        "provider_kind": profile["provider_kind"],
        "base_url": config.get("base_url", ""),
        "auth_mode": config.get("auth_mode", "none"),
        "enabled": profile["enabled"],
        "capabilities": config.get("capabilities", {}),
        "timeout_seconds": config.get("timeout_seconds", 20),
        "concurrency_limit": config.get("concurrency_limit", 1),
        "version": profile["version"],
        "secret_configured": bool(revision and revision.get("secret_ref")),
    }


def _revision_config(
    body: ProfileWrite, vault: DpapiSecretVault, old_secret_ref: str | None
) -> tuple[dict[str, Any], str | None]:
    probe_key = body.api_key or (
        SecretStr("present-secret-placeholder") if old_secret_ref else None
    )
    normalized_url = validate_provider_base_config(
        body.provider_kind, body.base_url, probe_key
    )
    if (body.auth_mode == "bearer") != (probe_key is not None):
        raise ProviderConfigurationError("Authentication mode and secret do not match")
    new_ref = (
        vault.put(body.api_key.get_secret_value().encode("utf-8"))
        if body.api_key
        else old_secret_ref
    )
    return body.to_config(normalized_url), new_ref


def _provider_adapter(
    revision: dict[str, Any], registry: ProviderRegistry, vault: DpapiSecretVault,
    capability: str | None = None,
):
    config = revision["config"]
    bindings = config["capabilities"]
    selected_capability = capability or next(iter(bindings))
    binding = bindings.get(selected_capability)
    if binding is None:
        raise RegistryRejected("Capability is not configured for this revision")
    ref = revision.get("secret_ref")
    key = SecretStr(vault.get(ref).decode("utf-8")) if ref else None
    return OpenAiCompatibleProviderAdapter(
        ChatProviderConfig(
            provider_kind=revision["provider_kind"],
            base_url=config["base_url"],
            model_id=binding["model_id"],
            api_key=key,
            timeout_seconds=config.get("timeout_seconds", 20),
            max_tokens=binding.get("max_tokens", 800),
            capability=selected_capability,
        )
    )


def _get_revision(registry: ProviderRegistry, profile_id: UUID):
    value = registry.latest_revision(profile_id)
    if value is None:
        raise RegistryNotFound("Provider configuration was not found")
    profile = registry.get_profile(profile_id)
    value = {**value, "provider_kind": profile["provider_kind"]}
    return profile, value


def _check_capability(capability: str) -> str:
    if capability not in _CAPABILITIES:
        raise HTTPException(status_code=422, detail="capability_unsupported")
    return capability


@router.get("/me")
def admin_me(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    mfa = registry.get_admin_mfa(user.user_id) or {}
    expires = registry.step_up_expires_at(user.user_id, user.session_id)
    return {
        "admin": True,
        "mfa_enrolled": mfa.get("enabled_at") is not None,
        "step_up_expires_at": expires.isoformat() if expires else None,
        "provisioned": True,
    }


@router.post("/mfa/enroll")
def enroll_mfa(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    mfa = registry.get_admin_mfa(user.user_id) or {}
    if mfa.get("enabled_at") is not None:
        raise HTTPException(status_code=409, detail="mfa_already_enrolled")
    secret = new_totp_secret()
    reference = _vault(settings).put(secret)
    registry.begin_mfa_enrollment(user.user_id, pending_secret_ref=reference)
    uri = totp_provisioning_uri(secret, str(user.user_id))
    encoded = parse_qs(urlsplit(uri).query).get("secret", [""])[0]
    return {"secret": encoded, "otpauth_uri": uri}


@router.post("/mfa/verify")
def verify_mfa_enrollment(
    body: StepUpBody,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    now = datetime.now(UTC)
    _consume_admin_mfa_attempt(settings, user, now)
    mfa = registry.get_admin_mfa(user.user_id) or {}
    reference = mfa.get("pending_secret_ref")
    if not reference:
        raise HTTPException(status_code=409, detail="mfa_enrollment_missing")
    secret = _vault(settings).get(reference)
    counter = _totp_counter(secret, body.code, now)
    if counter is None:
        raise HTTPException(status_code=401, detail="mfa_code_invalid")
    codes = generate_recovery_codes(10)
    pepper = settings.ai_provider_admin_recovery_pepper.get_secret_value().encode("utf-8")
    registry.activate_mfa(
        user.user_id, recovery_hashes=[hash_recovery_code(code, pepper) for code in codes]
    )
    registry.record_step_up(
        user.user_id,
        user.session_id,
        totp_counter=counter,
        verified_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    return {"mfa_enrolled": True, "recovery_codes": list(codes)}


@router.post("/mfa/step-up")
def step_up(
    body: StepUpBody,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    now = datetime.now(UTC)
    _consume_admin_mfa_attempt(settings, user, now)
    mfa = registry.get_admin_mfa(user.user_id) or {}
    if mfa.get("enabled_at") is None or not mfa.get("secret_ref"):
        raise HTTPException(status_code=403, detail="mfa_required")
    secret = _vault(settings).get(mfa["secret_ref"])
    counter = _totp_counter(secret, body.code, now)
    if counter is None:
        raise HTTPException(status_code=401, detail="mfa_code_invalid")
    registry.record_step_up(
        user.user_id,
        user.session_id,
        totp_counter=counter,
        verified_at=now,
        expires_at=now + timedelta(minutes=5),
    )
    expiry = now + timedelta(minutes=5)
    return {"step_up_expires_at": expiry.isoformat()}


@router.post("/mfa/recovery")
def recovery_step_up(
    body: RecoveryBody,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    now = datetime.now(UTC)
    _consume_admin_mfa_attempt(settings, user, now)
    pepper = settings.ai_provider_admin_recovery_pepper.get_secret_value().encode("utf-8")
    verifier = hash_recovery_code(body.code, pepper)
    if not registry.consume_recovery_and_step_up(
        user.user_id,
        user.session_id,
        verifier,
        verified_at=now,
        expires_at=now + timedelta(minutes=5),
    ):
        raise HTTPException(status_code=401, detail="recovery_code_invalid")
    return {"step_up_expires_at": (now + timedelta(minutes=5)).isoformat()}


@router.get("/profiles")
def profiles(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    output = []
    for profile in registry.list_profiles():
        latest = registry.latest_revision(profile["profile_id"])
        output.append(_public_profile(profile, latest))
    return {"profiles": output}


def _save_profile(
    body: ProfileWrite,
    *,
    registry: ProviderRegistry,
    vault: DpapiSecretVault,
    actor: UUID,
    profile_id: UUID | None = None,
    expected_version: int | None = None,
):
    previous_ref = None
    created_ref = None
    if profile_id is not None:
        current = registry.get_profile(profile_id)
        if current["provider_kind"] != body.provider_kind:
            raise RegistryRejected("Provider type cannot change after profile creation")
        latest = registry.latest_revision(profile_id)
        previous_ref = latest.get("secret_ref") if latest else None
    config, secret_ref = _revision_config(body, vault, previous_ref)
    if body.api_key:
        created_ref = secret_ref
    try:
        if profile_id is None:
            created, revision = registry.create_profile_with_revision(
                body.name,
                body.provider_kind,
                config=config,
                secret_ref=secret_ref,
                actor_id=actor,
            )
            profile_id = created["profile_id"]
        else:
            revision = registry.create_revision(
                profile_id,
                expected_profile_version=expected_version or 0,
                config=config,
                secret_ref=secret_ref,
                actor_id=actor,
                profile_name=body.name,
            )
    except Exception:
        if created_ref:
            try:
                vault.delete(created_ref)
            except VaultUnavailable:
                pass
        raise
    profile = registry.get_profile(profile_id)
    latest = registry.latest_revision(profile_id)
    return _public_profile(profile, latest), revision


@router.post("/profiles")
def create_profile(
    body: ProfileWrite,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    _step_up(registry, user)
    try:
        profile, _revision = _save_profile(
            body, registry=registry, vault=_vault(settings), actor=user.user_id
        )
        return profile
    except (RegistryRejected, RegistryConflict, ProviderConfigurationError, VaultUnavailable):
        raise HTTPException(status_code=422, detail="configuration_rejected") from None


@router.patch("/profiles/{profile_id}")
def update_profile(
    profile_id: UUID,
    body: ProfileUpdate,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    _step_up(registry, user)
    # expected_version is supplied separately by the frontend contract.
    try:
        profile, _revision = _save_profile(
            ProfileWrite.model_validate(body.model_dump(exclude={"expected_version"})),
            registry=registry,
            vault=_vault(settings),
            actor=user.user_id,
            profile_id=profile_id,
            expected_version=body.expected_version,
        )
        return profile
    except RegistryNotFound:
        raise HTTPException(status_code=404, detail="resource_not_found") from None
    except RegistryConflict:
        raise HTTPException(status_code=409, detail="version_conflict") from None
    except (RegistryRejected, ProviderConfigurationError, VaultUnavailable):
        raise HTTPException(status_code=422, detail="configuration_rejected") from None


@router.post("/profiles/{profile_id}/archive", status_code=204)
def archive_profile(
    profile_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    _step_up(registry, user)
    profile = registry.get_profile(profile_id)
    registry.update_profile(
        profile_id,
        expected_version=profile["version"],
        name=profile["name"],
        enabled=False,
        archived=True,
        actor_id=user.user_id,
    )
    return Response(status_code=204)


@router.post("/profiles/{profile_id}/discover-models")
async def discover_models(
    profile_id: UUID,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    _step_up(registry, user)
    try:
        _profile, revision = _get_revision(registry, profile_id)
        adapter = _provider_adapter(revision, registry, _vault(settings))
        models = await adapter.discover_models()
        support = adapter.capability_support()
        return {
            "models": list(models),
            "status": "reachable",
            "capability_support": support,
        }
    except (RegistryNotFound, VaultUnavailable):
        raise HTTPException(status_code=503, detail="provider_unavailable") from None
    except ProviderTransportError:
        raise HTTPException(status_code=503, detail="provider_unavailable") from None


class ConnectionTestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    capability: Literal["chat", "vision", "embedding", "reranking"]
    model_id: str = Field(min_length=1, max_length=160)
    test_kind: Literal["discovery", "inference"]
    max_output_tokens: StrictInt = Field(default=32, ge=1, le=64)


@router.post("/profiles/{profile_id}/test")
async def test_profile(
    profile_id: UUID,
    body: ConnectionTestBody,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    _step_up(registry, user)
    capability = _check_capability(body.capability)
    _profile, revision = _get_revision(registry, profile_id)
    binding = revision["config"].get("capabilities", {}).get(capability)
    if binding is None:
        raise HTTPException(status_code=422, detail="capability_not_configured")
    if binding["model_id"] != body.model_id:
        raise HTTPException(status_code=422, detail="model_not_configured")
    started = time.perf_counter()
    latency_ms = 0
    try:
        result = await _provider_adapter(
            revision, registry, _vault(settings), capability
        ).test_capability(
            capability,
            body.model_id,
            test_kind=body.test_kind,
            max_output_tokens=body.max_output_tokens,
        )
        latency_ms = int(result["latency_ms"])
        valid = bool(result["actual_inference_passed"])
        registry.record_validation(
            revision["revision_id"],
            outcome="valid" if valid else "unavailable" if result["status"] == "unavailable" else "invalid",
            safe_details={
                "capability": capability,
                "test_kind": body.test_kind,
                "tested_model_id": body.model_id,
                "models_catalog_reachable": result["models_catalog_reachable"],
                "model_selected": result["model_selected"],
                "capability_verified": result["capability_verified"],
                "actual_inference_passed": result["actual_inference_passed"],
                "latency_ms": latency_ms,
            },
            actor_id=user.user_id,
        )
        return result
    except ProviderAuthenticationError:
        latency_ms = round((time.perf_counter() - started) * 1000)
        registry.record_validation(
            revision["revision_id"],
            outcome="invalid",
            safe_details={
                "capability": capability,
                "test_kind": body.test_kind,
                "tested_model_id": body.model_id,
                "error_code": "authentication_failed",
                "latency_ms": latency_ms,
            },
            actor_id=user.user_id,
        )
        return {
            "success": False,
            "status": "authentication_failed",
            "latency_ms": latency_ms,
            "model_id": body.model_id,
            "capability": capability,
            "test_kind": body.test_kind,
            "models_catalog_reachable": False,
            "model_selected": False,
            "capability_verified": False,
            "actual_inference_passed": False,
        }
    except ProviderCapabilityUnsupported:
        latency_ms = round((time.perf_counter() - started) * 1000)
        registry.record_validation(
            revision["revision_id"],
            outcome="invalid",
            safe_details={
                "capability": capability,
                "test_kind": body.test_kind,
                "tested_model_id": body.model_id,
                "error_code": "unsupported",
                "latency_ms": latency_ms,
            },
            actor_id=user.user_id,
        )
        return {
            "success": False,
            "status": "unsupported",
            "latency_ms": latency_ms,
            "model_id": body.model_id,
            "capability": capability,
            "test_kind": body.test_kind,
            "models_catalog_reachable": False,
            "model_selected": False,
            "capability_verified": False,
            "actual_inference_passed": False,
        }
    except (ProviderTransportError, VaultUnavailable):
        latency_ms = round((time.perf_counter() - started) * 1000)
        registry.record_validation(
            revision["revision_id"],
            outcome="unavailable",
            safe_details={
                "capability": capability,
                "test_kind": body.test_kind,
                "tested_model_id": body.model_id,
                "error_code": "unavailable",
                "latency_ms": latency_ms,
            },
            actor_id=user.user_id,
        )
        return {
            "success": False,
            "status": "unavailable",
            "latency_ms": latency_ms,
            "model_id": body.model_id,
            "capability": capability,
            "test_kind": body.test_kind,
            "models_catalog_reachable": False,
            "model_selected": False,
            "capability_verified": False,
            "actual_inference_passed": False,
        }


@router.get("/routes")
def routes(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    revisions = [
        item
        for profile in registry.list_profiles()
        for item in registry.list_revisions(profile["profile_id"])
    ]
    by_revision = {str(item["revision_id"]): item for item in revisions}
    result = []
    for capability in sorted(_CAPABILITIES):
        active = registry.active_snapshot(capability)
        item = by_revision.get(str(active.revision_id)) if active.revision_id else None
        profile = registry.get_profile(item["profile_id"]) if item else None
        binding = active.config.get("capabilities", {}).get(capability, {}) if active.config else {}
        result.append(
            {
                "capability": capability,
                "profile_id": str(profile["profile_id"]) if profile else None,
                "profile_name": profile["name"] if profile else None,
                "revision": str(active.revision_id) if active.revision_id else None,
                "model_id": binding.get("model_id"),
                "active": active.revision_id is not None,
                "version": active.generation,
            }
        )
    return {"routes": result}


@router.get("/fallback")
def get_fallback_policies(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    return {
        "policies": [
            {
                "capability": capability,
                "enabled": policy["enabled"],
                "ordered_revision_ids": [str(value) for value in policy["ordered_revision_ids"]],
            }
            for capability in sorted(_CAPABILITIES)
            if (policy := registry.get_fallback(capability)) is not None
        ]
    }


@router.put("/fallback/{capability}")
def put_fallback_policy(
    capability: str,
    body: FallbackPolicyWrite,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    _step_up(registry, user)
    capability = _check_capability(capability)
    try:
        policy = registry.set_fallback(
            capability,
            body.enabled,
            body.ordered_revision_ids,
            actor_id=user.user_id,
        )
    except (RegistryRejected, RegistryNotFound):
        raise HTTPException(status_code=422, detail="fallback_configuration_rejected") from None
    return {
        "capability": capability,
        "enabled": policy["enabled"],
        "ordered_revision_ids": [str(value) for value in policy["ordered_revision_ids"]],
    }


@router.get("/revisions")
def revisions(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    routes_by_cap = {item["capability"]: item for item in routes(user, settings)["routes"]}
    output = []
    for profile in registry.list_profiles():
        for revision in registry.list_revisions(profile["profile_id"]):
            for capability, binding in revision["config"].get("capabilities", {}).items():
                validation = registry.capability_validation(
                    revision["revision_id"], capability, test_kind="inference"
                )
                output.append(
                    {
                        "revision": str(revision["revision_id"]),
                        "profile_id": str(profile["profile_id"]),
                        "profile_name": profile["name"],
                        "capability": capability,
                        "model_id": binding["model_id"],
                        "validated_at": validation["validated_at"].isoformat()
                        if validation and validation.get("validated_at")
                        else "",
                        "validation_status": validation.get("outcome") if validation else "pending",
                        "validation_details": validation.get("details", {}) if validation else {},
                        "validation_test_kind": "inference" if validation else None,
                        "active": routes_by_cap.get(capability, {}).get("revision")
                        == str(revision["revision_id"]),
                    }
                )
    return {"revisions": output}


@router.post("/routes/{capability}/activate")
def activate_route(
    capability: str,
    body: RouteChange,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    _step_up(registry, user)
    _check_capability(capability)
    _translate_registry_errors(
        lambda: registry.activate(
            capability,
            body.revision,
            expected_generation=body.expected_version,
            actor_id=user.user_id,
        )
    )
    return routes(user, settings)["routes"][
        [r["capability"] for r in routes(user, settings)["routes"]].index(capability)
    ]


@router.post("/routes/{capability}/deactivate")
def deactivate_route(
    capability: str,
    body: DeactivateRoute,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    _step_up(registry, user)
    _check_capability(capability)
    _translate_registry_errors(
        lambda: registry.deactivate(
            capability, expected_generation=body.expected_version, actor_id=user.user_id
        )
    )
    return next(
        item for item in routes(user, settings)["routes"] if item["capability"] == capability
    )


@router.post("/routes/{capability}/rollback")
def rollback_route(
    capability: str,
    body: RouteChange,
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    _csrf: Annotated[None, Depends(require_authenticated_csrf)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    _step_up(registry, user)
    _check_capability(capability)
    _translate_registry_errors(
        lambda: registry.rollback(
            capability,
            body.revision,
            expected_generation=body.expected_version,
            actor_id=user.user_id,
        )
    )
    return next(
        item for item in routes(user, settings)["routes"] if item["capability"] == capability
    )


@router.get("/audit")
def audit(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    return {
        "events": [
            {
                "action": row["action"],
                "actor": str(row["actor_id"] or "operator"),
                "target": row["target_id"],
                "result": row["outcome"],
                "created_at": row["occurred_at"].isoformat(),
            }
            for row in registry.list_audit()
        ]
    }


@router.get("/usage")
def usage(
    user: Annotated[AuthenticatedUser, Depends(authenticated_user)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    registry = _registry(settings)
    _admin(settings, registry, user)
    events = registry.list_usage()
    grouped = {}
    for event in events:
        entry = grouped.setdefault(
            event["capability"],
            {
                "capability": event["capability"],
                "calls": 0,
                "successes": 0,
                "failures": 0,
                "latency_ms_avg": None,
                "period_start": event["occurred_at"].isoformat(),
                "_latencies": [],
            },
        )
        entry["calls"] += 1
        entry["successes"] += event["outcome"] == "success"
        entry["failures"] += event["outcome"] != "success"
        if event["latency_ms"] is not None:
            entry["_latencies"].append(event["latency_ms"])
    for entry in grouped.values():
        latencies = entry.pop("_latencies")
        entry["latency_ms_avg"] = round(sum(latencies) / len(latencies)) if latencies else None
    return {"usage": list(grouped.values())}
