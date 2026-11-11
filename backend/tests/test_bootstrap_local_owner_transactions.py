"""Regression tests for durable owner bootstrap, not just a success message."""

from __future__ import annotations

from contextlib import contextmanager
from hashlib import sha256
from uuid import uuid4

import pytest

from scripts import bootstrap_local_owner as bootstrap


class _Result:
    def __init__(self, row):
        self.row = row

    def fetchone(self):
        return self.row


def test_owner_identity_preflight_does_not_open_outer_implicit_transaction(monkeypatch):
    """Psycopg would otherwise treat subsequent transaction() as a SAVEPOINT."""
    marker = "a" * 48
    options = {}

    class GuardConnection:
        def __init__(self):
            self.closed = False

        def execute(self, sql):
            assert "current_database()" in sql
            return _Result({
                "name": "rahgard_pilot_local",
                "role": bootstrap.ROLE,
                "version": 170000,
                "marker_count": 1,
                "marker": marker,
                "m13": sha256(bootstrap.MIGRATION_013.read_bytes()).hexdigest(),
                "m14": sha256(bootstrap.MIGRATION_014.read_bytes()).hexdigest(),
            })

        def close(self):
            self.closed = True

    connection = GuardConnection()

    def connect(**kwargs):
        options.update(kwargs)
        return connection

    monkeypatch.setattr(bootstrap, "_target", lambda: (
        "127.0.0.1", 55439, "rahgard_pilot_local", marker, "test-only-password"
    ))
    monkeypatch.setattr(bootstrap.psycopg, "connect", connect)
    verified, actual_marker = bootstrap._connect()
    assert verified is connection
    assert actual_marker == marker
    assert options["autocommit"] is True
    assert options["user"] == bootstrap.ROLE
    assert options["dbname"] == "rahgard_pilot_local"
    verified.close()


class _OwnerConnection:
    """A tiny transaction double to check commit-before-readback ordering."""

    def __init__(self, *, missing_after_commit=False):
        self.owner_id = None
        self.committed_id = None
        self.missing_after_commit = missing_after_commit
        self.active = False
        self.closed = False

    @contextmanager
    def transaction(self):
        self.active = True
        try:
            yield self
        except Exception:
            self.owner_id = None
            raise
        else:
            self.committed_id = self.owner_id
        finally:
            self.active = False

    def execute(self, sql, parameters=None):
        if "SELECT count(*) AS n FROM identity.local_owner_credentials" in sql:
            return _Result({"n": 0})
        if "INSERT INTO identity.users" in sql:
            assert self.active
            self.owner_id = parameters[0]
            return _Result(None)
        if "INSERT INTO identity.local_owner_credentials" in sql:
            assert self.active
            assert parameters[0] == self.owner_id
            return _Result(None)
        if "SELECT owner_id FROM identity.local_owner_credentials WHERE login_name=" in sql:
            assert not self.active, "Readback must happen after COMMIT"
            assert parameters == ("owner",)
            if self.missing_after_commit:
                return _Result(None)
            return _Result({"owner_id": self.committed_id})
        raise AssertionError("Unexpected SQL in bootstrap regression test")

    def close(self):
        self.closed = True


def test_owner_create_checks_durable_record_after_transaction(monkeypatch):
    connection = _OwnerConnection()
    monkeypatch.setattr(bootstrap, "_connect", lambda: (connection, "a" * 48))
    monkeypatch.setattr(bootstrap, "_credential", lambda _password, _owner_id: (
        b"s" * 32, b"v" * 32, 600000
    ))
    bootstrap.create_owner("owner", "test-only-long-password")
    assert connection.committed_id is not None
    assert connection.committed_id == connection.owner_id
    assert connection.closed is True


def test_bootstrap_refuses_success_when_owner_readback_is_missing(monkeypatch):
    connection = _OwnerConnection(missing_after_commit=True)
    monkeypatch.setattr(bootstrap, "_connect", lambda: (connection, "a" * 48))
    monkeypatch.setattr(bootstrap, "_credential", lambda _password, _owner_id: (
        b"s" * 32, b"v" * 32, 600000
    ))
    with pytest.raises(bootstrap.BootstrapBlocked, match="durably committed"):
        bootstrap.create_owner("owner", "test-only-long-password")
    assert connection.closed is True
