# Shiraz dataset integration and retrieval readiness

## Migration result

Migration `0007_shiraz_dalahoo_wikipedia_dataset_v1` imports the owner-reviewed Shiraz package additively. It uses the existing Unified Tourism Catalogue and existing provenance, document, chunk, and dataset-batch tables. It does not create a new table, embedding space, or embedding row.

The expected post-migration database contains 30 project tables and 695 rows. Relative to the 0006 baseline, the package adds 22 destination identities, enriches the existing Maragheh Observatory identity, registers 18 sources, adds 51 destination/source relationships, adds 23 Persian knowledge documents and 23 matching chunks, creates one import-batch row, and records migration 0007. The 15 legacy destination identities are preserved; 14 remain `user_supplied_unverified`, while Maragheh is now source-backed and held for review. The 12 synthetic QA destinations and their synthetic provenance remain unchanged.

All 22 new catalogue entities and the Maragheh enrichment have `record_origin='verified_external'`, `is_synthetic=false`, `verification_status='verified'`, `status='needs_review'`, and confidence 0. `verified` records source review; it does not mean editorial publication approval. The import does not duplicate or overwrite Persepolis or Pasargadae. Naqsh-e Rostam remains a separate nearby-trip entity in Marvdasht. Nine food/product entries intentionally have no coordinates.

The migration is idempotent: on the isolated test database, the migration was applied twice and exact row counts remained stable. Conflicts against active, synthetic, or protected identities abort before edits. Insert conflicts for sources, provenance, categories, documents, chunks, batch and migration ledger do not overwrite stored rows. Maragheh updates and replacement of its old unsupported tags are limited to its unapproved source-backed row.

## Provenance and publication path

```text
Owner-curated package (JSON/CSV/source register)
        │ offline validation and checksum
        ▼
Additive migration 0007 → Unified Tourism Catalogue + source links
        ├─ destination status remains needs_review
        ├─ Persian document + one integrity-checked chunk per entity
        └─ import batch records the package checksum and counts
        │
        ▼
Editorial review/publication status change (not part of this migration)
        │
        ▼
knowledge.production_destinations and related production provenance views
        │
        ▼
Retrieval adapter / RAG (not currently implemented)
```

The import test verifies no Shiraz destination or document enters the production views. Existing publication views continue to be the only approved production boundary. No query should substitute raw staging, fixture, or `needs_review` rows for those views.

## Retrieval readiness and blockers

The schema can store the supplied descriptions, source links, publication state, and chunks. It cannot currently express normalized access-route profiles or activity-difficulty profiles; those dataset fields remain unknown/NULL rather than being mapped into unrelated columns. Address this only through a separately reviewed data-model decision if the product needs those profiles.

The current repository has no production retrieval adapter that consumes `knowledge.production_retrieval_documents` / `knowledge.production_retrieval_chunks`, no configured embedding space, and no stored embeddings. Migration 0007 adds 23 Persian documents and 23 chunks, but that is storage readiness only; semantic retrieval is not operational. The existing RAG storage contract tests vector persistence and dimensional constraints, not semantic relevance or multilingual retrieval quality.

Current production-eligible destination count is **0**. Every Shiraz record remains `needs_review`, and existing source-backed UNESCO records also remain behind editorial approval. The isolated validation confirmed `knowledge.production_destinations=0` and `knowledge.production_retrieval_documents=0` after migration.

## Safe development-database application procedure

### Lifecycle states

As of 2026-11-05, the owner's shared `ai_tourism_dev` remains at **Migration 0006 / 30 tables / 419 rows**; Migration 0007 is absent. Migration 0007 has not been run on that database by this work.

`Initialize-Database.ps1` now has three behaviors:

- A completely fresh database follows the documented bootstrap and migration order through 0007.
- An existing exact 0006 / 419-row database is fully checksum/count validated, then stops without applying migrations by default. Applying 0007 requires the explicit `-ApplyPendingMigrationsToExistingDatabase` switch after separate owner approval.
- An exact 0007 / 695-row database is validated and left unchanged.

Any other ledger, checksum, or per-table count fails closed. `Test-Database.ps1` is state-aware and read-only with respect to migrations: it validates exact ledger IDs and checksums plus all 30 row counts, runs tests 000–008 for either supported state, and runs test 009 only for 0007. It does not replay seed migrations. Idempotency testing belongs only in disposable test databases.

Do not execute the supplied package SQL directly against the shared database. After separate approval to apply the migration, confirm the running `ai-tourism-postgres` container is healthy and belongs to this project; confirm database identity and the exact 0006 ledger/checksums/counts. Then invoke Initialize with `-ApplyPendingMigrationsToExistingDatabase`, or apply only `sql/007_shiraz_dalahoo_wikipedia_dataset_v1.sql` as `ai_tourism_owner`, setting `migration_hash` to the SHA-256 of that exact local file. Run test 009, the applicable 000–008 checks, and `sql/reports/final_row_counts.sql`. Stop if the marker/checksum, identity preflight, or any count differs. Do not reset, drop, recreate, or alter schema/seed data.

## Isolated validation evidence

In isolated PostgreSQL 17/PostGIS 3.6.4/pgvector 0.8.7 tmpfs-backed validation, State A passed tests 000–008 and the 419-row report without applying 0007. State B passed tests 000–009 and the 695-row report. State B totals were 66 destinations, 58 sources, 116 destination/source links, 208 tags, 47 category mappings, 52 documents, 81 chunks, 6 import batches, and 8 migration ledger rows; embedding spaces/chunks and production destinations/documents were 0. Reapplying 0007 in the disposable environment preserved counts. Controlled inconsistent clones with a missing 0007 marker, a marker without imported rows, a bad checksum, an incomplete ledger, and a wrong row count were rejected. No shared database was accessed or modified for this lifecycle task. See `sql/tests/009_shiraz_dataset_integration.sql` for the import contract assertions.

Next safe implementation units: (1) editorially review and approve publication for the first real destination subset, (2) implement or integrate the owner's replaceable retrieval port against production views only, then (3) select an embedding strategy through the existing provider decision process and separately assess Persian semantic retrieval quality. Do not bypass publication to unblock retrieval.
