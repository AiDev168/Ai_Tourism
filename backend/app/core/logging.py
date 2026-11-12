import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "event": record.getMessage(),
        }
        # Fixed, non-sensitive diagnostics only. Never serialize arbitrary
        # LogRecord extras, request bodies, URLs, credentials, or SQL.
        for key in ("request_id", "result", "latency_ms", "route", "outcome",
                    "connection_open_ms", "credential_read_ms", "verification_and_limiter_ms",
                    "pbkdf2_ms", "limiter_check_ms", "limiter_update_ms", "session_issue_ms",
                    "total_ms"):
            if hasattr(record, key):
                data[key] = getattr(record, key)
        return json.dumps(data, ensure_ascii=False)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
