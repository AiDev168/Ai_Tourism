#!/usr/bin/env python3
"""Validate the generated, isolated PostgreSQL 0026 schema reference."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs/database/rehearsed-schema-0026"


def main() -> int:
    manifest = json.loads((DOCS / "manifest.json").read_text(encoding="utf-8"))
    metadata_path = DOCS / "catalog_metadata_snapshot.json"
    metadata_bytes = metadata_path.read_bytes()
    metadata = json.loads(metadata_bytes)
    evidence = json.loads((DOCS / "SNAPSHOT_EVIDENCE.json").read_text(encoding="utf-8"))
    relations = manifest.get("relations", [])
    classes = manifest.get("undocumented_occurrences_by_origin", {})
    expected_classes = {
        "first_party_application_base": 631,
        "first_party_system_or_operations": 102,
        "derived_view": 150,
        "extension_managed": 19,
    }
    if manifest.get("environment_scope") != "isolated_local_owner_demo_post_0026":
        raise ValueError("manifest is not explicitly scoped to local isolated rehearsal")
    if manifest.get("database_inventory_complete") is not True or manifest.get("coverage_scope") != "authorized-rahgard-databases-only":
        raise ValueError("database inventory scope is incomplete or unauthorized")
    if manifest.get("complete") is not False or manifest.get("business_necessity_approved") is not False:
        raise ValueError("schema catalogue overstates product/architecture approval")
    if manifest.get("catalog_metadata_snapshot_sha256") != hashlib.sha256(metadata_bytes).hexdigest():
        raise ValueError("catalog metadata snapshot checksum mismatch")
    if manifest.get("source_snapshot_evidence_path") != "catalog_metadata_snapshot.json":
        raise ValueError("catalog metadata path is not recorded")
    if metadata.get("environment_scope") != "isolated_local_demo" or metadata.get("database_access_mode", "").find("no application rows read") < 0:
        raise ValueError("catalog metadata scope/privacy contract mismatch")
    if len(relations) != 105 or manifest.get("catalog_counts") != {
        "relations": 105, "tables": 91, "views": 14, "column_occurrences": 1132,
    }:
        raise ValueError("relation or column-occurrence counts differ from the isolated snapshot")
    if sum(classes.values()) != manifest.get("missing_field_descriptions") or classes != expected_classes:
        raise ValueError("glossary occurrence classification arithmetic mismatch")
    coverage = manifest.get("baseline_glossary_coverage", {})
    if coverage.get("distinct_business_requirement_count") is not None:
        raise ValueError("column occurrence count was represented as business requirements")
    owners = {(r.get("database"), r.get("schema"), r.get("name")) for r in relations}
    metadata_owners = {(r.get("database"), (r.get("relation") or {}).get("schema"),
                        (r.get("relation") or {}).get("name")) for r in metadata.get("relations", [])}
    if owners != metadata_owners or len(owners) != len(relations):
        raise ValueError("manifest and metadata relation identities differ")
    missing = [r.get("path") for r in relations if not r.get("path") or not (DOCS / r["path"]).is_file()]
    if missing:
        raise ValueError(f"relation documentation missing ({len(missing)} files)")
    readme = (DOCS / "README.md").read_text(encoding="utf-8")
    if readme.count("?") or any(marker in readme for marker in ("Ø", "Ù", "Ã", "\ufffd")):
        raise ValueError("schema README has encoding damage or replacement characters")
    if any(f"]({relation['path']})" not in readme for relation in relations):
        raise ValueError("schema README does not link every generated relation document")
    if evidence.get("snapshot_sha256") != hashlib.sha256(metadata_bytes).hexdigest():
        raise ValueError("sanitized evidence snapshot checksum mismatch")
    if evidence.get("environment_scope") != "isolated_local_owner_demo" or evidence.get("live_vps", {}).get("live_schema_or_data_changed") is not False:
        raise ValueError("evidence environment scope or live-data boundary mismatch")
    print(json.dumps({
        "result": "PASS", "environment_scope": manifest["environment_scope"],
        "relations": len(relations), "tables": 91, "views": 14,
        "column_occurrences": 1132, "undocumented_occurrences": sum(classes.values()),
        "business_necessity_approved": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, KeyError, TypeError, ValueError) as exc:
        print(f"REHEARSED_SCHEMA_VALIDATION_FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
