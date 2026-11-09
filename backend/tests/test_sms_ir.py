from __future__ import annotations

import json
import math
from pathlib import Path

import httpx
import pytest

from scripts import sms_ir_sandbox_smoke
from app.core.config import Settings
from app.modules.identity.sms import (
    FakeSmsAdapter,
    SmsDeliveryError,
    SmsFailureCategory,
    SmsIrSandboxAdapter,
    SmsMessage,
    sms_ir_mobile_number,
)


def message(recipient: str = "+989120000000") -> SmsMessage:
    return SmsMessage(
        recipient=recipient,
        verification_code="123456",
        purpose="login",
        locale="fa-IR",
        body="localized body is only for the fake adapter",
    )


def response(status: int = 1, *, content_type: str = "text/plain", body=None) -> httpx.Response:
    payload = {"status": status, "data": {"messageId": "sandbox-message-42"}} if body is None else body
    return httpx.Response(
        200,
        headers={"content-type": content_type},
        content=json.dumps(payload).encode(),
        request=httpx.Request("POST", SmsIrSandboxAdapter.endpoint),
    )


def test_sms_ir_serializes_exact_sandbox_verify_request_and_returns_safe_receipt():
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return response()

    adapter = SmsIrSandboxAdapter("sandbox-test-key", transport=httpx.MockTransport(handler))
    receipt = adapter.send(message(), timeout_seconds=2.5)

    request = captured[0]
    assert request.method == "POST"
    assert str(request.url) == "https://api.sms.ir/v1/send/verify"
    assert request.headers["X-API-KEY"] == "sandbox-test-key"
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["Accept"] == "text/plain"
    assert request.read().decode() == (
        '{"mobile":"9120000000","templateId":123456,'
        '"parameters":[{"name":"Code","value":"123456"}]}'
    )
    assert receipt.provider_message_id == "sandbox-message-42"


@pytest.mark.parametrize(
    ("canonical", "expected"),
    [("+989120000000", "9120000000"), ("+989991234567", "9991234567")],
)
def test_sms_ir_mobile_mapping(canonical: str, expected: str):
    assert sms_ir_mobile_number(canonical) == expected


@pytest.mark.parametrize(
    "value",
    ["09120000000", "00989120000000", "+9891200000", "+9891200000000", "+12025550123", "+98912١٢٣٤٥٦٧"],
)
def test_sms_ir_mobile_mapping_rejects_noncanonical_or_unsupported_values(value: str):
    with pytest.raises(SmsDeliveryError) as error:
        sms_ir_mobile_number(value)
    assert error.value.category is SmsFailureCategory.INVALID_CONFIGURATION


@pytest.mark.parametrize(
    ("status", "category"),
    [
        (400, SmsFailureCategory.REQUEST_REJECTED),
        (401, SmsFailureCategory.UNAUTHORIZED),
        (403, SmsFailureCategory.UNAUTHORIZED),
        (429, SmsFailureCategory.RATE_LIMITED),
        (500, SmsFailureCategory.PROVIDER_UNAVAILABLE),
        (302, SmsFailureCategory.PROVIDER_UNAVAILABLE),
    ],
)
def test_sms_ir_maps_http_failures_without_response_details(status, category):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status,
            text="secret response containing 123456 and +989120000000",
            request=request,
        )

    adapter = SmsIrSandboxAdapter("secret-api-key", transport=httpx.MockTransport(handler))
    with pytest.raises(SmsDeliveryError) as error:
        adapter.send(message(), timeout_seconds=1.0)
    assert error.value.category is category
    assert "secret-api-key" not in str(error.value)
    assert "123456" not in str(error.value)
    assert "+989120000000" not in str(error.value)


@pytest.mark.parametrize(
    ("content_type", "body", "category"),
    [
        ("text/html", {"status": 1}, SmsFailureCategory.MALFORMED_RESPONSE),
        ("text/plain", "not-json", SmsFailureCategory.MALFORMED_RESPONSE),
        ("application/json", [], SmsFailureCategory.MALFORMED_RESPONSE),
        ("application/json", {"status": "1"}, SmsFailureCategory.MALFORMED_RESPONSE),
        ("application/json", {"status": 9, "message": "do not leak"}, SmsFailureCategory.PROVIDER_REJECTED),
    ],
)
def test_sms_ir_rejects_malformed_and_provider_level_failures(content_type, body, category):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": content_type},
            content=body.encode() if isinstance(body, str) else json.dumps(body).encode(),
            request=request,
        )

    adapter = SmsIrSandboxAdapter("sandbox-test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(SmsDeliveryError) as error:
        adapter.send(message(), timeout_seconds=1.0)
    assert error.value.category is category
    assert "do not leak" not in str(error.value)


def test_sms_ir_timeout_is_bounded_and_never_retried():
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("timeout for OTP 123456", request=request)

    adapter = SmsIrSandboxAdapter("sandbox-test-key", transport=httpx.MockTransport(handler))
    with pytest.raises(SmsDeliveryError) as error:
        adapter.send(message(), timeout_seconds=0.25)
    assert error.value.category is SmsFailureCategory.TIMEOUT
    assert calls == 1
    assert "123456" not in str(error.value)


def test_sms_ir_timeout_is_capped_at_ten_seconds():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return response()

    adapter = SmsIrSandboxAdapter("sandbox-test-key", transport=httpx.MockTransport(handler))
    adapter.send(message(), timeout_seconds=35)
    assert requests[0].extensions["timeout"] == {
        "connect": 10.0, "read": 10.0, "write": 10.0, "pool": 10.0,
    }


@pytest.mark.parametrize("timeout", [0, -1, math.inf, math.nan, True, "2", None])
def test_sms_ir_rejects_invalid_timeout_without_sending(timeout):
    requests = []
    adapter = SmsIrSandboxAdapter(
        "sandbox-test-key",
        transport=httpx.MockTransport(lambda request: requests.append(request) or response()),
    )
    with pytest.raises(SmsDeliveryError) as error:
        adapter.send(message(), timeout_seconds=timeout)
    assert error.value.category is SmsFailureCategory.INVALID_CONFIGURATION
    assert requests == []


def test_sms_ir_does_not_follow_redirects_or_forward_the_api_key():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            307,
            headers={"location": "https://attacker.example/collect"},
            request=request,
        )

    adapter = SmsIrSandboxAdapter("secret-api-key", transport=httpx.MockTransport(handler))
    with pytest.raises(SmsDeliveryError):
        adapter.send(message(), timeout_seconds=1.0)
    assert len(requests) == 1
    assert str(requests[0].url) == SmsIrSandboxAdapter.endpoint


def test_sms_ir_rejects_invalid_configuration_and_message_purpose():
    with pytest.raises(SmsDeliveryError) as blank_key:
        SmsIrSandboxAdapter("  ")
    assert blank_key.value.category is SmsFailureCategory.INVALID_CONFIGURATION

    adapter = SmsIrSandboxAdapter("sandbox-test-key", transport=httpx.MockTransport(lambda req: response()))
    invalid = SmsMessage(
        recipient="+989120000000", verification_code="123456", purpose="other", locale="fa-IR", body=""
    )
    with pytest.raises(SmsDeliveryError) as bad_purpose:
        adapter.send(invalid, timeout_seconds=1.0)
    assert bad_purpose.value.category is SmsFailureCategory.INVALID_CONFIGURATION


def test_settings_keep_fake_without_a_key_and_reject_old_generic_key_or_sandbox_without_one():
    fake = Settings(_env_file=None, database_password="test-only", app_env="test", auth_sms_adapter="fake")
    assert fake.sms_ir_sandbox_api_key is None

    configured = Settings(
        _env_file=None,
        database_password="test-only",
        app_env="test",
        auth_sms_adapter="sms_ir_sandbox",
        sms_ir_sandbox_api_key="sandbox-test-key",
    )
    assert configured.sms_ir_sandbox_api_key.get_secret_value() == "sandbox-test-key"

    with pytest.raises(ValueError, match="SMS_IR_SANDBOX_API_KEY is required"):
        Settings(
            _env_file=None,
            database_password="test-only",
            app_env="development",
            auth_sms_adapter="sms_ir_sandbox",
            sms_ir_api_key="legacy-generic-key",
        )


def test_settings_reject_sandbox_adapter_in_production():
    with pytest.raises(ValueError, match="restricted to development and tests"):
        Settings(
            _env_file=None,
            database_password="test-only",
            app_env="production",
            auth_sms_adapter="sms_ir_sandbox",
            sms_ir_sandbox_api_key="sandbox-test-key",
        )


def test_env_example_uses_disabled_mode_and_only_dummy_sandbox_placeholder():
    env_sample = Path(__file__).resolve().parents[2] / ".env.example"
    content = env_sample.read_text(encoding="utf-8")
    assert "AUTH_SMS_ADAPTER=disabled" in content
    assert "SMS_IR_SANDBOX_API_KEY=replace-with-sms-ir-sandbox-api-key" in content
    assert "SMS_IR_API_KEY=" not in content
    assert "SMS_IR_PRODUCTION_API_KEY" not in content


def test_smoke_without_process_opt_in_skips_without_loading_settings_or_sending(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("SMS_IR_SANDBOX_SMOKE", raising=False)
    (tmp_path / ".env").write_text(
        "SMS_IR_SANDBOX_SMOKE=1\nAPP_ENV=test\nAUTH_SMS_ADAPTER=sms_ir_sandbox\n"
        "SMS_IR_SANDBOX_API_KEY=dummy-sandbox-test-key\n",
        encoding="utf-8",
    )
    def settings_factory(**kwargs):
        pytest.fail("Settings must not load without opt-in")

    def adapter_factory(*_args):
        pytest.fail("adapter must not be selected without opt-in")
    assert sms_ir_sandbox_smoke.main(
        root=tmp_path,
        settings_factory=settings_factory,
        adapter_factory=adapter_factory,
    ) == 0
    assert "SKIP" in capsys.readouterr().out


def test_smoke_missing_sandbox_key_skips_before_adapter_selection(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SMS_IR_SANDBOX_SMOKE", "1")
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("AUTH_SMS_ADAPTER", raising=False)
    monkeypatch.delenv("SMS_IR_SANDBOX_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "APP_ENV=development\nAUTH_SMS_ADAPTER=sms_ir_sandbox\n", encoding="utf-8"
    )
    def adapter_factory(*_args):
        pytest.fail("adapter must not be selected without a key")

    assert sms_ir_sandbox_smoke.main(root=tmp_path, adapter_factory=adapter_factory) == 0
    assert "no request was made" in capsys.readouterr().out


@pytest.mark.parametrize("app_env", ["production", "staging"])
def test_smoke_refuses_production_and_non_development_environments(monkeypatch, tmp_path, app_env, capsys):
    monkeypatch.setenv("SMS_IR_SANDBOX_SMOKE", "1")
    for key in ("APP_ENV", "AUTH_SMS_ADAPTER", "SMS_IR_SANDBOX_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        f"APP_ENV={app_env}\nAUTH_SMS_ADAPTER=sms_ir_sandbox\n"
        "SMS_IR_SANDBOX_API_KEY=dummy-sandbox-test-key\n",
        encoding="utf-8",
    )
    def adapter_factory(*_args):
        pytest.fail("refused configuration must not select adapter")

    assert sms_ir_sandbox_smoke.main(root=tmp_path, adapter_factory=adapter_factory) == 2
    assert "REFUSED" in capsys.readouterr().out


def test_smoke_loads_root_env_and_selects_only_sandbox_adapter(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("SMS_IR_SANDBOX_SMOKE", "1")
    for key in ("APP_ENV", "AUTH_SMS_ADAPTER", "SMS_IR_SANDBOX_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    (tmp_path / ".env").write_text(
        "APP_ENV=test\nAUTH_SMS_ADAPTER=sms_ir_sandbox\n"
        "SMS_IR_SANDBOX_API_KEY=dummy-sandbox-test-key\n",
        encoding="utf-8",
    )
    away = tmp_path / "working-directory"
    away.mkdir()
    monkeypatch.chdir(away)
    assert sms_ir_sandbox_smoke.repository_root() == Path(sms_ir_sandbox_smoke.__file__).resolve().parents[2]

    calls = []

    class FakeHttpAdapter:
        def send(self, outgoing, *, timeout_seconds):
            calls.append((outgoing, timeout_seconds))
            return type("Receipt", (), {"provider_message_id": "sandbox-test-id"})()

        def close(self):
            calls.append("closed")

    assert sms_ir_sandbox_smoke.main(
        root=tmp_path,
        adapter_factory=lambda key: (calls.append(("key", key)) or FakeHttpAdapter()),
    ) == 0
    output = capsys.readouterr().out
    assert "PASS" in output
    assert "dummy-sandbox-test-key" not in output
    assert "+989120000000" not in output
    assert "123456" not in output
    assert calls[0] == ("key", "dummy-sandbox-test-key")
    assert calls[-1] == "closed"
    with pytest.raises(ValueError, match="restricted to development and tests"):
        Settings(
            _env_file=None,
            database_password="test-only",
            app_env="production",
            auth_sms_adapter="sms_ir_sandbox",
            sms_ir_api_key="never-a-real-key",
        )


def test_fake_sms_still_captures_structured_message_without_provider_key():
    fake = FakeSmsAdapter()
    value = message()
    fake.send(value, timeout_seconds=1.0)
    assert fake.take_messages() == [value]
