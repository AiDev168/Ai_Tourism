"""Provider-neutral SMS port with fake and SMS.ir Sandbox adapters."""

import math
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from typing import Protocol

import httpx


class SmsFailureCategory(StrEnum):
    INVALID_CONFIGURATION = "invalid_configuration"
    REQUEST_REJECTED = "request_rejected"
    UNAUTHORIZED = "unauthorized"
    RATE_LIMITED = "rate_limited"
    PROVIDER_REJECTED = "provider_rejected"
    MALFORMED_RESPONSE = "malformed_response"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    TIMEOUT = "timeout"


class SmsDeliveryError(Exception):
    """Safe provider-neutral failure. Never carries provider response text or credentials."""

    def __init__(self, category: SmsFailureCategory = SmsFailureCategory.PROVIDER_UNAVAILABLE):
        self.category = category
        super().__init__("SMS delivery unavailable")


@dataclass(frozen=True, slots=True)
class SmsMessage:
    recipient: str
    verification_code: str
    purpose: str
    locale: str
    body: str


@dataclass(frozen=True, slots=True)
class SmsDeliveryReceipt:
    provider_message_id: str | None = None


class SmsPort(Protocol):
    def send(self, message: SmsMessage, *, timeout_seconds: float) -> SmsDeliveryReceipt: ...


def sms_ir_mobile_number(phone_e164: str) -> str:
    """Map canonical +98 Iranian mobiles to SMS.ir's national mobile format."""
    if (
        len(phone_e164) != 13
        or not phone_e164.startswith("+989")
        or not phone_e164[1:].isascii()
        or not phone_e164[1:].isdigit()
    ):
        raise SmsDeliveryError(SmsFailureCategory.INVALID_CONFIGURATION)
    return phone_e164[3:]


class DisabledSmsAdapter:
    def send(self, message: SmsMessage, *, timeout_seconds: float) -> SmsDeliveryReceipt:
        del message, timeout_seconds
        raise SmsDeliveryError()


class FakeSmsAdapter:
    """In-memory capture available to injected tests; never exposed over HTTP/logs."""

    def __init__(self) -> None:
        self._messages: list[SmsMessage] = []
        self._lock = Lock()

    def send(self, message: SmsMessage, *, timeout_seconds: float) -> SmsDeliveryReceipt:
        del timeout_seconds
        with self._lock:
            self._messages.append(message)
        return SmsDeliveryReceipt()

    def take_messages(self) -> list[SmsMessage]:
        with self._lock:
            messages, self._messages = self._messages, []
            return messages


class SmsIrSandboxAdapter:
    """SMS.ir Verify API adapter for an explicitly configured Sandbox key only."""

    endpoint = "https://api.sms.ir/v1/send/verify"
    sandbox_template_id = 123456
    max_timeout_seconds = 10.0

    def __init__(self, api_key: str, *, transport: httpx.BaseTransport | None = None) -> None:
        if not api_key or api_key != api_key.strip() or "\r" in api_key or "\n" in api_key:
            raise SmsDeliveryError(SmsFailureCategory.INVALID_CONFIGURATION)
        self._api_key = api_key
        self._client = httpx.Client(
            transport=transport,
            follow_redirects=False,
        )

    def close(self) -> None:
        self._client.close()

    def send(self, message: SmsMessage, *, timeout_seconds: float) -> SmsDeliveryReceipt:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise SmsDeliveryError(SmsFailureCategory.INVALID_CONFIGURATION)
        bounded_timeout = min(float(timeout_seconds), self.max_timeout_seconds)
        try:
            mobile = sms_ir_mobile_number(message.recipient)
        except SmsDeliveryError:
            raise
        if message.purpose != "login" or not message.verification_code.isascii() or not message.verification_code.isdigit():
            raise SmsDeliveryError(SmsFailureCategory.INVALID_CONFIGURATION)

        try:
            response = self._client.post(
                self.endpoint,
                headers={
                    "X-API-KEY": self._api_key,
                    "Content-Type": "application/json",
                    "Accept": "text/plain",
                },
                json={
                    "mobile": mobile,
                    "templateId": self.sandbox_template_id,
                    "parameters": [{"name": "Code", "value": message.verification_code}],
                },
                timeout=httpx.Timeout(bounded_timeout),
            )
        except httpx.TimeoutException:
            # A Verify POST timeout is ambiguous: never retry automatically.
            raise SmsDeliveryError(SmsFailureCategory.TIMEOUT) from None
        except httpx.HTTPError:
            raise SmsDeliveryError(SmsFailureCategory.PROVIDER_UNAVAILABLE) from None

        if response.status_code == 400:
            raise SmsDeliveryError(SmsFailureCategory.REQUEST_REJECTED)
        if response.status_code in {401, 403}:
            raise SmsDeliveryError(SmsFailureCategory.UNAUTHORIZED)
        if response.status_code == 429:
            raise SmsDeliveryError(SmsFailureCategory.RATE_LIMITED)
        if response.status_code >= 500 or not 200 <= response.status_code < 300:
            raise SmsDeliveryError(SmsFailureCategory.PROVIDER_UNAVAILABLE)

        content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if content_type not in {"text/plain", "application/json"}:
            raise SmsDeliveryError(SmsFailureCategory.MALFORMED_RESPONSE)
        try:
            payload = response.json()
        except ValueError:
            raise SmsDeliveryError(SmsFailureCategory.MALFORMED_RESPONSE) from None
        if not isinstance(payload, dict) or type(payload.get("status")) is not int:
            raise SmsDeliveryError(SmsFailureCategory.MALFORMED_RESPONSE)
        if payload["status"] != 1:
            raise SmsDeliveryError(SmsFailureCategory.PROVIDER_REJECTED)

        data = payload.get("data")
        message_id = None
        if isinstance(data, dict):
            candidate = data.get("messageId", data.get("message_id", data.get("id")))
            if isinstance(candidate, (str, int)) and not isinstance(candidate, bool):
                candidate_text = str(candidate)
                if candidate_text and len(candidate_text) <= 128:
                    message_id = candidate_text
        if message_id is None:
            candidate = payload.get("messageId", payload.get("message_id"))
            if isinstance(candidate, (str, int)) and not isinstance(candidate, bool):
                candidate_text = str(candidate)
                if candidate_text and len(candidate_text) <= 128:
                    message_id = candidate_text
        return SmsDeliveryReceipt(provider_message_id=message_id)
