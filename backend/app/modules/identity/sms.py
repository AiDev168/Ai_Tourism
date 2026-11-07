"""Provider-neutral SMS boundary; only a test/development fake is supplied."""

from dataclasses import dataclass
from threading import Lock
from typing import Protocol


class SmsDeliveryError(Exception):
    """Safe, provider-neutral delivery failure."""


@dataclass(frozen=True, slots=True)
class SmsMessage:
    recipient: str
    body: str


class SmsPort(Protocol):
    def send(self, message: SmsMessage, *, timeout_seconds: float) -> None: ...


class DisabledSmsAdapter:
    def send(self, message: SmsMessage, *, timeout_seconds: float) -> None:
        del message, timeout_seconds
        raise SmsDeliveryError("delivery unavailable")


class FakeSmsAdapter:
    """In-memory capture available to injected tests; never exposed over HTTP/logs."""

    def __init__(self) -> None:
        self._messages: list[SmsMessage] = []
        self._lock = Lock()

    def send(self, message: SmsMessage, *, timeout_seconds: float) -> None:
        del timeout_seconds
        with self._lock:
            self._messages.append(message)

    def take_messages(self) -> list[SmsMessage]:
        with self._lock:
            messages, self._messages = self._messages, []
            return messages
