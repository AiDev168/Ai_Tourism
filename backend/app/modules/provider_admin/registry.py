"""Transactional, secret-free persistence for administrator-managed providers.

The operating-system vault is deliberately outside this module. Database rows
contain only opaque vault references; callers must resolve a secret only in
trusted backend code after authorization and step-up checks.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from typing import Any
from uuid import UUID

import psycopg

CAPABILITIES = frozenset({"chat", "vision", "embedding", "reranking"})


class RegistryConflict(RuntimeError):
    """An optimistic version or activation generation is stale."""


class RegistryNotFound(LookupError):
    """A requested profile, revision, or administrator record is absent."""


class RegistryRejected(ValueError):
    """The requested state transition violates registry invariants."""


@dataclass(frozen=True, slots=True)
class ActiveRoute:
    capability: str
    revision_id: UUID | None
    generation: int
    config: Mapping[str, Any] | None
    secret_ref: str | None


def _validate_capability(capability: str) -> str:
    if capability not in CAPABILITIES:
        raise RegistryRejected("Unsupported AI capability")
    return capability


def _row(cursor: Any) -> dict[str, Any] | None:
    value = cursor.fetchone()
    if value is None:
        return None
    if isinstance(value, Mapping):
        return dict(value)
    names = [column.name for column in cursor.description]
    return dict(zip(names, value, strict=True))


class ProviderRegistry:
    """PostgreSQL repository with compare-and-swap activation semantics.

    `connection_factory` must create a least-privilege application connection.
    It never stores credentials or creates a connection string itself.
    """

    def __init__(self, connection_factory: Callable[[], psycopg.Connection[Any]], *,
                 provisioner_connection_factory: Callable[[], psycopg.Connection[Any]] | None = None) -> None:
        self._connect = connection_factory
        self._connect_provisioner = provisioner_connection_factory

    def list_profiles(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.execute(
                """SELECT p.profile_id,p.name,p.provider_kind,p.enabled,p.archived_at,p.version,
                          p.created_at,p.updated_at,
                          (SELECT r.revision_id FROM ai_provider.revisions r
                           WHERE r.profile_id=p.profile_id ORDER BY r.revision_no DESC LIMIT 1) AS latest_revision_id,
                          EXISTS(SELECT 1 FROM ai_provider.revisions r
                            JOIN LATERAL (SELECT v.outcome FROM ai_provider.revision_validations v
                              WHERE v.revision_id=r.revision_id ORDER BY v.validated_at DESC LIMIT 1) v ON TRUE
                            WHERE r.profile_id=p.profile_id AND v.outcome='valid') AS has_validated_revision
                   FROM ai_provider.profiles p ORDER BY lower(p.name),p.profile_id"""
            )
            result = []
            while (item := _row(cur)) is not None:
                result.append(item)
            return result

    def get_profile(self, profile_id: UUID) -> dict[str, Any]:
        with self._connect() as conn:
            cur = conn.execute(
                """SELECT profile_id,name,provider_kind,enabled,archived_at,version,created_by,created_at,updated_at
                   FROM ai_provider.profiles WHERE profile_id=%s""",
                (profile_id,),
            )
            item = _row(cur)
            if item is None:
                raise RegistryNotFound("Provider profile was not found")
            return item

    def list_revisions(self, profile_id: UUID) -> list[dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.execute(
                """SELECT r.revision_id,r.profile_id,r.revision_no,r.config,
                          (r.secret_ref IS NOT NULL) AS secret_configured,
                          v.outcome AS latest_validation,v.details AS validation_details,
                          v.validated_at,r.created_by,r.created_at
                   FROM ai_provider.revisions r
                   LEFT JOIN LATERAL (SELECT outcome,details,validated_at
                     FROM ai_provider.revision_validations WHERE revision_id=r.revision_id
                     ORDER BY validated_at DESC LIMIT 1) v ON TRUE
                   WHERE r.profile_id=%s ORDER BY r.revision_no DESC""",
                (profile_id,),
            )
            result = []
            while (item := _row(cur)) is not None:
                result.append(item)
            return result

    def latest_revision(self, profile_id: UUID) -> dict[str, Any] | None:
        """Trusted-backend-only complete revision, including opaque secret ref.

        Use internally to retain a credential reference when editing non-secret
        settings. Never serialize this result through an HTTP response.
        """
        with self._connect() as conn:
            return _row(conn.execute(
                """SELECT r.revision_id,r.profile_id,r.revision_no,r.config,r.secret_ref,
                          v.outcome AS latest_validation
                   FROM ai_provider.revisions r
                   LEFT JOIN LATERAL (SELECT outcome FROM ai_provider.revision_validations
                     WHERE revision_id=r.revision_id ORDER BY validated_at DESC LIMIT 1) v ON TRUE
                   WHERE r.profile_id=%s ORDER BY r.revision_no DESC LIMIT 1""", (profile_id,)
            ))

    def create_profile(self, name: str, provider_kind: str, actor_id: UUID) -> dict[str, Any]:
        clean = name.strip()
        if not 1 <= len(clean) <= 100 or provider_kind not in {"lm_studio", "openai_compatible"}:
            raise RegistryRejected("Invalid provider profile")
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO ai_provider.profiles(name,provider_kind,created_by)
                   VALUES (%s,%s,%s) RETURNING profile_id,name,provider_kind,enabled,version,created_at""",
                (clean, provider_kind, actor_id),
            )
            created = _row(cur)
            assert created is not None
            self._audit(conn, actor_id, "profile_created", "profile", str(created["profile_id"]), "success", {})
            return created

    def create_profile_with_revision(
        self, name: str, provider_kind: str, *, config: Mapping[str, Any],
        secret_ref: str | None, actor_id: UUID,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Create a profile and its initial immutable revision atomically."""
        clean = name.strip()
        capabilities = config.get("capabilities")
        if not 1 <= len(clean) <= 100 or provider_kind not in {"lm_studio", "openai_compatible"}:
            raise RegistryRejected("Invalid provider profile")
        if not isinstance(capabilities, Mapping) or not capabilities:
            raise RegistryRejected("At least one capability must be configured")
        if any(key not in CAPABILITIES for key in capabilities):
            raise RegistryRejected("Unsupported capability binding")
        self._ensure_no_secret_fields(config)
        if secret_ref is not None and not 8 <= len(secret_ref) <= 512:
            raise RegistryRejected("Invalid vault reference")
        with self._connect() as conn:
            profile = _row(conn.execute(
                """INSERT INTO ai_provider.profiles(name,provider_kind,created_by)
                   VALUES (%s,%s,%s)
                   RETURNING profile_id,name,provider_kind,enabled,archived_at,version,created_at""",
                (clean, provider_kind, actor_id),
            ))
            if profile is None:
                raise RegistryRejected("Provider profile could not be created")
            revision = _row(conn.execute(
                """INSERT INTO ai_provider.revisions(profile_id,revision_no,config,secret_ref,created_by)
                   VALUES (%s,1,%s::jsonb,%s,%s)
                   RETURNING revision_id,profile_id,revision_no,config,created_at""",
                (profile["profile_id"], json.dumps(dict(config), ensure_ascii=False), secret_ref, actor_id),
            ))
            if revision is None:
                raise RegistryRejected("Initial provider revision could not be created")
            self._audit(conn, actor_id, "profile_created", "profile", str(profile["profile_id"]), "success", {})
            self._audit(conn, actor_id, "revision_created", "revision", str(revision["revision_id"]), "success",
                        {"profile_id": str(profile["profile_id"]), "revision_no": 1,
                         "secret_configured": secret_ref is not None})
            return profile, revision

    def update_profile(
        self, profile_id: UUID, *, expected_version: int, name: str, enabled: bool,
        archived: bool, actor_id: UUID,
    ) -> dict[str, Any]:
        clean = name.strip()
        if not 1 <= len(clean) <= 100 or (archived and enabled):
            raise RegistryRejected("Invalid provider profile update")
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE ai_provider.profiles SET name=%s,enabled=%s,
                     archived_at=CASE WHEN %s THEN COALESCE(archived_at,pg_catalog.now()) ELSE NULL END,
                     version=version+1,updated_at=pg_catalog.now()
                   WHERE profile_id=%s AND version=%s
                   RETURNING profile_id,name,provider_kind,enabled,archived_at,version,updated_at""",
                (clean, enabled, archived, profile_id, expected_version),
            )
            updated = _row(cur)
            if updated is None:
                exists = conn.execute("SELECT 1 FROM ai_provider.profiles WHERE profile_id=%s", (profile_id,)).fetchone()
                if not exists:
                    raise RegistryNotFound("Provider profile was not found")
                raise RegistryConflict("Provider profile changed; reload and retry")
            self._audit(conn, actor_id, "profile_updated", "profile", str(profile_id), "success",
                        {"version": updated["version"], "enabled": enabled, "archived": archived})
            if not enabled or archived:
                conn.execute(
                    """UPDATE ai_provider.active_routes a SET revision_id=NULL,generation=generation+1,
                         updated_by=%s,updated_at=pg_catalog.now()
                       FROM ai_provider.revisions r WHERE a.revision_id=r.revision_id
                         AND r.profile_id=%s""", (actor_id, profile_id)
                )
                conn.execute(
                    """UPDATE ai_provider.fallback_policy f SET ordered_revision_ids=ARRAY(
                           SELECT item.revision_id
                           FROM unnest(f.ordered_revision_ids) WITH ORDINALITY AS item(revision_id,position)
                           WHERE NOT EXISTS (SELECT 1 FROM ai_provider.revisions r
                                             WHERE r.revision_id=item.revision_id AND r.profile_id=%s)
                           ORDER BY item.position)
                       WHERE f.ordered_revision_ids && COALESCE(
                           (SELECT array_agg(revision_id) FROM ai_provider.revisions WHERE profile_id=%s),
                           ARRAY[]::UUID[])""",
                    (profile_id, profile_id),
                )
                conn.execute(
                    """UPDATE ai_provider.fallback_policy SET enabled=FALSE,updated_by=%s,
                           updated_at=pg_catalog.now()
                       WHERE enabled=TRUE AND cardinality(ordered_revision_ids)=0""",
                    (actor_id,),
                )
            return updated

    def create_revision(
        self, profile_id: UUID, *, expected_profile_version: int,
        config: Mapping[str, Any], secret_ref: str | None, actor_id: UUID,
        profile_name: str | None = None,
    ) -> dict[str, Any]:
        """Insert immutable provider settings, storing only an opaque secret ref."""
        capabilities = config.get("capabilities")
        if not isinstance(capabilities, Mapping) or not capabilities:
            raise RegistryRejected("At least one capability must be configured")
        if any(key not in CAPABILITIES for key in capabilities):
            raise RegistryRejected("Unsupported capability binding")
        self._ensure_no_secret_fields(config)
        if secret_ref is not None and not 8 <= len(secret_ref) <= 512:
            raise RegistryRejected("Invalid vault reference")
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE ai_provider.profiles SET name=COALESCE(%s,name),version=version+1,updated_at=pg_catalog.now()
                   WHERE profile_id=%s AND enabled=TRUE AND archived_at IS NULL AND version=%s
                   RETURNING version""",
                (profile_name, profile_id, expected_profile_version),
            )
            if _row(cur) is None:
                exists = conn.execute("SELECT 1 FROM ai_provider.profiles WHERE profile_id=%s", (profile_id,)).fetchone()
                if not exists:
                    raise RegistryNotFound("Provider profile was not found")
                raise RegistryConflict("Provider profile changed or is disabled")
            cur = conn.execute(
                """INSERT INTO ai_provider.revisions(profile_id,revision_no,config,secret_ref,created_by)
                   SELECT %s,COALESCE(max(revision_no),0)+1,%s::jsonb,%s,%s
                   FROM ai_provider.revisions WHERE profile_id=%s
                   RETURNING revision_id,profile_id,revision_no,config,created_at""",
                (profile_id, json.dumps(dict(config), ensure_ascii=False), secret_ref, actor_id, profile_id),
            )
            revision = _row(cur)
            assert revision is not None
            self._audit(conn, actor_id, "revision_created", "revision", str(revision["revision_id"]), "success",
                        {"profile_id": str(profile_id), "revision_no": revision["revision_no"],
                         "secret_configured": secret_ref is not None})
            return revision

    def record_validation(
        self, revision_id: UUID, *, outcome: str, safe_details: Mapping[str, Any], actor_id: UUID,
    ) -> dict[str, Any]:
        if outcome not in {"valid", "invalid", "unavailable"}:
            raise RegistryRejected("Invalid validation outcome")
        safe_details = self._validation_details(safe_details)
        if outcome == "valid" and (
            not safe_details.get("capability") or not safe_details.get("test_kind")
        ):
            raise RegistryRejected("Successful validation must identify its capability and test kind")
        if outcome == "valid" and safe_details.get("test_kind") == "inference" and not all(
            safe_details.get(key) is True
            for key in ("model_selected", "capability_verified", "actual_inference_passed")
        ):
            raise RegistryRejected("Inference validation requires a successful model capability test")
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO ai_provider.revision_validations(revision_id,outcome,details,validated_by)
                   VALUES (%s,%s,%s::jsonb,%s) RETURNING validation_id,revision_id,outcome,validated_at""",
                (revision_id, outcome, json.dumps(dict(safe_details), ensure_ascii=False), actor_id),
            )
            result = _row(cur)
            if result is None:
                raise RegistryNotFound("Provider revision was not found")
            self._audit(conn, actor_id, "revision_validated", "revision", str(revision_id), outcome,
                        {"validation_id": str(result["validation_id"])})
            return result

    def capability_validation(
        self, revision_id: UUID, capability: str, *, test_kind: str = "inference"
    ) -> dict[str, Any] | None:
        cap = _validate_capability(capability)
        if test_kind not in {"discovery", "inference"}:
            raise RegistryRejected("Invalid provider validation kind")
        with self._connect() as conn:
            return _row(conn.execute(
                """SELECT outcome,details,validated_at FROM ai_provider.revision_validations
                   WHERE revision_id=%s AND details->>'capability'=%s AND details->>'test_kind'=%s
                   ORDER BY validated_at DESC,validation_id DESC LIMIT 1""",
                (revision_id, cap, test_kind),
            ))

    def active_snapshot(self, capability: str) -> ActiveRoute:
        cap = _validate_capability(capability)
        with self._connect() as conn:
            cur = conn.execute(
                """SELECT a.capability,a.revision_id,a.generation,r.config,r.secret_ref
                   FROM ai_provider.active_routes a
                   LEFT JOIN ai_provider.revisions r ON r.revision_id=a.revision_id
                   WHERE a.capability=%s""",
                (cap,),
            )
            item = _row(cur)
            if item is None:
                raise RegistryNotFound("Provider route was not found")
            return ActiveRoute(cap, item["revision_id"], item["generation"], item["config"], item["secret_ref"])

    def validated_snapshot(self, capability: str, revision_id: UUID) -> ActiveRoute:
        """Resolve one exact, validated revision for explicit fallback routing.

        This does not activate the revision or alter the runtime pointer. A
        caller must have independently authorized fallback and selected this
        revision from the configured order.
        """
        cap = _validate_capability(capability)
        with self._connect() as conn:
            cur = conn.execute(
                """SELECT r.revision_id,r.config,r.secret_ref,p.enabled,p.archived_at,
                          (SELECT v.outcome FROM ai_provider.revision_validations v
                           WHERE v.revision_id=r.revision_id AND v.details->>'capability'=%s
                             AND v.details->>'test_kind'='inference'
                           ORDER BY v.validated_at DESC,v.validation_id DESC LIMIT 1) AS latest_validation
                   FROM ai_provider.revisions r JOIN ai_provider.profiles p USING(profile_id)
                   WHERE r.revision_id=%s""", (cap, revision_id)
            )
            item = _row(cur)
            if item is None:
                raise RegistryNotFound("Provider revision was not found")
            bindings = item["config"].get("capabilities", {})
            if (not item["enabled"] or item["archived_at"] is not None
                    or item["latest_validation"] != "valid" or cap not in bindings):
                raise RegistryRejected("Provider revision is not currently eligible for this capability")
            route = _row(conn.execute(
                "SELECT generation FROM ai_provider.active_routes WHERE capability=%s", (cap,)
            ))
            return ActiveRoute(cap, item["revision_id"], route["generation"] if route else 0,
                               item["config"], item["secret_ref"])

    def activate(self, capability: str, revision_id: UUID, *, expected_generation: int, actor_id: UUID) -> ActiveRoute:
        return self._set_route(capability, revision_id, expected_generation, actor_id, "route_activated")

    def rollback(self, capability: str, revision_id: UUID, *, expected_generation: int, actor_id: UUID) -> ActiveRoute:
        # Only a previously validated immutable revision can be restored.
        return self._set_route(capability, revision_id, expected_generation, actor_id, "route_rolled_back")

    def deactivate(self, capability: str, *, expected_generation: int, actor_id: UUID) -> ActiveRoute:
        return self._set_route(capability, None, expected_generation, actor_id, "route_deactivated")

    def _set_route(self, capability: str, revision_id: UUID | None, expected_generation: int,
                   actor_id: UUID, action: str) -> ActiveRoute:
        cap = _validate_capability(capability)
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT revision_id,generation FROM ai_provider.active_routes WHERE capability=%s FOR UPDATE",
                (cap,),
            )
            current = _row(cur)
            if current is None:
                raise RegistryNotFound("Provider route was not found")
            if current["generation"] != expected_generation:
                raise RegistryConflict("Provider route changed; reload and retry")
            selected: dict[str, Any] | None = None
            if revision_id is not None:
                cur = conn.execute(
                    """SELECT r.revision_id,r.profile_id,r.config,r.secret_ref,p.enabled,p.archived_at,
                              (SELECT outcome FROM ai_provider.revision_validations v
                               WHERE v.revision_id=r.revision_id AND v.details->>'capability'=%s
                                 AND v.details->>'test_kind'='inference'
                               ORDER BY v.validated_at DESC,v.validation_id DESC LIMIT 1) AS latest_validation
                       FROM ai_provider.revisions r JOIN ai_provider.profiles p USING(profile_id)
                       WHERE r.revision_id=%s""",
                    (cap, revision_id),
                )
                selected = _row(cur)
                if selected is None:
                    raise RegistryNotFound("Provider revision was not found")
                if not selected["enabled"] or selected["archived_at"] is not None:
                    raise RegistryRejected("Provider profile is disabled")
                bindings = selected["config"].get("capabilities", {})
                if cap not in bindings or selected["latest_validation"] != "valid":
                    raise RegistryRejected("Provider revision is not validated for this capability")
            cur = conn.execute(
                """UPDATE ai_provider.active_routes SET revision_id=%s,generation=generation+1,
                       updated_by=%s,updated_at=pg_catalog.now()
                   WHERE capability=%s AND generation=%s
                   RETURNING generation""",
                (revision_id, actor_id, cap, expected_generation),
            )
            updated = _row(cur)
            if updated is None:
                raise RegistryConflict("Provider route changed; reload and retry")
            self._audit(conn, actor_id, action, "capability", cap, "success",
                        {"revision_id": str(revision_id) if revision_id else None,
                         "generation": updated["generation"]})
            return ActiveRoute(cap, revision_id, updated["generation"],
                               selected["config"] if selected else None,
                               selected["secret_ref"] if selected else None)

    def get_fallback(self, capability: str) -> dict[str, Any]:
        cap = _validate_capability(capability)
        with self._connect() as conn:
            item = _row(conn.execute(
                "SELECT capability,enabled,ordered_revision_ids,updated_by,updated_at FROM ai_provider.fallback_policy WHERE capability=%s",
                (cap,),
            ))
            if item is None:
                raise RegistryNotFound("Fallback policy was not found")
            return item

    def set_fallback(self, capability: str, enabled: bool, ordered_revision_ids: Sequence[UUID],
                     *, actor_id: UUID) -> dict[str, Any]:
        cap = _validate_capability(capability)
        ordered = list(ordered_revision_ids)
        if not enabled and ordered:
            raise RegistryRejected("Fallback routes must be empty while fallback is disabled")
        if enabled and not ordered:
            raise RegistryRejected("Enabled fallback requires an explicit ordered profile")
        if len(set(ordered)) != len(ordered) or len(ordered) > 3:
            raise RegistryRejected("Fallback order is invalid")
        with self._connect() as conn:
            if enabled:
                for revision_id in ordered:
                    cur = conn.execute(
                        """SELECT r.config,p.enabled,p.archived_at,
                                  (SELECT outcome FROM ai_provider.revision_validations v
                                   WHERE v.revision_id=r.revision_id AND v.details->>'capability'=%s
                                     AND v.details->>'test_kind'='inference'
                                   ORDER BY v.validated_at DESC,v.validation_id DESC LIMIT 1) AS result
                           FROM ai_provider.revisions r JOIN ai_provider.profiles p USING(profile_id)
                           WHERE r.revision_id=%s""",
                        (cap, revision_id),
                    )
                    candidate = _row(cur)
                    if (candidate is None or not candidate["enabled"] or candidate["archived_at"] is not None
                            or cap not in candidate["config"].get("capabilities", {}) or candidate["result"] != "valid"):
                        raise RegistryRejected("Fallback revision is not validated for this capability")
            item = _row(conn.execute(
                """UPDATE ai_provider.fallback_policy SET enabled=%s,ordered_revision_ids=%s,
                      updated_by=%s,updated_at=pg_catalog.now() WHERE capability=%s
                   RETURNING capability,enabled,ordered_revision_ids,updated_by,updated_at""",
                (enabled, ordered, actor_id, cap),
            ))
            assert item is not None
            self._audit(conn, actor_id, "fallback_updated", "capability", cap, "success",
                        {"enabled": enabled, "count": len(ordered)})
            return item

    def list_usage(self, limit: int = 100) -> list[dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= 500:
            raise RegistryRejected("Invalid usage page size")
        with self._connect() as conn:
            cur = conn.execute(
                """SELECT capability,revision_id,outcome,latency_ms,input_units,output_units,occurred_at
                   FROM ai_provider.usage_events ORDER BY occurred_at DESC LIMIT %s""", (limit,)
            )
            result = []
            while (item := _row(cur)) is not None:
                result.append(item)
            return result

    def record_usage(self, *, capability: str, revision_id: UUID | None, outcome: str,
                     latency_ms: int | None, input_units: int | None = None,
                     output_units: int | None = None) -> None:
        cap = _validate_capability(capability)
        if outcome not in {"success", "unavailable", "rejected"}:
            raise RegistryRejected("Invalid usage outcome")
        for value in (latency_ms, input_units, output_units):
            if value is not None and (type(value) is not int or value < 0):
                raise RegistryRejected("Invalid usage metric")
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO ai_provider.usage_events(capability,revision_id,outcome,latency_ms,input_units,output_units)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (cap, revision_id, outcome, latency_ms, input_units, output_units),
            )

    def list_audit(self, limit: int = 100) -> list[dict[str, Any]]:
        if type(limit) is not int or not 1 <= limit <= 500:
            raise RegistryRejected("Invalid audit page size")
        with self._connect() as conn:
            cur = conn.execute(
                """SELECT event_id,actor_id,action,target_type,target_id,outcome,metadata,occurred_at
                   FROM ai_provider.audit_events ORDER BY occurred_at DESC LIMIT %s""", (limit,)
            )
            result = []
            while (item := _row(cur)) is not None:
                result.append(item)
            return result

    def has_admin_grant(self, user_id: UUID) -> bool:
        with self._connect() as conn:
            return conn.execute(
                "SELECT 1 FROM identity.ai_provider_admin_grants WHERE user_id=%s AND revoked_at IS NULL",
                (user_id,),
            ).fetchone() is not None

    def get_admin_mfa(self, user_id: UUID) -> dict[str, Any] | None:
        """Trusted-backend-only MFA metadata; never serialize vault refs to HTTP."""
        with self._connect() as conn:
            return _row(conn.execute(
                """SELECT user_id,secret_ref,pending_secret_ref,enabled_at,last_totp_counter,
                          recovery_hashes,version,updated_at
                   FROM identity.ai_provider_admin_mfa WHERE user_id=%s""", (user_id,)
            ))

    def grant_admin(self, user_id: UUID, *, granted_by: UUID | None) -> None:
        with self._provisioner() as conn:
            conn.execute(
                """INSERT INTO identity.ai_provider_admin_grants(user_id,granted_by)
                   VALUES (%s,%s) ON CONFLICT(user_id) DO UPDATE SET granted_at=pg_catalog.now(),
                     granted_by=EXCLUDED.granted_by,revoked_at=NULL""", (user_id, granted_by)
            )
            conn.execute(
                "INSERT INTO identity.ai_provider_admin_mfa(user_id) VALUES (%s) ON CONFLICT DO NOTHING",
                (user_id,),
            )
            conn.execute(
                """UPDATE identity.ai_provider_admin_mfa SET secret_ref=NULL,pending_secret_ref=NULL,
                     enabled_at=NULL,last_totp_counter=-1,recovery_hashes=ARRAY[]::BYTEA[],
                     version=version+1,updated_at=pg_catalog.now() WHERE user_id=%s""", (user_id,)
            )
            self._audit(conn, granted_by, "admin_granted", "admin", str(user_id), "success", {})

    def revoke_admin(self, user_id: UUID, *, actor_id: UUID) -> None:
        with self._provisioner() as conn:
            cur = conn.execute(
                "UPDATE identity.ai_provider_admin_grants SET revoked_at=pg_catalog.now() WHERE user_id=%s AND revoked_at IS NULL RETURNING user_id",
                (user_id,),
            )
            if _row(cur) is None:
                raise RegistryNotFound("Active provider administrator was not found")
            conn.execute(
                "UPDATE identity.ai_provider_admin_step_up SET revoked_at=pg_catalog.now() WHERE user_id=%s AND revoked_at IS NULL",
                (user_id,),
            )
            conn.execute(
                """UPDATE identity.ai_provider_admin_mfa SET secret_ref=NULL,pending_secret_ref=NULL,
                     enabled_at=NULL,last_totp_counter=-1,recovery_hashes=ARRAY[]::BYTEA[],
                     version=version+1,updated_at=pg_catalog.now() WHERE user_id=%s""", (user_id,)
            )
            self._audit(conn, actor_id, "admin_revoked", "admin", str(user_id), "success", {})

    def begin_mfa_enrollment(self, user_id: UUID, *, pending_secret_ref: str) -> None:
        self._validate_secret_ref(pending_secret_ref)
        with self._connect() as conn:
            if conn.execute(
                "SELECT 1 FROM identity.ai_provider_admin_grants WHERE user_id=%s AND revoked_at IS NULL",
                (user_id,),
            ).fetchone() is None:
                raise RegistryRejected("Provider administrator grant is required")
            conn.execute(
                """UPDATE identity.ai_provider_admin_mfa SET pending_secret_ref=%s,version=version+1,
                     updated_at=pg_catalog.now() WHERE user_id=%s""", (pending_secret_ref, user_id)
            )

    def activate_mfa(self, user_id: UUID, *, recovery_hashes: Sequence[bytes]) -> None:
        if not 8 <= len(recovery_hashes) <= 20 or any(len(value) != 32 for value in recovery_hashes):
            raise RegistryRejected("Recovery verifier set is invalid")
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE identity.ai_provider_admin_mfa SET secret_ref=pending_secret_ref,
                       pending_secret_ref=NULL,enabled_at=pg_catalog.now(),last_totp_counter=-1,
                       recovery_hashes=%s,version=version+1,updated_at=pg_catalog.now()
                   WHERE user_id=%s AND pending_secret_ref IS NOT NULL RETURNING user_id""",
                (list(recovery_hashes), user_id),
            )
            if _row(cur) is None:
                raise RegistryRejected("MFA enrollment is not pending")

    def consume_recovery_hash(self, user_id: UUID, verifier_hash: bytes) -> bool:
        if len(verifier_hash) != 32:
            return False
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE identity.ai_provider_admin_mfa SET recovery_hashes=array_remove(recovery_hashes,%s),
                       version=version+1,updated_at=pg_catalog.now()
                   WHERE user_id=%s AND enabled_at IS NOT NULL AND %s=ANY(recovery_hashes)
                   RETURNING user_id""", (verifier_hash, user_id, verifier_hash)
            )
            return _row(cur) is not None

    def replace_recovery_hashes(self, user_id: UUID, *, recovery_hashes: Sequence[bytes]) -> None:
        if not 8 <= len(recovery_hashes) <= 20 or any(len(value) != 32 for value in recovery_hashes):
            raise RegistryRejected("Recovery verifier set is invalid")
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE identity.ai_provider_admin_mfa SET recovery_hashes=%s,version=version+1,
                       updated_at=pg_catalog.now() WHERE user_id=%s AND enabled_at IS NOT NULL
                   RETURNING user_id""", (list(recovery_hashes), user_id)
            )
            if _row(cur) is None:
                raise RegistryRejected("Enabled provider-admin MFA is required")

    def consume_recovery_and_step_up(
        self, user_id: UUID, session_id: UUID, verifier_hash: bytes, *,
        verified_at: datetime, expires_at: datetime,
    ) -> bool:
        """Atomically consume one recovery verifier and step up this session.

        Recovery use does not advance or bypass the TOTP replay counter. The
        recovery credential itself is single-use and can grant only a bounded
        session-bound step-up after the operator has separately approved the
        recovery policy.
        """
        now = datetime.now(UTC)
        if len(verifier_hash) != 32 or verified_at.tzinfo is None or expires_at.tzinfo is None:
            return False
        if verified_at > now or not now < expires_at <= now + timedelta(minutes=15):
            return False
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE identity.ai_provider_admin_mfa m
                   SET recovery_hashes=array_remove(m.recovery_hashes,%s),version=version+1,
                       updated_at=pg_catalog.now()
                   FROM identity.ai_provider_admin_grants g
                   WHERE m.user_id=%s AND m.user_id=g.user_id AND m.enabled_at IS NOT NULL
                     AND g.revoked_at IS NULL AND %s=ANY(m.recovery_hashes)
                   RETURNING m.user_id""", (verifier_hash, user_id, verifier_hash)
            )
            if _row(cur) is None:
                return False
            conn.execute(
                """INSERT INTO identity.ai_provider_admin_step_up(user_id,session_id,verified_at,expires_at)
                   VALUES (%s,%s,%s,%s) ON CONFLICT(user_id,session_id) DO UPDATE SET
                     verified_at=EXCLUDED.verified_at,expires_at=EXCLUDED.expires_at,revoked_at=NULL""",
                (user_id, session_id, verified_at, expires_at),
            )
            self._audit(conn, user_id, "admin_recovery_step_up", "session", str(session_id), "success", {})
            return True

    def record_step_up(self, user_id: UUID, session_id: UUID, *, totp_counter: int,
                       verified_at: datetime, expires_at: datetime) -> None:
        now = datetime.now(UTC)
        if type(totp_counter) is not int or verified_at.tzinfo is None or expires_at.tzinfo is None:
            raise RegistryRejected("Invalid step-up proof")
        if not now < expires_at <= now + timedelta(minutes=15) or verified_at > now:
            raise RegistryRejected("Step-up expiry is outside the allowed window")
        with self._connect() as conn:
            cur = conn.execute(
                """UPDATE identity.ai_provider_admin_mfa SET last_totp_counter=%s,updated_at=pg_catalog.now()
                   WHERE user_id=%s AND enabled_at IS NOT NULL AND last_totp_counter < %s
                     AND EXISTS (SELECT 1 FROM identity.ai_provider_admin_grants g
                                 WHERE g.user_id=%s AND g.revoked_at IS NULL)
                   RETURNING user_id""", (totp_counter, user_id, totp_counter, user_id)
            )
            if _row(cur) is None:
                raise RegistryRejected("TOTP step-up is invalid, replayed, or unauthorized")
            conn.execute(
                """INSERT INTO identity.ai_provider_admin_step_up(user_id,session_id,verified_at,expires_at)
                   VALUES (%s,%s,%s,%s) ON CONFLICT(user_id,session_id) DO UPDATE SET
                     verified_at=EXCLUDED.verified_at,expires_at=EXCLUDED.expires_at,revoked_at=NULL""",
                (user_id, session_id, verified_at, expires_at),
            )

    def has_fresh_step_up(self, user_id: UUID, session_id: UUID, *, now: datetime | None = None) -> bool:
        point = now or datetime.now(UTC)
        with self._connect() as conn:
            return conn.execute(
                """SELECT 1 FROM identity.ai_provider_admin_step_up s
                   JOIN identity.ai_provider_admin_grants g USING(user_id)
                   JOIN identity.ai_provider_admin_mfa m USING(user_id)
                   WHERE s.user_id=%s AND s.session_id=%s AND s.revoked_at IS NULL
                     AND s.expires_at>%s AND g.revoked_at IS NULL AND m.enabled_at IS NOT NULL""",
                (user_id, session_id, point),
            ).fetchone() is not None

    def step_up_expires_at(self, user_id: UUID, session_id: UUID, *,
                           now: datetime | None = None) -> datetime | None:
        point = now or datetime.now(UTC)
        with self._connect() as conn:
            cur = conn.execute(
                """SELECT s.expires_at FROM identity.ai_provider_admin_step_up s
                   JOIN identity.ai_provider_admin_grants g USING(user_id)
                   JOIN identity.ai_provider_admin_mfa m USING(user_id)
                   WHERE s.user_id=%s AND s.session_id=%s AND s.revoked_at IS NULL
                     AND s.expires_at>%s AND g.revoked_at IS NULL AND m.enabled_at IS NOT NULL""",
                (user_id, session_id, point),
            )
            item = cur.fetchone()
            return item["expires_at"] if item else None

    def revoke_step_up(self, user_id: UUID, session_id: UUID) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE identity.ai_provider_admin_step_up SET revoked_at=pg_catalog.now() WHERE user_id=%s AND session_id=%s AND revoked_at IS NULL",
                (user_id, session_id),
            )

    def _audit(self, conn: Any, actor_id: UUID | None, action: str, target_type: str,
               target_id: str | None, outcome: str, metadata: Mapping[str, Any]) -> None:
        # Metadata is caller-selected safe state only; never pass user prompts
        # or provider responses/secrets here.
        allowed_keys = {"version", "enabled", "archived", "profile_id", "revision_no",
                        "secret_configured", "validation_id", "revision_id", "generation",
                        "count", "fallback_enabled"}
        if any(key not in allowed_keys for key in metadata):
            raise RegistryRejected("Audit metadata contains an unsupported field")
        if any(not (value is None or type(value) in {bool, int, str}) for value in metadata.values()):
            raise RegistryRejected("Audit metadata contains an unsupported value")
        conn.execute(
            """INSERT INTO ai_provider.audit_events(actor_id,action,target_type,target_id,outcome,metadata)
               VALUES (%s,%s,%s,%s,%s,%s::jsonb)""",
            (actor_id, action, target_type, target_id, outcome,
             json.dumps(dict(metadata), ensure_ascii=False)),
        )

    def _provisioner(self):
        if self._connect_provisioner is None:
            raise RegistryRejected("Private administrator provisioning connection is not configured")
        return self._connect_provisioner()

    @staticmethod
    def _validate_secret_ref(value: str) -> None:
        if not 8 <= len(value) <= 512 or any(ord(ch) < 33 for ch in value):
            raise RegistryRejected("Invalid opaque vault reference")

    @classmethod
    def _ensure_no_secret_fields(cls, value: Any) -> None:
        forbidden_parts = {"secret", "secret_ref", "token", "access_token", "password", "key",
                           "api_key", "authorization", "credential", "credentials"}
        if isinstance(value, Mapping):
            for key, child in value.items():
                parts = set(key.lower().replace("-", "_").split("_")) if isinstance(key, str) else set()
                if not isinstance(key, str) or parts & forbidden_parts:
                    raise RegistryRejected("Provider configuration must not contain secret fields")
                cls._ensure_no_secret_fields(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                cls._ensure_no_secret_fields(child)

    @staticmethod
    def _validation_details(value: Mapping[str, Any]) -> dict[str, Any]:
        allowed = {"status_code", "latency_ms", "error_code", "available_model_count",
                   "tested_model_id", "capability", "model_available", "test_kind",
                   "models_catalog_reachable", "model_selected", "capability_verified",
                   "actual_inference_passed"}
        if any(key not in allowed for key in value):
            raise RegistryRejected("Validation details contain an unsupported field")
        result = dict(value)
        for key in ("status_code", "latency_ms", "available_model_count"):
            item = result.get(key)
            if item is not None and (type(item) is not int or item < 0):
                raise RegistryRejected("Validation details contain an invalid number")
        if result.get("status_code") is not None and result["status_code"] > 599:
            raise RegistryRejected("Validation details contain an invalid status")
        if result.get("latency_ms") is not None and result["latency_ms"] > 120_000:
            raise RegistryRejected("Validation details contain an invalid latency")
        if result.get("available_model_count") is not None and result["available_model_count"] > 1000:
            raise RegistryRejected("Validation details contain an invalid model count")
        for key in ("error_code", "capability", "test_kind"):
            item = result.get(key)
            if item is not None and (not isinstance(item, str) or not 1 <= len(item) <= 80
                                     or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for ch in item)):
                raise RegistryRejected("Validation details contain an invalid code")
        if result.get("test_kind") is not None and result["test_kind"] not in {"discovery", "inference"}:
            raise RegistryRejected("Validation details contain an invalid test kind")
        model_id = result.get("tested_model_id")
        if model_id is not None and (not isinstance(model_id, str) or not 1 <= len(model_id) <= 160
                                     or any(ord(ch) < 32 for ch in model_id)):
            raise RegistryRejected("Validation details contain an invalid model identifier")
        available = result.get("model_available")
        if available is not None and type(available) is not bool:
            raise RegistryRejected("Validation details contain an invalid availability flag")
        for key in ("models_catalog_reachable", "model_selected", "capability_verified", "actual_inference_passed"):
            item = result.get(key)
            if item is not None and type(item) is not bool:
                raise RegistryRejected("Validation details contain an invalid test result flag")
        if result.get("actual_inference_passed") is True and (
            result.get("test_kind") != "inference"
            or result.get("capability_verified") is not True
            or result.get("model_selected") is not True
        ):
            raise RegistryRejected("Inference success requires a verified selected model and capability")
        return result
