from argparse import Namespace
from uuid import UUID

import pytest

from backend.scripts import provision_platform_capability as provisioning


TARGET = UUID("00000000-0000-0000-0000-000000000011")
OPERATOR = UUID("00000000-0000-0000-0000-000000000022")
MARKER = "b" * 64


class Cursor:
    def __init__(self, *, active=False, admin_exists=True, operator_admin=True):
        self.active = active
        self.admin_exists = admin_exists
        self.operator_admin = operator_admin
        self.row = None
        self.queries = []

    def execute(self, query, params=()):
        sql = " ".join(query.split())
        self.queries.append((sql, params))
        if "current_database()" in sql:
            self.row = {
                "database_name": provisioning.DATABASE_NAME,
                "version_num": 170004,
                "server_port": 5432,
                "database_role": "ai_tourism_owner",
                "marker_count": 1,
                "marker_value": MARKER,
                "m24": __import__("hashlib").sha256(provisioning.MIGRATION_024.read_bytes()).hexdigest(),
                "m25": __import__("hashlib").sha256(provisioning.MIGRATION_025.read_bytes()).hexdigest(),
                "migration_count": 24,
                "latest_migration": "0025_owner_control_center",
            }
        elif "capability='admin_overview_read'" in sql and "user_id=%s" in sql:
            self.row = {"active": self.operator_admin}
        elif "capability='admin_overview_read'" in sql:
            self.row = {"active": self.admin_exists}
        elif "EXISTS(SELECT 1 FROM identity.users" in sql:
            self.row = {"ok": True}
        elif "EXISTS(SELECT 1 FROM partner.platform_grants WHERE user_id=%s" in sql or "EXISTS(SELECT 1 FROM identity.catalogue_review_grants" in sql:
            self.row = {"active": self.active}
        else:
            self.row = None
        return self

    def fetchone(self): return self.row
    def __enter__(self): return self
    def __exit__(self, *_): return False


class Connection:
    def __init__(self, cursor):
        self.cursor_value = cursor
        self.committed = False

    def cursor(self):
        return self.cursor_value

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        self.committed = exc_type is None
        return False


def args(*, capability="organization_review", action="grant", apply=False, target=TARGET, operator=OPERATOR):
    return Namespace(target_user=target, operator_user=operator, capability=capability,
                     action=action, reason="Approved by controlled operator process.", apply=apply)


def test_self_grant_is_rejected_before_database_access(monkeypatch):
    monkeypatch.setattr(provisioning.psycopg, "connect", lambda *a, **k: pytest.fail("unexpected DB access"))
    with pytest.raises(provisioning.ProvisioningError, match="self_provisioning_forbidden"):
        provisioning.run(args(target=OPERATOR), environ={})


def test_first_control_center_admin_is_explicitly_bootstrapped_read_only_by_default(monkeypatch):
    cursor = Cursor(admin_exists=False, operator_admin=False)
    connection = Connection(cursor)
    monkeypatch.setattr(provisioning.psycopg, "connect", lambda *a, **k: connection)
    result = provisioning.run(args(capability="admin_overview_read"), environ={
        "RAHGARD_OPERATOR_DATABASE_URL": "postgresql://private-dsn-not-printed",
        "RAHGARD_PILOT_DATABASE_MARKER": MARKER,
    })
    assert result.startswith("DRY_RUN")
    assert not any("INSERT INTO" in sql or "UPDATE " in sql for sql, _ in cursor.queries)
    assert connection.committed  # read-only context exits successfully


def test_additional_grants_require_existing_admin_operator(monkeypatch):
    cursor = Cursor(admin_exists=True, operator_admin=False)
    monkeypatch.setattr(provisioning.psycopg, "connect", lambda *a, **k: Connection(cursor))
    with pytest.raises(provisioning.ProvisioningError, match="operator_admin_capability_required"):
        provisioning.run(args(), environ={
            "RAHGARD_OPERATOR_DATABASE_URL": "postgresql://private-dsn-not-printed",
            "RAHGARD_PILOT_DATABASE_MARKER": MARKER,
        })


def test_apply_requires_separate_explicit_operator_confirmation(monkeypatch):
    cursor = Cursor(admin_exists=True, operator_admin=True)
    monkeypatch.setattr(provisioning.psycopg, "connect", lambda *a, **k: Connection(cursor))
    with pytest.raises(provisioning.ProvisioningError, match="explicit_operator_confirmation_missing"):
        provisioning.run(args(apply=True), environ={
            "RAHGARD_OPERATOR_DATABASE_URL": "postgresql://private-dsn-not-printed",
            "RAHGARD_PILOT_DATABASE_MARKER": MARKER,
        })
    assert not any("INSERT INTO" in sql or "UPDATE " in sql for sql, _ in cursor.queries)


def test_approved_grant_records_actor_and_audit_event(monkeypatch):
    cursor = Cursor(active=False, admin_exists=True, operator_admin=True)
    connection = Connection(cursor)
    monkeypatch.setattr(provisioning.psycopg, "connect", lambda *a, **k: connection)
    result = provisioning.run(args(apply=True, capability="candidate_review"), environ={
        "RAHGARD_OPERATOR_DATABASE_URL": "postgresql://private-dsn-not-printed",
        "RAHGARD_PILOT_DATABASE_MARKER": MARKER,
        "RAHGARD_OPERATOR_GRANT_CONFIRM": "APPLY_APPROVED_PLATFORM_GRANT",
    })
    statements = "\n".join(sql for sql, _ in cursor.queries)
    assert result.startswith("APPLIED action=granted")
    assert "INSERT INTO identity.catalogue_review_grants" in statements
    assert "INSERT INTO partner.platform_grant_events" in statements
    assert connection.committed


def test_database_marker_ledger_and_role_mismatches_fail_closed(monkeypatch):
    cursor = Cursor()
    connection = Connection(cursor)
    monkeypatch.setattr(provisioning.psycopg, "connect", lambda *a, **k: connection)
    with pytest.raises(provisioning.ProvisioningError, match="pilot_marker_mismatch"):
        provisioning.run(args(), environ={
            "RAHGARD_OPERATOR_DATABASE_URL": "postgresql://private-dsn-not-printed",
            "RAHGARD_PILOT_DATABASE_MARKER": "c" * 64,
        })
