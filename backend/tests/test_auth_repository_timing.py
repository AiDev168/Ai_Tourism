from pydantic import SecretStr
import psycopg
import pytest

from app.core.config import Settings
from app.modules.identity import auth_repository
from app.modules.identity.auth_repository import AuthRepository


def _settings() -> Settings:
    return Settings(_env_file=None, database_password=SecretStr("test-only-database-password"))


class _Connection:
    def __init__(self):
        self.entered = False
        self.exited = False

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *_args):
        self.exited = True


def test_connection_open_timing_contains_only_safe_measurements(monkeypatch, caplog):
    caplog.set_level("INFO", logger="ai_tourism.auth.database")
    connection = _Connection()
    kwargs_seen = {}

    def connect(**kwargs):
        kwargs_seen.update(kwargs)
        return connection

    monkeypatch.setattr(auth_repository.psycopg, "connect", connect)
    repository = AuthRepository(_settings())

    with repository.connection() as actual:
        assert actual is connection
        assert connection.entered
        assert not connection.exited

    assert connection.exited
    assert kwargs_seen["application_name"] == "ai-tourism-auth"
    record = next(
        item for item in caplog.records
        if item.msg == "auth.database.connection.timing"
    )
    assert record.outcome == "opened"
    assert record.connection_open_ms >= 0
    assert "127.0.0.1" not in caplog.text
    assert "test-only-database-password" not in caplog.text
    assert "ai_tourism_dev" not in caplog.text
    assert "ai_tourism_app" not in caplog.text
    assert "password" not in record.__dict__
    assert "query" not in record.__dict__
    assert "user_id" not in record.__dict__


def test_connection_failure_logs_duration_without_driver_error_details(monkeypatch, caplog):
    caplog.set_level("INFO", logger="ai_tourism.auth.database")
    def connect(**_kwargs):
        raise psycopg.OperationalError("private host and password must not leak")

    monkeypatch.setattr(auth_repository.psycopg, "connect", connect)
    repository = AuthRepository(_settings())

    with pytest.raises(psycopg.OperationalError):
        with repository.connection():
            pytest.fail("connection body must not execute")

    record = next(
        item for item in caplog.records
        if item.msg == "auth.database.connection.timing"
    )
    assert record.outcome == "failed"
    assert record.connection_open_ms >= 0
    assert "private host" not in caplog.text
    assert "password must not leak" not in caplog.text
