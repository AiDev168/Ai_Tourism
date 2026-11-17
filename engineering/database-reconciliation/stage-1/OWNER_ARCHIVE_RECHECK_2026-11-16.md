# Owner archive recheck — 2026-11-16

**Source:** original user-provided `دیتابیس - توریسم.zip` available in the ChatGPT execution container; this raw archive has **not** been committed to the public GitHub repository. Results are from a bounded in-memory recursive ZIP / UTF-8 CSV inventory run, not from PostgreSQL imports. No live database changes.

| Metric | Independently observed |
|---|---:|
| Outer archive SHA-256 | `7e9a27654535590f593aeea8e9f7ba9422fb128ca2c4fc93129061c544aff397` |
| Outer archive size | 1,209,656 bytes |
| Non-directory members, including nested archive entries | 236 |
| Nested ZIP files | 17 |
| CSV delivery files | 128 |
| Unique CSV byte contents (SHA-256) | 118 |
| Repeated CSV content groups | 10 |
| Redundant CSV deliveries | 10 |
| All CSV row instances, including repeated deliveries and research tables | 3,904 |

The duplicated content groups arise from the previously observed repeated Alborz Batch 001 delivery under `ALBORZ_DELIVERY_FIXED` with distinct nested paths. Duplicate CSV **delivery** is not equivalent to duplicate geographic destination identity. The earlier Stage 1 source-to-live identity comparison found 167 unique destination keys (165 unmatched, two review leads); this recheck does **not** claim a live import of those keys.

## Why there are still zero real imported candidates

The owner archive was not present in the Codex local workspace when commit `098fa13a` was produced, although it was available to ChatGPT as a conversation attachment. The importer and private partner workspace were built and tested with fixtures, but there is no proof of archive staging in the real browser/API/PostgreSQL flow or of published destinations.

The public GitHub repository is not an appropriate location for potentially rights-restricted raw third-party descriptions and private research bundles. Supply the archive to the **local** authenticated ingestion route or an owner-controlled private storage location; do not make public archive uploads a requirement for source review.

## Implementation review: verified code-path gaps

At `df8957f7a302e7dc61b23536de46ca588bac24b8`:

- `backend/app/api/catalogue_review.py` only implements ZIP upload, candidate list and identity decision; it has **no endpoint to create canonical destinations from approved new candidates, enrich claims/sources, or publish a verified canonical destination**. These are genuine delivery gaps relative to the one-mission outcome; not reasons to redesign the schema.
- `frontend/src/admin/catalogue/CatalogueReviewPanel.tsx` displays the first 50 candidates only and does not consume its API's `next_cursor`; national-scale review needs pagination and batch-action/queue filters. Every candidate row also shares a single form state for target, relation, evidence and reason, which risks applying the wrong review fields to an item.
- The `unresolved` relationship combined with `accept` currently yields `approved_new_identity`; distinguish an explicit **new-identity approval** from an unresolved/insufficient-evidence case to avoid confusing reviewers.
- The new `frontend/src/trip/destinationCatalogApi.ts` consumes `/api/v2/catalog/destinations` page by page, but no authenticated full browser-to-API-to-Postgres acceptance was run. Backend unit tests/SQL runner are positive evidence for modules, not for the complete traveler journey.

## Acceptance still required

Use the owner archive in an isolated, authenticated stack and demonstrate: exact stage counts and idempotent reimport; provenance/identity review; authorized canonical creation and publication without weakening `knowledge.production_destinations`; national search and itinerary saved/reopened from approved data; partner own-tenant workflow and negative cross-tenant browser tests. Preserve real data and the live VPS deployment unless explicitly authorized.

**Do not repeatedly re-audit or refactor Stage 1. Close these actual product gaps in one coordinated implementation.**
