# Rahgard P0 Product Recovery — Acceptance Report

Date: 2026-11-15
Branch: fix/rahgard-default-ai-relative-dates-gps-v1
Baseline: 5e2bd06a37f55c752a2705393c2a61b9e0586890
Decision: **NO-GO for release/deployment**. Focused code and isolated checks pass, but configured-vLLM, authenticated browser/PostgreSQL journey, backup/restore, and three-environment release proof were not available in this execution.

## Product corrections implemented

- **Semantic intake:** The initial request is persisted once and reused as the first assistant turn, avoiding a separate deterministic interpretation request and duplicate provider invocation. LLM field hints can populate editable candidates when bounded syntax and quoted evidence validate; deterministic extraction remains the fallback. Candidate fields carry llm/fallback source and do not confirm or overwrite the saved profile by themselves.
- **Relative dates and budget:** Relative offsets use saved traveler timezone/reference context and remain separate from trip duration. Budget keeps raw amount, scale, and currency. The acceptance test exposed colloquial «تومنه» being rejected by the strict syntax parser; it is now accepted as TOMAN without conversion.
- **GPS origin:** One-shot position requests reject invalid, stale, and low-accuracy fixes and expose only a coarsened approximate coordinate string. It is explicitly labeled approximate and does not claim a city. Explicit-origin detection was repaired to use valid Persian and Arabic Unicode patterns; manual or explicit trip origins are not replaced. No reverse-geocoding source is configured, so city resolution remains unavailable.
- **Requirement outcomes:** Known traveler values remain known even when the catalogue cannot verify destination-dependent facts. Hard constraints continue to block when unevaluable; ordinary known profile fields do not become consent blockers.
- **Empty catalogue:** Added a separate provisional_unverified editable itinerary path with owner-scoped persistence, optimistic revisions, unplanned days, and warnings. It is separate from approved catalogue recommendations and does not create production destination identities or factual citations.
- **Visual styling:** Existing styles were refined for clearer buttons, state feedback, and spacing. Screenshots are limited to the anonymous static PWA shell, with API requests stubbed locally.

## Exact reference scenario evidence

A focused candidate-contract regression used the required Persian request semantics and a controlled reference date (2026-11-15, Asia/Tehran). The constructed LLM field result was:

- Origin: مشهد
- Destination: شیراز
- Departure: 2026-11-17 (offset 2)
- Duration: 5 days
- Travelers: 5
- Budget: 30 million TOMAN, raw quoted denomination retained
- Interests: historical attractions plus the quoted historical-sites/gardens phrase

All seven fields in this test were labeled llm. This proves the adapter-to-candidate contract under a test response. **It is not evidence of a real vLLM request or real traveler acceptance.** The end date was not observed in an actual UI/backend journey.

## Verification actually performed

| Check | Result |
|---|---|
| Focused backend recommendation, assistant, Chat adapter, and provisional-itinerary suite | **110 passed**, 1 existing Starlette/anyio deprecation warning |
| Frontend Vitest command (package script runs all src/) | **177 passed, 19 files** |
| Frontend production build | **Passed** (tsc, Vite, PWA asset injection) |
| PWA build test | **2 passed** |
| Focused Ruff on changed backend modules/tests | **Passed** |
| Isolated PostgreSQL 17 migration 0017 runner | **Passed** earlier in this work session; network-disabled container/tmpfs, migration and ACL/cascade checks; container removed |
| git diff --check | **Passed** (line-ending advisory warnings only) |
| Static-shell Chromium capture, Persian mobile 390×844 and desktop 1440×1000 | **Passed**; no horizontal overflow or page errors; API deliberately stubbed |
| Existing npm run visual-qa | **Failed** on a stale .itinerary .outline selector; it did not exercise the new browser acceptance journey |
| Public HTTPS health | https://rahgard.hinaa.ir returned **HTTP 200**, TLS verification result 0; this does not prove the changed SHA is deployed |
| Authenticated real browser + configured private vLLM + PostgreSQL journey | **Not run** |
| LLM-unavailable fallback through actual browser/API/database | **Not run** |
| Backup and isolated restore rehearsal for this release | **Not run** |
| Physical Android acceptance | **Not run** |

Screenshots and machine-readable visual report:

- artifacts/p0-product-recovery/screenshots/before-fa-IR-exact-intake-360.png (HEAD baseline screenshot)
- artifacts/p0-product-recovery/screenshots/fa-IR-mobile.png
- artifacts/p0-product-recovery/screenshots/fa-IR-desktop.png
- artifacts/p0-product-recovery/screenshots/report.json

The after screenshots show the anonymous landing/intake shell only; they do not show a real authenticated trip, AI response, catalogue recommendation, or itinerary. The before image was recovered from the starting HEAD and is a prior visual-QA capture; it is not data or traveler-journey evidence.

## Persistence and migration

Migration 0017_provisional_itineraries.sql adds a separate owner-scoped table and does not alter existing traveler/catalogue rows. It passed the isolated PostgreSQL 17 test. It has **not** been applied to the live pilot. Existing live data counts were not queried or modified in this task.

## Release blockers

1. A real configured-vLLM call and authenticated end-to-end run are required to verify provider routing, persisted assistant response, extraction-to-editable-profile, provisional draft creation/edit/save/reopen, and fallback.
2. Local SSH attempts could not authenticate: the supplied SSH_SERVER_KEY value did not parse as a private key, and the available SSH-agent identity was rejected. No VPS command was run. Therefore a pre-deployment backup, restore rehearsal, application-only upgrade, deployed SHA check, and post-deployment browser acceptance remain unverified.
3. Browser evidence is static-shell QA, not the required actual product journey. The old visual-qa harness also needs its selector aligned before it can serve as evidence.
4. GPS yields an explicitly approximate coordinate origin, not a city, because no approved reverse-geocoding service or offline city index is configured.
5. No release SHA is claimed. The live HTTP 200 is the existing site's health only.

No shared database, production data, provider credentials, or paid calls were accessed. The authorized SSH_SERVER_KEY setting was read in the prior connection attempt but its value was never displayed, logged, or committed; it was rejected as an invalid private-key format. No database reset, migration against the live service, public deployment, or user-data mutation was performed.