#!/usr/bin/env python3
"""Report glossary coverage without synthesizing undocumented meanings.

Field descriptions are manually curated in docs/database/field_descriptions.json.
This command only classifies documented/undocumented column occurrences against
the sanitized PostgreSQL snapshot and emits a coverage report. It intentionally
does not invent prose from SQL type, field name, or a guessed domain.
"""
from __future__ import annotations

import json
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "docs/database/live-schema/catalog_snapshot.json"
GLOSSARY = ROOT / "docs/database/field_descriptions.json"
OUTPUT = ROOT / "docs/database/architecture-usage/glossary_coverage.json"
EXTENSION = {("public", "spatial_ref_sys"), ("public", "geometry_columns"), ("public", "geography_columns")}
SYSTEM_SCHEMAS = {"system", "operations", "integration"}


def main() -> int:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    glossary_data = json.loads(GLOSSARY.read_text(encoding="utf-8"))
    origins: Counter[str] = Counter()
    glossary_counts: Counter[str] = Counter()
    by_origin: dict[str, Counter[str]] = defaultdict(Counter)
    by_schema: dict[str, Counter[str]] = defaultdict(Counter)
    unmatched = []
    seen = set()
    for relation in snapshot["relations"]:
        schema = relation["relation"]["schema"]
        table = relation["relation"]["name"]
        kind = relation["relation"]["kind"]
        for column in relation["columns"]:
            key = (schema, table, column["name"])
            seen.add(key)
            documented = glossary_data.get(f"{schema}.{table}", {}).get(column["name"])
            is_described = isinstance(documented, str) and bool(documented.strip())
            # Extension-owned views (geometry_columns/geography_columns) are
            # extension metadata, not Rahgard-derived business projections.
            if (schema, table) in EXTENSION:
                origin = "extension_managed_occurrence"
            elif kind in {"v", "m"}:
                origin = "derived_view_occurrence"
            elif schema in SYSTEM_SCHEMAS or (schema, table) == ("public", "rahgard_private_pilot_marker"):
                origin = "first_party_system_or_operations_occurrence"
            else:
                origin = "first_party_application_base_occurrence"
            origins[origin] += 1
            glossary_state = "documented" if is_described else "undocumented"
            glossary_counts[glossary_state] += 1
            by_origin[origin][glossary_state] += 1
            by_schema[schema][origin] += 1
            by_schema[schema][f"glossary_{glossary_state}"] += 1
    for object_key, fields in glossary_data.items():
        if object_key.startswith("_") or not isinstance(fields, dict):
            continue
        schema, _, table = object_key.partition(".")
        for name, description in fields.items():
            if name.startswith("_") or not isinstance(description, str) or not description.strip():
                continue
            if (schema, table, name) not in seen:
                unmatched.append(f"{object_key}.{name}")
    report = {
        "scope": "column_occurrences_in_one_authorized_database_snapshot",
        "source_snapshot_sha256": hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),
        "baseline_glossary_sha256": hashlib.sha256(GLOSSARY.read_bytes()).hexdigest(),
        "database": snapshot.get("database_identity", {}).get("database"),
        "column_occurrence_count": sum(origins.values()),
        "distinct_business_requirement_count": None,
        "origin_categories": dict(origins),
        "baseline_glossary_coverage": {"documented_occurrences": glossary_counts["documented"],
                                        "undocumented_occurrences": glossary_counts["undocumented"]},
        "glossary_coverage_by_origin": {origin: dict(counts) for origin, counts in sorted(by_origin.items())},
        "by_schema": {schema: dict(counts) for schema, counts in sorted(by_schema.items())},
        "glossary_entries_not_matching_snapshot": sorted(unmatched),
        "warning": "Undocumented occurrences are documentation gaps, not validated business requirements. Derived views and extension metadata are classified separately; no meanings are generated.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), **report["origin_categories"],
                      **report["baseline_glossary_coverage"], "unmatched_glossary": len(unmatched)}, ensure_ascii=False, sort_keys=True))
    return 0 if not unmatched else 1


if __name__ == "__main__":
    raise SystemExit(main())
