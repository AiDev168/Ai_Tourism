"""Read-only access to the approved, spatial production destination view."""

import logging
from collections.abc import Mapping

import psycopg
from psycopg.rows import dict_row

from app.core.config import Settings
from app.modules.catalog.alias_manifest import (
    AliasManifestUnavailable,
    ReviewedAliasSet,
    load_reviewed_aliases,
)
from app.modules.catalog.schemas import ApprovedDestinationAlias, ProductionDestinationItem

logger = logging.getLogger("ai_tourism.catalog")

MAX_CATALOGUE_ITEMS = 1_000
MAX_ALIASES_PER_ITEM = 32
MAX_NAME_LENGTH = 240
MAX_ALIAS_LENGTH = 200

_PRODUCTION_CATALOGUE_SQL = """
SELECT d.destination_id::text AS destination_id,
       d.destination_key,
       d.canonical_name,
       d.destination_type,
       d.province_name,
       d.city_name,
       EXISTS (
           SELECT 1
           FROM knowledge.production_destination_sources AS s
           WHERE s.destination_id = d.destination_id
       ) AS has_verified_provenance
FROM knowledge.production_destinations AS d
ORDER BY d.destination_id ASC
LIMIT %s
"""


class CatalogueUnavailableError(Exception):
    """Database or bounded-response failure; deliberately carries no details."""


def _bounded_text(value: object, maximum: int, *, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise CatalogueUnavailableError
    return value


def _to_item(
    row: Mapping[str, object], reviewed_aliases: ReviewedAliasSet | None
) -> ProductionDestinationItem:
    aliases = reviewed_aliases.aliases if reviewed_aliases is not None else []
    if len(aliases) > MAX_ALIASES_PER_ITEM:
        raise CatalogueUnavailableError
    normalized_aliases: list[ApprovedDestinationAlias] = []
    for alias in aliases:
        value = _bounded_text(alias["value"], MAX_ALIAS_LENGTH)
        assert value is not None
        normalized_aliases.append(ApprovedDestinationAlias.model_validate(alias))

    if row.get("has_verified_provenance") is not True:
        raise CatalogueUnavailableError

    city_name = _bounded_text(row.get("city_name"), MAX_NAME_LENGTH, required=False)
    localized_names = reviewed_aliases.localized_names if reviewed_aliases else {
        "fa-IR": None, "en-US": None, "ar": None,
    }
    return ProductionDestinationItem(
        destination_id=str(row["destination_id"]),
        destination_key=_bounded_text(row.get("destination_key"), MAX_NAME_LENGTH),
        canonical_name=_bounded_text(row.get("canonical_name"), MAX_NAME_LENGTH),
        localized_names=localized_names,
        aliases=normalized_aliases,
        destination_type=_bounded_text(row.get("destination_type"), 64),
        province_name=_bounded_text(row.get("province_name"), MAX_NAME_LENGTH),
        city_name=city_name,
    )


def list_production_destinations(settings: Settings) -> list[ProductionDestinationItem]:
    """Read the whole small catalogue or fail closed; never return a truncated page.

    The application role has SELECT only on the two production views. A single
    bounded query plus MAX+1 detection keeps response completeness explicit.
    """
    query_timeout_ms = settings.database_connect_timeout_seconds * 1_000
    try:
        reviewed_aliases = load_reviewed_aliases()
    except AliasManifestUnavailable:
        logger.warning("catalogue.alias_manifest_unavailable")
        raise CatalogueUnavailableError from None

    try:
        with psycopg.connect(
            host=settings.database_host,
            port=settings.database_port,
            dbname=settings.database_name,
            user=settings.database_user,
            password=settings.database_password.get_secret_value(),
            connect_timeout=settings.database_connect_timeout_seconds,
            application_name="ai-tourism-catalogue-read",
            options=f"-c statement_timeout={query_timeout_ms}",
            row_factory=dict_row,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute(_PRODUCTION_CATALOGUE_SQL, (MAX_CATALOGUE_ITEMS + 1,))
                rows = cursor.fetchall()
    except Exception:
        logger.warning("catalogue.read_unavailable")
        raise CatalogueUnavailableError from None

    if len(rows) > MAX_CATALOGUE_ITEMS:
        logger.warning("catalogue.read_limit_exceeded")
        raise CatalogueUnavailableError

    try:
        return [
            _to_item(row, reviewed_aliases.get(str(row["destination_key"])))
            for row in rows
        ]
    except (AliasManifestUnavailable, KeyError, TypeError, ValueError):
        logger.warning("catalogue.read_invalid_projection")
        raise CatalogueUnavailableError from None
