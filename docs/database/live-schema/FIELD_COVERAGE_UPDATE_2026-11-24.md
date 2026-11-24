# Rahgard live schema coverage update — 2026-11-24

## Authorized inventory boundary

The read-only `pg_catalog` scan ran through `ai_tourism_app` against the authorized VPS instance. It found two connectable, non-template database names: `rahgard_pilot_vps_staging` and `postgres`. The Rahgard database was attempted and its metadata was read inside read-only transactions. `postgres` was skipped because it is outside the authorized Rahgard database namespace. No database was recorded as inaccessible. No other application database was opened, and no table rows, account data, secrets, traveler messages, or company records were read.

The catalog covers PostgreSQL 17.11, database `rahgard_pilot_vps_staging`, role `ai_tourism_app`: 11 schemas, 101 relations and 1,106 columns. It is complete for the explicitly authorized Rahgard database only, not a claim of exhaustive inventory for every application on the PostgreSQL instance.

## Field descriptions and drift checks

Every captured column has exact PostgreSQL type, nullability, sanitized default, available CHECK/PK/FK/unique constraints, format or units, business meaning, source evidence, sensitivity classification, owner, and read/write surface. Metadata-only extension relations (`spatial_ref_sys`, `geometry_columns`, `geography_columns`) are identified separately from application relations and refer to official PostGIS documentation. No row values are included.

Current coverage is 1,106/1,106 field metadata entries, zero unresolved meanings, and 101/101 generated relation documents. `manifest.json` records the source snapshot SHA-256 and database discovery/attempt/skip outcome. `tools/schema/validate_live_schema_docs.py` fails on missing relations or columns, absent evidence/source files, incorrect inventory accounting, stale snapshot hashes, and an unsupported `complete` flag; it is run in the repository CI workflow.

Descriptions are derived from the checked-in DDL, constraint definitions, application contracts and official type documentation. The completion count means those sources support a concrete documented meaning; it does not mean every business field has been independently reviewed by a domain owner. Where no exact business semantics can be established, the field must remain explicitly unresolved rather than be promoted by naming heuristics.

## Partner branch fields

`partner.branches` is schema-documented but intentionally read-only to partner users. The existing company onboarding and service workflow does not require a branch: a company can create a service without associating a branch, and no branch API or user-facing branch form currently exists. Adding branch CRUD would expand the normal workflow without a demonstrated need. If multi-location service management becomes a product requirement, it should be introduced as a narrow organization-scoped workflow with ownership/RLS tests, not as generic table editing.

## Release and data gates

- Last read-only VPS API/Web image source label observed: `9b5b07d0786578abdfac56848baf3c6d1260832e`.
- Existing release marker observed separately as `5e2664fb51e18f52549aa37a8b5793e12ace09b2`; this mismatch remains a release-identity issue and is not hidden by this schema snapshot.
- Live schema ledger observed at 22 rows through migration 0023. Migration 0024 was rehearsed only in isolated PostgreSQL and is not applied to live.
- Live `knowledge.production_destinations` count: 0. Live `partner.share_eligible_organizations` count: 0. No real destination or eligible company is asserted by the isolated acceptance fixtures.
- No live write, migration, publication, service restart, or deployment was performed for this documentation update.
