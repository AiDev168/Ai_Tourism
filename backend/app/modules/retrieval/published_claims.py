"""Read the application's exact approved spatial claim/source projection."""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.core.config import Settings
from app.modules.retrieval.identity_mapping import (
    PublishedClaimProjection,
    PublishedSourceIdentity,
)

logger = logging.getLogger("ai_tourism.retrieval.publication")
MAX_PUBLISHED_CLAIM_ROWS = 512

_PUBLISHED_CLAIMS_SQL = """
SELECT canonical_entity_key, destination_id, document_id, claim_key,
       content_hash, locale, corpus, valid_from, valid_until,
       is_published, is_destination_verified, is_document_processed,
       is_synthetic, is_revoked,
       source_id, source_name, source_url, source_role, license,
       retrieved_at, source_valid_from AS source_valid_from,
       source_valid_until AS source_valid_until,
       is_source_verified, is_source_synthetic, is_source_revoked
FROM knowledge.production_destination_claim_evidence
WHERE canonical_entity_key = ANY(%s::TEXT[])
  AND locale = %s
ORDER BY canonical_entity_key, document_id, claim_key, source_id
LIMIT %s
"""


class PublishedClaimReadUnavailable(RuntimeError):
    """The approved claim projection is unavailable or invalid."""


def projections_from_rows(rows: Sequence[dict[str, Any]]) -> dict[str, list[PublishedClaimProjection]]:
    """Group one row per approved claim/source into exact mapper projections."""

    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        identity = (
            row["canonical_entity_key"],
            row["destination_id"],
            row["document_id"],
            row["claim_key"],
            row["content_hash"],
            row["locale"],
            row["corpus"],
            row["valid_from"],
            row["valid_until"],
            row["is_published"],
            row["is_destination_verified"],
            row["is_document_processed"],
            row["is_synthetic"],
            row["is_revoked"],
        )
        entry = grouped.setdefault(identity, {"claim": row, "sources": []})
        entry["sources"].append(
            PublishedSourceIdentity(
                source_id=row["source_id"],
                source_name=row["source_name"],
                source_url=row["source_url"],
                source_role=row["source_role"],
                license=row["license"],
                retrieved_at=row["retrieved_at"],
                valid_from=row["source_valid_from"],
                valid_until=row["source_valid_until"],
                is_verified=row["is_source_verified"],
                is_synthetic=row["is_source_synthetic"],
                is_revoked=row["is_source_revoked"],
            )
        )

    by_key: dict[str, list[PublishedClaimProjection]] = defaultdict(list)
    for entry in grouped.values():
        row = entry["claim"]
        by_key[row["canonical_entity_key"]].append(
            PublishedClaimProjection(
                canonical_entity_key=row["canonical_entity_key"],
                destination_id=row["destination_id"],
                document_id=row["document_id"],
                claim_key=row["claim_key"],
                content_hash=row["content_hash"],
                locale=row["locale"],
                corpus=row["corpus"],
                valid_from=row["valid_from"],
                valid_until=row["valid_until"],
                is_published=row["is_published"],
                is_destination_verified=row["is_destination_verified"],
                is_document_processed=row["is_document_processed"],
                is_synthetic=row["is_synthetic"],
                is_revoked=row["is_revoked"],
                sources=tuple(entry["sources"]),
            )
        )
    return dict(by_key)


def load_published_claim_projections(
    settings: Settings,
    destination_keys: Sequence[str],
    locale: str,
) -> dict[str, list[PublishedClaimProjection]]:
    """Read only mapped, current claim/source rows from the granted view."""

    keys = list(dict.fromkeys(destination_keys))
    if not keys:
        return {}
    if len(keys) > 20 or any(not isinstance(key, str) or not key.strip() for key in keys):
        raise PublishedClaimReadUnavailable
    try:
        with psycopg.connect(
            host=settings.database_host,
            port=settings.database_port,
            dbname=settings.database_name,
            user=settings.database_user,
            password=settings.database_password.get_secret_value(),
            connect_timeout=settings.database_connect_timeout_seconds,
            application_name="ai-tourism-approved-claim-read",
            options=f"-c statement_timeout={settings.database_connect_timeout_seconds * 1_000}",
            row_factory=dict_row,
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute(_PUBLISHED_CLAIMS_SQL, (keys, locale, MAX_PUBLISHED_CLAIM_ROWS + 1))
                rows = cursor.fetchall()
    except Exception:
        logger.warning("owner_rag.published_claim_projection_unavailable")
        raise PublishedClaimReadUnavailable from None
    if len(rows) > MAX_PUBLISHED_CLAIM_ROWS:
        raise PublishedClaimReadUnavailable
    try:
        return projections_from_rows(rows)
    except (KeyError, TypeError, ValueError):
        logger.warning("owner_rag.published_claim_projection_invalid")
        raise PublishedClaimReadUnavailable from None
