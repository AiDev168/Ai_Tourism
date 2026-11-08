"""Opt-in SMS.ir Sandbox Verify smoke test. Never contacts Production."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings  # noqa: E402
from app.modules.identity.sms import SmsDeliveryError, SmsIrSandboxAdapter, SmsMessage  # noqa: E402


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(
    *,
    root: Path | None = None,
    settings_factory: Callable[..., Settings] = Settings,
    adapter_factory: Callable[[str], Any] = SmsIrSandboxAdapter,
) -> int:
    # Keep the opt-in outside .env: merely configuring a key must never send a request.
    if os.environ.get("SMS_IR_SANDBOX_SMOKE") != "1":
        print("SKIP: set SMS_IR_SANDBOX_SMOKE=1 in the process environment to opt in.")
        return 0

    env_file = (root or repository_root()) / ".env"
    file_values = dotenv_values(env_file)
    effective = {key: value for key, value in file_values.items() if value is not None}
    effective.update(os.environ)

    app_env = str(effective.get("APP_ENV", "development")).lower()
    adapter_name = effective.get("AUTH_SMS_ADAPTER", "disabled")
    if app_env == "production":
        print("REFUSED: Sandbox smoke tests cannot run in production.")
        return 2
    if app_env not in {"development", "test"}:
        print("REFUSED: APP_ENV must be development or test.")
        return 2
    if adapter_name != "sms_ir_sandbox":
        print("REFUSED: AUTH_SMS_ADAPTER must be sms_ir_sandbox.")
        return 2
    if not str(effective.get("SMS_IR_SANDBOX_API_KEY", "")).strip():
        print("SKIP: SMS_IR_SANDBOX_API_KEY is not configured; no request was made.")
        return 0

    adapter = None
    try:
        # Settings loads the explicitly resolved repository .env. The dummy DB
        # password is only for validation; this script never opens a DB connection.
        settings = settings_factory(
            _env_file=env_file,
            database_password="sandbox-smoke-unused-database-password",
        )
        if settings.app_env.lower() not in {"development", "test"}:
            print("REFUSED: APP_ENV must be development or test.")
            return 2
        if settings.auth_sms_adapter != "sms_ir_sandbox":
            print("REFUSED: AUTH_SMS_ADAPTER must be sms_ir_sandbox.")
            return 2
        if settings.sms_ir_sandbox_api_key is None:
            print("SKIP: SMS_IR_SANDBOX_API_KEY is not configured; no request was made.")
            return 0

        adapter = adapter_factory(settings.sms_ir_sandbox_api_key.get_secret_value())
        receipt = adapter.send(
            SmsMessage(
                recipient="+989120000000",
                verification_code="123456",
                purpose="login",
                locale="en-US",
                body="Sandbox smoke test message.",
            ),
            timeout_seconds=5.0,
        )
    except SmsDeliveryError as error:
        print(f"FAIL: {error.category.value}")
        return 1
    except Exception:
        print("FAIL: configuration or transport unavailable")
        return 1
    finally:
        if adapter is not None:
            adapter.close()

    suffix = f"; message_id={receipt.provider_message_id}" if receipt.provider_message_id else ""
    print(f"PASS: SMS.ir Sandbox accepted the Verify request{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
