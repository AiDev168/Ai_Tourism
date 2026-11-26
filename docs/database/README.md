# Rahgard database documentation

## Isolated migration-0026 rehearsal

For the local Windows owner demo and schema generated from its isolated PostgreSQL 17 database, start with the [Persian owner index](rehearsed-schema-0026/OWNER_INDEX_FA.md), [rehearsed catalogue](rehearsed-schema-0026/README.md), [snapshot evidence](rehearsed-schema-0026/SNAPSHOT_EVIDENCE.json) and [role-to-form/API map](rehearsed-schema-0026/FORM_API_COVERAGE.md). This is not the live VPS snapshot and does not establish architectural approval. The live historical snapshot below remains separately scoped.

The local Issue #27 acceptance database has since been migrated additively through 0027. Its source-derived provider-admin field reference is [here](rehearsed-schema-0027/PROVIDER_ADMIN_FIELD_REFERENCE.md); the complete 0026 rehearsal catalogue and 0023 live snapshot remain separate and unchanged. See the [Persian Issue #27 owner index](rehearsed-schema-0027/OWNER_INDEX_FA.md) for these boundaries and the new administration fields.

## Current evidence boundary

The checked-in live schema snapshot describes one authorized database, `rahgard_pilot_vps_staging`, observed read-only on PostgreSQL 17. It records 101 relations (87 tables and 14 views) and 1,106 **column occurrences**. The baseline glossary contains 230 matching descriptions and has 876 unmatched occurrences.

These are catalog and glossary counts. A column occurrence is not necessarily a distinct logical attribute: views can repeat or derive fields. The 876 figure is a documentation gap, not a count of validated business requirements. The snapshot does not prove that every existing object is necessary, and it is not a whole-server database inventory.

## Read the architecture/usage evidence first

- [Object decision matrix](architecture-usage/object_decision_matrix.csv): all 101 objects, relation owner, migration/DDL touchpoints, FK edges, static backend/frontend references, publication-policy evidence, disposition and change risk.
- [Column occurrence matrix](architecture-usage/column_occurrence_matrix.csv): all 1,106 occurrences, types, constraints, baseline glossary state, source evidence, provisional sensitivity and necessity status.
- [View output lineage](architecture-usage/view_column_lineage.csv): each view output expression and its recorded view-definition hash.
- [Sanitized catalog metadata snapshot](live-schema/catalog_metadata_snapshot.json): relation owners and view SQL definitions only; no application rows or secrets.
- [Foreign-key graph](architecture-usage/foreign_key_edges.csv) and [API dependency map](architecture-usage/api_dependency_map.csv).
- [Architecture and usage review](architecture-usage/ARCHITECTURE_AND_USAGE_REVIEW.md): scope, boundaries, counts, risks and unresolved evidence.
- [Schema coverage](architecture-usage/coverage_by_schema.csv) and [glossary classification](architecture-usage/glossary_coverage.json).

The object dispositions are preservation and investigation decisions, not approval of the schema. Static source matches are evidence leads, not proof of runtime use; absence is not proof of dead code. No application rows were read, so row-level synthetic/legacy/import origin remains unassessed. Database object owners are not product or privacy sign-off owners.

## Meaning and classification policy

The existing 230 descriptions are preserved as baseline glossary entries. No description is synthesized from a field name or SQL type. Undocumented first-party fields remain explicitly undocumented unless their meaning, constraints, units and API ownership are supported by code or an authoritative contract. Derived-view outputs link to their source expression rather than receiving duplicate business prose. PostgreSQL/PostGIS-managed objects link to the official extension documentation and are not Rahgard form fields. System, operations and legacy-compatible fields are classified separately from traveler/company requirements.

Technical catalog completeness, glossary coverage and architecture necessity are separate statuses. The manifest deliberately keeps `complete` false and `business_necessity_approved` false.

## Safe reproduction

The committed snapshot renderer does not connect to a database. To refresh it, first create a sanitized metadata-only snapshot through the documented read-only operator procedure, then run:

```powershell
uv run python tools/schema/build_architecture_usage_matrix.py
uv run python tools/schema/build_field_descriptions.py
uv run python tools/schema/rahgard_schema_documenter.py --catalog-snapshot-json docs/database/live-schema/catalog_snapshot.json --descriptions-json docs/database/field_descriptions.json --output-root docs/database/live-schema
uv run python tools/schema/validate_live_schema_docs.py
```

Live collection requires an authorized read-only role and the private `RAHGARD_SCHEMA_DSN` environment variable. Never put a DSN in source, a command line, or generated files. The `--all-accessible-databases` mode records the server's non-template database names but opens only explicitly authorized `rahgard_` databases; outside names are listed as skipped. This is not permission to inspect other applications or tenants.

No database writes, migrations, imports, publication or deployment are performed by these documentation tools.
