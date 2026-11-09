# Phase 4 Pilot Readiness Report

**Run window:** 2026-11-08–09  
**Branch:** `fix/initialize-database-powershell-inspect-v1`  
**HEAD:** `a921277cd8488b6b5959429c7cb74ff5a05be462`  
**Decision:** **NO-GO for pilot**

## Summary

Phase 3 remains accepted. This Phase 4 run closed bounded internal readiness work: documentation drift was reconciled, a minimal provider-neutral capability seam with deterministic tests was added, the backend/frontend checks passed, and the real three-locale browser path was exercised against a fresh disposable PostgreSQL 17 database. The browser showed the honest empty production catalogue. No reviewed pilot dataset, owner-RAG interface, real provider activation, staging host or device acceptance was available.

The engineering evidence does not satisfy the owner/data/security/operations release gates. Do not treat this report as pilot or production approval.

## Workstreams

| Workstream | Result |
|---|---|
| Owner RAG | **Blocked.** `backend/app/modules/retrieval` remains a placeholder. Structured destination retrieval is not semantic RAG. No owner callable contract or approved evaluation set was supplied; no adapter was invented. |
| Pilot geography/content | **Blocked.** No pilot geography, source-rights policy, named reviewer, freshness policy or publication authority was approved. No source registry or production data was changed. Browser API returned zero approved destinations. |
| Deterministic recommendations | **Verified as guarded.** Phase 3 constraint/consent tests and current browser flow preserve mandatory blockers and explicit `not_evaluated` consent. Real recommendation quality remains unverified because production content is empty. |
| AI Provider Gateway | **Partial.** Added an internal injected capability seam and deterministic fake tests. No routing, live provider adapter, fallback, configuration API or admin control plane exists. No external calls were made. |
| Auth/privacy operations | **Implemented locally; production gated.** Auth remains disabled by default. Production SMS, carrier testing, account recovery, admin MFA/bootstrap/recovery, retention, monitoring and incident ownership remain open. |
| PWA/staging/mobile | **Browser verified; staging/device gated.** Local Chromium journeys passed. No approved HTTPS staging origin or physical Android/iOS devices were supplied; no deployment occurred. |
| Documentation | **Updated.** Historical audits were preserved with dated addenda; ADR-0006 status now distinguishes accepted traveler auth from production/admin gates. ADR-0007/0008 and Proposed ADR-0009–0013 were not changed. |

## Database and content evidence

- No repository migration was added or modified.
- SQL migrations 0000–0010 were applied only to a disposable cluster named `ai-tourism-phase4-pg17-20261108-a921277`, database `ai_tourism_auth_test_phase4_20261108`, bound to `127.0.0.1:55497`, using `ai_tourism_app` for guarded application tests and a private random marker. PostgreSQL was `17.11` (`170011`), PostGIS `3.6.4`, pgvector `0.8.7`; database storage was tmpfs.
- SQL tests `000`–`013` all passed (14 files). The exact immutable seed/migration row manifest was `698/698`; the final-row report showed zero runtime auth/traveler records before integration tests. Lifecycle classifier passed all listed recognized/invalid-state cases.
- The historical SQL grant migration contains a hard-coded `GRANT CONNECT` target named `ai_tourism_dev`. To execute that unchanged migration, an empty placeholder database with that name was created only inside the disposable cluster. It was never connected to, migrated or seeded; no shared service/container/volume was accessed. The entire disposable cluster was stopped and removed, with no named data volume.
- Guarded PostgreSQL integration tests passed against the named disposable database. Browser E2E subsequently confirmed an empty approved catalogue in each locale. No candidate pack was imported and no production view was published or modified.

## Browser evidence

Command: from `frontend/`, `node scripts/traveler-e2e.mjs` — exit 0. Browser: Chromium `156.0.8078.47`; live Vite, FastAPI and the disposable PostgreSQL 17 database; fake SMS only.

All three locale journeys (`fa-IR`, `en-US`, `ar`) passed through OTP, persisted trip/conversation, consent snapshot, empty catalogue, history/reopen, ownership and CSRF denial, deletion/logout, and no-store checks. The report recorded zero external requests/responses and zero browser page errors. Twelve sanitized screenshots were manually inspected: mobile/desktop empty-catalogue and test-only ten-day partial-fixture captures per locale.

Artifacts: `artifacts/visual-qa-task32/run-2026-11-08T15-15-28-643Z-55016/` (ignored local QA output). The partial-plan fixture was intercepted in Playwright, labeled test-only and not written to PostgreSQL or production views. The screenshots show the page's separately labelled illustrative inspiration section alongside an empty API-backed recommendation state; those inspiration cards are not evidence-backed recommendations.

## Verification results

| Check | Command / working directory | Result |
|---|---|---|
| Backend full unit/API suite | `uv run pytest -p no:cacheprovider tests -q --basetemp ..\.venv\pytest-phase4-a921277` from `backend/`; dummy process-only `DATABASE_PASSWORD`, integration opt-in off | Exit 0 — **138 passed, 4 skipped**, 1 Starlette deprecation warning. Skips were the three auth PostgreSQL tests and one traveler PostgreSQL test, each requiring the explicit disposable DB opt-in. |
| Guarded PostgreSQL suite | `uv run pytest -p no:cacheprovider tests/test_auth_postgres.py tests/test_traveler_postgres.py -q --basetemp ..\.venv\pytest-phase4-postgres` from `backend/`, with all `AUTH_TEST_DATABASE_*` values bound to the disposable target | Exit 0 — **4 passed**, 1 warning. |
| Frontend tests | `npm.cmd test -- --reporter=dot --pool=threads --maxWorkers=1` from `frontend/` | Exit 0 — **8 files, 83 passed**. |
| Production build/type check | `npm.cmd run build` from `frontend/` | Exit 0 — TypeScript and Vite production build passed. |
| Browser E2E | `node scripts/traveler-e2e.mjs` from `frontend/` | Exit 0 — 3 locale journeys; 12 screenshots. |
| SQL contracts | `engineering/database-prep/sql/tests/000_extension_versions.sql` through `013_task32_addendum_review_contract.sql`, run with `ON_ERROR_STOP` as database owner inside the disposable cluster | Exit 0 — **14/14 passed**. |
| Database lifecycle classifier | `engineering/database-prep/scripts/Test-Database-Lifecycle-Classifier.ps1` | Exit 0 — all reported classifier/opt-in cases passed. |
| Ruff | `uv run ruff check backend` from repository root | Exit 0 — all checks passed. `uv` warned that inherited `VIRTUAL_ENV` pointed to another project and used this repository's pinned environment. |
| Diff whitespace | `git diff --check` | Exit 0. |

The first backend run without an explicit basetemp reported **7 setup errors** and 128 passes because pytest could not scan the user-wide temp directory (`PermissionError` under `AppData\Local\Temp\pytest-of-coole`). No test assertion failed. Rerunning with unique basetemp under the project `.venv` passed as reported above.

## Remaining gates before pilot GO

1. Owner supplies and approves the actual RAG interface/provenance contract and evaluation set.
2. Owner selects pilot geography and approves source rights/classes, source registry rules, editorial reviewer/publication authority, locale quality and freshness operations; then approved source-backed coverage is curated and verified.
3. Owner approves provider/data-processing region, secret management, privacy/consent, cost/rate limits and explicit live-call activation; any real provider integration must remain behind ADR-0008's server-side gateway.
4. Owner approves SMS vendor and route only after representative MCI, Irancell and Rightel delivery tests, plus production authentication settings and recovery/support operation.
5. Administrator MFA assurance, bootstrap, recovery/break-glass, authorization matrix and provider-secret controls must be approved and implemented before any privileged control plane is exposed.
6. Conversation/backup retention, deletion operations, incident ownership and production monitoring must be resolved.
7. Hosting region, HTTPS origin, trusted proxy, backup/restore and staging credentials must be approved. Real Android Chrome and iOS Safari installation/full-screen/offline acceptance remains unrun because physical devices and an approved staging origin were not supplied.

## Changes and safety

Changed files are limited to: root README status, two architecture indexes, dated addenda to the authentication decision brief and MVP functionality audit, the internal AI capability gateway and its tests, this report, and the linked Phase 3/Phase 4 status document. No migration, production content, RAG implementation, provider configuration, `.env`, shared database, remote service, or deployment was changed.

No commit, push, merge, branch change, PR or deployment was performed. Final worktree details are in the task completion message.
