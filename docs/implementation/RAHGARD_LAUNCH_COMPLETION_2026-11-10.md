# Rahgard Launch Completion — Issues #4–#6

Date: 2026-11-10  
Branch: `feat/rahgard-launch-integration-v1`  
Base/final committed HEAD: `d55dcda32d7465904ba60687d4d1d5875e2ce57d` (work remains uncommitted)

## Decision

**Issue #4: integration work delivered; evidence-fed traveler recommendations remain blocked.** The authenticated recommendation path made real HTTP calls to the owner's loopback TourismRagApiV1 service. Its approved index was explicitly empty, so all three calls returned `no_evidence`. Retrieved text is withheld. The application also lacks a trusted projection mapping owner document/claim/hash identifiers to current approved source-valid content, so this patch does not use owner text as recommendation facts.

**Issue #5: BLOCKED. Issue #6: BLOCKED.** The engineering work that can proceed without editorial approval, live paid Chat, production credentials, or hosting is prepared and the existing three-locale acceptance path passes. Owner approvals and operational inputs listed below are still required for real traveler/pilot acceptance.

This is not a pilot-ready or real-data recommendation-quality claim. The preserved earlier Gate-A NO-GO artifacts remain historical evidence; this report records the later positive API/PostgreSQL itinerary path and real empty-index RAG probe.

## Git and preservation

- Starting and final committed SHA: `d55dcda32d7465904ba60687d4d1d5875e2ce57d`.
- Branch: `feat/rahgard-launch-integration-v1`; upstream: `origin/feat/c1-c3-internal-installable-mvp-v1`; synchronization reported `0 ahead / 0 behind`.
- Task changes and sanitized browser artifacts remain uncommitted and unstaged. No commit, push, merge, deployment, reset, clean, rebase, or stash occurred.
- No production migration, content publication, source-registry update, owner RAG implementation change, or provider-gateway change was made.

## What works for a traveler

- The existing fa-IR/en-US/ar PWA conversation, persisted trip/profile, explicit review/confirmation, honest unresolved/empty production catalogue, history/reopen/delete and editable long-duration itinerary behavior remain in place.
- The authenticated recommendation endpoint can make a bounded owner-RAG probe using only the localized label and exact key of an already eligible structured-catalogue recommendation. It does not transmit conversation history, use RAG to override deterministic eligibility/ranking, or return retrieved text.
- With the production catalogue empty, the traveler receives `needs_confirmation` for unresolved hard constraints. The E2E's four-stop itinerary fixture is explicitly test-only and injected at a private test boundary; it exercises real FastAPI and PostgreSQL create/edit/save/reopen persistence, while production catalogue views remain empty.

## Integrations and browser evidence

The final browser run used Chromium 156.0.8078.47, Vite, FastAPI, guarded disposable PostgreSQL 17, fake SMS, simulated Chat, and the real local TourismRagApiV1 HTTP service at loopback. A task-local empty approved index was initialized without downloading/loading models. The live service health check reported ready with `approved_corpus_empty=true`.

The sanitized run report records three locale journeys and 12 screenshots (mobile 390×844 and desktop 1440×1000 for each locale's empty production state and test-only partial itinerary):

- [Run report](../../artifacts/visual-qa-task15d/run-2026-11-10T07-55-19-497Z-17016/report.json)
- Screenshots: `artifacts/visual-qa-task15d/run-2026-11-10T07-55-19-497Z-17016/{fa-IR,en-US,ar}/`

Observed: owner RAG calls 3; outcomes `no_evidence=3`, `ok=0`, `unavailable=0`; traveler evidence text returned=false. Chat remained simulated with two calls per locale and zero live provider calls. Browser audit recorded zero successful external requests and zero page errors. The Persian journey persisted 13 user turns and a 15-day profile. The test-only itinerary started with four stops across 15 days, then was edited/saved/reopened with three stops and 12 unplanned days. All three locales passed history/reopen, ownership/CSRF, deletion, locale and no-store checks.

## Essential verification actually run

| Command/check | Result | Exit |
|---|---:|---:|
| Focused retrieval, owner HTTP, recommendation and consent tests (from `backend/`) | 79 passed, 1 warning | 0 |
| Full backend suite (from `backend/`, before final E2E harness-only edits) | 274 passed, 14 skipped, 1 warning | 0 |
| Ruff: `uv run ruff check app tests` (from `backend/`) | All checks passed | 0 |
| Frontend: `npm.cmd test` | 109 passed, 13 files | 0 |
| Frontend: `npm.cmd run build` | TypeScript/Vite/PWA build passed | 0 |
| Guarded PG17 tests: `tests/test_positive_itinerary_postgres.py tests/test_assistant_postgres.py` | 1 passed, 9 skipped | 0 |
| Integrated browser: `node scripts/traveler-e2e.mjs` with opt-in local RAG env | fa-IR/en-US/ar passed; 12 screenshots; real owner HTTP outcomes `no_evidence=3` | 0 |
| Harness checks: `node --check scripts/traveler-e2e.mjs`; `uv run python -m py_compile tests/traveler_e2e_server.py` | Passed | 0 |
| `git diff --check` | Passed | 0 |

PG tests used a task-created PostgreSQL 17 disposable container with tmpfs, loopback-only port and least-privilege app role; migrations 0000–0011 were applied only there. The run cleaned up its disposable DB container and exact task-created RAG process. Shared PostgreSQL/port 55433 was not used. No full SQL contract suite was rerun because no migration changed.

## Remaining owner blockers

1. **Approved evidence:** approve pilot geography and editorial/source rights; provide native-reviewed, source-valid published content and freshness/revocation semantics.
2. **Application publication mapping:** implement/approve a trusted identity projection connecting owner evidence IDs, document/claim keys, content hashes and sources to AI Tourism's current approved records. Until then, owner-RAG text must remain withheld.
3. **Remote Chat:** authorize provider, data-processing/retention terms, consent language, budget/rate limits, and server-side credentials for a separately bounded live test. No paid/live Chat call occurred.
4. **Pilot operations:** authorize production host/domain/region/secrets/monitoring/backup/rollback, production SMS/carrier credentials and tests, authentication recovery and admin MFA/bootstrap, and physical device/SIM testing.

Issue #5/#6 acceptance therefore remains blocked by owner decisions and production prerequisites, not by the simulated Chat or empty-corpus tests being mistaken for live evidence.

## Safety statement

No root `.env` was read. No shared database, production service, paid API, real SMS, ScaleRAG repository, unapproved content, or production data was accessed or modified. No merge or deployment occurred.

### خلاصه برای مالک

اتصال واقعی برنامه به API محلی TourismRagApiV1 انجام شد و سه درخواست واقعی، پاسخ صادقانهٔ `no_evidence` گرفتند؛ چون نمایهٔ محتوای تأییدشده خالی بود. متن بازیابی‌شده به کاربر نمایش داده نشد. مسیر فارسی، انگلیسی و عربی با FastAPI و PostgreSQL آزمایشی اجرا شد و برنامهٔ ۱۵روزهٔ آزمایشی ذخیره، ویرایش و دوباره باز شد. گفت‌وگوی هوش مصنوعی شبیه‌سازی‌شده بود و هیچ فراخوانی پولی انجام نشد. برای توصیهٔ واقعی، تأیید محتوای مستند و سازوکار نگاشت امن شواهد RAG به رکوردهای منتشرشده لازم است؛ میزبانی، پیامک و مجوزهای پایلوت نیز هنوز مسدود هستند.
