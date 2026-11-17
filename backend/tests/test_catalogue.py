from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from unittest.mock import MagicMock

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import app
from app.modules.catalog.alias_manifest import (
    AliasManifest,
    AliasManifestUnavailable,
    _build_projection,
)
from app.modules.catalog.repository import (
    MAX_CATALOGUE_ITEMS,
    CatalogueUnavailableError,
    _PRODUCTION_CATALOGUE_SQL,
    _to_item,
    list_production_destinations,
)
from app.modules.catalog.schemas import ProductionDestinationItem

client = TestClient(app)


def settings() -> Settings:
    return Settings(_env_file=None, database_password="test-only", database_user="ai_tourism_app")


def alias_entry(**overrides: str) -> dict[str, str]:
    entry = {
        "destination_key": "shiraz-city",
        "locale": "fa-IR",
        "canonical_display_name": "شیراز",
        "alias": "شیراز",
        "alias_type": "canonical_display_name",
        "source_reference": "owner-reviewed-source:shiraz-city/fa-IR",
        "editorial_status": "approved",
        "review_notes": "Reviewed against the cited source.",
    }
    return {**entry, **overrides}


def test_alias_manifest_projects_only_explicitly_approved_locale_entries():
    manifest = AliasManifest.model_validate({
        "manifest_version": 1,
        "entries": [
            alias_entry(),
            alias_entry(locale="en-US", canonical_display_name="Shiraz", alias="Shiraz", alias_type="canonical_display_name"),
            alias_entry(locale="ar", canonical_display_name="شيراز", alias="شيراز", alias_type="canonical_display_name"),
            alias_entry(locale="en-US", canonical_display_name="Shiraz", alias="Shiraz City", alias_type="spelling_variant"),
            alias_entry(destination_key="unreviewed", editorial_status="in_review", alias="Unreviewed name"),
            alias_entry(destination_key="proposed", editorial_status="proposed", alias="Proposed name"),
        ],
    })
    projected = _build_projection(manifest)
    assert projected["shiraz-city"].localized_names == {
        "fa-IR": "شیراز", "en-US": "Shiraz", "ar": "شيراز",
    }
    assert {alias["value"] for alias in projected["shiraz-city"].aliases} == {
        "شیراز", "Shiraz", "شيراز", "Shiraz City",
    }
    assert "unreviewed" not in projected
    assert "proposed" not in projected


def test_alias_manifest_rejects_same_identity_normalized_duplicates_and_bad_canonical_rows():
    duplicate = AliasManifest.model_validate({"manifest_version": 1, "entries": [
        alias_entry(), alias_entry(alias="ش‌یراز،"),
    ]})
    with pytest.raises(AliasManifestUnavailable):
        _build_projection(duplicate)

    bad_canonical = AliasManifest.model_validate({"manifest_version": 1, "entries": [
        alias_entry(alias="Shiraz", alias_type="canonical_display_name"),
    ]})
    with pytest.raises(AliasManifestUnavailable):
        _build_projection(bad_canonical)


def test_alias_manifest_keeps_cross_identity_homonyms_for_explicit_ambiguity():
    manifest = AliasManifest.model_validate({"manifest_version": 1, "entries": [
        alias_entry(alias="Maragheh", alias_type="alternate_script_name", review_notes="Reviewed homonym; must remain ambiguous."),
        alias_entry(destination_key="maragheh-city", alias="Maragheh", alias_type="alternate_script_name", review_notes="Reviewed homonym; must remain ambiguous."),
    ]})
    projected = _build_projection(manifest)
    assert projected["shiraz-city"].aliases[0]["value"] == "Maragheh"
    assert projected["maragheh-city"].aliases[0]["value"] == "Maragheh"


def test_visitiran_review_package_stays_proposed_and_out_of_runtime_projection():
    package_path = Path(__file__).parents[2] / "engineering/database-prep/alias-review/visitiran-alias-proposals-v1.json"
    manifest = AliasManifest.model_validate(json.loads(package_path.read_text(encoding="utf-8")))
    assert len(manifest.entries) == 12
    assert {entry.editorial_status for entry in manifest.entries} == {"proposed"}
    assert all(entry.source_reference.startswith("https://visitiran.ir/") for entry in manifest.entries)
    assert _build_projection(manifest) == {}


def test_repository_sql_uses_only_approved_production_views_and_complete_bound():
    assert "FROM knowledge.production_destinations AS d" in _PRODUCTION_CATALOGUE_SQL
    assert "knowledge.production_destination_sources AS s" in _PRODUCTION_CATALOGUE_SQL
    for raw_table in ("knowledge.destinations AS", "knowledge.knowledge_sources", "operations."):
        assert raw_table not in _PRODUCTION_CATALOGUE_SQL
    assert "ORDER BY d.destination_id ASC" in _PRODUCTION_CATALOGUE_SQL
    assert "d.latitude" in _PRODUCTION_CATALOGUE_SQL
    assert "d.longitude" in _PRODUCTION_CATALOGUE_SQL
    assert "d.coordinate_role" in _PRODUCTION_CATALOGUE_SQL
    assert "LIMIT %s" in _PRODUCTION_CATALOGUE_SQL
    assert MAX_CATALOGUE_ITEMS == 1_000


def test_repository_rejects_ineligible_provenance_projection():
    row: Mapping[str, object] = {
        "destination_id": "12", "destination_key": "example", "canonical_name": "Example",
        "destination_type": "city", "province_name": "Province", "city_name": "City",
        "has_verified_provenance": False,
    }
    with pytest.raises(CatalogueUnavailableError):
        _to_item(row, None)


@pytest.mark.parametrize(
    ("role", "latitude", "longitude"),
    [
        ("property_reference", 29.93444, 52.89028),
        ("representative_point", 29.6254028, 52.5583194),
        ("visitor_entrance", 29.61, 52.5425),
    ],
)
def test_repository_preserves_approved_coordinate_role_without_relabeling(role, latitude, longitude):
    row = {
        "destination_id": "12",
        "destination_key": "geo-example",
        "canonical_name": "Example",
        "destination_type": "heritage_site",
        "province_name": "Fars",
        "city_name": None,
        "latitude": latitude,
        "longitude": longitude,
        "coordinate_role": role,
        "has_verified_provenance": True,
    }

    item = _to_item(row, None)

    assert item.latitude == latitude
    assert item.longitude == longitude
    assert item.coordinate_role == role


def test_repository_preserves_null_coordinates_and_rejects_malformed_coordinate_pairs():
    row = {
        "destination_id": "12",
        "destination_key": "geo-example",
        "canonical_name": "Example",
        "destination_type": "heritage_site",
        "province_name": "Fars",
        "city_name": None,
        "latitude": None,
        "longitude": None,
        "coordinate_role": "unknown",
        "has_verified_provenance": True,
    }
    item = _to_item(row, None)
    assert item.latitude is None
    assert item.longitude is None
    assert item.coordinate_role == "unknown"

    with pytest.raises(ValueError, match="both be present or both be null"):
        ProductionDestinationItem.model_validate(
            {
                **item.model_dump(),
                "latitude": 29.0,
                "longitude": None,
                "coordinate_role": "representative_point",
            }
        )


def test_repository_maps_a_verified_production_projection_and_fails_on_overflow(monkeypatch):
    monkeypatch.setattr("app.modules.catalog.repository.load_reviewed_aliases", lambda: {})
    row = {
        "destination_id": "21", "destination_key": "eligible-example", "canonical_name": "Example",
        "destination_type": "city", "province_name": "Province", "city_name": "Example",
        "has_verified_provenance": True,
    }
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = [row]
    monkeypatch.setattr(psycopg, "connect", lambda **_kwargs: connection)
    result = list_production_destinations(settings())
    assert [item.destination_key for item in result] == ["eligible-example"]
    assert cursor.execute.call_args_list[1].args[0] == _PRODUCTION_CATALOGUE_SQL
    assert cursor.execute.call_args_list[1].args[1] == (MAX_CATALOGUE_ITEMS + 1,)

    cursor.fetchall.return_value = [row] * (MAX_CATALOGUE_ITEMS + 1)
    with pytest.raises(CatalogueUnavailableError):
        list_production_destinations(settings())


def test_repository_sanitizes_unexpected_connection_failures(monkeypatch):
    monkeypatch.setattr("app.modules.catalog.repository.load_reviewed_aliases", lambda: {})

    def broken_connect(**_kwargs):
        raise RuntimeError("host=private-db password=private-secret")

    monkeypatch.setattr(psycopg, "connect", broken_connect)
    with pytest.raises(CatalogueUnavailableError) as error:
        list_production_destinations(settings())
    assert str(error.value) == ""


def test_endpoint_returns_successful_empty_catalogue(monkeypatch):
    monkeypatch.setattr("app.api.catalogue.list_production_destinations", lambda _settings: [])
    response = client.get("/api/v1/catalog/destinations")
    assert response.status_code == 200
    assert response.json() == {"status": "available", "complete": True, "count": 0, "items": []}
    assert response.headers["cache-control"] == "no-store"


def test_endpoint_returns_complete_production_projection(monkeypatch):
    item = ProductionDestinationItem(
        destination_id="17", destination_key="shiraz-city", canonical_name="شیراز",
        localized_names={"fa-IR": "شیراز", "en-US": "Shiraz", "ar": "شيراز"},
        aliases=[], destination_type="city", province_name="فارس", city_name="شیراز",
        latitude=29.61, longitude=52.5425, coordinate_role="representative_point",
    )
    monkeypatch.setattr("app.api.catalogue.list_production_destinations", lambda _settings: [item])
    response = client.get("/api/v1/catalog/destinations")
    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["items"][0]["destination_key"] == "shiraz-city"
    assert response.json()["items"][0]["latitude"] == 29.61
    assert response.json()["items"][0]["longitude"] == 52.5425
    assert response.json()["items"][0]["coordinate_role"] == "representative_point"
    assert "status" not in response.json()["items"][0]
    assert "has_verified_provenance" not in response.json()["items"][0]


def test_endpoint_maps_database_and_size_failures_to_stable_sanitized_503(monkeypatch):
    def unavailable(_settings):
        raise CatalogueUnavailableError("password=should-not-leak connection details")

    monkeypatch.setattr("app.api.catalogue.list_production_destinations", unavailable)
    response = client.get("/api/v1/catalog/destinations")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "error": {"code": "catalogue_unavailable"}}
    for secret in ("password", "connection", "details", "database_host", "SELECT"):
        assert secret.lower() not in response.text.lower()


def test_endpoint_has_no_query_or_request_body_contract():
    operation = app.openapi()["paths"]["/api/v1/catalog/destinations"]["get"]
    assert not operation.get("security")
    assert "requestBody" not in operation
    assert operation["responses"]["200"]
    assert operation["responses"]["503"]
