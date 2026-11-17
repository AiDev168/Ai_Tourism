"""Keep the actual SQL owner-login path compatible with least-privilege grants.

These unit-level SQL boundary tests do not claim a successful Windows pilot
login. The operator must separately verify a genuine authenticated session.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from app.modules.identity.auth_repository import AuthRepository


class _Result:
    def __init__(self, row=None):
        self.row = row

    def fetchone(self):
        return self.row


class _LeastPrivilegeConnection:
    """Reject the real PostgreSQL privilege violation before reporting success."""

    def __init__(self, *, owner_id, salt, verifier, iterations, session_id):
        self.owner_id = owner_id
        self.salt = salt
        self.verifier = verifier
        self.iterations = iterations
        self.session_id = session_id
        self.statements = []
        self.in_transaction = False

    @contextmanager
    def transaction(self):
        self.in_transaction = True
        try:
            yield self
        finally:
            self.in_transaction = False

    def execute(self, query, params=()):
        sql = " ".join(query.split())
        self.statements.append((sql, params))
        if sql.startswith("SELECT pg_advisory_xact_lock"):
            assert self.in_transaction
            assert params == ("rahgard:local-owner-credential:" + str(self.owner_id),)
            return _Result()
        if sql.startswith("SELECT user_id FROM identity.users"):
            assert "FOR UPDATE" in sql  # owner row is legitimately writable by app
            return _Result({"user_id": self.owner_id})
        if sql.startswith("SELECT salt,verifier,iterations FROM identity.local_owner_credentials"):
            assert "FOR UPDATE" not in sql
            assert "FOR SHARE" not in sql
            assert "FOR KEY SHARE" not in sql
            return _Result({
                "salt": self.salt,
                "verifier": self.verifier,
                "iterations": self.iterations,
            })
        if sql.startswith("INSERT INTO identity.web_sessions"):
            assert self.in_transaction
            return _Result({"session_id": self.session_id})
        raise AssertionError("unexpected SQL on the owner session path")


def test_local_owner_session_works_with_select_only_credential_access():
    owner_id = uuid4()
    session_id = uuid4()
    salt = bytes(range(32))
    verifier = bytes(range(32, 64))
    now = datetime.now(UTC)
    connection = _LeastPrivilegeConnection(
        owner_id=owner_id, salt=salt, verifier=verifier,
        iterations=600000, session_id=session_id,
    )
    repo = AuthRepository.__new__(AuthRepository)
    @contextmanager
    def connection_factory():
        yield connection
    repo.connection = connection_factory
    result = repo.create_local_owner_session(
        user_id=owner_id, token_hash=b"t" * 32, csrf_hash=b"c" * 32,
        now=now, idle_expires_at=now + timedelta(minutes=30),
        absolute_expires_at=now + timedelta(hours=8),
        expected_salt=salt, expected_verifier=verifier,
        expected_iterations=600000,
    )
    assert result == {"user_id": owner_id, "session_id": session_id}
    assert len(connection.statements) == 4
    assert connection.statements[0][0].startswith("SELECT pg_advisory_xact_lock")
    assert connection.statements[2][0].startswith(
        "SELECT salt,verifier,iterations FROM identity.local_owner_credentials"
    )


def test_pilot_sql_does_not_grant_update_on_stored_verifiers():
    sql = (
        Path(__file__).resolve().parents[2]
        / "engineering" / "pilot" / "sql" / "014_local_owner_login.sql"
    ).read_text(encoding="utf-8")
    assert "GRANT SELECT ON identity.local_owner_credentials TO ai_tourism_app;" in sql
    assert "GRANT UPDATE ON identity.local_owner_credentials TO ai_tourism_app" not in sql


def test_password_reset_uses_identical_transaction_lock():
    bootstrap = (
        Path(__file__).resolve().parents[1]
        / "scripts" / "bootstrap_local_owner.py"
    ).read_text(encoding="utf-8")
    assert '("rahgard:local-owner-credential:" + str(row["owner_id"]),)' in bootstrap
    assert "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))" in bootstrap
