"""Offline, operator-injected staging for reviewed content proposals.

There is intentionally no HTTP write route and this module never opens a
connection or loads credentials. The caller supplies a controlled connection
and an already existing import-batch UUID.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, date, datetime, time
from typing import Any
from uuid import UUID

from app.modules.catalog.alias_manifest import normalize_alias
from app.modules.catalog.content_pack import (
    CandidateContentPack,
    CandidateIdentityError,
    CulinaryProposal,
    import_disposition,
    payload_sha256,
    proposal_stable_key,
    resolve_exact_destination_id,
    resolve_optional_source_ids_exactly,
)

_SPATIAL_IDENTITY_SQL = """
SELECT destination_id, destination_key
FROM knowledge.destinations
WHERE destination_key = ANY(%s::TEXT[])
"""
_SOURCE_IDENTITY_SQL = """
SELECT source_id, url
FROM knowledge.knowledge_sources
WHERE url = ANY(%s::TEXT[])
"""
_LEGACY_CULINARY_SQL = """
SELECT destination_id, destination_key, canonical_name, destination_type, aliases
FROM knowledge.destinations
WHERE destination_type IN ('food_dish', 'local_sweet')
"""


class ContentImportConflict(RuntimeError):
    """Identity, review state, or retry conflict; message contains no DB detail."""


def _json_value(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _edge_values(
    pack: CandidateContentPack,
    source_map: Mapping[str, int | None],
    claims: list[tuple[str, list[str], str, str | None]],
) -> list[tuple[Any, ...]]:
    """(claim_key, source_key, source_id, name, url, license, role, note, retrieved)."""
    refs = {source.source_id: source for source in pack.source_register}
    values: set[tuple[Any, ...]] = set()
    for claim_key, source_keys, role, evidence_note in claims:
        for source_key in source_keys:
            source = refs[source_key]
            retrieved_at = source.retrieved_at
            if isinstance(retrieved_at, date) and not isinstance(retrieved_at, datetime):
                retrieved_at = datetime.combine(retrieved_at, time.min, tzinfo=UTC)
            values.add(
                (
                    claim_key,
                    source_key,
                    source_map[source_key],
                    source.title,
                    source.url,
                    source.license or None,
                    role,
                    evidence_note,
                    retrieved_at,
                    None,
                    None,
                )
            )
    return sorted(values, key=lambda item: (item[0], item[1], item[6]))


def _read_rows(connection: Any, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    return [dict(row) for row in rows]


def _exact_destinations(connection: Any, keys: list[str]) -> list[dict[str, Any]]:
    return _read_rows(connection, _SPATIAL_IDENTITY_SQL, (keys,))


def _exact_sources(connection: Any, urls: list[str]) -> list[dict[str, Any]]:
    return _read_rows(connection, _SOURCE_IDENTITY_SQL, (urls,))


def _legacy_foods(connection: Any) -> list[dict[str, Any]]:
    rows = _read_rows(connection, _LEGACY_CULINARY_SQL)
    # Legacy aliases have no locale tags. Treating them as possible exact
    # collisions is conservative; they are never promoted to reviewed aliases.
    normalized: list[dict[str, Any]] = []
    for row in rows:
        names = [row.get("canonical_name"), *(row.get("aliases") or [])]
        normalized.append(
            {
                "record_key": str(row.get("destination_key") or row.get("destination_id")),
                "category": "legacy_food",
                "name_by_locale": {
                    "und": normalize_alias(name) for name in names if isinstance(name, str)
                },
            }
        )
    return normalized


def _resolve_destination_ids(
    pack: CandidateContentPack, rows: list[dict[str, Any]]
) -> dict[str, int]:
    return {
        proposal.target_record_key: resolve_exact_destination_id(proposal.target_record_key, rows)
        for proposal in pack.existing_destination_enrichment_proposals
    }


def _resolve_legacy_food_id(
    proposal: CulinaryProposal,
    destination_rows: list[dict[str, Any]],
    legacy_foods: list[dict[str, Any]],
) -> int | None:
    if proposal.record_action == "stage_new_non_spatial_candidate_review":
        # Check all localized names conservatively against untagged legacy
        # names/aliases, regardless of their original locale.
        candidate_names = {normalize_alias(value) for value in proposal.name_by_locale.values()}
        for row in legacy_foods:
            if candidate_names & set(row["name_by_locale"].values()):
                raise CandidateIdentityError(
                    "new culinary candidate conflicts with an existing legacy food"
                )
        return None

    matches = [row for row in destination_rows if row.get("destination_key") == proposal.record_key]
    if len(matches) != 1:
        raise CandidateIdentityError(
            "existing culinary identity must resolve by exact stable destination key"
        )
    return resolve_exact_destination_id(proposal.record_key, destination_rows)


def _ensure_proposal(
    connection: Any,
    *,
    table: str,
    id_column: str,
    key_column: str,
    stable_key: str,
    payload: dict[str, Any],
    digest: str,
    parent_columns: dict[str, Any],
    edge_table: str,
    edge_parent_column: str,
    edges: list[tuple[Any, ...]],
) -> LiteralResult:
    select_sql = f"SELECT {id_column}, {key_column}, payload_sha256, review_status, publishable, is_synthetic FROM {table} WHERE {key_column} = %s FOR UPDATE"
    insert_columns = list(parent_columns)
    insert_values = [parent_columns[name] for name in insert_columns]
    insert_columns.extend(("payload", "payload_sha256"))
    insert_values.extend((_json_value(payload), digest))
    placeholders = ", ".join(["%s"] * len(insert_values))
    insert_sql = f"INSERT INTO {table} ({', '.join(insert_columns)}) VALUES ({placeholders}) ON CONFLICT ({key_column}) DO NOTHING RETURNING {id_column}"

    created = False
    with connection.cursor() as cursor:
        cursor.execute(select_sql, (stable_key,))
        existing = cursor.fetchone()
        if existing is None:
            cursor.execute(insert_sql, tuple(insert_values))
            inserted = cursor.fetchone()
            if inserted is None:
                cursor.execute(select_sql, (stable_key,))
                existing = cursor.fetchone()
            else:
                created = True
                existing = {
                    id_column: inserted[id_column],
                    key_column: stable_key,
                    "payload_sha256": digest,
                    "review_status": "needs_review"
                    if table.endswith("destination_enrichment_proposals")
                    else "pending_review",
                    "publishable": False,
                    "is_synthetic": False,
                }
    if existing is None:
        raise ContentImportConflict("proposal insert could not be confirmed")

    disposition = (
        "insert"
        if created
        else import_disposition(
            stable_key,
            digest,
            {
                "proposal_key": existing.get(key_column),
                "payload_sha256": str(existing.get("payload_sha256", "")).strip(),
                "review_status": existing.get("review_status"),
                "publication_status": "published"
                if existing.get("publishable") is True
                else "unpublished",
            },
        )
    )
    if existing.get("is_synthetic") is not False:
        raise ContentImportConflict("proposal has an invalid synthetic-data classification")
    parent_id = existing[id_column]
    actual = _read_rows(
        connection,
        f"SELECT claim_key, source_key, source_id, source_name, source_url, source_license, source_role, evidence_note, retrieved_at, valid_from, valid_until FROM {edge_table} WHERE {edge_parent_column} = %s",
        (parent_id,),
    )
    desired = [
        dict(
            zip(
                (
                    "claim_key",
                    "source_key",
                    "source_id",
                    "source_name",
                    "source_url",
                    "source_license",
                    "source_role",
                    "evidence_note",
                    "retrieved_at",
                    "valid_from",
                    "valid_until",
                ),
                edge,
            )
        )
        for edge in edges
    ]
    if actual:
        if sorted(
            actual, key=lambda row: (row["claim_key"], row["source_key"], row["source_role"])
        ) != sorted(
            desired, key=lambda row: (row["claim_key"], row["source_key"], row["source_role"])
        ):
            raise ContentImportConflict(
                "existing proposal provenance differs from the reviewed package"
            )
        return "noop"
    if disposition == "noop" and edges:
        # An idempotent proposal with missing edges signals partial/tampered data.
        raise ContentImportConflict("existing proposal has incomplete provenance")
    with connection.cursor() as cursor:
        cursor.executemany(
            f"INSERT INTO {edge_table} ({edge_parent_column}, claim_key, source_key, source_id, source_name, source_url, source_license, source_role, evidence_note, retrieved_at, valid_from, valid_until) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            [(parent_id, *edge) for edge in edges],
        )
    return "insert"


LiteralResult = str


def stage_review_content_pack(
    connection: Any, batch_id: str | UUID, pack: CandidateContentPack
) -> dict[str, int]:
    """Stage all proposals transactionally using an operator-injected connection.

    This callable performs no connection creation, source registration, or
    canonical writes. The supplied batch must already exist. It should be run
    under an operator role outside product HTTP handling.
    """
    try:
        batch_uuid = UUID(str(batch_id))
    except (TypeError, ValueError):
        raise ContentImportConflict("an existing import batch UUID is required") from None
    counts = {"inserted": 0, "unchanged": 0}
    urls = [source.url for source in pack.source_register]
    source_rows = _exact_sources(connection, urls)
    source_map = resolve_optional_source_ids_exactly(pack, source_rows)
    dest_rows = _exact_destinations(
        connection,
        [proposal.target_record_key for proposal in pack.existing_destination_enrichment_proposals],
    )
    destination_ids = _resolve_destination_ids(pack, dest_rows)
    legacy_foods = _legacy_foods(connection)
    all_destination_rows = _read_rows(
        connection,
        "SELECT destination_id, destination_key FROM knowledge.destinations WHERE destination_key = ANY(%s::TEXT[])",
        (
            [
                item.record_key
                for item in pack.non_spatial_knowledge
                if item.record_action == "stage_existing_record_enrichment_review"
            ],
        ),
    )

    with connection.transaction():
        for proposal in pack.existing_destination_enrichment_proposals:
            stable_key = proposal_stable_key(
                pack.dataset_key, pack.version, proposal.target_record_key
            )
            payload = proposal.model_dump(mode="json")
            edges: list[tuple[Any, ...]] = []
            for claim in proposal.factual_claims:
                edges.extend(
                    _edge_values(
                        pack,
                        source_map,
                        [(claim.claim_id, claim.source_ids, "claim_support", None)],
                    )
                )
            edges.extend(
                _edge_values(
                    pack,
                    source_map,
                    [
                        (
                            "coordinate",
                            [proposal.coordinates.source_id],
                            "coordinate_reference",
                            proposal.coordinates.coordinate_status,
                        )
                    ],
                )
            )
            edges.extend(
                _edge_values(
                    pack,
                    source_map,
                    [("record_provenance", proposal.provenance.source_ids, "record_context", None)],
                )
            )
            result = _ensure_proposal(
                connection,
                table="knowledge.destination_enrichment_proposals",
                id_column="proposal_id",
                key_column="proposal_key",
                stable_key=stable_key,
                payload=payload,
                digest=payload_sha256(payload),
                parent_columns={
                    "proposal_key": stable_key,
                    "dataset_import_batch_id": batch_uuid,
                    "target_destination_id": destination_ids[proposal.target_record_key],
                    "target_destination_key": proposal.target_record_key,
                    "record_action": proposal.record_action,
                },
                edge_table="knowledge.destination_enrichment_proposal_sources",
                edge_parent_column="proposal_id",
                edges=edges,
            )
            counts["inserted" if result == "insert" else "unchanged"] += 1

        for item in pack.non_spatial_knowledge:
            legacy_id = _resolve_legacy_food_id(item, all_destination_rows, legacy_foods)
            stable_key = proposal_stable_key(pack.dataset_key, pack.version, item.record_key)
            payload = item.model_dump(mode="json")
            claims = [
                {
                    "claim_id": claim.claim_id,
                    "text_by_locale": claim.claim_by_locale or claim.text_by_locale,
                    "source_ids": claim.source_ids,
                }
                for claim in item.claims
            ]
            edges = []
            for claim in item.claims:
                edges.extend(
                    _edge_values(
                        pack,
                        source_map,
                        [(claim.claim_id, claim.source_ids, "claim_support", None)],
                    )
                )
            result = _ensure_proposal(
                connection,
                table="knowledge.culinary_knowledge_items",
                id_column="item_id",
                key_column="item_key",
                stable_key=stable_key,
                payload=payload,
                digest=payload_sha256(payload),
                parent_columns={
                    "item_key": stable_key,
                    "record_key": item.record_key,
                    "dataset_import_batch_id": batch_uuid,
                    "record_action": item.record_action,
                    "legacy_destination_id": legacy_id,
                    "category": item.category,
                    "names_by_locale": _json_value(item.name_by_locale),
                    "descriptions_by_locale": _json_value(item.description_by_locale_draft),
                    "claims": _json_value(claims),
                    "review_status": "pending_review",
                    "verification_status": "pending",
                    "record_origin": "verified_external",
                    "is_synthetic": False,
                    "approval_confidence": 0,
                    "publishable": False,
                },
                edge_table="knowledge.culinary_item_sources",
                edge_parent_column="item_id",
                edges=edges,
            )
            counts["inserted" if result == "insert" else "unchanged"] += 1
    return counts
