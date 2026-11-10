# Rahgard 15-Day Traveler Vertical Acceptance

Date: 2026-11-10  
Branch: `feat/rahgard-15day-journey-acceptance`  
Base and final HEAD: `f627702472272dc01f16141f324033b989522081` (no commit created)

## Decision

**NO-GO for full vertical-slice acceptance.** The live Persian traveler journey reached the truthful `needs_confirmation` response and proved that the 15-day request, 13 user turns, simulated assistant calls, trip history and deletion survive the real FastAPI/PostgreSQL boundary. The production destination catalogue was empty. The 15-day four-stop itinerary editor was exercised as an explicitly test-only Playwright fixture; its recommendation and itinerary calls were intercepted, so this run does not prove positive recommendation/itinerary persistence through FastAPI and PostgreSQL.

**Gate A — integrated engineering acceptance: FAIL (one remaining evidence gap).** A positive, isolated test-only recommendation-to-itinerary journey must still exercise the actual authenticated API and PostgreSQL persistence path. No fixture was inserted into or published through the production catalogue to force that result.

**Gate B — real traveler MVP acceptance: BLOCKED.** No authorized live provider call was made, and no owner-approved published destination content was available. There is no evidence here of real model behavior or real-data recommendation quality.

## Git and preservation

- The task-specified starting SHA (`d55dcda32d7465904ba60687d4d1d5875e2ce57d`) did not match the checked-out integration branch. Actual starting HEAD was `f627702472272dc01f16141f324033b989522081`; its upstream was synchronized 0/0 at preflight.
- Created the requested separate task branch from that actual integration HEAD. The task branch has no upstream configured. Final HEAD is unchanged.
- Existing untracked `artifacts/acceptance/rahgard-mvp-closure.json` and `docs/implementation/RAHGARD_MVP_VERTICAL_SLICE_CLOSURE.md` were preserved unchanged.
- No staging, commit, push, merge, rebase, reset, clean, or deployment occurred.

## Delivered changes

- The assistant-turn API now keeps the original stored trip request in the bounded model context after the recent-message window advances, while preserving the latest correction and keeping AI hints advisory. It adds the original request once, caps it at 1,200 characters, and retains at most eleven recent messages for a 12-message total.
- The authenticated browser harness now exercises a Persian 15-day request, corrected budget denomination and traveler count, 13 persisted user turns, simulated Chat consent/idempotency, explicit field-by-field advisory decisions, mandatory accessibility/hard constraints, honest recommendation blocking, history/reopen and deletion.
- The PWA separates local conversation notes from consented remote-AI processing in fa-IR, en-US and ar, explains that prompt chips only fill a draft, shows the recorded trip duration, and keeps AI suggestions from silently mutating the confirmed profile.
- The browser harness captures 15-day Persian and 10-day English/Arabic four-stop partial itinerary fixtures. Their API routes are intercepted in Playwright and the report labels them synthetic/test-only.
- Added a service-level regression for a 15-day partial plan with four evidence-bearing stops and eleven unplanned days.
- No migration, production catalogue content, RAG implementation, provider architecture, or production data changed.

## Browser evidence

The final run used Chromium 156.0.8078.47, real Vite, real FastAPI, a fresh guarded PostgreSQL 17 disposable container on loopback port `59584`, fake SMS, and the in-process simulated Chat gateway. The helper verified the disposable-database marker and application role. It applied migrations 0000–0011. The container was stopped and removed by the task runner (cleanup exit 0). No request reached an external service.

Final sanitized report: [report.json](../../artifacts/visual-qa-task15d/run-2026-11-10T04-28-10-931Z-31776/report.json)

The report records three locale journeys and twelve screenshots: empty production catalogue at mobile 390×844 and desktop 1440×1000, plus clearly labeled partial-plan fixtures at the same viewports. For `fa-IR`, the fixture contains 4 stops over 15 days and 11 unplanned days. For en-US and ar, the fixture uses 10 days, 4 stops and 6 unplanned days. Screenshot review found no phone, OTP, cookie, session token or raw traveler request text. The empty-catalogue screenshots also show existing general home-page inspiration cards; they are not API recommendations and the live recommendation response remained `needs_confirmation`.

## Verification actually run

| Check | Result | Exit |
|---|---:|---:|
| Focused UI regression: `vitest run src/trip/TravelerJourney.assistant.test.tsx src/trip/TravelerJourney.test.tsx src/trip/TravelerJourney.clarification.test.tsx` | 3 files, 11 passed | 0 |
| Full frontend suite: `npm.cmd test` | 13 files, 109 passed | 0 |
| Frontend production build: `npm.cmd run build` | TypeScript + Vite + PWA build passed | 0 |
| Focused backend assistant/recommendation tests | 49 passed, 8 skipped (guarded DB tests before disposable setup) | 0 |
| Guarded PostgreSQL assistant tests: `tests/test_assistant_postgres.py` | 8 passed | 0 |
| Final full backend suite from `backend/`, with unique backend-local `--basetemp` | 261 passed, 12 skipped, 1 Starlette/anyio deprecation warning | 0 |
| Itinerary/recommendation/service-contract focused suite | 31 passed, including the new 15-day partial service test | 0 |
| Ruff on changed backend files | all checks passed | 0 |
| `node --check frontend/scripts/traveler-e2e.mjs` | passed | 0 |
| Final browser run | 3 locales passed; 12 screenshots; 0 page errors; external requests blocked | 0 |
| Disposable PostgreSQL cleanup | stopped and removed task-created container | 0 |
| `git diff --check` | passed | 0 |

The first full backend attempt failed during seven test setups because pytest could not enumerate the user-level temp directory (`PermissionError`); 253 tests had passed and 12 skipped before setup errors. It did not reach those seven test bodies. Re-running with a unique `.venv/pytest-task15d-full-20261110-a` basetemp passed (260 passed, 12 skipped). After adding the 15-day service regression, the final backend rerun with a second unique local basetemp passed at 261/12. No root `.env` was read.

Two initial browser runs failed on harness assumptions that expected only two consent fields. The actual reviewed 15-day profile also required a field-specific traveler-count decision. The harness was corrected to make and acknowledge each rendered advisory choice separately; safety/access requirements remained outside the waiver loop. The final browser run passed. These earlier failures are retained here as test-fix history, not counted as passes.

Full SQL contract suite 000–013 and the remaining guarded traveler/itinerary PostgreSQL positive persistence path were not run. The browser partial-plan fixture is not equivalent to that persistence evidence.

## Changed files

- `backend/app/api/assistant.py`
- `backend/tests/test_assistant_api.py`
- `backend/tests/test_assistant_postgres.py`
- `backend/tests/test_chat_adapter.py`
- `backend/app/modules/itinerary/tests/test_itinerary_service.py`
- `frontend/scripts/traveler-e2e.mjs`
- `frontend/src/trip/TravelerGuidance.css`
- `frontend/src/trip/TravelerJourney.assistant.test.tsx`
- `frontend/src/trip/TravelerJourney.clarification.test.tsx`
- `frontend/src/trip/TravelerJourney.tsx`
- `docs/implementation/RAHGARD_15_DAY_TRAVELER_VERTICAL_ACCEPTANCE_2026-11-10.md` (this report)
- `artifacts/acceptance/rahgard-15-day-acceptance-2026-11-10.json`
- Twelve sanitized browser screenshots and one sanitized browser report under `artifacts/visual-qa-task15d/run-2026-11-10T04-28-10-931Z-31776/`.

## Remaining blocker and next action

The immediate release-acceptance gap is one guarded browser run that injects clearly labeled test-only evidence at the application test boundary, then exercises recommendation creation, 15-day partial itinerary creation, edit/save, and reopen through real FastAPI and PostgreSQL. Keep production catalogue views empty and assert the fixture cannot escape the test boundary. Separately, Gate B requires owner approval for real provider configuration/calls and editorially approved, source-valid destination content.

No shared database (including port 55433), root `.env`, live provider, paid service, real SMS, RAG service, or production data was accessed or changed.
