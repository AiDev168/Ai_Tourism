from __future__ import annotations

from copy import deepcopy
from contextlib import nullcontext
from datetime import UTC, datetime
from unittest.mock import MagicMock

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.modules.catalog.content_pack import (
    CandidateIdentityError,
    ContentPackUnavailable,
    CulinaryProposal,
    import_disposition,
    load_candidate_content_pack,
    payload_sha256,
    proposal_stable_key,
    resolve_exact_destination_id,
    resolve_new_culinary_duplicate,
    resolve_source_ids_exactly,
    resolve_optional_source_ids_exactly,
)
from app.modules.catalog.schemas import AvailableCulinaryCatalogue
from app.modules.catalog.repository import (
    MAX_CULINARY_ITEMS,
    CatalogueUnavailableError,
    _PRODUCTION_CULINARY_SQL,
    _to_culinary_item,
    list_production_culinary,
)
from app.modules.catalog.content_importer import (
    ContentImportConflict,
    _SOURCE_IDENTITY_SQL,
    stage_review_content_pack,
)
from app.core.config import Settings
from app.main import app

client = TestClient(app)


def settings() -> Settings:
    return Settings(_env_file=None, database_password="test-only", database_user="ai_tourism_app")


def test_review_pack_has_expected_inventory_and_never_publishable() -> None:
    pack = load_candidate_content_pack()

    assert len(pack.existing_destination_enrichment_proposals) == 11
    assert len(pack.non_spatial_knowledge) == 5
    assert len(pack.source_register) == 23
    assert all(item.provenance.status == "needs_review" for item in pack.non_spatial_knowledge)
    assert all(
        item.provenance.verification_status == "pending" for item in pack.non_spatial_knowledge
    )
    assert all(item.provenance.publishable is False for item in pack.non_spatial_knowledge)
    assert all(not item.venue_ids for item in pack.non_spatial_knowledge)
    assert all(item.dietary_and_allergen_data is None for item in pack.non_spatial_knowledge)


def test_candidate_pack_preserves_claim_text_and_source_references() -> None:
    pack = load_candidate_content_pack()
    dish = next(
        item for item in pack.non_spatial_knowledge if item.record_key == "shiraz-kalam-polo-v1"
    )
    claim = dish.claims[0]

    assert claim.text_by_locale is not None
    assert set(claim.text_by_locale) == {"fa-IR", "en-US", "ar"}
    assert claim.source_ids
    assert all(
        source_id in {source.source_id for source in pack.source_register}
        for source_id in claim.source_ids
    )


def test_duplicate_claim_text_forms_are_rejected() -> None:
    from app.modules.catalog.content_pack import ClaimDraft

    with pytest.raises(ValueError, match="exactly one"):
        ClaimDraft(
            claim_id="claim",
            claim_by_locale={"fa-IR": "الف", "en-US": "A", "ar": "أ"},
            text_by_locale={"fa-IR": "الف", "en-US": "A", "ar": "أ"},
            source_ids=["source"],
        )


def test_destination_identity_requires_exactly_one_existing_stable_key() -> None:
    assert (
        resolve_exact_destination_id(
            "shiraz-hafezieh-v1",
            [{"destination_key": "shiraz-hafezieh-v1", "destination_id": 7}],
        )
        == 7
    )

    with pytest.raises(CandidateIdentityError):
        resolve_exact_destination_id(
            "Hafezieh", [{"destination_key": "shiraz-hafezieh-v1", "destination_id": 7}]
        )
    with pytest.raises(CandidateIdentityError):
        resolve_exact_destination_id(
            "shiraz-hafezieh-v1",
            [
                {"destination_key": "shiraz-hafezieh-v1", "destination_id": 7},
                {"destination_key": "shiraz-hafezieh-v1", "destination_id": 8},
            ],
        )
    with pytest.raises(CandidateIdentityError):
        resolve_exact_destination_id(
            "shiraz-hafezieh-v1", [{"destination_key": "shiraz-hafezieh-v1", "destination_id": 0}]
        )


def test_source_mapping_requires_exactly_one_existing_source_and_never_inserts() -> None:
    pack = load_candidate_content_pack()
    source = pack.source_register[0]
    registered = [
        {"source_id": index + 1, "url": item.url} for index, item in enumerate(pack.source_register)
    ]
    mapped = resolve_source_ids_exactly(pack, registered)
    assert mapped[source.source_id] == 1

    with pytest.raises(CandidateIdentityError):
        resolve_source_ids_exactly(pack, [])
    with pytest.raises(CandidateIdentityError):
        resolve_source_ids_exactly(pack, registered + [{"source_id": 24, "url": source.url}])

    optional = resolve_optional_source_ids_exactly(
        pack, [row for row in registered if row["url"] != source.url]
    )
    assert optional[source.source_id] is None
    with pytest.raises(CandidateIdentityError):
        resolve_optional_source_ids_exactly(
            pack, registered + [{"source_id": 24, "url": source.url}]
        )


def test_importer_source_lookup_uses_existing_url_column():
    assert "SELECT source_id, url" in _SOURCE_IDENTITY_SQL
    assert "WHERE url = ANY(%s::TEXT[])" in _SOURCE_IDENTITY_SQL
    assert "source_url" not in _SOURCE_IDENTITY_SQL


def test_new_culinary_duplicate_match_is_locale_and_category_exact() -> None:
    pack = load_candidate_content_pack()
    proposal = next(
        item for item in pack.non_spatial_knowledge if item.record_key == "fars-aush-sabzi-v1"
    )

    assert resolve_new_culinary_duplicate(proposal, []) is None
    assert (
        resolve_new_culinary_duplicate(
            proposal,
            [
                {
                    "record_key": "existing-aush",
                    "category": proposal.category,
                    "name_by_locale": {"fa-IR": proposal.name_by_locale["fa-IR"]},
                }
            ],
        )
        == "existing-aush"
    )
    assert (
        resolve_new_culinary_duplicate(
            proposal,
            [
                {
                    "record_key": "other-category",
                    "category": "dessert",
                    "name_by_locale": {"fa-IR": proposal.name_by_locale["fa-IR"]},
                }
            ],
        )
        is None
    )
    with pytest.raises(CandidateIdentityError, match="ambiguous"):
        resolve_new_culinary_duplicate(
            proposal,
            [
                {
                    "record_key": "first",
                    "category": proposal.category,
                    "name_by_locale": {"fa-IR": proposal.name_by_locale["fa-IR"]},
                },
                {
                    "record_key": "second",
                    "category": proposal.category,
                    "name_by_locale": {"en-US": proposal.name_by_locale["en-US"]},
                },
            ],
        )


def test_new_culinary_identity_projection_fails_closed_when_incomplete() -> None:
    proposal = CulinaryProposal.model_validate(
        {
            "entity_kind": "non_spatial_culinary_knowledge",
            "record_key": "new-dish-v1",
            "record_action": "stage_new_non_spatial_candidate_review",
            "category": "regional_dish",
            "name_by_locale": {"fa-IR": "غذای تازه", "en-US": "New dish", "ar": "طبق جديد"},
            "description_by_locale_draft": {"fa-IR": "متن", "en-US": "Text", "ar": "نص"},
            "claims": [
                {
                    "claim_id": "claim",
                    "text_by_locale": {"fa-IR": "متن", "en-US": "Text", "ar": "نص"},
                    "source_ids": ["S"],
                }
            ],
            "dietary_and_allergen_data": None,
            "venue_ids": [],
            "provenance": {
                "record_origin": "verified_external",
                "verification_status": "pending",
                "is_synthetic": False,
                "status": "needs_review",
                "data_confidence": 0.0,
                "publishable": False,
            },
            "editorial_notes": ["review"],
            "duplicate_check": {
                "match_by": ["normalized_locale_names", "culinary_category"],
                "must_resolve_no_existing_duplicate_before_insert": True,
                "if_match_found": "stage_as_existing_record_enrichment_instead",
            },
        }
    )
    with pytest.raises(CandidateIdentityError, match="incomplete"):
        resolve_new_culinary_duplicate(
            proposal, [{"record_key": "existing", "category": proposal.category}]
        )


def test_stable_key_hash_and_retry_classification_are_deterministic() -> None:
    payload = {"record_key": "dish-v1", "description": "متن"}
    stable_key = proposal_stable_key("dataset", "2.0.0", "dish-v1")
    digest = payload_sha256(payload)

    assert stable_key == "dataset:2.0.0:dish-v1"
    assert digest == payload_sha256(deepcopy(payload))
    assert import_disposition(stable_key, digest, None) == "insert"
    assert (
        import_disposition(
            stable_key,
            digest,
            {
                "proposal_key": stable_key,
                "payload_sha256": digest,
                "review_status": "needs_review",
                "publication_status": "unpublished",
            },
        )
        == "noop"
    )
    with pytest.raises(CandidateIdentityError, match="different content"):
        import_disposition(
            stable_key,
            "different",
            {
                "proposal_key": stable_key,
                "payload_sha256": digest,
                "review_status": "needs_review",
                "publication_status": "unpublished",
            },
        )
    with pytest.raises(CandidateIdentityError, match="reviewed or published"):
        import_disposition(
            stable_key,
            digest,
            {
                "proposal_key": stable_key,
                "payload_sha256": digest,
                "review_status": "approved",
                "publication_status": "published",
            },
        )


def test_invalid_stable_keys_and_non_json_payloads_fail_closed() -> None:
    with pytest.raises(ContentPackUnavailable):
        proposal_stable_key("dataset", "2.0.0", "bad\nkey")
    with pytest.raises(ContentPackUnavailable):
        payload_sha256({"float": float("nan")})


def test_culinary_response_is_localized_non_spatial_and_strict() -> None:
    response = AvailableCulinaryCatalogue.model_validate(
        {
            "status": "available",
            "count": 0,
            "locale": "fa-IR",
            "items": [],
        }
    )
    assert response.count == 0

    item = {
        "item_id": "00000000-0000-0000-0000-000000000001",
        "item_key": "shiraz-kalam-polo-v1",
        "category": "regional_dish",
        "record_key": "shiraz-kalam-polo-v1",
        "locale": "fa-IR",
        "name": "کلم‌پلو شیرازی",
        "description": "توضیح منتشرشده",
        "claims": [
            {
                "claim_key": "regional_dish_origin",
                "text": "متن ادعا",
                "sources": [
                    {
                        "source_name": "منبع",
                        "source_url": "https://example.test/source",
                        "source_role": "supports",
                    }
                ],
            }
        ],
        "updated_at": datetime.now(UTC),
    }
    assert (
        AvailableCulinaryCatalogue.model_validate(
            {"status": "available", "count": 1, "locale": "fa-IR", "items": [item]}
        )
        .items[0]
        .name
        == "کلم‌پلو شیرازی"
    )
    with pytest.raises(ValueError):
        AvailableCulinaryCatalogue.model_validate(
            {
                "status": "available",
                "count": 1,
                "locale": "fa-IR",
                "items": [{**item, "destination_id": 9}],
            }
        )


def _culinary_projection() -> dict[str, object]:
    return {
        "item_id": "00000000-0000-0000-0000-000000000001",
        "item_key": "shiraz-kalam-polo-v1",
        "category": "regional_dish",
        "record_key": "shiraz-kalam-polo-v1",
        "names_by_locale": {"fa-IR": "کلم پلو", "en-US": "Kalam Polo", "ar": "كلم پلو"},
        "descriptions_by_locale": {"fa-IR": "شرح", "en-US": "Description", "ar": "وصف"},
        "claims": [
            {"claim_key": "dish_profile", "locale": locale, "text": f"claim-{locale}"}
            for locale in ("fa-IR", "en-US", "ar")
        ],
        "provenance": [
            {
                "claim_key": "dish_profile",
                "source_key": "source-1",
                "source_name": "Source",
                "source_url": "https://example.test/source",
                "license": None,
                "source_role": "claim_support",
                "evidence_note": None,
                "retrieved_at": None,
                "valid_from": None,
                "valid_until": None,
            }
        ],
        "updated_at": datetime.now(UTC),
    }


def test_culinary_adapter_projects_only_requested_locale_and_source_evidence(monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = [_culinary_projection()]
    monkeypatch.setattr(psycopg, "connect", lambda **_kwargs: connection)

    result = list_production_culinary(settings(), locale="ar", category="regional_dish")
    assert result.count == 1
    assert result.items[0].locale == "ar"
    assert result.items[0].name == "كلم پلو"
    assert result.items[0].claims[0].text == "claim-ar"
    assert result.items[0].claims[0].sources[0].source_url == "https://example.test/source"
    query = cursor.execute.call_args_list[1]
    assert query.args[0] == _PRODUCTION_CULINARY_SQL
    assert query.args[1] == ("regional_dish", "regional_dish", MAX_CULINARY_ITEMS + 1)
    assert "knowledge.production_culinary_knowledge" in _PRODUCTION_CULINARY_SQL
    for forbidden in (
        "knowledge.culinary_knowledge_items",
        "knowledge.destinations",
        "knowledge.knowledge_sources",
    ):
        assert forbidden not in _PRODUCTION_CULINARY_SQL


def test_culinary_adapter_empty_result_and_overflow(monkeypatch):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = []
    monkeypatch.setattr(psycopg, "connect", lambda **_kwargs: connection)
    assert list_production_culinary(settings(), locale="fa-IR").count == 0

    cursor.fetchall.return_value = [_culinary_projection()] * (MAX_CULINARY_ITEMS + 1)
    with pytest.raises(CatalogueUnavailableError):
        list_production_culinary(settings(), locale="fa-IR")


def test_culinary_adapter_fails_closed_on_missing_locale_or_claim_provenance():
    projection = _culinary_projection()
    projection["names_by_locale"] = {"en-US": "Name"}
    with pytest.raises(CatalogueUnavailableError):
        _to_culinary_item(projection, "fa-IR")

    projection = _culinary_projection()
    projection["provenance"] = []
    with pytest.raises(CatalogueUnavailableError):
        _to_culinary_item(projection, "fa-IR")


def test_culinary_api_success_empty_unavailable_and_missing_locale(monkeypatch):
    monkeypatch.setattr(
        "app.api.catalogue.list_production_culinary",
        lambda _settings, *, locale, category=None: AvailableCulinaryCatalogue(
            status="available", count=0, locale=locale, items=[]
        ),
    )
    empty = client.get("/api/v1/catalog/culinary?locale=fa-IR")
    assert empty.status_code == 200
    assert empty.json() == {"status": "available", "count": 0, "locale": "fa-IR", "items": []}
    assert empty.headers["cache-control"] == "no-store"

    def unavailable(*_args, **_kwargs):
        raise CatalogueUnavailableError

    monkeypatch.setattr("app.api.catalogue.list_production_culinary", unavailable)
    failure = client.get("/api/v1/catalog/culinary?locale=en-US")
    assert failure.status_code == 503
    assert failure.json() == {"status": "unavailable", "error": {"code": "catalogue_unavailable"}}
    assert failure.headers["cache-control"] == "no-store"

    missing = client.get("/api/v1/catalog/culinary")
    assert missing.status_code == 422


class ImportConnection:
    """Small SQL-contract fake; no database connection is opened."""

    def __init__(self, pack, *, omit_source_url: str | None = None):
        self.pack = pack
        self.omit_source_url = omit_source_url
        self.statements: list[str] = []
        self.inserted_parent_count = 0
        self.parents: dict[tuple[str, str], dict[str, object]] = {}
        self.edges: dict[str, list[dict[str, object]]] = {}

    def cursor(self):
        return ImportCursor(self)

    def transaction(self):
        return nullcontext(self)


class ImportCursor:
    def __init__(self, connection: ImportConnection):
        self.connection = connection
        self.rows: list[dict[str, object]] = []
        self.one: dict[str, object] | None = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql: str, params=()):
        self.connection.statements.append(sql)
        self.rows = []
        self.one = None
        if "FROM knowledge.knowledge_sources" in sql:
            self.rows = [
                {"source_id": index + 1, "url": source.url}
                for index, source in enumerate(self.connection.pack.source_register)
                if source.url != self.connection.omit_source_url
            ]
        elif "WHERE destination_type IN ('food_dish', 'local_sweet')" in sql:
            self.rows = []
        elif "SELECT destination_id, destination_key" in sql:
            keys = params[0]
            spatial_keys = [
                item.target_record_key
                for item in self.connection.pack.existing_destination_enrichment_proposals
            ]
            food_keys = [
                item.record_key
                for item in self.connection.pack.non_spatial_knowledge
                if item.record_action == "stage_existing_record_enrichment_review"
            ]
            all_keys = [*spatial_keys, *food_keys]
            self.rows = [
                {"destination_id": index + 1, "destination_key": key}
                for index, key in enumerate(all_keys)
                if key in keys
            ]
        elif sql.startswith("SELECT") and "payload_sha256" in sql:
            table = (
                "knowledge.destination_enrichment_proposals"
                if "destination_enrichment_proposals" in sql
                else "knowledge.culinary_knowledge_items"
            )
            self.one = self.connection.parents.get((table, str(params[0])))
        elif sql.startswith("SELECT") and "claim_key, source_key, source_id" in sql:
            parent_id = str(params[0])
            self.rows = self.connection.edges.get(parent_id, [])
        elif sql.startswith("INSERT INTO knowledge.destination_enrichment_proposals"):
            self.connection.inserted_parent_count += 1
            self.one = {
                "proposal_id": f"00000000-0000-0000-0000-{self.connection.inserted_parent_count:012d}"
            }
            self.connection.parents[
                ("knowledge.destination_enrichment_proposals", str(params[0]))
            ] = {
                "proposal_id": self.one["proposal_id"],
                "proposal_key": params[0],
                "payload_sha256": params[-1],
                "review_status": "needs_review",
                "publishable": False,
                "is_synthetic": False,
            }
        elif sql.startswith("INSERT INTO knowledge.culinary_knowledge_items"):
            self.connection.inserted_parent_count += 1
            self.one = {
                "item_id": f"00000000-0000-0000-0000-{self.connection.inserted_parent_count:012d}"
            }
            self.connection.parents[("knowledge.culinary_knowledge_items", str(params[0]))] = {
                "item_id": self.one["item_id"],
                "item_key": params[0],
                "payload_sha256": params[-1],
                "review_status": "pending_review",
                "publishable": False,
                "is_synthetic": False,
            }

    def executemany(self, sql: str, params):
        self.connection.statements.append(sql)
        for values in params:
            parent_id, *edge = values
            self.connection.edges.setdefault(str(parent_id), []).append(
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
            )

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.one


def test_offline_importer_stages_review_rows_without_writing_canonical_or_source_tables():
    pack = load_candidate_content_pack()
    connection = ImportConnection(pack)
    result = stage_review_content_pack(connection, "00000000-0000-0000-0000-000000000099", pack)

    assert result == {"inserted": 16, "unchanged": 0}
    assert connection.inserted_parent_count == 16
    writes = [
        sql
        for sql in connection.statements
        if sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
    ]
    assert writes
    assert all(
        "knowledge.destinations" not in sql and "knowledge.knowledge_sources" not in sql
        for sql in writes
    )
    assert any("knowledge.destination_enrichment_proposals" in sql for sql in writes)
    assert any("knowledge.culinary_knowledge_items" in sql for sql in writes)


def test_offline_importer_fails_before_writes_when_a_source_url_is_missing():
    pack = load_candidate_content_pack()
    connection = ImportConnection(pack, omit_source_url=pack.source_register[0].url)

    result = stage_review_content_pack(connection, "00000000-0000-0000-0000-000000000099", pack)
    assert result["inserted"] == 16
    assert any(edge["source_id"] is None for group in connection.edges.values() for edge in group)


def test_offline_importer_retry_is_idempotent_and_rejects_changed_payload():
    pack = load_candidate_content_pack()
    connection = ImportConnection(pack)
    batch_id = "00000000-0000-0000-0000-000000000099"
    first = stage_review_content_pack(connection, batch_id, pack)
    assert first == {"inserted": 16, "unchanged": 0}
    second = stage_review_content_pack(connection, batch_id, pack)
    assert second == {"inserted": 0, "unchanged": 16}
    assert connection.inserted_parent_count == 16

    changed = pack.model_copy(deep=True)
    changed.non_spatial_knowledge[0].name_by_locale["fa-IR"] += " ویرایش"
    with pytest.raises(CandidateIdentityError, match="different content"):
        stage_review_content_pack(connection, batch_id, changed)


def test_offline_importer_requires_an_existing_batch_uuid():
    pack = load_candidate_content_pack()
    with pytest.raises(ContentImportConflict):
        stage_review_content_pack(ImportConnection(pack), "not-a-uuid", pack)
