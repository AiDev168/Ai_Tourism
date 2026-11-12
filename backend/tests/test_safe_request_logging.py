import json
import logging

from app.core.logging import JsonFormatter


def test_pilot_timing_logs_only_allowlisted_diagnostics():
    record = logging.LogRecord("ai_tourism", logging.INFO, __file__, 1, "request.completed", (), None)
    record.request_id = "test-request-id"
    record.result = "200"
    record.route = "/api/v1/admin/ai-providers/{profile_id}"
    record.connection_open_ms = 8.5
    record.password = "must-not-appear"
    record.query = "private traveler request"

    payload = json.loads(JsonFormatter().format(record))

    assert payload["request_id"] == "test-request-id"
    assert payload["route"] == "/api/v1/admin/ai-providers/{profile_id}"
    assert payload["connection_open_ms"] == 8.5
    assert "password" not in payload
    assert "query" not in payload
    assert "must-not-appear" not in json.dumps(payload)
