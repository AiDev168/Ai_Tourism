from unittest.mock import MagicMock

import psycopg
import pytest

from app.core.config import Settings
from app.modules.catalog.repository import (
    MAX_CATALOGUE_ITEMS,
    MAX_TAGS_PER_DESTINATION,
    CatalogueUnavailableError,
    _PRODUCTION_DESTINATION_TAGS_SQL,
    list_production_destination_tags,
)


def _settings() -> Settings:
    return Settings(_env_file=None, database_password="test-only", database_user="ai_tourism_app")


def _mock_connection(monkeypatch, rows):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = rows
    monkeypatch.setattr(psycopg, "connect", lambda **_kwargs: connection)
    return connection, cursor


def test_empty_tag_request_returns_empty_without_opening_database(monkeypatch):
    def forbidden_connect(**_kwargs):
        raise AssertionError("empty tag requests must not connect to PostgreSQL")

    monkeypatch.setattr(psycopg, "connect", forbidden_connect)
    assert list_production_destination_tags(_settings(), []) == {}


@pytest.mark.parametrize(
    "destination_ids",
    [
        ["0"],
        ["-1"],
        ["1.5"],
        ["١٢"],
        ["9223372036854775808"],
        ["1" * 20],
        ["1"] * (MAX_CATALOGUE_ITEMS + 1),
    ],
)
def test_invalid_or_oversized_ids_fail_closed_without_database_access(monkeypatch, destination_ids):
    def forbidden_connect(**_kwargs):
        raise AssertionError("invalid tag requests must fail before connecting")

    monkeypatch.setattr(psycopg, "connect", forbidden_connect)
    with pytest.raises(CatalogueUnavailableError):
        list_production_destination_tags(_settings(), destination_ids)


def test_tags_query_is_scoped_to_approved_view_and_deduplicates_numeric_ids(monkeypatch):
    rows = [
        {"destination_id": 2, "tag": "historic-garden"},
        {"destination_id": 17, "tag": "historic-site"},
    ]
    connection, cursor = _mock_connection(monkeypatch, rows)

    result = list_production_destination_tags(_settings(), ["017", "2", 2])

    assert result == {"2": ("historic-garden",), "17": ("historic-site",)}
    assert cursor.execute.call_args_list[1].args[0] == _PRODUCTION_DESTINATION_TAGS_SQL
    assert cursor.execute.call_args_list[1].args[1] == (
        [2, 17], MAX_CATALOGUE_ITEMS * MAX_TAGS_PER_DESTINATION + 1,
    )
    assert "FROM knowledge.production_destination_tags" in _PRODUCTION_DESTINATION_TAGS_SQL
    assert "knowledge.destinations" not in _PRODUCTION_DESTINATION_TAGS_SQL
    assert "knowledge.destination_aliases" not in _PRODUCTION_DESTINATION_TAGS_SQL
    assert "ORDER BY destination_id ASC, tag ASC" in _PRODUCTION_DESTINATION_TAGS_SQL
    connection.cursor.assert_called_once()


def test_tags_max_plus_one_overflow_fails_closed(monkeypatch):
    rows = [
        {"destination_id": 17, "tag": f"tag-{index}"}
        for index in range(MAX_CATALOGUE_ITEMS * MAX_TAGS_PER_DESTINATION + 1)
    ]
    _mock_connection(monkeypatch, rows)

    with pytest.raises(CatalogueUnavailableError):
        list_production_destination_tags(_settings(), ["17"])
