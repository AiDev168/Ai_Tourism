"""Read-only access to the approved, spatial production destination view."""

import logging
import re
from collections.abc import Mapping
from typing import Literal

import psycopg
from psycopg.rows import dict_row

from app.core.config import Settings
from app.modules.catalog.alias_manifest import (
    AliasManifestUnavailable,
    ReviewedAliasSet,
    load_reviewed_aliases,
)
from app.modules.catalog.schemas import (
    ApprovedDestinationAlias,
    ProductionDestinationItem,
    ProductionDestinationSource,
    ProductionDestinationTag,
    AvailableCulinaryCatalogue,
    CulinaryClaim,
    ProductionCulinaryItem,
)

logger = logging.getLogger("ai_tourism.catalog")

MAX_CATALOGUE_ITEMS = 1_000
MAX_ALIASES_PER_ITEM = 32
MAX_SOURCES_PER_DESTINATION = 32
MAX_TAGS_PER_DESTINATION = 64
MAX_NAME_LENGTH = 240
MAX_ALIAS_LENGTH = 200
MAX_CULINARY_ITEMS = 500
MAX_CULINARY_CLAIMS_PER_ITEM = 32
MAX_CULINARY_PROVENANCE_PER_ITEM = 128
_CULINARY_CATEGORY_PATTERN = re.compile(r"^[a-z][a-z0-9_]{1,63}$")

_PRODUCTION_CATALOGUE_SQL = """
SELECT d.destination_id::text AS destination_id,
       d.destination_key,
       d.canonical_name,
       d.destination_type,
       d.province_name,
       d.city_name,
       d.latitude,
       d.longitude,
       d.coordinate_role,
       EXISTS (
           SELECT 1
           FROM knowledge.production_destination_sources AS s
           WHERE s.destination_id = d.destination_id
       ) AS has_verified_provenance
FROM knowledge.production_destinations AS d
ORDER BY d.destination_id ASC
LIMIT %s
"""

_PRODUCTION_DESTINATION_SOURCES_SQL = """
SELECT destination_id, source_id, source_name, source_url, source_role,
       evidence_note, retrieved_at, valid_from, valid_until, reliability_score
FROM knowledge.production_destination_sources
WHERE destination_id = ANY(%s::BIGINT[])
ORDER BY destination_id ASC, source_id ASC
"""

_PRODUCTION_DESTINATION_TAGS_SQL = """
SELECT destination_id, tag
FROM knowledge.production_destination_tags
WHERE destination_id = ANY(%s::BIGINT[])
ORDER BY destination_id ASC, tag ASC
LIMIT %s
"""

_PRODUCTION_CULINARY_SQL = """
SELECT item_id::text AS item_id, item_key, category, record_key,
       names_by_locale, descriptions_by_locale, claims, provenance, updated_at
FROM knowledge.production_culinary_knowledge
WHERE (%s::TEXT IS NULL OR category = %s::TEXT)
ORDER BY item_key ASC
LIMIT %s
"""


class CatalogueUnavailableError(Exception):
    """Database or bounded-response failure; deliberately carries no details."""


def _to_culinary_item(row: Mapping[str, object], locale: str) -> ProductionCulinaryItem:
    names = row.get("names_by_locale")
    descriptions = row.get("descriptions_by_locale")
    raw_claims = row.get("claims")
    raw_provenance = row.get("provenance")
    if not isinstance(names, dict) or not isinstance(descriptions, dict):
        raise CatalogueUnavailableError
    if not isinstance(names.get(locale), str) or not names[locale].strip():
        raise CatalogueUnavailableError
    if not isinstance(descriptions.get(locale), str) or not descriptions[locale].strip():
        raise CatalogueUnavailableError
    if not isinstance(raw_claims, list) or len(raw_claims) > MAX_CULINARY_CLAIMS_PER_ITEM:
        raise CatalogueUnavailableError
    if (
        not isinstance(raw_provenance, list)
        or len(raw_provenance) > MAX_CULINARY_PROVENANCE_PER_ITEM
    ):
        raise CatalogueUnavailableError

    claims_for_locale: dict[str, str] = {}
    all_claim_keys: set[str] = set()
    for claim in raw_claims:
        if not isinstance(claim, dict):
            raise CatalogueUnavailableError
        claim_key, claim_locale, text = (
            claim.get("claim_key"),
            claim.get("locale"),
            claim.get("text"),
        )
        if not isinstance(claim_key, str) or not claim_key.strip():
            raise CatalogueUnavailableError
        if claim_locale not in {"fa-IR", "en-US", "ar"}:
            raise CatalogueUnavailableError
        all_claim_keys.add(claim_key)
        if claim_locale != locale:
            continue
        if not isinstance(text, str) or not text.strip() or claim_key in claims_for_locale:
            raise CatalogueUnavailableError
        claims_for_locale[claim_key] = text

    sources_by_claim: dict[str, list[dict[str, object]]] = {}
    for source in raw_provenance:
        if not isinstance(source, dict):
            raise CatalogueUnavailableError
        claim_key = source.get("claim_key")
        if not isinstance(claim_key, str) or not claim_key.strip():
            raise CatalogueUnavailableError
        sources_by_claim.setdefault(claim_key, []).append(
            {
                "source_name": source.get("source_name"),
                "source_url": source.get("source_url"),
                "license": source.get("license"),
                "source_role": source.get("source_role"),
                "evidence_note": source.get("evidence_note"),
                "retrieved_at": source.get("retrieved_at"),
                "valid_from": source.get("valid_from"),
                "valid_until": source.get("valid_until"),
            }
        )
    if set(sources_by_claim) != all_claim_keys:
        raise CatalogueUnavailableError

    projected_claims: list[CulinaryClaim] = []
    for claim_key, text in sorted(claims_for_locale.items()):
        sources = sources_by_claim.get(claim_key)
        if not sources:
            raise CatalogueUnavailableError
        projected_claims.append(
            CulinaryClaim.model_validate(
                {
                    "claim_key": claim_key,
                    "text": text,
                    "sources": sources,
                }
            )
        )

    return ProductionCulinaryItem(
        item_id=_bounded_text(row.get("item_id"), 36),
        item_key=_bounded_text(row.get("item_key"), 240),
        category=_bounded_text(row.get("category"), 64),
        record_key=_bounded_text(row.get("record_key"), 240),
        locale=locale,
        name=_bounded_text(names[locale], 240),
        description=_bounded_text(descriptions[locale], 8_000),
        claims=projected_claims,
        updated_at=row.get("updated_at"),
    )


def list_production_culinary(
    settings: Settings,
    *,
    locale: Literal["fa-IR", "en-US", "ar"],
    category: str | None = None,
) -> AvailableCulinaryCatalogue:
    """Read only the approved non-spatial culinary publication view.

    The bounded full result fails closed on overflow so callers never mistake
    a truncated catalogue for a complete one. Empty is a successful result.
    """
    if category is not None and not _CULINARY_CATEGORY_PATTERN.fullmatch(category):
        raise CatalogueUnavailableError
    query_timeout_ms = settings.database_connect_timeout_seconds * 1_000
    try:
        with psycopg.connect(
            host=settings.database_host,
            port=settings.database_port,
            dbname=settings.database_name,
            user=settings.database_user,
            password=settings.database_password.get_secret_value(),
            connect_timeout=settings.database_connect_timeout_seconds,
            application_name="ai-tourism-culinary-catalogue-read",
            options=f"-c statement_timeout={query_timeout_ms}",
            row_factory=dict_row,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute(
                    _PRODUCTION_CULINARY_SQL, (category, category, MAX_CULINARY_ITEMS + 1)
                )
                rows = cursor.fetchall()
    except Exception:
        logger.warning("catalogue.culinary_read_unavailable")
        raise CatalogueUnavailableError from None

    if len(rows) > MAX_CULINARY_ITEMS:
        logger.warning("catalogue.culinary_limit_exceeded")
        raise CatalogueUnavailableError
    try:
        items = [_to_culinary_item(row, locale) for row in rows]
        return AvailableCulinaryCatalogue(
            status="available", count=len(items), locale=locale, items=items
        )
    except (CatalogueUnavailableError, KeyError, TypeError, ValueError):
        logger.warning("catalogue.culinary_invalid_projection")
        raise CatalogueUnavailableError from None


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
    localized_names = (
        reviewed_aliases.localized_names
        if reviewed_aliases
        else {
            "fa-IR": None,
            "en-US": None,
            "ar": None,
        }
    )
    return ProductionDestinationItem(
        destination_id=str(row["destination_id"]),
        destination_key=_bounded_text(row.get("destination_key"), MAX_NAME_LENGTH),
        canonical_name=_bounded_text(row.get("canonical_name"), MAX_NAME_LENGTH),
        localized_names=localized_names,
        aliases=normalized_aliases,
        destination_type=_bounded_text(row.get("destination_type"), 64),
        province_name=_bounded_text(row.get("province_name"), MAX_NAME_LENGTH),
        city_name=city_name,
        latitude=row.get("latitude"),
        longitude=row.get("longitude"),
        coordinate_role=row.get("coordinate_role"),
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
        return [_to_item(row, reviewed_aliases.get(str(row["destination_key"]))) for row in rows]
    except (AliasManifestUnavailable, KeyError, TypeError, ValueError):
        logger.warning("catalogue.read_invalid_projection")
        raise CatalogueUnavailableError from None


def list_production_destination_sources(
    settings: Settings, destination_ids: list[str] | tuple[str, ...]
) -> dict[str, list[ProductionDestinationSource]]:
    """Return verified, current provenance through the approved source view only.

    The adapter accepts only a bounded list of numeric IDs and never queries raw
    knowledge tables. An empty ID list is a successful empty result.
    """
    if not destination_ids:
        return {}
    if len(destination_ids) > MAX_CATALOGUE_ITEMS:
        raise CatalogueUnavailableError
    try:
        raw_ids = [str(value) for value in destination_ids]
        if any(
            not value.isascii() or not value.isdecimal() or len(value) > 19 for value in raw_ids
        ):
            raise ValueError
        parsed_ids = sorted({int(value) for value in raw_ids})
        if any(value < 1 or value > 9_223_372_036_854_775_807 for value in parsed_ids):
            raise ValueError
    except (TypeError, ValueError):
        raise CatalogueUnavailableError from None

    query_timeout_ms = settings.database_connect_timeout_seconds * 1_000
    try:
        with psycopg.connect(
            host=settings.database_host,
            port=settings.database_port,
            dbname=settings.database_name,
            user=settings.database_user,
            password=settings.database_password.get_secret_value(),
            connect_timeout=settings.database_connect_timeout_seconds,
            application_name="ai-tourism-catalogue-provenance-read",
            options=f"-c statement_timeout={query_timeout_ms}",
            row_factory=dict_row,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute(_PRODUCTION_DESTINATION_SOURCES_SQL, (parsed_ids,))
                rows = cursor.fetchall()
    except Exception:
        logger.warning("catalogue.provenance_read_unavailable")
        raise CatalogueUnavailableError from None

    if len(rows) > MAX_CATALOGUE_ITEMS * MAX_SOURCES_PER_DESTINATION:
        logger.warning("catalogue.provenance_limit_exceeded")
        raise CatalogueUnavailableError
    try:
        result: dict[str, list[ProductionDestinationSource]] = {}
        for row in rows:
            source = ProductionDestinationSource.model_validate(row)
            bucket = result.setdefault(str(source.destination_id), [])
            if len(bucket) >= MAX_SOURCES_PER_DESTINATION:
                raise CatalogueUnavailableError
            bucket.append(source)
        return result
    except (CatalogueUnavailableError, KeyError, TypeError, ValueError):
        logger.warning("catalogue.provenance_invalid_projection")
        raise CatalogueUnavailableError from None


def list_production_destination_tags(
    settings: Settings, destination_ids: list[str] | tuple[str, ...]
) -> dict[str, tuple[str, ...]]:
    """Read bounded tag metadata only from the approved production tag view."""
    if not destination_ids:
        return {}
    if len(destination_ids) > MAX_CATALOGUE_ITEMS:
        raise CatalogueUnavailableError
    try:
        raw_ids = [str(value) for value in destination_ids]
        if any(
            not value.isascii() or not value.isdecimal() or len(value) > 19 for value in raw_ids
        ):
            raise ValueError
        parsed_ids = sorted({int(value) for value in raw_ids})
        if any(value < 1 or value > 9_223_372_036_854_775_807 for value in parsed_ids):
            raise ValueError
    except (TypeError, ValueError):
        raise CatalogueUnavailableError from None

    query_timeout_ms = settings.database_connect_timeout_seconds * 1_000
    try:
        with psycopg.connect(
            host=settings.database_host,
            port=settings.database_port,
            dbname=settings.database_name,
            user=settings.database_user,
            password=settings.database_password.get_secret_value(),
            connect_timeout=settings.database_connect_timeout_seconds,
            application_name="ai-tourism-catalogue-tags-read",
            options=f"-c statement_timeout={query_timeout_ms}",
            row_factory=dict_row,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute(
                    _PRODUCTION_DESTINATION_TAGS_SQL,
                    (parsed_ids, MAX_CATALOGUE_ITEMS * MAX_TAGS_PER_DESTINATION + 1),
                )
                rows = cursor.fetchall()
    except Exception:
        logger.warning("catalogue.tags_read_unavailable")
        raise CatalogueUnavailableError from None

    if len(rows) > MAX_CATALOGUE_ITEMS * MAX_TAGS_PER_DESTINATION:
        logger.warning("catalogue.tags_limit_exceeded")
        raise CatalogueUnavailableError
    try:
        result: dict[str, list[str]] = {}
        for row in rows:
            tag = ProductionDestinationTag.model_validate(row)
            bucket = result.setdefault(str(tag.destination_id), [])
            if len(bucket) >= MAX_TAGS_PER_DESTINATION:
                raise CatalogueUnavailableError
            bucket.append(tag.tag)
        return {destination_id: tuple(tags) for destination_id, tags in result.items()}
    except (CatalogueUnavailableError, KeyError, TypeError, ValueError):
        logger.warning("catalogue.tags_invalid_projection")
        raise CatalogueUnavailableError from None
