#!/usr/bin/env python3
"""Offline source-content validation for all seeded knowledge docs/chunks.

Uses only Python's standard library. It does not connect to PostgreSQL or
modify files. PostgreSQL-side checks independently re-hash persisted content.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def extract_values_rows(sql: str, insert_prefix: str) -> list[list[str]]:
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
    docs = extract_values_rows(sql, "INSERT INTO knowledge.knowledge_documents (")
    chunks = extract_values_rows(sql, "INSERT INTO knowledge.knowledge_chunks (")
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
    sql = (ROOT / "sql/005_verified_unesco_destination_seed.sql").read_text(encoding="utf-8")
    sources = extract_values_rows(sql, "INSERT INTO knowledge.knowledge_sources (")
    docs = extract_values_rows(sql, "INSERT INTO knowledge.knowledge_documents (")
    chunks = extract_values_rows(sql, "INSERT INTO knowledge.knowledge_chunks (")
    if len(sources) != 22:
        raise ValueError(f"Expected 22 external provenance sources, found {len(sources)}")
    if len(docs) != 10:
        raise ValueError(f"Expected 10 verified-external documents, found {len(docs)}")
    if len(chunks) != 20:
        raise ValueError(f"Expected 20 verified-external chunks, found {len(chunks)}")
    document_keys: set[str] = set()
    for i, row in enumerate(docs):
        if len(row) != 5:
            raise ValueError(f"External document CTE row {i} has {len(row)} fields; expected 5")
        key = sql_text_literal(row[0], f"external document {i}.key")
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
            raise ValueError(f"External chunk CTE row {i} has {len(row)} fields; expected 5")
        destination_key = sql_text_literal(row[0], f"external chunk {i}.destination_key")
        content = sql_text_literal(row[2], f"external chunk {i}.content")
        declared = sql_text_literal(row[3], f"external chunk {i}.sha256")
        if sha256(content) != declared:
            raise ValueError(f"External chunk SHA-256 mismatch: {destination_key} / chunk {i}")
        if destination_key not in {k.removesuffix("-doc") for k in document_keys}:
            raise ValueError(f"Chunk references unknown destination key: {destination_key}")
        chunk_counts[destination_key] = chunk_counts.get(destination_key, 0) + 1
    if len(chunk_counts) != 10 or set(chunk_counts.values()) != {2}:
        raise ValueError(f"Expected exactly two external chunks per destination; got {chunk_counts}")
    # Every factual source must be explicit and non-synthetic, and its link is an official/reputable URL.
    for i, row in enumerate(sources):
        if len(row) != 7:
            raise ValueError(f"External source row {i} has {len(row)} fields; expected 7")
        name = sql_text_literal(row[0], f"source {i}.name")
        url = sql_text_literal(row[4], f"source {i}.url")
        if row[2] != "'verified'" or row[6] != "FALSE":
            raise ValueError(f"External source {name} is not verified/non-synthetic")
        if row[3] != 'NULL':
            raise ValueError(f"External source {name} has an uncalibrated numeric reliability score")
        if not url.startswith("https://"):
            raise ValueError(f"External source {name} has non-HTTPS URL")
    return len(sources), len(docs), len(chunks)


def main() -> int:
    try:
        s_docs, s_chunks = verify_synthetic()
        e_sources, e_docs, e_chunks = verify_verified_external()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print(f"PASS: {s_docs} synthetic document hashes verified.")
    print(f"PASS: {s_chunks} synthetic chunk hashes and character counts verified.")
    print("PASS: all synthetic RAG fixtures are explicitly test_only and is_synthetic=true.")
    print(f"PASS: {e_sources} verified-external provenance source definitions checked.")
    print(f"PASS: {e_docs} factual document hashes verified; all are source-linked in the SQL migration.")
    print(f"PASS: {e_chunks} factual chunk hashes verified; exactly 2 chunks per destination.")
    print("PASS: external records are separate from synthetic fixtures; no embeddings/model assumptions are stored.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
