from __future__ import annotations

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.modules.catalog.repository import sign_catalogue_cursor, verify_catalogue_cursor


def test_cursor_is_signed_stable_and_bound_to_search_filters():
    settings = Settings(
        _env_file=None,
        database_password="test-only",
        database_user="ai_tourism_app",
        auth_rate_limit_secret=SecretStr("x" * 32),
    )
    filters = {"q": "Shiraz", "province": None, "destination_type": None, "bbox": None}
    token = sign_catalogue_cursor(settings, last_id=41, filters=filters)
    assert verify_catalogue_cursor(settings, token, filters) == 41
    with pytest.raises(ValueError):
        verify_catalogue_cursor(settings, token, {**filters, "q": "Mashhad"})
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(ValueError):
        verify_catalogue_cursor(settings, tampered, filters)
