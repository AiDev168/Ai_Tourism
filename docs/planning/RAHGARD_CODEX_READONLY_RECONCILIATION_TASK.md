# CODEX — Rahgard Live Schema and Dataset Reconciliation (READ-ONLY)

## Objective
Close the **specific remaining evidence gap** before freezing the national catalogue + partner ERD. Do not start broad implementation, migrations, publication, or partner portal development.

Repo `AiDev168/Ai_Tourism`. Reference the current **verified live** SHA, not an assumed main branch. The owner has supplied `دیتابیس - توریسم.zip`. The architecture audit prepared by ChatGPT is `RAHGARD_DATA_ARCHITECTURE_RECONCILIATION_V1.md`; read it along with existing ADR-0004, marketplace proposal/contract/ADRs, and existing SQL migrations. Treat the audit as *proposed*, not owner-approved DDL.

## Part 1 — live PostgreSQL read-only introspection

Use authorized `ssh rahgard-vps` via existing SSH config and the supported Docker Compose environment. Connect with a **read-only transaction** to `rahgard_pilot_vps_staging`; do not execute migrations or writes.

Record, using `pg_catalog` / `information_schema`, only safe schema metadata:
- schemas; tables; columns (type, nullable, default); PK, FK, UNIQUE, CHECK; indexes, views and view definitions (redact possible secrets); constraints, grants/RLS; migration IDs + checksums;
- count of `knowledge.destinations`, distinct `destination_key`, `status`, `verification_status`, `record_origin`, coordinate roles, canonical cities/provinces, production-view count; document/chunk/source counts and publication states;
- `operations.dataset_import_batches`, `destination_enrichment_proposals`, candidate/review structures and actual partner tables if present;
- verify active API/web DB name and live release identity against current GitHub HEAD.

**Do not export user records, phone numbers, credentials, conversation contents, secrets, user identifiers or raw private company evidence.** Aggregate counts are sufficient. Do not include `identity.users`, `travel.trips`, `conversation.messages` row contents; if preservation baseline needed use counts only.

If readonly DB access fails, report exactly which permission failed and emit a standalone SQL script for a trusted operator; do not request broad privileges or mutate the database.

## Part 2 — dataset reconciliation

Safely inspect the nested ZIP **without extracting arbitrary paths** or running bundled SQL. Build a manifest of all nested archives, CSV filenames, row counts, SHA-256, schema signatures and language/status columns.

- Deduplicate exact `destination_key` and distinguish the Alborz Batch 001 repeated delivery from genuinely new sources. Assess whether the same real-world place occurs under different keys; keep ambiguous matches for human review.
- Match all 167 candidate destination keys to actual Live DB `destination_key`. Also check stable official external IDs where available and produce a human-review list for fuzzy name/admin/coordinate matches.
- Record categories for every item: `already_exists_exact`, `possible_existing_different_key`, `new_staging_candidate`, `insufficient_identity`, `duplicate_within_upload`.
- Analyze 533 national discovery leads and the Alborz/other discovery files separately; do not count leads as publishable destinations.
- Validate coordinate roles against actual DB CHECK; report raw values, the source evidence, and proposed semantic normalization, never auto-label reference points as entrances.
- Check source URLs/hashes and source identity duplicates. Do not perform bulk remote crawling; flag source uncertainty.
- Compare 501 unique document keys/associated chunks with live DB; note `pending` ingestion and missing embedding. Do not call semantic quality verified.
- Produce CSV summaries without private identifiers or full copyrighted source text.

## Part 3 — architecture gap matrix, no implementation

For each proposed entity in the owner audit, mark `REUSE_EXISTING`, `ALTER_EXISTING`, `NEW_IF_APPROVED`, or `DO_NOT_IMPLEMENT_YET`; give precise existing table/column or constraint and dependent API. Explicitly cover:
- `operations.dataset_import_batches` vs new ingestion tables;
- `destination_enrichment_proposals` vs new-discovery candidate staging;
- existing production source/retrieval views and claim-level evidence;
- normalized geo hierarchy, access points, localized aliases, dynamic visit facts;
- catalogue 1000-item ceiling, server filtering/cursors and recommendation bounds;
- partner organizations/memberships/verification/services/offers/prices/schedules, which are presently **proposals**;
- external links vs referral proposals;
- RAG corpora/index handoff; never rebuild owner's RAG.

Deliver `LIVE_SCHEMA_MANIFEST.json`, `UPLOAD_INVENTORY.csv`, `DESTINATION_MATCH_AUDIT.csv`, `REUSE_GAP_MATRIX.md`, and a short `DECISION_REPORT.md`. Use redaction and no user-level data.

## Stop and acceptance

No DDL/DML, migration, import, deployment, PR merge or data publication in this task. Commit/push **documentation and sanitized audit outputs** if suitable; never commit private DB dumps or raw uploaded archives. Provide SHA and paths. Finish with an exact, evidence-backed answer: what is already implemented, what remains, how many source records are truly new, and which proposed schema changes are necessary. Then hand the matrix back to the architect for ERD freeze and owner decisions.
