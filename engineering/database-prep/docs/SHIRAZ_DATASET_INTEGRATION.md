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

Do not run `Initialize-Database.ps1` as a way to initialize/reset a database for this dataset, and do not execute the supplied package SQL directly against the shared database. First ensure the expected branch and local changes are reviewed and backed up under the project's normal development procedure. Confirm the running `ai-tourism-postgres` container is healthy and belongs to this project; confirm the destination database and migration 0000–0006 checksums/counts. Then apply only `sql/007_shiraz_dalahoo_wikipedia_dataset_v1.sql` as `ai_tourism_owner`, supplying `migration_hash` as the SHA-256 of that exact local file, using the existing container and database. Run `sql/tests/009_shiraz_dataset_integration.sql`, the established read-only integrity/publication checks, and `sql/reports/final_row_counts.sql`. Stop if the migration marker exists with a different checksum, any identity conflict preflight fails, or actual counts differ. Do not reset, drop, recreate, or alter schema/seed data. This task has **not** applied 0007 to the shared `ai_tourism_dev` database; owner approval is still required for that final write.

## Isolated validation evidence

The migration and SQL checks 000–009 passed against a uniquely named disposable PostgreSQL 17/PostGIS 3.6.4/pgvector 0.8.7 container whose data directory was tmpfs-backed and which had no mounted Docker volumes. The baseline was 44 destinations, 40 sources, and 29 documents. Post-migration totals were 66 destinations, 58 sources, 116 destination/source links, 208 tags, 47 category mappings, 52 documents, 81 chunks, 6 import batches, and 8 migration ledger rows; embedding spaces/chunks were 0 and production destinations/documents were 0. Reapplying 0007 preserved these exact totals. See `sql/tests/009_shiraz_dataset_integration.sql` for the contract assertions.

Next safe implementation units: (1) editorially review and approve publication for the first real destination subset, (2) implement or integrate the owner's replaceable retrieval port against production views only, then (3) select an embedding strategy through the existing provider decision process and separately assess Persian semantic retrieval quality. Do not bypass publication to unblock retrieval.
