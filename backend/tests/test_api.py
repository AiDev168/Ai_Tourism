from fastapi.testclient import TestClient
from pydantic import ValidationError
import logging
import json

from app.main import app
from app.core.config import Settings
from app.core.logging import JsonFormatter

client = TestClient(app)


def test_live_and_request_id():
    response = client.get("/health/live", headers={"X-Request-ID": "client-trace.123"})
    assert response.status_code == 200
    assert response.json() == {"status": "live"}
    assert response.headers["X-Request-ID"] == "client-trace.123"


def test_invalid_request_id_is_replaced():
    response = client.get("/health/live", headers={"X-Request-ID": "bad\nvalue"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "bad\nvalue"


def test_readiness_returns_safe_status(monkeypatch):
    monkeypatch.setattr("app.api.health.check_database", lambda _settings: False)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}
    assert "database" not in response.text.lower()


def test_settings_require_password_and_app_role():
    try:
        Settings(_env_file=None, database_user="database_owner", database_password="test")
    except ValidationError as error:
        assert "least-privilege" in str(error)
    else:
        raise AssertionError("non-app database role must be rejected")


def test_json_logging_uses_allowlisted_fields_only():
    record = logging.LogRecord("app", logging.INFO, "test.py", 1, "request.completed", (), None)
    record.request_id = "safe-id"
    record.result = "200"
    record.password = "do-not-log-this"
    record.raw_message = "private travel request"
    output = JsonFormatter().format(record)
    data = json.loads(output)
    assert data["request_id"] == "safe-id"
    assert "do-not-log-this" not in output
    assert "private travel request" not in output


def test_internal_error_envelope_and_logs_are_redacted(caplog):
    def private_failure():
        raise RuntimeError("password=sentinel-secret private-message")

    app.add_api_route("/_test/private-failure", private_failure, methods=["GET"], include_in_schema=False)
    response = client.get("/_test/private-failure")
    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error"}}
    assert "sentinel-secret" not in response.text
    assert "private-message" not in caplog.text
