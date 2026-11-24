# Live schema observation — 2026-11-24

This is a bounded, read-only metadata snapshot for the authorized database `rahgard_pilot_vps_staging` on PostgreSQL 17.11. The live `pg_database` scan discovered two non-template names: the Rahgard database and `postgres`. The Rahgard database was inspected; `postgres` was skipped as outside the approved application namespace. No other application database was opened, so this is not an exhaustive server-wide inventory.

The snapshot contains 101 relations (87 tables and 14 views), with 1,106 column occurrences. The baseline glossary has 230 matching descriptions and 876 unmatched column occurrences. **876 is the number of glossary gaps in this snapshot, not 876 validated or independently necessary business requirements.** The count includes repeated/derived view outputs and PostgreSQL/PostGIS extension metadata. See the occurrence-class breakdown and object-by-object decisions in `../architecture-usage/`.

No application rows were read. Row-level synthetic, imported, or legacy origin is therefore not assessed. PostgreSQL relation ownership identifies technical database owners, not domain or privacy approvers. Static source references and UI mappings are evidence leads; a missing literal reference does not prove an object is unused. The review assigns KEEP, INVESTIGATE, or EXTENSION-MANAGED dispositions conservatively and does not declare the schema architecture approved.

The database migration ledger was observed through 0023; migration 0024 was not applied by this task. No live database write, migration, service change, or deployment occurred.
