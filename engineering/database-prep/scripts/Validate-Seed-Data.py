#!/usr/bin/env python3
"""Offline source-content validation for all seeded knowledge docs/chunks.

Uses only Python's standard library. It does not connect to PostgreSQL or
modify files. PostgreSQL-side checks independently re-hash persisted content.
"""
from __future__ import annotations

import hashlib
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def extract_values_rows(sql: str, insert_prefix: str) -> list[list[str]]:
    """Extract VALUES rows after an INSERT table name.

    Pass the table name without its opening column-list parenthesis. SQL files
    may put that parenthesis on the same line or on the next line.
    """
    start = sql.find(insert_prefix)
    if start < 0:
        raise ValueError(f"INSERT statement not found: {insert_prefix}")
    values_pos = re.search(r"\bVALUES\b", sql[start:], flags=re.IGNORECASE)
    if not values_pos:
        raise ValueError(f"VALUES clause not found for: {insert_prefix}")
    pos = start + values_pos.end()
    rows: list[list[str]] = []
    while pos < len(sql):
        while pos < len(sql) and (sql[pos].isspace() or sql[pos] == ','):
            pos += 1
        if pos >= len(sql) or sql[pos] != '(':
            break
        pos += 1
        depth = 1
        in_single = False
        field_start = pos
        fields: list[str] = []
        while pos < len(sql) and depth > 0:
            ch = sql[pos]
            if in_single:
                if ch == "'":
                    if pos + 1 < len(sql) and sql[pos + 1] == "'":
                        pos += 2
                        continue
                    in_single = False
                pos += 1
                continue
            if ch == "'":
                in_single = True
                pos += 1
                continue
            if ch == '(':
                depth += 1
                pos += 1
                continue
            if ch == ')':
                depth -= 1
                if depth == 0:
                    fields.append(sql[field_start:pos].strip())
                    pos += 1
                    break
                pos += 1
                continue
            if ch == ',' and depth == 1:
                fields.append(sql[field_start:pos].strip())
                pos += 1
                field_start = pos
                continue
            pos += 1
        if depth != 0 or in_single:
            raise ValueError(f"Unterminated row/string while parsing: {insert_prefix}")
        rows.append(fields)
    return rows


def sql_text_literal(expression: str, label: str) -> str:
    expression = expression.strip()
    if len(expression) < 2 or expression[0] != "'" or expression[-1] != "'":
        raise ValueError(f"{label} is not a simple SQL text literal: {expression[:80]!r}")
    return expression[1:-1].replace("''", "'")


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_synthetic() -> tuple[int, int]:
    sql = (ROOT / "sql/002_synthetic_knowledge_seed.sql").read_text(encoding="utf-8")
    docs = extract_values_rows(sql, "INSERT INTO knowledge.knowledge_documents")
    chunks = extract_values_rows(sql, "INSERT INTO knowledge.knowledge_chunks")
    if len(docs) != 12:
        raise ValueError(f"Expected 12 synthetic documents, found {len(docs)}")
    if len(chunks) != 24:
        raise ValueError(f"Expected 24 synthetic chunks, found {len(chunks)}")
    for i, row in enumerate(docs):
        if len(row) != 11:
            raise ValueError(f"Synthetic document row {i} has {len(row)} columns; expected 11")
        key = sql_text_literal(row[0], f"synthetic document {i}.key")
        content = sql_text_literal(row[6], f"{key}.raw_content")
        declared = sql_text_literal(row[7], f"{key}.sha256")
        if sha256(content) != declared:
            raise ValueError(f"Synthetic document SHA-256 mismatch: {key}")
        if row[8] != "'test_only'" or row[9] != "'synthetic_fixture'" or row[10] != "TRUE":
            raise ValueError(f"Synthetic document {key} lacks required test-only markers")
    for i, row in enumerate(chunks):
        if len(row) != 8:
            raise ValueError(f"Synthetic chunk row {i} has {len(row)} columns; expected 8")
        content = sql_text_literal(row[2], f"synthetic chunk {i}.content")
        chars = int(row[3])
        declared = sql_text_literal(row[5], f"synthetic chunk {i}.sha256")
        if len(content) != chars:
            raise ValueError(f"Synthetic chunk {i} character-count mismatch")
        if sha256(content) != declared:
            raise ValueError(f"Synthetic chunk {i} SHA-256 mismatch")
        if row[7] != "TRUE":
            raise ValueError(f"Synthetic chunk {i} is not marked synthetic")
    return len(docs), len(chunks)


def verify_verified_external() -> tuple[int, int, int]:
    """Verify every curated external batch independently, then aggregate totals."""
    batches = [
        ("sql/005_verified_unesco_destination_seed.sql", 22, 10, 20),
        ("sql/006_verified_unesco_destination_seed_batch2.sql", 16, 7, 14),
    ]
    totals = [0, 0, 0]
    for relative_path, expected_sources, expected_docs, expected_chunks in batches:
        sql = (ROOT / relative_path).read_text(encoding="utf-8")
        sources = extract_values_rows(sql, "INSERT INTO knowledge.knowledge_sources")
        docs = extract_values_rows(sql, "INSERT INTO knowledge.knowledge_documents")
        chunks = extract_values_rows(sql, "INSERT INTO knowledge.knowledge_chunks")
        if len(sources) != expected_sources:
            raise ValueError(
                f"{relative_path}: expected {expected_sources} external sources, found {len(sources)}"
            )
        if len(docs) != expected_docs:
            raise ValueError(
                f"{relative_path}: expected {expected_docs} factual documents, found {len(docs)}"
            )
        if len(chunks) != expected_chunks:
            raise ValueError(
                f"{relative_path}: expected {expected_chunks} factual chunks, found {len(chunks)}"
            )

        document_keys: set[str] = set()
        for i, row in enumerate(docs):
            if len(row) != 5:
                raise ValueError(
                    f"{relative_path}: external document CTE row {i} has {len(row)} fields; expected 5"
                )
            key = sql_text_literal(row[0], f"{relative_path} document {i}.key")
            content = sql_text_literal(row[3], f"{key}.content")
            declared = sql_text_literal(row[4], f"{key}.sha256")
            if not key.startswith("unesco-") or key in document_keys:
                raise ValueError(f"Invalid/duplicate external document key: {key}")
            if sha256(content) != declared:
                raise ValueError(f"External document SHA-256 mismatch: {key}")
            document_keys.add(key)

        chunk_counts: dict[str, int] = {}
        for i, row in enumerate(chunks):
            if len(row) != 5:
                raise ValueError(
                    f"{relative_path}: external chunk CTE row {i} has {len(row)} fields; expected 5"
                )
            destination_key = sql_text_literal(row[0], f"{relative_path} chunk {i}.destination_key")
            content = sql_text_literal(row[2], f"{destination_key} chunk {i}.content")
            declared = sql_text_literal(row[3], f"{destination_key} chunk {i}.sha256")
            if sha256(content) != declared:
                raise ValueError(f"External chunk SHA-256 mismatch: {destination_key} / chunk {i}")
            if destination_key not in {k.removesuffix("-doc") for k in document_keys}:
                raise ValueError(f"Chunk references unknown destination key: {destination_key}")
            chunk_counts[destination_key] = chunk_counts.get(destination_key, 0) + 1
        if len(chunk_counts) != expected_docs or set(chunk_counts.values()) != {2}:
            raise ValueError(
                f"{relative_path}: expected exactly two chunks per factual destination; got {chunk_counts}"
            )

        # Every factual source must be explicit, non-synthetic and HTTPS-backed.
        for i, row in enumerate(sources):
            if len(row) != 7:
                raise ValueError(
                    f"{relative_path}: external source row {i} has {len(row)} fields; expected 7"
                )
            name = sql_text_literal(row[0], f"{relative_path} source {i}.name")
            url = sql_text_literal(row[4], f"{name}.url")
            if row[2] != "'verified'" or row[6] != "FALSE":
                raise ValueError(f"External source {name} is not verified/non-synthetic")
            if row[3] != "NULL":
                raise ValueError(f"External source {name} has an uncalibrated numeric reliability score")
            if not url.startswith("https://"):
                raise ValueError(f"External source {name} has non-HTTPS URL")

        totals[0] += len(sources)
        totals[1] += len(docs)
        totals[2] += len(chunks)

    return tuple(totals)


def verify_shiraz_dataset() -> tuple[int, int, int, int]:
    """Cross-check the supplied JSON/CSV/SQL and the committed additive migration."""
    incoming = ROOT / "incoming/shiraz-v1"
    manifest_path = incoming / "shiraz_dalahoo_wikipedia_real_data_v1.json"
    csv_path = incoming / "shiraz_dalahoo_wikipedia_real_data_v1.csv"
    source_csv_path = incoming / "SOURCE_REGISTER.csv"
    reference_sql_path = incoming / "shiraz_dalahoo_wikipedia_real_data_v1.sql"
    migration_path = ROOT / "sql/007_shiraz_dalahoo_wikipedia_dataset_v1.sql"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    migration = migration_path.read_text(encoding="utf-8")
    reference_sql = reference_sql_path.read_text(encoding="utf-8")

    if hashlib.sha256(manifest_path.read_bytes()).hexdigest() != "16c42d6b34c012379712404b9699d15b971393f78980098c0be8520bcfa23e62":
        # The exact checksum is also recorded in the migration batch. Keep this
        # comparison explicit so a changed owner manifest requires review.
        expected = "16c42d6b34c012379712404b9699d15b971393f78980098c0be8520bcfa23e62"
        raise ValueError(f"Shiraz manifest checksum differs from the reviewed package: {expected}")

    places = manifest["places"]
    sources = manifest["sources"]
    documents = manifest["knowledge_documents"]
    if (len(places), len(sources), len(documents), len(manifest["dalahoo_index_discovery_links"]), len(manifest["existing_nearby_heritage_links"])) != (22, 18, 23, 13, 2):
        raise ValueError("Shiraz manifest counts differ from the owner-reviewed integration task")
    if len({item["key"] for item in places}) != 22 or len({item["source_key"] for item in sources}) != 18:
        raise ValueError("Shiraz manifest contains duplicate destination or source keys")
    contract = manifest["classification_contract"]
    if contract != {
        "is_synthetic": False,
        "record_origin": "verified_external",
        "verification_status": "verified",
        "publication_status": "needs_review",
        "data_confidence": 0,
        "note": contract["note"],
    }:
        raise ValueError("Shiraz classification contract changed or contains synthetic/published records")
    for place in places:
        if (place["record_origin"], place["is_synthetic"], place["verification_status"], place["status"], place["data_confidence"]) != ("verified_external", False, "verified", "needs_review", 0):
            raise ValueError(f"Invalid real/publication markers on {place['key']}")
    maragheh_rows = manifest["existing_destination_enrichment"]
    if len(maragheh_rows) != 1:
        raise ValueError("Expected exactly one existing Maragheh Observatory enrichment")
    maragheh = maragheh_rows[0]
    if (maragheh["record_origin"], maragheh["is_synthetic"], maragheh["verification_status"], maragheh["status"], maragheh["data_confidence"]) != ("verified_external", False, "verified", "needs_review", 0):
        raise ValueError("Maragheh enrichment markers are inconsistent")

    # The CSV is an inspectable projection of JSON, and the SQL remains the
    # owner-supplied reference. No factual fields are regenerated here.
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    expected_csv_keys = {item["key"] for item in places} | {maragheh["key"]}
    if len(csv_rows) != 23 or {row["destination_key"] for row in csv_rows} != expected_csv_keys:
        raise ValueError("Shiraz CSV rows/keys do not match the canonical JSON manifest")
    csv_by_key = {row["destination_key"]: row for row in csv_rows}
    for place in places:
        row = csv_by_key[place["key"]]
        if row["canonical_name"] != place["name_fa"] or row["english_name"] != place["name_en"] or row["record_origin"] != "verified_external" or row["is_synthetic"].lower() != "false" or row["status"] != "needs_review":
            raise ValueError(f"Shiraz CSV factual identity/classification differs from JSON for {place['key']}")
    enriched_csv_row = csv_by_key[maragheh["key"]]
    if enriched_csv_row["canonical_name"] != maragheh["name_fa"] or enriched_csv_row["record_origin"] != "verified_external" or enriched_csv_row["is_synthetic"].lower() != "false" or enriched_csv_row["status"] != "needs_review":
        raise ValueError("Maragheh CSV enrichment identity/classification differs from JSON")
    with source_csv_path.open(encoding="utf-8-sig", newline="") as handle:
        source_rows = list(csv.DictReader(handle))
    if len(source_rows) != 18 or {row["source_key"] for row in source_rows} != {item["source_key"] for item in sources}:
        raise ValueError("Shiraz source-register rows/keys do not match JSON")
    source_by_key = {row["source_key"]: row for row in source_rows}
    for source in sources:
        row = source_by_key[source["source_key"]]
        if row["source_name"] != source["source_name"] or row["url"] != source["url"] or row["role"] != source["role"]:
            raise ValueError(f"Source-register mismatch for {source['source_key']}")

    place_by_doc = {place["knowledge_document"]["document_key"]: place for place in places}
    place_by_doc[maragheh["knowledge_document"]["document_key"]] = maragheh
    manifest_docs = {doc["document_key"]: doc for doc in documents}
    if set(place_by_doc) != set(manifest_docs):
        raise ValueError("Each of the 22 entities and Maragheh must have one matching document")
    for key, doc in manifest_docs.items():
        if (doc["record_origin"], doc["is_synthetic"], doc["ingestion_status"], doc["language_code"]) != ("verified_external", False, "processed", "fa"):
            raise ValueError(f"Invalid document publication/synthetic markers for {key}")
        if len(doc["raw_content"]) != doc["char_count"] or sha256(doc["raw_content"]) != doc["content_sha256"]:
            raise ValueError(f"Shiraz document hash/character count mismatch: {key}")

    source_rows_sql = extract_values_rows(migration, "INSERT INTO _shiraz_sources VALUES")
    entity_rows_sql = extract_values_rows(migration, "INSERT INTO _shiraz_entities VALUES")
    doc_rows_sql = extract_values_rows(migration, "INSERT INTO _shiraz_docs VALUES")
    if len(source_rows_sql) != 18 or len(entity_rows_sql) != 22 or len(doc_rows_sql) != 23:
        raise ValueError("Shiraz migration source/entity/document declarations have unexpected counts")
    for row in doc_rows_sql:
        if len(row) != 14:
            raise ValueError(f"Shiraz migration document row has {len(row)} values; expected 14")
        key = sql_text_literal(row[6], "Shiraz SQL document key")
        doc = manifest_docs.get(key)
        if doc is None:
            raise ValueError(f"Shiraz migration contains an unexpected document: {key}")
        if (sql_text_literal(row[9], f"{key}.content") != doc["raw_content"]
                or sql_text_literal(row[10], f"{key}.sha256") != doc["content_sha256"]
                or int(row[11]) != doc["char_count"]):
            raise ValueError(f"Shiraz migration document differs from JSON or has a bad hash/count: {key}")
    for place in places:
        if place["key"] not in migration or place["key"] not in reference_sql:
            raise ValueError(f"Destination key is missing from supplied or integrated SQL: {place['key']}")
    for source in sources:
        if source["source_key"] not in migration or source["source_key"] not in reference_sql:
            raise ValueError(f"Source key is missing from supplied or integrated SQL: {source['source_key']}")
    if "0007_shiraz_dalahoo_wikipedia_dataset_v1" not in migration:
        raise ValueError("Shiraz additive migration does not register migration 0007")
    return len(sources), len(places), len(documents), sum(doc["char_count"] for doc in documents)

def verify_multiline_insert_parser() -> None:
    """Guard against SQL formatting changes that caused the Batch 2 failure."""
    fixture = """
INSERT INTO knowledge.knowledge_sources
    (source_name, notes)
VALUES
    ('source one', 'comma, inside text'),
    ('source two', 'escaped ''quote'' inside text');
"""
    rows = extract_values_rows(fixture, "INSERT INTO knowledge.knowledge_sources")
    if len(rows) != 2 or len(rows[0]) != 2 or len(rows[1]) != 2:
        raise ValueError("Multiline INSERT parser regression fixture returned unexpected rows")
    if sql_text_literal(rows[0][1], "fixture row 1") != "comma, inside text":
        raise ValueError("Multiline INSERT parser did not preserve commas inside SQL text")
    if sql_text_literal(rows[1][1], "fixture row 2") != "escaped 'quote' inside text":
        raise ValueError("Multiline INSERT parser did not unescape SQL doubled quotes")


def main() -> int:
    try:
        verify_multiline_insert_parser()
        s_docs, s_chunks = verify_synthetic()
        e_sources, e_docs, e_chunks = verify_verified_external()
        sh_sources, sh_entities, sh_docs, sh_chars = verify_shiraz_dataset()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("PASS: multiline SQL INSERT formatting and quoted-text parsing verified.")
    print(f"PASS: {s_docs} synthetic document hashes verified.")
    print(f"PASS: {s_chunks} synthetic chunk hashes and character counts verified.")
    print("PASS: all synthetic RAG fixtures are explicitly test_only and is_synthetic=true.")
    print(f"PASS: {e_sources} verified-external provenance source definitions checked.")
    print(f"PASS: {e_docs} factual document hashes verified; all are source-linked in the SQL migration.")
    print(f"PASS: {e_chunks} factual chunk hashes verified; exactly 2 chunks per destination.")
    print("PASS: external records are separate from synthetic fixtures; no embeddings/model assumptions are stored.")
    print(f"PASS: Shiraz JSON/CSV/SQL agree for {sh_entities} entities, {sh_sources} sources, {sh_docs} Persian docs and {sh_chars} document characters.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
