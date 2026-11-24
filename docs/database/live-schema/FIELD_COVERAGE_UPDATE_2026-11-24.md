# Rahgard live schema coverage update — 2026-11-24

## Authorized inventory boundary

The read-only `pg_catalog` scan ran through `ai_tourism_app` against the authorized VPS instance. It found two connectable, non-template database names: `rahgard_pilot_vps_staging` and `postgres`. The Rahgard database was attempted and its metadata was read inside read-only transactions. `postgres` was skipped because it is outside the authorized Rahgard database namespace. No database was recorded as inaccessible. No other application database was opened, and no table rows, account data, secrets, traveler messages, or company records were read.

The catalog covers PostgreSQL 17.11, database `rahgard_pilot_vps_staging`, role `ai_tourism_app`: 11 schemas, 101 relations and 1,106 columns. It is complete for the explicitly authorized Rahgard database only, not a claim of exhaustive inventory for every application on the PostgreSQL instance.

## Corrected occurrence and glossary coverage

There are 1,106 catalogued **column occurrences**, not 1,106 independent business fields. The preserved baseline glossary has 230 matching descriptions and 876 occurrences without a baseline glossary entry. The 876 figure is a documentation gap, not 876 validated business requirements. It includes derived outputs and extension metadata.

The architecture/usage matrix classifies all occurrences as first-party application base, first-party system/operations, derived-view, or extension-managed. Derived outputs have a separate source-expression/hash lineage ledger; they must point to their source attributes rather than receive duplicate business prose. PostGIS-managed objects link to the official extension docs. The 230 existing glossary descriptions are preserved; no meanings are generated from names or SQL types. Business necessity remains unapproved and unresolved fields remain explicit.

The metadata snapshot captures SQL types, nullability, sanitized defaults and catalog constraints. The source matrices separately link DDL touchpoints, relation ownership, foreign keys, static API/UI references and provisional sensitivity. Static references are not proof of runtime behavior, PostgreSQL object owner is not product approval, and no application rows were read; row-level imported/synthetic/legacy origin is not assessed. `manifest.json` therefore keeps `complete=false` and `business_necessity_approved=false`.

The validator checks occurrence counts, matrix identity coverage, lineage, FK totals, extension classification, baseline glossary arithmetic, snapshot hashes and the authorized database inventory boundary. It does not claim architectural sufficiency or field-level domain sign-off.

## Partner branch fields

`partner.branches` is schema-documented but intentionally read-only to partner users. The existing company onboarding and service workflow does not require a branch: a company can create a service without associating a branch, and no branch API or user-facing branch form currently exists. Adding branch CRUD would expand the normal workflow without a demonstrated need. If multi-location service management becomes a product requirement, it should be introduced as a narrow organization-scoped workflow with ownership/RLS tests, not as generic table editing.

## Release and data gates

- Last read-only VPS API/Web image source label observed: `9b5b07d0786578abdfac56848baf3c6d1260832e`.
- Existing release marker observed separately as `5e2664fb51e18f52549aa37a8b5793e12ace09b2`; this mismatch remains a release-identity issue and is not hidden by this schema snapshot.
- Live schema ledger observed at 22 rows through migration 0023. Migration 0024 was rehearsed only in isolated PostgreSQL and is not applied to live.
- Live `knowledge.production_destinations` count: 0. Live `partner.share_eligible_organizations` count: 0. No real destination or eligible company is asserted by the isolated acceptance fixtures.
- No live write, migration, publication, service restart, or deployment was performed for this documentation update.
