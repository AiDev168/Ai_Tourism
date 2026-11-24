# Live schema observation — 2026-11-24

This file is superseded by [FIELD_COVERAGE_UPDATE_2026-11-24.md](FIELD_COVERAGE_UPDATE_2026-11-24.md) and the machine-readable [manifest.json](manifest.json). The prior observation described an earlier, one-database snapshot with 876 unresolved field descriptions. The updated snapshot enumerated the non-template database names through a read-only `pg_database` scan, attempted the authorized `rahgard_pilot_vps_staging` database, skipped `postgres` outside the approved Rahgard namespace, and documents 1,106/1,106 fields across 101 relations with no unresolved meanings.

The completeness boundary remains limited to the authorized Rahgard database. No other application database was opened. Migration 0024 remains rehearsal-only and has not been applied to the live database. This update made no live data or service changes.
