#!/usr/bin/env python3
"""Validate schema occurrence, lineage, and documentation-gap accounting.

This validator rejects claims that catalogued columns are validated business
requirements. It verifies object/column matrices against the sanitized
pg_catalog snapshot and preserves unknown meanings as unknown.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "docs/database/live-schema/catalog_snapshot.json"
GLOSSARY = ROOT / "docs/database/field_descriptions.json"
MANIFEST = ROOT / "docs/database/live-schema/manifest.json"
DOC_ROOT = ROOT / "docs/database/live-schema"
AUDIT = ROOT / "docs/database/architecture-usage"
CATALOG_METADATA = DOC_ROOT / "catalog_metadata_snapshot.json"
REQUIRED_MATRIX_FILES = [
    "object_decision_matrix.csv", "column_occurrence_matrix.csv", "view_column_lineage.csv",
    "foreign_key_edges.csv", "api_dependency_map.csv", "coverage_by_schema.csv", "glossary_coverage.json",
]
EXTENSION_OBJECTS = {
    ("public", "spatial_ref_sys"), ("public", "geometry_columns"), ("public", "geography_columns"),
}


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def fail(message: str) -> None:
    raise ValueError(message)


def main() -> int:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    glossary = json.loads(GLOSSARY.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if snapshot.get("scope") != "authorized-rahgard-databases-only":
        fail("snapshot scope is not the authorized Rahgard namespace")
    discovered = set(snapshot.get("discovered_non_template_databases", []))
    attempted = set(snapshot.get("databases_attempted", []))
    skipped = {row.get("database") for row in snapshot.get("databases_skipped", [])}
    inaccessible = {row.get("database") for row in snapshot.get("databases_inaccessible", [])}
    if discovered != attempted | skipped | inaccessible or attempted & skipped or attempted & inaccessible or skipped & inaccessible:
        fail("database inventory accounting overlaps or omits a discovered database")
    if manifest.get("database_inventory_complete") is not True:
        fail("authorized Rahgard namespace inventory is not accounted for")
    if manifest.get("complete") is not False or manifest.get("architecture_usage_review", {}).get("business_necessity_approved") is not False:
        fail("manifest overstates architecture/business-field approval")
    canonical_hash = hashlib.sha256(
        json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if manifest.get("source_snapshot_sha256") != canonical_hash:
        fail("manifest snapshot checksum mismatch")
    catalog_metadata = json.loads(CATALOG_METADATA.read_text(encoding="utf-8"))
    catalog_metadata_hash = hashlib.sha256(CATALOG_METADATA.read_bytes()).hexdigest()
    if manifest.get("catalog_metadata_snapshot_sha256") != catalog_metadata_hash:
        fail("manifest catalog metadata snapshot checksum mismatch")
    if catalog_metadata.get("database") != snapshot["database_identity"]["database"] or catalog_metadata.get("role") != snapshot.get("database_role"):
        fail("catalog metadata snapshot database identity mismatch")

    snapshot_objects = {}
    expected_columns = {}
    view_relations = set()
    for rel in snapshot.get("relations", []):
        schema, name, kind = rel["relation"]["schema"], rel["relation"]["name"], rel["relation"]["kind"]
        key = (rel["database"], schema, name)
        if key in snapshot_objects:
            fail(f"duplicate catalog object: {key}")
        snapshot_objects[key] = rel
        if kind in {"v", "m"}:
            view_relations.add(key)
        for col in rel["columns"]:
            expected_columns[(rel["database"], schema, name, col["name"])] = col
    table_count = sum(1 for x in snapshot_objects.values() if x["relation"]["kind"] in {"r", "p"})
    view_count = sum(1 for x in snapshot_objects.values() if x["relation"]["kind"] in {"v", "m"})
    if (len(snapshot_objects), table_count, view_count, len(expected_columns)) != (101, 87, 14, 1106):
        fail("catalog occurrence counts differ from recorded audit baseline")
    if manifest.get("relation_count") != len(snapshot_objects) or manifest.get("catalog_counts", {}).get("column_occurrences") != len(expected_columns):
        fail("manifest catalog counts disagree with snapshot")

    baseline_described = 0
    for db, schema, relation, column in expected_columns:
        meaning = glossary.get(f"{schema}.{relation}", {}).get(column)
        if isinstance(meaning, str) and meaning.strip():
            baseline_described += 1
    baseline_missing = len(expected_columns) - baseline_described
    if (baseline_described, baseline_missing) != (230, 876):
        fail(f"baseline glossary arithmetic changed unexpectedly: {baseline_described}/{len(expected_columns)}")
    coverage = manifest.get("baseline_glossary_coverage", {})
    if coverage.get("described_occurrences") != baseline_described or coverage.get("undocumented_occurrences") != baseline_missing or coverage.get("distinct_business_requirement_count") is not None:
        fail("manifest incorrectly counts descriptions as distinct business requirements")

    missing_files = [name for name in REQUIRED_MATRIX_FILES if not (AUDIT / name).is_file()]
    if missing_files:
        fail("missing architecture/coverage artifacts: " + ", ".join(missing_files))
    objects = load_csv(AUDIT / "object_decision_matrix.csv")
    columns = load_csv(AUDIT / "column_occurrence_matrix.csv")
    lineage = load_csv(AUDIT / "view_column_lineage.csv")
    fk_edges = load_csv(AUDIT / "foreign_key_edges.csv")
    api_map = load_csv(AUDIT / "api_dependency_map.csv")
    if len(objects) != len(snapshot_objects) or len({(r["database"], r["schema"], r["relation"]) for r in objects}) != len(objects):
        fail("object matrix is incomplete or has duplicate relation rows")
    object_keys = {(r["database"], r["schema"], r["relation"]) for r in objects}
    if object_keys != set(snapshot_objects):
        fail("object matrix relation identities differ from snapshot")
    if any(not row.get("database_owner") or row["database_owner"] == "not captured" for row in objects):
        fail("a PostgreSQL relation owner is missing")
    allowed_decisions = {"KEEP", "CONSOLIDATE-LATER", "LEGACY-COMPAT", "EXTENSION-MANAGED", "INVESTIGATE"}
    if any(row["decision"] not in allowed_decisions for row in objects):
        fail("object matrix has an invalid disposition")
    if any(row["data_row_origin_assessment"].startswith("not assessed") is False for row in objects):
        fail("matrix must not infer row-level legacy/synthetic origin without reading rows")
    manifest_relations = {(row["database"], row["schema"], row["name"]): row for row in manifest.get("relations", [])}
    if set(manifest_relations) != object_keys:
        fail("manifest relation inventory differs from object matrix")
    for row in objects:
        key = (row["database"], row["schema"], row["relation"])
        if manifest_relations[key].get("database_owner") != row["database_owner"]:
            fail(f"manifest database owner differs from read-only metadata: {key}")

    column_keys = {(r["database"], r["schema"], r["relation"], r["column_name"]) for r in columns}
    if len(columns) != len(expected_columns) or column_keys != set(expected_columns):
        fail("column occurrence matrix is incomplete or has duplicate/missing column identities")
    for row in columns:
        key = (row["database"], row["schema"], row["relation"], row["column_name"])
        source = expected_columns[key]
        if row["pg_type"] != source["pg_type"] or row["nullable"] != str(not source["notnull"]):
            fail(f"column storage metadata mismatch: {key}")
        if not row["source_evidence"] or "not privacy-owner sign-off" not in row["sensitivity_basis"]:
            fail(f"missing evidence or provisional sensitivity qualifier: {key}")
        if (row["schema"], row["relation"]) in EXTENSION_OBJECTS and row["glossary_status"] != "official_extension_reference":
            fail(f"extension field incorrectly treated as business glossary: {key}")
        if row["relation_kind"] in {"v", "m"} and row["necessity_status"] != "derived_projection_not_independent_attribute":
            fail(f"derived view field incorrectly treated as independent attribute: {key}")
        if (row["schema"], row["relation"]) in EXTENSION_OBJECTS and row["origin_class"] != "extension_managed":
            fail(f"PostgreSQL/PostGIS relation is not classified as extension-managed: {key}")
        if (row["schema"], row["relation"]) in EXTENSION_OBJECTS and "postgis.net/docs/" not in row["source_evidence"]:
            fail(f"extension field lacks official PostGIS source: {key}")

    expected_origin_counts = {
        "first_party_application_base": 827,
        "first_party_system_or_operations": 107,
        "derived_view": 153,
        "extension_managed": 19,
    }
    actual_origin_counts = {}
    for row in columns:
        actual_origin_counts[row["origin_class"]] = actual_origin_counts.get(row["origin_class"], 0) + 1
    if actual_origin_counts != expected_origin_counts:
        fail(f"column occurrence classification changed unexpectedly: {actual_origin_counts}")
    expected_glossary_gaps = {
        "first_party_application_base": 605,
        "first_party_system_or_operations": 102,
        "derived_view": 150,
        "extension_managed": 19,
    }
    actual_glossary_gaps = {}
    for row in columns:
        if not row["baseline_glossary_meaning"]:
            actual_glossary_gaps[row["origin_class"]] = actual_glossary_gaps.get(row["origin_class"], 0) + 1
    if actual_glossary_gaps != expected_glossary_gaps:
        fail(f"glossary gap classification changed unexpectedly: {actual_glossary_gaps}")

    expected_view_columns = {(db, schema, name, col["name"])
                             for (db, schema, name), rel in snapshot_objects.items()
                             if (db, schema, name) in view_relations for col in rel["columns"]}
    lineage_keys = {(r["database"], *r["view"].split(".", 1), r["output_column"]) for r in lineage}
    if lineage_keys != expected_view_columns or len(lineage) != len(expected_view_columns):
        fail("view lineage matrix does not cover every derived output exactly once")
    if any(not row["source_expression"] or not row["view_definition_sha256"] for row in lineage):
        fail("derived view output lacks source SQL expression/hash")
    catalog_objects = {(row["schema"], row["name"]): row for row in catalog_metadata.get("objects", [])}
    if set(catalog_objects) != {(schema, name) for db, schema, name in snapshot_objects}:
        fail("catalog metadata snapshot does not exactly cover relation identities")
    if any(manifest_relations[(db, schema, name)].get("database_owner") != catalog_objects[(schema, name)].get("database_owner")
           for db, schema, name in snapshot_objects):
        fail("manifest relation owner differs from sanitized catalog metadata")
    view_sql_by_key = {(row["schema"], row["name"]): row["view_sql"] for row in catalog_metadata.get("objects", []) if row.get("view_sql")}
    if set(view_sql_by_key) != {(schema, name) for db, schema, name in view_relations}:
        fail("view-definition snapshot does not exactly cover the catalog views")
    for row in lineage:
        schema, relation = row["view"].split(".", 1)
        expected_hash = hashlib.sha256(view_sql_by_key[(schema, relation)].encode("utf-8")).hexdigest()
        if row["view_definition_sha256"] != expected_hash:
            fail(f"lineage view SQL hash mismatch: {row['view']}")
    expected_api_relations = {f"{schema}.{name}" for _, schema, name in snapshot_objects}
    if {row["relation"] for row in api_map} != expected_api_relations:
        fail("API dependency map omits or adds one or more relations")
    expected_fks = sum(1 for rel in snapshot["relations"] for constraint in rel.get("constraints", []) if constraint.get("type") == "f")
    if len(fk_edges) != expected_fks:
        fail("foreign key edge matrix does not match pg_catalog constraints")

    if manifest.get("missing_field_descriptions") != baseline_missing or manifest.get("business_glossary_complete") is not False:
        fail("manifest field-description gap count/status is misleading")
    if manifest.get("column_occurrence_classification") != expected_origin_counts:
        fail("manifest occurrence classifications disagree with the audited matrix")
    if manifest.get("undocumented_occurrences_by_origin") != expected_glossary_gaps:
        fail("manifest glossary-gap classification disagrees with the audited matrix")
    print(json.dumps({"result": "PASS", "database": snapshot["database_identity"]["database"],
                      "objects": len(objects), "tables": table_count, "views": view_count,
                      "column_occurrences": len(columns), "baseline_glossary_described": baseline_described,
                      "undocumented_occurrences": baseline_missing, "view_lineage_rows": len(lineage),
                      "foreign_key_edges": len(fk_edges), "decision_counts": manifest["architecture_usage_review"]["decision_counts"],
                      "snapshot_sha256": canonical_hash}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"SCHEMA_DOCUMENTATION_VALIDATION_FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
