# Rahgard: 15-day Persian traveler vertical-slice acceptance (Codex team execution)

**Date:** 2026-11-09
**Repository:** AiDev168/Ai_Tourism
**Starting integration branch:** feat/c1-c3-internal-installable-mvp-v1
**Product baseline:** 6680288c9b311f8089d9f2f5a692398d661cc382 (the latest conversational UX/history fix before this task)
**Owner-facing goal:** a genuinely usable Persian 15-day traveler journey, not another infrastructure-only or documentation-only milestone.
**Status:** Ready for LOCAL Codex execution. Not executed or passed merely by being defined.

## Mission

Complete and verify ONE end-to-end story using the existing React PWA, authenticated FastAPI,
real disposable PostgreSQL 17 and controlled mock AI gateway. A traveler describes a 15-day
trip in Persian; the assistant asks follow-ups or answers; the traveler changes the length
or budget, states mandatory access/terrain constraints, explicitly reviews structured
profile details and consent, and requests evidence-backed recommendations.
If approved destination data are absent, the correct observed response is honest
NO_EVIDENCE / EMPTY, not an invented recommendation or itinerary.

If a 15-day partial-itinerary UI fixture is necessary, label it test-only.
Do NOT claim it was sourced from approved live catalogue data or persisted in
PostgreSQL unless the actual authenticated API wrote and reloaded it.

The product already permits **1–365 days**, has a ten-day partial itinerary fixture,
and already has a working three-locale browser harness. Do not implement a new planner,
RAG engine, Chat gateway, database or parallel test harness.

## Agent assignments (run in parallel only in disjoint files/worktrees)

**Coordinator:** Verify current branch, upstream, exact HEAD, dirty worktree and existing
status; preserve user changes. Create a feature branch from the checked-out integration
HEAD (e.g. feat/rahgard-15day-journey-acceptance) only if safe. Keep one integrated
change set. Do not automatically merge, reset, clean, rebase or force-push.

**Agent A — Traveler UI and language:** Work on frontend/src/trip, user-facing text and
focused UI tests. Preserve Persian/Arabic RTL and English LTR. Make the chat/local-note
vs remote-AI choice obvious; verify prompt chips cannot become unintended traveler facts.
Make the 15-day state and confirmed details visible. Do not hide or lower mandatory
constraints. The traveler must never have to type the whole initial request again.

**Agent B — Browser acceptance:** Own only frontend/scripts/traveler-e2e.mjs and its
non-production fixture helpers. Extend the existing guarded Chromium E2E rather than
creating another runner. Keep the established three locales and owner-scope checks.
Create an explicit Persian 15-day scenario; validate browser form, persisted trip
duration, follow-up corrections, source/empty state and record reopening. Also test
a 15-day partial itinerary *only as a labelled test-only fixture* if it cannot pass
real evidence gates. Collect sanitized screenshot/report artifacts.

**Agent C — Backend and provider boundary:** Own backend tests and, only if a
reproduced defect requires it, backend application code. Check the assistant request
goes through authenticated CSRF-protected /assistant-turns, persists real user+assistant
messages and bounded candidate suggestions, and NEVER silently changes the confirmed
trip profile. The latest explicit correction wins, original trip context stays
available after 12+ messages, and hard/access constraints remain blocking.
Run real PostgreSQL integration tests on the disposable DB, not the shared DB.
No paid/real provider network calls.

**Agent D — Product/recommendation review:** Inspect recommendation eligibility,
source provenance and hard/soft-consent gates. Confirm that empty production
catalogue returns a truthful no-evidence result and never exposes fake destination
candidates as verified. Check no unverified hours, price, accessibility, travel time,
route, destination suitability or quality score appears. Report actual owner RAG
contract/data blockers; do not invent a ScaleRAG transport or implement its engine.

Coordinator should use one review of agent outputs; fix demonstrated defects,
not speculative refactors or a new task board.

## Non-negotiable safety constraints

1. **NEVER touch** the shared PostgreSQL container ai-tourism-postgres or TCP 55433;
   no drop/alter/migrate/reset of its databases or volumes.
2. Use ONLY the existing Start-Disposable-Mvp-E2E.ps1 helper. It launches a different
   ephemeral tmpfs PostgreSQL container and exports guarded AUTH_TEST_DATABASE_* vars.
   If guards fail, stop; do not bypass them. Stop only the disposable container
   identified by AI_TOURISM_MVP_E2E_CONTAINER in a finally block.
3. No real LLM/API calls or model credential use by default. Simulated gateway
   must be clearly identified in the report. A live TaHa1_VL/other provider test
   is a distinct, opt-in owner action and must NOT run as part of this task.
4. Do not log raw personal trip content, OTPs, session cookies, bearer tokens,
   provider prompts/responses with secrets, or database passwords into screenshots
   or committed artifacts. Do not publish candidate/editorial/research rows.
5. Preserve CSRF, owner-scoping, idempotency, profile-version consent binding,
   mandatory constraints, irreversible deletions, original-request provenance,
   and locale semantics. No booking, payments, SMS-provider activation or admin/partner scope.
6. Do not change 365-day technical limit to 3 days; verify 15 days, and ideally
   a separate 30-day intake case, remain allowed by default configuration.

## Scenario and acceptance checkpoints

A. Open the PWA in fa-IR, sign in using the existing fake-OTP test bridge
   (not a debug HTTP endpoint), and enter a natural Persian request for
   **15 days** with a specified destination and some interests. Save it to
   the disposable DB; re-read it through the authenticated trip API and assert
   duration_days=15. Verify no 3-day cap appears in the form or day-count control.

B. Continue the same conversation with two or more traveler turns. Include
   an explicit change of party size or budget and a *mandatory* constraint
   (e.g. wheelchair/step-free access or prohibited rough terrain). Verify
   correction semantics in the UI and database, no accidental field erasure,
   and that follow-ups do not auto-confirm any field.

C. With explicit checked remote-processing consent, ask the simulated AI.
   Browser must reach the REAL FastAPI assistant-turn route, the guarded
   mock gateway must receive no more than the expected test calls, and user
   and assistant messages must persist. Without consent, neither UI nor API
   may send a model request. Reopen an old suggestion without a new call;
   reject it and verify no profile mutation. Apply one bounded safe suggestion,
   then verify the save button remains gated pending review and field decisions.

D. Confirm only after explicit choices. Compare the authenticated PATCH
   payload and persisted server profile; the source of confirmation must be
   traveler_reviewed, not an AI-derived authority. When a must-have field
   cannot be verified against published data, recommender must block it.
   When there are zero eligible published destinations, response and UI
   must truthfully report empty/no-evidence without invented candidates.

E. If creating a 15-day test-only itinerary preview, show all 15 day slots,
   distinguish unplanned days, and do not fabricate attractions or visit details.
   Clearly separate intercepted/fixture state from actually persisted itinerary
   API evidence. Do not weaken provenance policy just to get a green test.

F. Reload the browser. Assert history, ownership isolation, consent version and
   empty/no-evidence state remain correct. Test at least desktop and mobile
   Chromium sizes in Persian; retain the existing three-locale smoke coverage.
   Ensure zero browser runtime errors and no external network requests in
   the simulated run.

## Local execution (Windows PowerShell 5.1; exact commands, adapt if already running)

    cd C:\Projects\Ai_Tourism
    git status --short --branch
    git rev-parse HEAD
    # Preserve dirty changes; establish a safe working branch before editing.
    # Guarded ephemeral database:
    . .\engineering\database-prep\scripts\Start-Disposable-Mvp-E2E.ps1 -ProjectRoot (Get-Location).Path
    $env:ASSISTANT_INTEGRATION_TESTS = '1'
    try {
        uv run pytest -p no:cacheprovider backend/tests/test_assistant_postgres.py -q
        if ($LASTEXITCODE -ne 0) { throw 'Guarded assistant PostgreSQL tests failed' }
        node frontend/scripts/traveler-e2e.mjs
        if ($LASTEXITCODE -ne 0) { throw 'Traveler Chromium E2E failed' }
        npm --prefix frontend run build
        if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
    } finally {
        if ($env:AI_TOURISM_MVP_E2E_CONTAINER) {
            docker stop $env:AI_TOURISM_MVP_E2E_CONTAINER
        }
    }

Run focused unit tests for the actual changed components and a single backend
regression pass. Avoid indefinitely rerunning unchanged test suites.
If Docker/browser image is missing, report a specific environment blocker and
complete static/API-level verification without inventing a green browser result.

## Done means ALL of the following

- A runnable 15-day Persian journey exists in the existing browser acceptance
  suite, not merely a fixture definition or a screen mock.
- Exact observed Git SHA, branch, test commands and counts are recorded.
- Real FastAPI + guarded disposable Postgres + actual Chromium are used;
  the LLM gateway is explicitly **simulated** unless separately authorized.
- Confirmed, provisional, unavailable and no-evidence states are distinguishable.
- The 1–365-day input capability remains intact; 15-day and 30-day cases are
  not silently capped or treated as exactly 3 days.
- Hard constraints, explicit advisory consent, source provenance, user ownership,
  message replay and long-history context have no regressions.
- Artifacts include sanitized status JSON/JSONL and a small number of useful
  browser screenshots; no secrets or raw personal details are committed.
- Report unresolved limitations explicitly, especially zero approved pilot
  catalogue, no live owner ScaleRAG contract, no authorized live provider calls,
  no approved production SMS/hosting/mobile gates.

**Final response:** Give an English engineering acceptance report and a concise
Persian owner summary. State work that is done versus still blocked. Never
auto-merge to the integration branch; present the feature branch/commit for
owner approval.
