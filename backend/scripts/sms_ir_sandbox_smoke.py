"""Opt-in SMS.ir Sandbox Verify smoke test. Never contacts Production."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import Settings
from app.modules.identity.sms import SmsDeliveryError, SmsIrSandboxAdapter, SmsMessage


def main() -> int:
    if os.environ.get("SMS_IR_SANDBOX_SMOKE") != "1":
        print("SKIP: set SMS_IR_SANDBOX_SMOKE=1 to opt in to the Sandbox request.")
        return 0

    environment = os.environ.get("APP_ENV", "development").lower()
    adapter_name = os.environ.get("AUTH_SMS_ADAPTER", "disabled")
    api_key = os.environ.get("SMS_IR_API_KEY", "")
    if environment == "production":
        print("REFUSED: Sandbox smoke tests cannot run in production.")
        return 2
    if adapter_name != "sms_ir_sandbox":
        print("REFUSED: AUTH_SMS_ADAPTER must be sms_ir_sandbox.")
        return 2
    if not api_key:
        print("SKIP: SMS_IR_API_KEY is not configured; no Sandbox request was made.")
        return 0

    try:
        Settings(
            _env_file=None,
            database_password=os.environ.get("DATABASE_PASSWORD", "unused-local-smoke-value"),
            app_env=os.environ.get("APP_ENV", "development"),
            auth_sms_adapter=os.environ.get("AUTH_SMS_ADAPTER", "disabled"),
            sms_ir_api_key=api_key,
        )

        adapter = SmsIrSandboxAdapter(api_key)
        try:
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
        finally:
            adapter.close()
    except SmsDeliveryError as error:
        print(f"FAIL: {error.category.value}")
        return 1
    except Exception:
        print("FAIL: configuration or transport unavailable")
        return 1

    suffix = f"; message_id={receipt.provider_message_id}" if receipt.provider_message_id else ""
    print(f"PASS: SMS.ir Sandbox accepted the Verify request{suffix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
