# Rahgard V2 — Independent planning acceptance audit (2026-11-21)

## Verdict: FULL TRAVEL-PLANNING ACCEPTANCE = NO-GO

Audited immutable GitHub commit: `9e490cf58ee5f6726009e0a2ab6757ef25830dd0`.
This is a **source/trace/report audit**, not an independent execution of the operator's Windows PWA, LM Studio or PostgreSQL. GitHub-hosted PNG screenshot bytes were not available to the reviewer through the available file connector; visual quality cannot be independently certified.

The narrower **LOCAL GO** in `docs/implementation/RAHGARD_V2_USER_ACCEPTANCE_2026-11-21.md` is supported for a **real LM Studio + simulated/publication-empty provisional itinerary and two-organization authenticated inbox**. It must not be generalized to user-facing catalogue-backed trip planning, verified route scheduling or two separate share URLs.

## Exact evidence, not inference

| Check | Source | Verified audit finding | Gate |
|---|---|---|---|
| Real model transport | `docs/implementation/evidence/issue23/lm-studio-trace.json` | 3 calls, 3 successes, model `qwen3-8b-abliterated`; remote `TaHa1_VL` blocked by missing private runner token | Local LM Studio PASS only |
| Catalogue-backed recommendation | same trace | `recommendationStatus=needs_confirmation`, `recommendationReason=destination_identity_unresolved`, `selectedDestinationCount=0`, `recommendationCount=0`, `unresolvedFields=[destination_resolution]` | **NOT PROVED** |
| Saved four-day plan | same trace; `frontend/src/trip/TravelerJourney.tsx` lines ~1267–1337, 1767–1812 | `provisional_unverified`, model-proposed names; verified itinerary creation requires `recommendations.status=available`. No verified travel times, opening hours or road routes | Provisional SAVE PASS; real planner **NO-GO** |
| Positive recommendation E2E | acceptance report and trace | `syntheticCatalogueAcceptance.status=test_only_dependency_override`; publication view remained empty. Dependency replacement does not prove the real catalogue/API-to-ranking path | **NOT PROVED** |
| Weather/difficulty/local cuisine | `backend/app/modules/recommendation/service.py` around lines 417–422 | Explicit code says these fields are known but cannot be evaluated by published catalogue and **do not enter ranking as a match**. The provisional AI prompt contains their free text, without structured feasibility verification | **PARTIAL, NOT REQUIREMENT-COMPLETE** |
| Geography and itinerary feasibility | `backend/app/modules/itinerary/service.py` around lines 58–67, 95–165, 244–267, 328–335 | Great-circle cluster/nearest-neighbor **display heuristic**, not road travel, feasibility, real weather/hours, or travel-time aware itinerary. Warnings `approximate_order_only` and `no_hours_or_routes_inferred` | **NOT VERIFIED AS PRACTICAL TRIP PLAN** |
| Two company "links" | `frontend/src/partners/PartnerWorkspace.tsx` lines 50–75 | One authenticated inbox item and one `<details>` combining request and itinerary, JSON `<pre>` for plan; backend exposes per-organization inbox and revisions, but separate navigable protected request URL and plan URL are not shown/verified | Inbox/revision PASS; **two links NOT DELIVERED** |
| Confirmation/eligibility | `frontend/src/trip/TravelerJourney.tsx` around lines 400–452, 1140–1211, 1246–1265 | Confirmed destination name/duration are distinct from catalogue identity. Manual edits invalidate prior confirmation, as required for safety. User still must confirm profile, request recommendations, then choose separate provisional AI action | Multi-step usability and real running-app result **UNVERIFIED** |
| Actual local UI being used by owner | isolated browser report; existing local PWA | Windows/Git HEAD equals source commit does **not** prove owner’s already running `localhost` PWA/server is serving that release. Separate disposable runner starts its own stack; SW/assets may be cached or old local pilot may still be running. Verify runtime fingerprint and SW asset hashes | **UNVERIFIED** |
| Visual inspection | GitHub PNG evidence paths | PNG files exist, but file connector supplied no usable bytes for two main PNGs; this review did not inspect visual screenshots | **UNVERIFIED** |
| Authentic remote provider | acceptance report | No remote request made because private token not present in process | **BLOCKED**, not connection failure |

## Mandatory correction to acceptance contract

Do not mark the overall application `LOCAL GO` solely because an unverified AI itinerary can be saved and companies can view an inbox event. Distinguish these separate outcomes:

- `INTAKE_AND_PROVISIONAL_GO`: real model/regex, confirmed user profile, explicitly unverified model suggestion, persistence and authenticated partner inbox.
- `CATALOGUE_BACKED_PLANNER_GO`: a full browser journey calls the **real** published-catalogue API and actual recommendation service (no dependency override), receives >=1 grounded destination with source/geo provenance in an *isolated, explicitly QA-approved catalogue*, produces a saved itinerary with each day’s coverage and transparent unknown feasibility. No synthetic public publication on a persistent instance.
- `SHARE_LINKS_GO`: two distinct authenticated addressable deep links (request and plan), stable trip/share/revision identity, per-organization ACLs, replay/expired/revoked denial and revision notices in inbox. No publicly exposed bearer URLs.
- `OWNER_RUNNING_BUILD_GO`: owner’s same local PWA/browser inspected for served SHA, SW and assets, tested against actual owner-reported failure state; no stale PWA false positive.
- `REAL_WORLD_TRAVEL_QUALITY`: metadata-backed opening times, accessibility, costs, weather, road travel time, and realistic day capacity either verified or prominently marked unknown; heuristic geography alone is insufficient.

## Codex immediate, outcome-oriented fix

1. **Reproduce on the same URL and installed PWA the owner uses.** Non-destructively fingerprint the served build and SW, verify local pilot container/release vs Git checkout; do not conclude synced Git means synced running app. Capture sanitized exact Persian steps, `reason_code`, `unresolved_fields`, `requirement_assessments`, active saved version, `destination_ids` and state of `confirmed/dirty`, and browser screenshot. Work only with owner-authorized QA data. A stale build must be fixed through approved local-only upgrade after preserving local pilot data; no VPS.
2. Repair the actual planning failure, not just wording. Ensure legitimate minimal confirmed requirements reach planner. Explain real absence of publishable Shiraz entries; use an explicitly consented/owner-approved disposable QA catalogue with *real recommendation repository* and approved source-bound records for a positive test; do not use `dependency_override` as primary evidence.
3. Preserve safety for hard constraints but make required missing fields and catalogue shortage actionable; keep simple primary action chat → confirm → generate when safe, with truthful provisional fallback when no trustworthy source data is available.
4. Make weather/difficulty/cuisine genuinely available to planning decisions where evidence exists (or explicitly unknown with honest rules); define practical scheduling and time/geography quality gates. If a complete travel plan is impossible due to absent source data, return precise CONTENT BLOCKED rather than pretending that an unverified names-only list is full planning.
5. Deliver the **two distinct protected URL views** for the original request and versioned itinerary to selected verified companies, in addition to authenticated inbox notifications. Test links when signed in as each company, revocation, revisions, tenant isolation, and denial on anonymous access.
6. Run reproducible full local browser E2E and owner-same-runtime smoke test; report separate statuses for provisional plan, catalogue-backed recommendation, trip itinerary quality and share links, plus full frontend/backend regression. Compare current SHA/asset hash to the running PWA, verify tenant authorization and no synthetic production exposure.
7. Keep branch `feat/rahgard-unified-travel-v2`, local-only Windows and GitHub; no VPS, DNS or persistent DB modifications, no migration 0022 on live; remote `TaHa1_VL` remains blocked without private process token. Produce sanitized evidence, commit/push exact outcome. Return honest NO-GO if real planning remains unsatisfied.

The owner specifically reports the planner still fails in the local UI. This observed defect outranks automated fixture PASS for overall acceptance.
