from __future__ import annotations

from copy import deepcopy
from contextlib import nullcontext
from pathlib import Path

import pytest

from app.modules.catalog.content_addendum import (
    ContentAddendumUnavailable,
    addendum_payload_hash,
    load_content_addendum,
)
from app.modules.catalog.content_importer import (
    stage_review_content_addendum,
)

ADDENDUM_PATH = (
    Path(__file__).resolve().parents[2]
    / "engineering"
    / "data-research"
    / "shiraz_fars_candidate_content_addendum_v1"
)
BATCH_ID = "00000000-0000-0000-0000-000000000099"


def test_addendum_is_independent_four_record_review_only_contract() -> None:
    pack = load_content_addendum(ADDENDUM_PATH)
    assert pack.dataset_key == "shiraz_fars_candidate_content_addendum_v1"
    assert pack.version == "1.0.0"
    assert len(pack.spatial_entities) == 4
    assert {item.record_key for item in pack.spatial_entities} == {
        "shiraz-delgosha-garden-v1",
        "shiraz-afifabad-garden-v1",
        "shiraz-shah-cheragh-v1",
        "shiraz-naqsh-e-rostam-v1",
    }
    assert pack.publication_contract["status"] == "needs_review"
    assert pack.publication_contract["publishable"] is False
    assert pack.publication_contract["data_confidence"] == 0.0
    assert pack.locale_contract["translation_status"] == "draft_human_review_required"
    naqsh = next(x for x in pack.spatial_entities if x.record_key == "shiraz-naqsh-e-rostam-v1")
    assert (naqsh.city_name, naqsh.geographic_scope) == ("Marvdasht", "regional_day_trip")
    assert all(set(item.names_by_locale) == {"fa-IR", "en-US", "ar"} for item in pack.spatial_entities)


def test_addendum_source_csv_must_match_json_exactly(tmp_path: Path) -> None:
    load_content_addendum(ADDENDUM_PATH)
    (tmp_path / "spatial_enrichment_addendum_v1.json").write_text(
        (ADDENDUM_PATH / "spatial_enrichment_addendum_v1.json").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    csv_text = (ADDENDUM_PATH / "SOURCE_REGISTER.csv").read_text(encoding="utf-8")
    (tmp_path / "SOURCE_REGISTER.csv").write_text(
        csv_text.replace("https://visitiran.ir/attraction/shah-cheragh", "https://invalid.example/"),
        encoding="utf-8",
    )
    with pytest.raises(ContentAddendumUnavailable):
        load_content_addendum(tmp_path)


def test_addendum_rejects_missing_or_duplicate_proposal_identity(tmp_path: Path) -> None:
    source = ADDENDUM_PATH / "spatial_enrichment_addendum_v1.json"
    import json

    payload = json.loads(source.read_text(encoding="utf-8"))
    payload["spatial_entities"].pop()
    (tmp_path / source.name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "SOURCE_REGISTER.csv").write_bytes((ADDENDUM_PATH / "SOURCE_REGISTER.csv").read_bytes())
    with pytest.raises(ContentAddendumUnavailable):
        load_content_addendum(tmp_path)


class _StageConnection:
    def __init__(self, pack, *, duplicate_key: bool = False, missing_key: str | None = None, omit_source: str | None = None):
        self.pack = pack
        self.duplicate_key = duplicate_key
        self.missing_key = missing_key
        self.omit_source = omit_source
        self.parents: dict[str, dict] = {}
        self.edges: dict[str, list[dict]] = {}
        self.statements: list[str] = []
        self.next_id = 0

    def transaction(self):
        return nullcontext()

    def cursor(self):
        return _StageCursor(self)


class _StageCursor:
    def __init__(self, connection: _StageConnection):
        self.connection = connection
        self.rows: list[dict] = []
        self.one: dict | None = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql: str, params=()):
        connection = self.connection
        connection.statements.append(sql)
        self.rows = []
        self.one = None
        if "FROM knowledge.destinations" in sql:
            keys = params[0]
            rows = [
                {"destination_id": i + 1, "destination_key": key}
                for i, key in enumerate(item.record_key for item in connection.pack.spatial_entities)
                if key in keys and key != connection.missing_key
            ]
            self.rows = rows + ([dict(rows[0])] if rows and connection.duplicate_key else [])
        elif "FROM knowledge.knowledge_sources" in sql:
            self.rows = [
                {"source_id": i + 1, "url": source.url}
                for i, source in enumerate(connection.pack.source_register)
                if source.url != connection.omit_source
            ]
        elif sql.startswith("SELECT") and "payload_sha256" in sql:
            self.one = connection.parents.get(str(params[0]))
        elif sql.startswith("SELECT") and "claim_key, source_key, source_id" in sql:
            self.rows = connection.edges.get(str(params[0]), [])
        elif sql.startswith("INSERT INTO knowledge.destination_enrichment_proposals"):
            connection.next_id += 1
            proposal_id = f"proposal-{connection.next_id}"
            self.one = {"proposal_id": proposal_id}
            connection.parents[str(params[0])] = {
                "proposal_id": proposal_id,
                "proposal_key": params[0],
                "payload_sha256": params[-1],
                "review_status": "needs_review",
                "publishable": False,
                "is_synthetic": False,
            }

    def executemany(self, sql: str, values):
        self.connection.statements.append(sql)
        for params in values:
            parent_id, *edge = params
            self.connection.edges.setdefault(str(parent_id), []).append(
                dict(zip(
                    ("claim_key", "source_key", "source_id", "source_name", "source_url",
                     "source_license", "source_role", "evidence_note", "retrieved_at",
                     "valid_from", "valid_until"), edge
                ))
            )

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.one


def test_addendum_import_is_insert_only_retry_safe_and_source_snapshotted() -> None:
    pack = load_content_addendum(ADDENDUM_PATH)
    connection = _StageConnection(pack, omit_source=pack.source_register[0].url)
    first = stage_review_content_addendum(connection, BATCH_ID, pack)
    assert first == {"inserted": 4, "unchanged": 0}
    assert len(connection.parents) == 4
    assert any(edge["source_id"] is None for group in connection.edges.values() for edge in group)
    writes = [sql for sql in connection.statements if sql.lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))]
    assert writes
    assert all("knowledge.destinations" not in sql and "knowledge.knowledge_sources" not in sql for sql in writes)
    assert all("destination_enrichment_proposals" in sql or "destination_enrichment_proposal_sources" in sql for sql in writes)
    destination_lookup = next(sql for sql in connection.statements if "FROM knowledge.destinations" in sql)
    assert "WHERE destination_key = ANY(%s::TEXT[])" in destination_lookup
    assert "FOR UPDATE" not in destination_lookup.upper()
    assert "FOR KEY SHARE" not in destination_lookup.upper()
    proposal_reads = [
        sql for sql in connection.statements
        if sql.lstrip().upper().startswith("SELECT") and "payload_sha256" in sql
    ]
    proposal_inserts = [
        sql for sql in connection.statements
        if sql.lstrip().upper().startswith("INSERT INTO KNOWLEDGE.DESTINATION_ENRICHMENT_PROPOSALS")
    ]
    assert proposal_reads and all("FOR UPDATE" not in sql.upper() for sql in proposal_reads)
    assert proposal_inserts and all("ON CONFLICT" in sql.upper() and "DO NOTHING" in sql.upper() for sql in proposal_inserts)
    assert stage_review_content_addendum(connection, BATCH_ID, pack) == {"inserted": 0, "unchanged": 4}
    changed = pack.model_copy(deep=True)
    changed.spatial_entities[0].editorial_notes[0] += " changed"
    with pytest.raises(ValueError, match="different content"):
        stage_review_content_addendum(connection, BATCH_ID, changed)


def test_addendum_import_aborts_all_writes_on_missing_or_duplicate_destination() -> None:
    pack = load_content_addendum(ADDENDUM_PATH)
    for kwargs in ({"missing_key": "shiraz-naqsh-e-rostam-v1"}, {"duplicate_key": True}):
        connection = _StageConnection(pack, **kwargs)
        with pytest.raises(ValueError):
            stage_review_content_addendum(connection, BATCH_ID, connection.pack)
        assert connection.next_id == 0
        assert not connection.parents


def test_addendum_payload_hash_is_stable_and_provenance_sensitive() -> None:
    value = {"proposal": {"name": "Garden"}, "source": {"url": "https://example.test/a"}}
    first = addendum_payload_hash(value)
    assert first == addendum_payload_hash(deepcopy(value))
    value["source"]["url"] = "https://example.test/b"
    assert addendum_payload_hash(value) != first
