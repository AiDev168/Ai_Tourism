from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from proxy_origin import expected_host, expected_origin, normalize_trusted_origin


def test_non_default_local_origin_is_canonicalized_only_for_its_exact_listener():
    assert expected_host(18443) == "localhost:18443"
    assert expected_origin(18443) == "https://localhost:18443"
    assert normalize_trusted_origin("localhost:18443", "https://localhost:18443", 18443) == "https://localhost"


def test_cross_port_origin_and_host_are_rejected():
    assert normalize_trusted_origin("localhost:18443", "https://localhost", 18443) is None
    assert normalize_trusted_origin("localhost:18443", "https://localhost:18444", 18443) is None
    assert normalize_trusted_origin("attacker.invalid:18443", "https://localhost:18443", 18443) is None


def test_default_https_origin_remains_unchanged():
    assert normalize_trusted_origin("localhost", "https://localhost", 443) == "https://localhost"


def test_missing_or_untrusted_origin_is_not_normalized():
    assert normalize_trusted_origin("localhost:18443", None, 18443) is None
    assert normalize_trusted_origin("localhost:18443", "null", 18443) is None
