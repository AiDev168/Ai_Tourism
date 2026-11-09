# Natural-language trip intake V2 and retrieval readiness

**Status:** Phase 1 deterministic client-side extraction; no request persistence, destination verification, recommendation, model call, or production retrieval integration.

## Request format and privacy boundary

The traveler enters the complete request in one message. The browser retains the original text exactly in transient page state and extracts an ordered destination list, requested duration, and only explicit optional details. Nothing is sent to the backend or persisted. A later authenticated conversation API remains gated by ADR-0006. Extraction is deterministic; future model-assisted extraction must use the server-side Provider Gateway after the applicable architecture gates.

## Supported extraction

- Locales: Persian (`fa-IR`), English (`en-US`), and Arabic (`ar`); Western, Persian, and Arabic-Indic numerals are normalized for parsing while original request text is preserved.
- Duration: explicit day expressions and common number words, plus week expressions converted to seven days. The default configurable technical limit is 365 days (`VITE_MAX_TRIP_DURATION_DAYS`). The parser does not convert months to 30 days.
- Destinations: travel constructions are required; common city aliases and bounded preposition patterns extract user-provided place names and explicit sequences. A city name by itself is not a complete trip. The current deterministic alias list is intentionally small and is not a geographic authority.
- Optional fields: explicit traveler counts, budget amount/unit, interests and preference phrases are extracted when recognized. “With family” does not imply a count. Toman and rial remain distinct; no currency conversion occurs. Dates are currently unknown unless a future parser supports an explicit unambiguous format.
- Ambiguous or missing required values produce localized clarification in the same form. Conflicting durations and `or` destination alternatives require clarification. Editing the text clears stale extracted output; resubmission parses the new original text.

## Data semantics

Each extracted field contains a value, extraction state and evidence text. `unknown` optional values remain null. `missingRequired` and `ambiguousRequired` distinguish what is absent from what needs confirmation. `destinationVerification` is always `user_input_unverified`; extraction never means verification, eligibility, or recommendation. The captured summary includes the exact submitted request text.

## Retrieval readiness audit

Existing boundary (source and publication controls are implemented in the database; the application port remains a placeholder):

```text
reviewed external source + provenance
  → knowledge.destinations and editorial status
  → processed knowledge_documents / knowledge_chunks
  → knowledge.production_destinations + production provenance views
  → production_retrieval_documents / chunks / active embedding views
  → owner-controlled RetrievalPort (not implemented in this repository)
  → deterministic eligibility and ranking (not implemented)
```

The backend `app/modules/retrieval` package contains only its module placeholder. ADR-0003 defines an owner-controlled `RetrievalPort` seam, but no callable interface or adapter is currently present. The Phase 1 database includes publication/provenance views, search/vector indexes, and a transactional positive/negative gate test in `engineering/database-prep/sql/tests/005_production_publication_gate.sql`. That test covers verified publication, source revocation, unpublished destinations, and a synthetic destination/source/document explicitly excluded from production views; its transaction rolls back. The synthetic negative-control assertions were added in this task. The test was inspected, not executed against the live database.

Read-only verification against the running `ai-tourism-postgres`, database `ai_tourism_dev`, as `ai_tourism_app` returned:

| Production view | Rows |
|---|---:|
| `knowledge.production_destinations` | 0 |
| `knowledge.production_destination_sources` | 0 |
| `knowledge.production_retrieval_documents` | 0 |
| `knowledge.production_retrieval_chunks` | 0 |

The catalog contains no production-eligible destination candidates today. Recommendation generation is therefore correctly unavailable. No records, schema, seeds, or persistent data were changed.

### Blockers

1. The owner-approved retrieval contract and integration behavior have not been supplied/approved; do not build a competing RAG implementation.
2. No destination is published with reviewed source provenance. Existing UNESCO records are `needs_review` and are not recommendation candidates.
3. Production retrieval documents/chunks and active embedding space/vectors are empty. Embedding provider/model/dimension and semantic evaluation remain unselected.
4. Editorial review/publication and freshness ownership need an operational process and explicit acceptance criteria.
5. Authentication under ADR-0006 is unresolved; do not persist trip requests or plans.

### Ordered first-dataset plan

1. Agree on destination scope, accepted primary sources, rights/attribution, review owner, freshness cadence, and minimum localized content quality.
2. Ingest source-backed records through the existing staging/import workflow with provenance, retrieval time, content hash, explicit unknowns, and non-synthetic origin.
3. Review records and evidence, resolve coordinate roles and publication status, then publish through the approved editorial controls; never directly promote staging rows.
4. Verify positive/negative publication contract tests and expected row counts in an isolated test database; keep the live database unchanged.
5. Obtain the owner's `RetrievalPort` contract and integrate an adapter that queries only production views and preserves evidence metadata.
6. Select an embedding configuration only through the approved provider/retrieval decisions; evaluate multilingual recall and factual grounding before recommendations are enabled.
7. Add deterministic eligibility/ranking and source/uncertainty presentation only after usable published candidates exist.

## Known parser limits

Extraction is heuristic, not a named-entity recognizer or fact service. A small destination alias set is used first, with contextual pattern extraction for other text. Unsupported scripts/spellings, complex date ranges, indirect destinations, and less common compound number wording can need clarification. It must never silently convert that uncertainty into verified destination data.

## Verification record

- `npm.cmd test`: 31 frontend tests passed.
- `npm.cmd run build`: passed with the repository's pinned Vite/TypeScript toolchain.
- `npm.cmd run visual-qa`: 18 browser cases passed across all three locales and 360, 390, 430, 768, 1024, and 1440 CSS px. The browser tested the exact Persian family request and 4/7/14/30-day cases in all locales, direction switching, summary text retention, stale-summary clearing, missing-field clarification, keyboard focus, reduced motion, font/image loading, offline shell and cached assets.
- Review output: `artifacts/visual-qa-v2/` (kept separate from pre-existing modified screenshots), including `scenarios/fa-IR-exact-intake-360.png` for the exact Persian sample. Representative Persian mobile, English desktop, and Arabic mobile captures, plus the exact request/summary screenshot, were inspected. Automated axe WCAG 2.2 AA scan reported zero violations in the 18 captured page states; browser console errors and same-origin 404 responses were zero.
- Read-only database query through `ai_tourism_app` confirmed zero production destinations, destination provenance links, retrieval documents, and retrieval chunks. A raw-table review-status aggregate was denied by the app role, as expected; counts/status detail in this audit uses repository migration/handoff documentation. Existing SQL publication-gate test 005 was inspected but not executed against the live database because it uses insert/update statements inside a rollback transaction and would still touch non-transactional sequence state.
