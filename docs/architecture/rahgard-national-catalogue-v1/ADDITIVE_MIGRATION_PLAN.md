# Additive Migration Plan

**This is a proposed future plan only. No migration was authored or executed in Stage 2A.** Implement as a sequence of reviewed migrations on an isolated disposable PostgreSQL 17/PostGIS instance first. Preserve all live rows and views until a versioned replacement is validated.

## Phase 0 — Pre-migration contract checks

1. Read the exact live `schema_migrations` ledger and inspect current columns, constraints, grants, view definitions and owner/app roles at migration time; Stage 1 is a dated snapshot.
2. Confirm `geo` schema does not already exist and no equivalent localization/access assertions were added after Stage 1. Stop and adapt the package if the remote/live schema advanced; do not create duplicates.
3. Check PostGIS version/SRID and installed extensions. Do not require `pg_trgm` unless separately approved and measured.
4. Take/verify a pre-migration backup under the operational procedure. Record counts and checksums for all affected relations/views, plus user/travel data counts. Stage2A has no write authorization.
5. Obtain owner decisions for authoritative administrative source, aliases/locales/coordinate policy and freshness. Partner migrations require the separate ADR approvals listed in `DECISION_LOG.md`.

## Phase 1 — Administrative hierarchy

1. Create `geo` schema and `admin_area_releases`, `admin_areas`, `admin_area_aliases` with PK/FK/check/unique constraints.
2. Add nullable `knowledge.destinations.admin_area_id bigint REFERENCES geo.admin_areas` and index concurrently where migration framework supports it safely. Keep legacy free-text province/city unchanged.
3. Load only an authoritative official release into the new hierarchy with release source URL, checksum and effective date.
4. Produce a dry-run mapping of existing destinations using exact code/alias and reviewed parent chain. Do not use fuzzy name match to write FK. Ambiguous/unresolved rows remain NULL and are exported for review.
5. Backfill in bounded, idempotent batches; verify row count unchanged and no legacy text changed. Never set `admin_area_id` to an administrative centroid or destination geometry.

Rollback: nullable FK/data is additive. To rollback application code, ignore `admin_area_id`; retain reference data. Dropping hierarchy tables is not an automatic rollback and is unnecessary; only remove them in a separately reviewed later migration after confirming no references.

## Phase 2 — File/candidate review

1. Create `operations.dataset_import_files` with batch FK and unique file identity.
2. Create `knowledge.destination_candidates` and append-only `destination_candidate_reviews` with constrained status and exact identity relation values.
3. Grant importer/reviewer roles least privilege. Public/traveler application role receives no candidate/raw access. Do not add candidate rows to any production view.
4. Implement parser/import command in dry-run mode first; enforce archive traversal, size, row count, encoding and JSON schema limits.
5. Validate idempotency on the audited repeated Alborz file pair and conflict cases in isolated PostgreSQL. No owner-upload data import is covered by this architecture task.

Rollback: disable importer/API routes and revoke writes; keep candidate audit rows. Do not cascade-delete candidate rows or accepted canonical links. Existing canonical data untouched.

## Phase 3 — Presentation, coordinate access and temporal facts

1. Create destination localizations and alternate-name relations without dropping existing `canonical_name` or `aliases`.
2. Add a reviewed one-time backfill only where content locale is known; unknown locale stays unmapped, not guessed. Existing alias manifest remains compatibility input until a separately tested migration replaces it.
3. Create visitor access points, visit-duration evidence and typed-by-contract operational assertions. Enforce geometry and source constraints; retain observation time and freshness policy key.
4. Add indexes (BTREE by destination/status/locale/time; GiST for geometry). Evaluate query plans on realistic synthetic volume in isolated test data; do not benchmark against live production with large scans.
5. Build new versioned production views side-by-side, compare exact expected membership/provenance against current views, then switch readers only after acceptance. The new view must not widen eligibility.

Rollback: route back to old views and old response projection; new rows remain stored and unpublished. Do not drop or replace legacy columns/views during the rollback window.

## Phase 4 — Cursor catalogue API

1. Add typed query and response models plus signed cursor verifier.
2. Implement keyset pagination on published views with bounded query timeout and deterministic tie-break.
3. Preserve old response fields and request compatibility; dual-test old and new client versions.
4. Ship client cursor consumption and pagination tests before removing the old all-at-once expectation.
5. Monitor cursor invalidation/503/error counts and query execution time using privacy-safe aggregate metrics.

Rollback: disable cursor parameters/use first page compatibility behavior; do not change stored data or weaken source filters.

## Phase 5 — Partner tables (strictly gated)

Only after owner approval of ADR-0006 and ADR-0009–0013 decisions relevant to first scope:

1. Create `partner` schema and table constraints with organization-scoped composite FKs.
2. Create DB roles/grants and RLS policies before enabling any route. Runtime role cannot own tables or bypass RLS; migration role separate.
3. Run positive and negative tenant tests through actual API and direct SQL as runtime role. Include nested cross-tenant FK attack, membership revocation, reviewer/author conflict, and public field leakage tests.
4. Add moderation/event history and explicit approved public projections; do not expose tables directly.
5. Begin only a small approved pilot scope with no lead/referral data unless separately authorized.

Partner migration rollback is app-feature disable plus restrictive grants; preserve partner submissions and audit. Do not drop a tenant schema containing user-submitted data as a rollback shortcut.

## Required migration acceptance checks

- Before/after table counts for all existing canonical, source, document/chunk, embedding, traveler, trip, conversation, itinerary and migration-ledger relations exactly reconciled; no old records disappear.
- All new table counts match deterministic fixture input; repeated import adds zero duplicates.
- `PRAGMA` not applicable; check PostgreSQL `pg_catalog` FK/check/index/grant definitions, `postgis` geometry SRIDs and `ANALYZE`/query plans in isolated DB.
- `SET TRANSACTION READ ONLY` app-role tests for published views; application role cannot read candidate raw JSON, partner evidence or secrets.
- Test every production view has no candidate, synthetic, unpublished, unverified, revoked or stale fact leakage.
- Migration failure test at each phase can roll back transaction or safely resume; no migration runs on a shared DB without a separate explicit execution task and approved backup.
