#!/usr/bin/env python3
"""Fail-closed validation for the sanitized Rahgard schema documentation package."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "docs/database/live-schema/catalog_snapshot.json"
DESCRIPTIONS = ROOT / "docs/database/field_descriptions.json"
MANIFEST = ROOT / "docs/database/live-schema/manifest.json"
DOC_ROOT = ROOT / "docs/database/live-schema"
REQUIRED = {
    "meaning", "resolution", "accepted_format_units_enums", "source_evidence",
    "sensitivity", "owner", "read_surface", "write_surface",
}
EXTENSION_OBJECTS = {
    ("public", "spatial_ref_sys"),
    ("public", "geometry_columns"),
    ("public", "geography_columns"),
}


def fail(message: str) -> None:
    raise ValueError(message)


def main() -> int:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    descriptions = json.loads(DESCRIPTIONS.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if snapshot.get("scope") != "authorized-rahgard-databases-only":
        fail("snapshot scope is not the authorized Rahgard namespace")
    discovered = set(snapshot.get("discovered_non_template_databases", []))
    attempted = set(snapshot.get("databases_attempted", []))
    skipped = {row.get("database") for row in snapshot.get("databases_skipped", [])}
    inaccessible = {row.get("database") for row in snapshot.get("databases_inaccessible", [])}
    if discovered != attempted | skipped | inaccessible:
        fail("database inventory is not fully accounted for")
    if attempted & skipped or attempted & inaccessible or skipped & inaccessible:
        fail("database inventory classifications overlap")
    if manifest.get("databases_discovered_non_template") != snapshot.get("discovered_non_template_databases"):
        fail("manifest database discovery differs from source snapshot")
    if manifest.get("database_inventory_complete") is not True:
        fail("manifest does not confirm complete inventory classification")
    canonical_hash = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if manifest.get("source_snapshot_sha256") != canonical_hash:
        fail("manifest snapshot checksum does not match snapshot")
    relation_ids = set()
    total_fields = unresolved = 0
    source_errors: list[str] = []
    for rel in snapshot.get("relations", []):
        schema, table = rel["relation"]["schema"], rel["relation"]["name"]
        db = rel["database"]
        key = f"{db}.{schema}.{table}"
        if key in relation_ids:
            fail(f"duplicate relation identity: {key}")
        relation_ids.add(key)
        metadata = descriptions.get(key, {}).get("_field_metadata", {})
        matching = [x for x in manifest.get("relations", []) if
                    (x.get("database"), x.get("schema"), x.get("name")) == (db, schema, table)]
        if len(matching) != 1:
            fail(f"manifest relation coverage mismatch: {key}")
        rel_doc = DOC_ROOT / matching[0]["path"]
        if not rel_doc.is_file():
            fail(f"missing generated relation document: {key}")
        rendered = rel_doc.read_text(encoding="utf-8")
        for col in rel.get("columns", []):
            total_fields += 1
            spec = metadata.get(col["name"])
            if not isinstance(spec, dict) or not REQUIRED.issubset(spec):
                fail(f"incomplete field metadata: {key}.{col['name']}")
            if not spec.get("meaning") or not spec.get("accepted_format_units_enums"):
                fail(f"empty field meaning/format: {key}.{col['name']}")
            evidence = spec.get("source_evidence")
            if not isinstance(evidence, list) or not evidence:
                fail(f"missing field evidence: {key}.{col['name']}")
            for source in evidence:
                if source.startswith("https://"):
                    continue
                if not (ROOT / source).is_file():
                    source_errors.append(f"{key}.{col['name']} -> {source}")
            if spec["resolution"] == "unresolved":
                unresolved += 1
            elif spec["resolution"] != "resolved":
                fail(f"invalid field resolution: {key}.{col['name']}")
            if col["name"] not in rendered or col["pg_type"] not in rendered:
                fail(f"generated document missing column/type: {key}.{col['name']}")
        is_extension = (schema, table) in EXTENSION_OBJECTS
        expected_owner = "extension" if is_extension else "application"
        actual_owner = "extension" if matching[0].get("object_owner") == "extension" else "application"
        if expected_owner != actual_owner:
            fail(f"extension/application ownership classification mismatch: {key}")
    if source_errors:
        fail("field metadata references missing source files: " + "; ".join(source_errors[:10]))
    if manifest.get("field_metadata_coverage") != {"total": total_fields, "complete": total_fields, "missing": 0}:
        fail("manifest field metadata totals do not match snapshot")
    if manifest.get("missing_field_descriptions") != unresolved:
        fail("manifest unresolved-field count does not match dictionary")
    if manifest.get("complete") != (not inaccessible and unresolved == 0 and manifest.get("database_inventory_complete") is True):
        fail("manifest completeness flag is not supported by its coverage evidence")
    print(json.dumps({"result": "PASS", "databases_discovered": len(discovered),
                      "databases_attempted": len(attempted), "databases_skipped": len(skipped),
                      "databases_inaccessible": len(inaccessible), "relations": len(relation_ids),
                      "fields": total_fields, "unresolved_fields": unresolved,
                      "extension_relations": sum(1 for r in snapshot["relations"] if
                          (r["relation"]["schema"], r["relation"]["name"]) in EXTENSION_OBJECTS),
                      "snapshot_sha256": canonical_hash}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"SCHEMA_DOCUMENTATION_VALIDATION_FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
