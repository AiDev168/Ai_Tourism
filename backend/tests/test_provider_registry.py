"""Focused no-network tests for provider-registry state transitions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from app.modules.provider_admin.registry import (
    ProviderRegistry,
    RegistryConflict,
    RegistryRejected,
)


class _Cursor:
    def __init__(self, row=None):
        self._row = row

    def fetchone(self):
        return self._row


class _ActivationConnection:
    def __init__(self, revision_id, generation=4):
        self.revision_id = revision_id
        self.generation = generation
        self.queries = []
        self.calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, params=None):
        normalized = " ".join(query.split())
        self.queries.append((normalized, params))
        if "FROM ai_provider.active_routes WHERE capability=%s FOR UPDATE" in normalized:
            return _Cursor({"revision_id": None, "generation": self.generation})
        if "FROM ai_provider.revisions r JOIN ai_provider.profiles" in normalized:
            return _Cursor({"revision_id": self.revision_id, "profile_id": uuid4(),
                            "config": {"capabilities": {"chat": {"model": "real-model-id"}}},
                            "secret_ref": "dpapi:opaque-ref-123", "enabled": True,
                            "archived_at": None, "latest_validation": "valid"})
        if "UPDATE ai_provider.active_routes SET" in normalized:
            self.generation += 1
            return _Cursor({"generation": self.generation})
        if "INSERT INTO ai_provider.audit_events" in normalized:
            return _Cursor(None)
        raise AssertionError(f"Unexpected registry query: {normalized}")


def test_activation_is_cas_guarded_validated_and_keeps_secret_reference_opaque():
    revision_id, actor_id = uuid4(), uuid4()
    connection = _ActivationConnection(revision_id)
    registry = ProviderRegistry(lambda: connection)

    result = registry.activate("chat", revision_id, expected_generation=4, actor_id=actor_id)

    assert result.revision_id == revision_id
    assert result.generation == 5
    assert result.secret_ref == "dpapi:opaque-ref-123"
    assert result.config["capabilities"]["chat"]["model"] == "real-model-id"
    assert any("FOR UPDATE" in query for query, _ in connection.queries)
    assert any("generation=%s" in query for query, _ in connection.queries)
    validation_query = next(query for query, _ in connection.queries if "revision_validations" in query)
    assert "details->>'capability'=%s" in validation_query
    assert "details->>'test_kind'='inference'" in validation_query
    assert "dpapi:opaque-ref-123" not in " ".join(query for query, _ in connection.queries)


def test_fallback_snapshot_is_exact_enabled_validated_and_not_activated():
    revision_id = uuid4()

    class SnapshotConnection:
        def __init__(self):
            self.queries = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params=None):
            normalized = " ".join(query.split())
            self.queries.append(normalized)
            if "FROM ai_provider.revisions r JOIN ai_provider.profiles" in normalized:
                return _Cursor({"revision_id": revision_id,
                                "config": {"capabilities": {"chat": {"model": "m1"}}},
                                "secret_ref": "opaque-vault-ref", "enabled": True,
                                "archived_at": None, "latest_validation": "valid"})
            if "FROM ai_provider.active_routes WHERE capability=%s" in normalized:
                return _Cursor({"generation": 9})
            raise AssertionError(normalized)

    conn = SnapshotConnection()
    snapshot = ProviderRegistry(lambda: conn).validated_snapshot("chat", revision_id)
    assert snapshot.revision_id == revision_id
    assert snapshot.generation == 9
    assert snapshot.config["capabilities"]["chat"]["model"] == "m1"
    assert not any("UPDATE ai_provider.active_routes" in query for query in conn.queries)


@pytest.mark.parametrize("state", [
    {"enabled": False, "archived_at": None, "latest_validation": "valid",
     "config": {"capabilities": {"chat": {}}}},
    {"enabled": True, "archived_at": "archived", "latest_validation": "valid",
     "config": {"capabilities": {"chat": {}}}},
    {"enabled": True, "archived_at": None, "latest_validation": "invalid",
     "config": {"capabilities": {"chat": {}}}},
    {"enabled": True, "archived_at": None, "latest_validation": "valid",
     "config": {"capabilities": {"vision": {}}}},
])
def test_fallback_snapshot_rejects_ineligible_revision(state):
    class IneligibleConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, *_args):
            return _Cursor({"revision_id": uuid4(), "secret_ref": None, **state})

    with pytest.raises(RegistryRejected):
        ProviderRegistry(IneligibleConnection).validated_snapshot("chat", uuid4())


def test_unsupported_capability_and_stale_expected_generation_fail_closed():
    registry = ProviderRegistry(lambda: pytest.fail("invalid capability must fail before DB"))
    with pytest.raises(RegistryRejected):
        registry.activate("all", uuid4(), expected_generation=0, actor_id=uuid4())

    class StaleConnection(_ActivationConnection):
        def execute(self, query, params=None):
            if "FROM ai_provider.active_routes WHERE capability=%s FOR UPDATE" in " ".join(query.split()):
                return _Cursor({"revision_id": None, "generation": 5})
            return super().execute(query, params)

    connection = StaleConnection(uuid4())
    with pytest.raises(RegistryConflict):
        ProviderRegistry(lambda: connection).deactivate("chat", expected_generation=4, actor_id=uuid4())


@pytest.mark.parametrize("capability", ["vision", "embedding", "reranking"])
def test_independent_capability_route_requires_its_own_validated_inference(capability):
    revision_id = uuid4()

    class CapabilityConnection:
        def __init__(self):
            self.generation = 2
            self.queries = []

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params=None):
            normalized = " ".join(query.split())
            self.queries.append((normalized, params))
            if "FROM ai_provider.active_routes WHERE capability=%s FOR UPDATE" in normalized:
                return _Cursor({"revision_id": None, "generation": self.generation})
            if "FROM ai_provider.revisions r JOIN ai_provider.profiles" in normalized:
                return _Cursor({
                    "revision_id": revision_id,
                    "profile_id": uuid4(),
                    "config": {"capabilities": {capability: {"model_id": f"{capability}-model"}}},
                    "secret_ref": "opaque-vault-reference",
                    "enabled": True,
                    "archived_at": None,
                    "latest_validation": "valid",
                })
            if "UPDATE ai_provider.active_routes SET" in normalized:
                self.generation += 1
                return _Cursor({"generation": self.generation})
            if "INSERT INTO ai_provider.audit_events" in normalized:
                return _Cursor(None)
            raise AssertionError(normalized)

    connection = CapabilityConnection()
    active = ProviderRegistry(lambda: connection).activate(
        capability, revision_id, expected_generation=2, actor_id=uuid4()
    )
    assert active.capability == capability
    assert active.revision_id == revision_id
    validation_query = next(query for query, _ in connection.queries if "revision_validations" in query)
    assert "details->>'capability'=%s" in validation_query
    assert "details->>'test_kind'='inference'" in validation_query


@pytest.mark.parametrize("args", [
    ("chat", True, []),
    ("chat", False, [uuid4()]),
    ("unknown", False, []),
])
def test_fallback_requires_explicit_valid_order_or_disabled_empty(args):
    capability, enabled, order = args
    registry = ProviderRegistry(lambda: pytest.fail("invalid fallback input must fail before DB"))
    with pytest.raises(RegistryRejected):
        registry.set_fallback(capability, enabled, order, actor_id=uuid4())


def test_step_up_window_is_bounded_and_future_verification_rejected():
    registry = ProviderRegistry(lambda: pytest.fail("invalid step-up must fail before DB"))
    now = datetime.now(UTC)
    with pytest.raises(RegistryRejected, match="expiry"):
        registry.record_step_up(uuid4(), uuid4(), totp_counter=10, verified_at=now,
                                expires_at=now + timedelta(minutes=16))
    with pytest.raises(RegistryRejected, match="expiry"):
        registry.record_step_up(uuid4(), uuid4(), totp_counter=10, verified_at=now + timedelta(minutes=1),
                                expires_at=now + timedelta(minutes=2))


def test_secret_material_cannot_be_embedded_in_revision_config_or_validation_details():
    with pytest.raises(RegistryRejected, match="secret fields"):
        ProviderRegistry._ensure_no_secret_fields({"capabilities": {"chat": {}}, "api_key": "never-store"})
    with pytest.raises(RegistryRejected, match="unsupported field"):
        ProviderRegistry._validation_details({"error": "raw provider response"})
    assert ProviderRegistry._validation_details({"latency_ms": 25, "error_code": "timeout"}) == {
        "latency_ms": 25, "error_code": "timeout"
    }


def test_inference_validation_details_cannot_be_claimed_by_discovery_or_partial_result():
    with pytest.raises(RegistryRejected, match="Inference success"):
        ProviderRegistry._validation_details({
            "capability": "embedding", "test_kind": "discovery",
            "models_catalog_reachable": True, "model_selected": True,
            "capability_verified": False, "actual_inference_passed": True,
        })
    assert ProviderRegistry._validation_details({"capability": "chat", "test_kind": "inference"}) == {
        "capability": "chat", "test_kind": "inference"
    }


def test_valid_inference_record_cannot_be_written_without_all_success_flags():
    registry = ProviderRegistry(lambda: pytest.fail("invalid validation must fail before DB"))
    with pytest.raises(RegistryRejected, match="successful model capability test"):
        registry.record_validation(uuid4(), outcome="valid", actor_id=uuid4(), safe_details={
            "capability": "embedding", "test_kind": "inference",
            "models_catalog_reachable": True, "model_selected": True,
            "capability_verified": False, "actual_inference_passed": False,
        })


def test_migration_has_marker_guard_opaque_refs_and_disabled_fallback():
    migration = (Path(__file__).resolve().parents[2] / "engineering/pilot/sql/015_ai_provider_admin.sql").read_text(encoding="utf-8")
    normalized = migration.lower()
    assert "current_database() ~ '^rahgard_pilot_" in normalized
    assert "inet_server_port() <> 55433" in normalized
    assert "rahgard_pilot_migration_0014_sha256" in normalized
    assert "secret_ref text" in normalized
    assert "provider_key text" not in normalized
    assert "fallback_policy" in normalized
    assert "enabled boolean not null default false" in normalized
    assert "identity.web_sessions(session_id)" in normalized
    assert "bytea[] not null default array[]::bytea[]" in normalized

    runner = (Path(__file__).resolve().parents[2] / "engineering/pilot/local-persistent/Rahgard-LocalPilot.ps1").read_text(encoding="utf-8")
    assert "RAHGARD_PILOT_MIGRATION_0014_SHA256" in runner
    assert "RAHGARD_PILOT_MIGRATION_0015_SHA256" in runner
    assert "Invoke-LocalPilotGuardedTcpSql $wrapper" in runner
    assert "REVOKE CREATE ON DATABASE" in runner
    assert "ProvisionProviderAdmin" in runner and "RevokeProviderAdmin" in runner


def test_initial_profile_and_revision_share_one_transaction():
    profile_id, revision_id = uuid4(), uuid4()

    class AtomicConnection:
        def __init__(self):
            self.commands = []
            self.exit_error = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, _traceback):
            self.exit_error = exc
            return False

        def execute(self, query, params=None):
            normalized = " ".join(query.split())
            self.commands.append((normalized, params))
            if "INSERT INTO ai_provider.profiles" in normalized:
                return _Cursor({"profile_id": profile_id, "version": 1, "name": "Local",
                                "provider_kind": "lm_studio", "enabled": True,
                                "archived_at": None, "created_at": datetime.now(UTC)})
            if "INSERT INTO ai_provider.revisions" in normalized:
                return _Cursor({"revision_id": revision_id, "profile_id": profile_id,
                                "revision_no": 1, "config": {"capabilities": {"chat": {}}},
                                "created_at": datetime.now(UTC)})
            if "INSERT INTO ai_provider.audit_events" in normalized:
                return _Cursor(None)
            raise AssertionError(normalized)

    connection = AtomicConnection()
    profile, revision = ProviderRegistry(lambda: connection).create_profile_with_revision(
        "Local", "lm_studio", config={"capabilities": {"chat": {"model_id": "m1"}}},
        secret_ref=None, actor_id=uuid4(),
    )
    assert profile["profile_id"] == profile_id
    assert revision["revision_id"] == revision_id
    assert connection.exit_error is None
    assert sum("INSERT INTO ai_provider.profiles" in query for query, _ in connection.commands) == 1
    assert sum("INSERT INTO ai_provider.revisions" in query for query, _ in connection.commands) == 1


def test_initial_revision_failure_aborts_profile_transaction():
    class FailingConnection:
        def __init__(self):
            self.exit_error = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, _traceback):
            self.exit_error = exc
            return False

        def execute(self, query, _params=None):
            normalized = " ".join(query.split())
            if "INSERT INTO ai_provider.profiles" in normalized:
                return _Cursor({"profile_id": uuid4(), "version": 1})
            if "INSERT INTO ai_provider.revisions" in normalized:
                raise RuntimeError("revision insert failed")
            raise AssertionError(normalized)

    connection = FailingConnection()
    with pytest.raises(RuntimeError, match="revision insert failed"):
        ProviderRegistry(lambda: connection).create_profile_with_revision(
            "Local", "lm_studio", config={"capabilities": {"chat": {"model_id": "m1"}}},
            secret_ref=None, actor_id=uuid4(),
        )
    assert isinstance(connection.exit_error, RuntimeError)

@pytest.mark.parametrize("has_current_step_up", [True, False])
def test_step_up_expiry_reads_dict_row_by_column_name(has_current_step_up):
    """An active MFA step-up must not fail when psycopg returns a dict_row."""
    user_id, session_id = uuid4(), uuid4()
    expiry = datetime.now(UTC) + timedelta(minutes=3)
    row = {"expires_at": expiry} if has_current_step_up else None

    class DictRowConnection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, params):
            normalized = " ".join(query.split())
            assert "SELECT s.expires_at" in normalized
            assert "s.revoked_at IS NULL" in normalized
            assert "s.expires_at>%s" in normalized
            assert "g.revoked_at IS NULL" in normalized
            assert "m.enabled_at IS NOT NULL" in normalized
            assert params[:2] == (user_id, session_id)
            return _Cursor(row)

    actual = ProviderRegistry(DictRowConnection).step_up_expires_at(user_id, session_id)
    assert actual == (expiry if has_current_step_up else None)
