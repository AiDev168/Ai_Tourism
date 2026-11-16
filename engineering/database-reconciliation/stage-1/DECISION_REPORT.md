# Rahgard database and upload reconciliation — Stage 1 decision report

## Decision

Stage 1 read-only reconciliation is complete. The live schema and the supplied archive were inspected without writes. The current national-catalogue/partner ERD is **not ready to freeze solely from the proposed design**: reuse is substantial, but the new-identity queue, normalized admin geography, localization and temporal access facts remain explicit owner/architect decisions. Partner tables remain proposals and should not be implemented in this stage.

## Verified snapshot

- Live release / reviewed feature baseline: `5e2664fb51e18f52549aa37a8b5793e12ace09b2`; GitHub release branch `fix/rahgard-default-ai-relative-dates-gps-v1` resolves to the same SHA. GitHub default `main` is `c912000bccaee982a98d58f6810ad74431945ed0`; that default branch is an ancestor of this release, which is 155 commits ahead (main is not the live release branch). API/web image identities and release marker are recorded in `LIVE_SCHEMA_MANIFEST.json`.
- Database: API config resolves to `rahgard_pilot_vps_staging` at host `db`; web database env keys: `none`; read-only introspection reached `rahgard_pilot_vps_staging`, PostgreSQL 17.11 (Debian 17.11-1.pgdg13+2); introspection executed as `ai_tourism_owner` in an explicit read-only transaction ending in `ROLLBACK`. Migration ledger: 16 migration IDs/checksums. The schema manifest contains 62 relations, 333 constraints, 139 indexes, 11 views, and 572 table-grant rows. Fifty base tables were inspected; none had RLS enabled or forced, and there were no row-security policies in `pg_policies`.
- Existing destinations: 66 rows / 66 keys; production destination view: 0. Status: 54 `needs_review`, 12 `test_only`; verification: 40 `verified`, 14 `pending`, 12 `not_applicable`; origin: 40 `verified_external`, 14 `user_supplied_unverified`, 12 `synthetic_fixture`; coordinate roles: 17 `property_reference`, 14 `representative_point`, 23 `unknown`, 12 `test_fixture`. Live source rows/links: 58/116; documents/chunks/embeddings: 52/81/0; production documents/chunks: 0/0; claim evidence: 0; import batches: 6; enrichment proposals: 0; partner tables: 0. No user rows or message/trip contents were read.
- ZIP: 17 nested archives, 236 non-directory members, 128 CSV files; outer SHA-256 `7e9a27654535590f593aeea8e9f7ba9422fb128ca2c4fc93129061c544aff397`. Nested archives were processed in memory; bundled SQL was inventoried only and never executed.

## Destination and lead reconciliation

The upload contains 177 destination rows representing 167 unique nonempty destination keys and 10 repeated-key rows. For uploaded destination rows (row-level, including repeated delivery) the categories are: `already_exists_exact` 0; `possible_existing_different_key` 2; `new_staging_candidate` 165; `insufficient_identity` 0; `duplicate_within_upload` 10. At unique-key level (excluding repeated delivery): exact 0; possible-existing 2; staging candidates 165; insufficient identity 0. The 10 repeated-key rows are the same Batch 001 `destinations.csv` delivered in two nested ZIPs with identical SHA-256 `036124c0bb2d0c629367a71c8c580a121022304055dd38fed2b89a9f5a62208a`; all 10 repeated Batch 001 CSV payload pairs are byte-identical in the archive inventory, so they are repeated delivery, not ten additional destination identities or evidence of additional sources. Exact live-key matches are `already_exists_exact`; repeated upload rows are `duplicate_within_upload`; normalized identity overlap under another key and conservative fuzzy/coordinate proximity are review-only `possible_existing_different_key`; unmatched identity-complete rows are `new_staging_candidate`; missing identity fields are `insufficient_identity`. Full row evidence and match basis are in `DESTINATION_MATCH_AUDIT.csv`.

The national discovery archive contains 533 lead rows: `{"already_exists_exact": 8, "possible_existing_different_key": 4, "new_staging_candidate": 521, "insufficient_identity": 0, "duplicate_within_upload": 0}`. These are **discovery leads, not publishable destination records**; `new_staging_candidate` means an unmatched review candidate, not approved content. Alborz and other discovery/candidate files are likewise listed by nested file and classified independently. No candidate was imported or published.

## Sources and knowledge packages

Across source-register CSV rows, 235 unique valid URLs were compared by normalized exact URL: 0 are already represented in the live source URL set and 235 candidate URL references are absent from that set. 58 source URL rows repeat an upload URL. No source entity is confirmed genuinely new by this audit: the `235` URLs are unmatched candidate references, not verified new publisher/source identities. No bulk crawling was performed.

The upload carries 531 document rows / 501 unique document keys and 531 chunk rows. Exact document-key overlap with live DB: 0 keys; key plus content-hash matches: 0 rows. Of 501 unique valid uploaded chunk hashes, 0 occur in live chunks. Live ingestion statuses: `{"test_only": 12, "processed": 40}`. This is identity/presence matching only; it does not establish approved ingestion, missing-per-document embeddings, or retrieval quality. The archive contains 501 document keys absent from live; the live DB has 52 documents (40 processed, 12 test_only), 81 chunks and zero embeddings. The upload's 501 unique valid chunk hashes have zero exact live hash matches. The 235 URL references absent from live are candidate new references only; the number of genuinely new publisher/source entities is not determined without source identity/redirect review.

Coordinate-role comparison is in the manifest and audit CSV. The live CHECK accepts coordinate-bearing `property_reference`, `representative_point`, `visitor_entrance`, and `test_fixture`, while `unknown` is valid only with null coordinates. Seven uploaded destination rows are incompatible: five have unsupported raw roles (`unesco_component_reference` 1, `village_reference_point` 3, `mapped_building_reference` 1) with coordinate pairs, and two use `pending` with null coordinate pairs. All 54 coordinate-evidence rows and their source/status field schemas are inventoried; per-record source refs are linked where the uploaded IDs match. Proposed normalization is conservative: retain supported property_reference/representative_point labels; leave pending and unsupported roles raw in staging; only a human may map a sourced feature to representative_point or property_reference. No reference point is normalized to visitor entrance.

## Existing implementation and remaining work

Already implemented: canonical destination identity and aliases/parent relationships; source registry and destination-source links; import-batch tracking; existing-record enrichment review proposals; claim evidence and publication-gated production views; knowledge document/chunk/embedding storage and owner RAG application boundary; outbound external-link/referral support.

Not established by this snapshot: a general new-identity candidate queue, normalized administrative-area hierarchy, separate localized-content records, distinct verified access points, or temporal opening/access facts. Their status and dependencies are documented in the reuse/gap matrix. No partner schema/tables were found; partner architecture documents are proposals, not deployed structures.

## Recommendation / decisions needed

1. Freeze current destination identity and evidence contracts by reusing existing `knowledge.*` objects.
2. Decide whether new candidate staging can be represented with current import-batch/proposal structures; if not, approve a minimal review-only queue before any DDL.
3. Approve official administrative identity source, coordinate-role vocabulary and localization API contract before proposing schema changes.
4. Keep partner ERD deferred until owner decisions on scope, authorization and verification are recorded.
5. Before any Stage 2+ import, reconcile the `2` possible identity rows and all source/hash conflicts in the CSV; require editorial publication approval separately.

**No DDL/DML, migration, import, publication, deployment or database write was performed.**
