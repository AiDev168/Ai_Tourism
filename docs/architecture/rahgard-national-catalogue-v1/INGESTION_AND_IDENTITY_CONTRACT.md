# Ingestion and Identity Contract

**Status:** Proposed additive contract based on the Stage 1 uploaded archive and live schema snapshot. It does not authorize import, publication, source creation, or a live write.

## 1. Ingestion boundary

The canonical catalogue remains `knowledge.destinations`; source identities remain `knowledge.knowledge_sources`; existing `operations.dataset_import_batches` continues to represent an import run; existing enrichment proposals remain the path for changing an already-resolved destination. A new `knowledge.destination_candidates` queue is only for newly discovered, unresolved, conflicting, or suspected duplicate identities. It is not a shadow production catalogue and is never directly queried by traveler APIs or RAG.

Use an immutable upload envelope:

1. **Batch** — existing `dataset_import_batches.batch_key` identifies the logical import. Include the uploaded archive SHA-256 and parser-contract version in deterministic batch key material. A human label alone is not identity.
2. **File** — proposed `operations.dataset_import_files` stores archive-relative path, byte length, SHA-256, format and normalized header/schema signature. Do not use basename alone because archives can repeat names.
3. **Row** — proposed candidate records preserve the raw source row and exact source spelling. Prefer a supplied stable source record ID. If absent, use a stable row locator (`sheet/table + source row number` or CSV logical row number) scoped to `file_id`, plus SHA-256 of canonicalized row bytes.
4. **Mapping** — parser mappings are versioned by source/dataset and column header. An unrecognized or ambiguous field stays in `raw_record`; it is not silently discarded or coerced.

The 2026 Stage 1 archive contained 236 archive members including 17 nested ZIPs, 128 CSV files, 1,278 reconciliation rows, and a byte-identical repeated 10-row Alborz CSV payload in two deliveries. The repeated payload is an idempotency test case, not evidence of a duplicate real-world place. It also contained 533 document rows/501 unique document keys and 531 chunk rows/501 unique hashes; none matched live document keys/chunk hashes. These figures characterize that audited archive only.

## 2. Idempotency and conflict behavior

| Input condition | Required result |
|---|---|
| Same batch key, archive hash, parser version | Return prior batch result; no new file, row, source or destination writes. |
| Same batch key but changed archive bytes or parser contract | Reject as identity conflict; create a distinct explicitly versioned batch only after operator action. Never mutate old snapshots. |
| Same batch + relative path + same file SHA | Reuse the file row and candidate rows; no duplicates. |
| Same batch + relative path + changed file SHA | Mark file conflict; preserve both file hashes through an explicit new batch/version. Do not overwrite the existing file identity. |
| Same `file_id` + `source_record_key` + same row SHA | Idempotent no-op. |
| Same file/key with changed row SHA | Quarantine as `conflict`; keep old and new payload versions or create a separate immutable candidate revision. Require review. |
| New external record key | Insert a candidate, even if names appear similar; identity review follows. |
| Missing external key | Use stable row locator, never a transliterated name alone. |

Use database uniqueness for these invariants and importer transactions for each file or bounded row batch. Import result records include inserted/reused/conflict/rejected counts. A repeated import must reproduce the same logical candidate set and deterministic export order. Row checksums must be computed over a documented UTF-8 canonical JSON encoding (stable key order, normalized line endings, no lossy Unicode normalization of raw strings). A separate normalized search key may apply Unicode NFC, Persian/Arabic character folding, zero-width/half-space policy and whitespace folding; it never replaces the raw name.

## 3. Candidate field mapping

Each source file receives a versioned mapping profile with:

- source dataset key/version and publisher, if evidenced;
- raw column names and declared/observed types;
- source-record ID mapping or stable row locator;
- canonical candidate field mapping (name, type, locality text, province/county text, aliases, coordinates, raw coordinate role, description, source reference);
- field coercion rules, rejected values and schema signature;
- locale/language claims and whether text is original, translation, or unknown;
- licensing/usage status where supplied, without inferring permission from file presence;
- import operator, time, tool version and batch identifier.

Do not import uploaded URLs as source-register rows by default. Stage 1 found 235 unique valid uploaded URLs, zero exact matches to live source URLs, and no confirmation that each URL is a real or fetched source. Create a `knowledge.knowledge_sources` row only after the URL is opened/inspected, the publisher/title/type and actual claim relevance are captured, and the existing verification process approves it. A search result or uploaded URL string alone is not evidence.

Uploaded documents/chunks remain separately governed. The presence of uploaded text does not grant copyright or publication permission. Reuse the existing document/chunk/claim-evidence pipeline and preserve source URL, retrieval time, content hash, review and validity metadata. Embedding is optional and downstream.

## 4. Identity reconciliation lifecycle

Candidate status and canonical destination publication are separate dimensions.

```text
received -> parsed -> needs_review -> in_review
                               |-> conflict
                               |-> rejected
                               |-> resolved_existing
                               |-> approved_new_identity
```

Each review decision is append-only and records candidate, proposed target, relation, decision, reviewer, timestamp, evidence references, reason and policy version. Reconsideration appends a new review; it does not erase the prior outcome. Candidate row raw values are immutable.

Allowed identity relations:

- **`same_entity`** — both records denote the same physical/cultural entity. After independent evidence and reviewer approval, set `canonical_destination_id` to the existing row. Do not create a duplicate destination. Similar spelling alone is insufficient.
- **`part_of_or_within`** — candidate is a distinct independently meaningful entity that is a component inside a larger parent/site/area. Keep its own identity; after review, canonicalize as a separate destination and optionally set the existing `parent_destination_id` to the parent. This is not a merge.
- **`nearby_distinct`** — entities are near each other but distinct. Keep separate destination IDs; do not set parent-child just from proximity. Linkage may be represented as a reviewed relation only if a real domain need and evidence exist; Stage 2A does not add a general arbitrary relation graph.
- **`unresolved`** — evidence cannot determine identity or relation. Do not assign a canonical destination ID; stay out of publication and recommendation data.

**Required collision example:** Naqsh-e Jahan Square, Imam Mosque and Sheikh Lotfollah Mosque are distinct POIs. The two mosques may be `part_of_or_within` the square if the source supports that relationship; they are not the same entity as each other or the square. Nearby coordinates/name similarity are not merge authority. Existing uploaded candidates matching Meidan Emam/Naqsh-e Jahan remain review signals, not automatic merges.

Other resolution outcomes can be `duplicate_exact` (a duplicate uploaded row mapped to one candidate, preserving a duplicate audit record), `not_a_destination` (route, product or food routed to the correct separate collection), `out_of_scope`, or `insufficient_evidence`. These are workflow outcomes, not additional identity relation values.

## 5. Candidate-to-canonical operation

For an approved existing match, the command must verify the exact destination key/ID, append identity decision, and set `canonical_destination_id`; it must not modify canonical content. If requested content differs, create an existing `destination_enrichment_proposals` record against that exact target with source proposals and preserve its normal review process.

For an approved new identity, a separate operator command may create one row in `knowledge.destinations` with a deterministic reviewed `destination_key`, `status='needs_review'` (or the migration-approved non-active equivalent), `verification_status='pending'`, `record_origin` reflecting its real origin, `is_synthetic=false` only for genuinely sourced non-test data, and coordinate fields only if evidence/role passes existing constraints. Add source relationships only to verified source records. Link candidate to created canonical ID in the same transaction and append audit. This step still does **not** publish it.

If there are no defensible feature coordinates, leave canonical coordinates null and coordinate role `unknown`; it cannot enter the current spatial production view. Do not substitute city/village center. Stage 1 found seven uploaded point-role combinations incompatible with the current coordinate-role check; preserve their raw roles in candidate staging and require reviewed role normalization before any canonical write.

## 6. Deduplication and review queue

Discovery tooling may propose candidate pairs using exact IDs, normalized names, aliases, administrative hierarchy, source context and reliable geometry distance. It may not decide identity. Store candidate-pair review evidence in the review event, including the method/version and pair. Do not auto-merge based on transliteration, shared town, geographic proximity or common monument names. Stable identity decisions require a reviewer and evidence from inspected source pages/registry or exact feature matching.

The human queue must show raw and normalized name side by side, source/file/row, raw coordinate and stated role, possible canonical targets, relationship proposal, confidence/rationale, source links and contradictory claims. It must visually distinguish “nearby distinct” from “same entity.”

## 7. Test contract for the next implementation task

Tests must cover byte-identical repeated nested files; filename collision with different hash; changed payload under same source key; duplicate names in different counties; Persian/Arabic Unicode normalization while retaining exact raw strings; parent/component versus nearby distinct; Imam/Sheikh Lotfollah non-merge; unresolved never receives canonical ID; no candidate enters production views; invalid coordinate role remains in candidate staging; and idempotent import counts/data across two full runs. Tests use isolated disposable PostgreSQL and assert exact row counts, constraints, FK integrity, and production view exclusion.
