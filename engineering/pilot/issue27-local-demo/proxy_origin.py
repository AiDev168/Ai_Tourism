"""Exact-origin handling for the loopback-only Issue 27 HTTPS proxy."""

from __future__ import annotations


def expected_host(web_port: int) -> str:
    return "localhost" if web_port == 443 else f"localhost:{web_port}"


def expected_origin(web_port: int) -> str:
    return "https://localhost" if web_port == 443 else f"https://localhost:{web_port}"


def normalize_trusted_origin(host: str, origin: str | None, web_port: int) -> str | None:
    """Map only the exact local listener origin to the backend's canonical origin.

    The backend's staging contract intentionally uses the canonical HTTPS origin
    without a port. A loopback demo on a non-default port must not cause the
    proxy to accept an arbitrary or cross-port browser Origin.
    """
    if host.strip().lower() != expected_host(web_port):
        return None
    if origin != expected_origin(web_port):
        return None
    return "https://localhost"
