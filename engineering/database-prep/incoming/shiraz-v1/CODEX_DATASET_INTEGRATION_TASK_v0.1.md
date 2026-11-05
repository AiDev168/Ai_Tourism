# Codex Software Integration Task — Assistant-Prepared Shiraz Tourism Dataset v0.1

## Ownership boundary

The research, source selection, factual curation, Persian editorial paraphrasing, coordinates, data classification, and dataset files in this package were prepared by the project assistant.

**Codex is responsible only for software/database integration, migration correctness, test updates, and safe execution in an isolated database. Do not repeat the tourism research, invent more facts, or rewrite the curated dataset.**

## Supplied data artefacts

- `shiraz_dalahoo_wikipedia_real_data_v1.json`
- `shiraz_dalahoo_wikipedia_real_data_v1.csv`
- `shiraz_dalahoo_wikipedia_real_data_v1.sql`
- `SOURCE_REGISTER.csv`
- `DATA_RESEARCH_REPORT_FA.md`

Use the JSON as the canonical data manifest and the SQL as an import reference. Reconcile any discrepancy by reporting it; do not silently change source-backed facts.

## Required software work

1. Inspect the actual current branch, worktree, database migrations and seed conventions. Preserve all user changes and do not switch to or modify `main`.
2. Review the supplied SQL against the actual schema, current migration order, exact constraints, source roles, destination key/natural-key uniqueness, document/chunk schema, and publication views.
3. Convert/integrate the dataset into the repository's controlled migration/seed mechanism. Prefer the next additive migration after the existing migration 0006; do not run the standalone SQL directly against the owner's shared database.
4. Do not create a separate attractions table. Use the accepted `knowledge.destinations` unified catalogue with `destination_type` and `parent_destination_id`.
5. Keep the dataset classifications exactly:
   - factual candidates: `record_origin='verified_external'`, `is_synthetic=FALSE`, `verification_status='verified'`, `status='needs_review'`, `data_confidence=0`;
   - existing QA synthetic rows: `record_origin='synthetic_fixture'`, `is_synthetic=TRUE`, `verification_status='not_applicable'`, `status='test_only'`;
   - legacy rows that are only linked to the Dalahoo index remain `user_supplied_unverified`, `is_synthetic=FALSE`, `verification_status='pending'`, `status='needs_review'`.
6. Never equate `is_synthetic=FALSE` with editorial approval. Do not publish these records or bypass `knowledge.production_destinations` / retrieval views.
7. Preserve the in-city / nearby-trip distinction. Naqsh-e Rostam belongs to Marvdasht as a nearby trip candidate, not to the Shiraz city hierarchy. Do not duplicate or overwrite the existing UNESCO Persepolis/Pasargadae records or their official coordinates.
8. Add the 23 assistant-prepared Persian `knowledge_documents` and 23 corresponding chunks with the provided SHA-256 and character counts. Do not create embeddings or an embedding space.
9. Make the import idempotent. A repeated migration/seed run must not duplicate sources, destinations, provenance relations, tags, category mappings, documents, chunks, or import batches.
10. Update exact expected row counts and SQL/data invariants only after validating the actual isolated test database. Do not weaken or auto-adjust expected counts to make tests pass.
11. Add tests for:
    - real/synthetic marker consistency;
    - no synthetic-to-production leakage;
    - every factual candidate stays `needs_review`;
    - source URLs and destination-source relations;
    - representative-point coordinate semantics;
    - Shiraz parent-child linkage;
    - Naqsh-e Rostam geographic separation;
    - exact document/chunk counts, content hashes and character counts;
    - import idempotency;
    - no overwrite of active/published rows;
    - preserving existing synthetic QA rows and the 15 legacy rows not substantively verified.
12. Execute only against an isolated disposable test database. Do not reset, drop, overwrite or otherwise mutate the user's shared `ai_tourism_dev` database.

## Important modelling limitation

The current MVP schema has no normalized multi-route access profiles or separate activity-difficulty profiles. This dataset intentionally leaves generic `difficulty` and `suitable_transport` empty for the Shiraz attractions rather than copying tour-specific Dalahoo itinerary timings into permanent attraction facts. Do not invent new fields or schema in this integration task; report the limitation for a separately approved follow-up.

## Expected data payload

- 22 catalogue entities: one Shiraz city, eleven in-city attractions, one nearby-trip candidate, and nine local food/product experiences.
- One existing Maragheh Observatory row enriched from its legacy state, with unsupported legacy difficulty/transport/season/food/souvenir values cleared.
- Thirteen Dalahoo index discovery relationships requested for existing destination rows. Discovery-only relationships do not validate those rows.
- Two Dalahoo discovery relationships to already-existing UNESCO entries for Persepolis and Pasargadae.
- 18 source records.
- 23 Persian knowledge documents and 23 chunks.
- No embeddings.

## Delivery restrictions

- No production publication.
- No unapproved schema redesign.
- No new tourism facts, additional source scraping, or dataset expansion.
- No commits, pushes, merges, PRs, or changes to `main` unless separately authorized.
- Report exact branch/HEAD, migrations, expected count changes, actual isolated DB counts, tests, and any blockers.
