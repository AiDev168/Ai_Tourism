# Codex Task Packet — Phase 1: Technical Skeleton

- **Packet version:** 0.2
- **Project:** `AiDev168/Ai_Tourism`
- **Prepared from:** Phase 0 design package, current database baseline and repository guardrails
- **Status:** Owner-approved stack and visual quality brief are recorded. Codex may perform the mandatory preflight and then implement Phase 1 within this packet; ADR-0006 remains a Phase 2 gate before authentication or user-data routes.
- **Target outcome:** A minimal, testable technical skeleton — not a complete travel-advisor feature set.

## 1. Mandatory first action: inspect, do not code

Before editing, Codex must read:

1. `AGENTS.md`
2. `README.md`
3. `docs/architecture/README.md`
4. all ADRs in `docs/architecture/decisions/`
5. `docs/architecture/ERD_MVP_v0.1.md`
6. `docs/api/openapi-mvp-v1.yaml`
7. `docs/security/SECURITY_PRIVACY_BOUNDARIES_v0.1.md`
8. `docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.5.md`
9. `docs/design/PWA_VISUAL_DESIGN_BRIEF_v0.1.md`
10. `docs/reference/AI_Travel_Advisor_Reference_Architecture.md`
11. `docs/reference/ARCHITECTURE_ANALYSIS.md`

Then report:
- current branch, HEAD, `git status --short`, remote tracking state;
- existing files and tooling, if any;
- Python/Node/package-manager versions actually available;
- any mismatch between the selected stack and installed tools;
- exact proposed files to add/change;
- tests and local commands;
- risks and decisions still blocking implementation.

**ADR-0005 is accepted.** The owner approved PWA + React + TypeScript, FastAPI + Python 3.13, and native Windows app processes for the initial local workflow on 2026-11-05. Do not ask the owner to reconfirm these choices. First perform the required read-only preflight and report the branch/HEAD/status and exact build-tool/package-manager/version choice. Once the preflight is clean and compatible, proceed with Phase 1 in this approved stack. ADR-0006 may remain Open during Phase 1 because authentication belongs to Phase 2; do not implement authentication, expose user-data endpoints or ship anonymous placeholders until ADR-0006 is accepted.

## 2. Approved scope boundary

Phase 1 is a polished, testable technical skeleton with a high-quality Persian PWA shell. It is not a complete travel-advisor feature set. Deliver:

- backend application entry point and configuration validation;
- explicit modular-monolith package/module layout;
- non-sensitive liveness and readiness endpoints;
- database connection configuration and a safe connectivity/readiness check using the least-privilege application role;
- a visually distinctive, mobile-first Persian RTL PWA shell following `docs/design/PWA_VISUAL_DESIGN_BRIEF_v0.1.md`; include high-fidelity Home/discovery and representative conversation, recommendation and itinerary layouts;
- request/correlation ID propagation and structured redacted logs;
- `.env.example` with placeholders and local developer commands;
- a small token-based design system and reusable visual primitives;
- deterministic tests and a short local development guide;
- responsive screenshot pack and visual QA report at the specified mobile/tablet/desktop viewports;
- mobile performance baseline and WCAG 2.2 AA accessibility review.

Do not implement the complete conversation journey, authentication provider, RAG, LLM, recommendation algorithm, working itinerary generation, weather, live maps/routing, booking partner integration or privacy deletion in Phase 1. Representative screens may use isolated, clearly labelled UI-only fixtures; never connect review-required or synthetic seed destinations to a public recommendation API.

## 3. Approved stack and bounded tooling choice

See accepted ADR-0005. The owner approved the following Phase 1 stack on 2026-11-05:

| Layer | Approved choice | Implementation note |
|---|---|---|
| Client | Installable mobile-first PWA | Persian-first; RTL from the document root |
| Frontend | React + TypeScript | No generic dashboard template; follow the visual design brief |
| Backend | Python 3.13 + FastAPI | Modular monolith; `uv` and a project-local virtual environment |
| Local application process | Native Windows initially | Do not containerize app services without a measured reason |
| Database | Existing PostgreSQL 17 / PostGIS 3.6.4 / pgvector 0.8.7 | Existing 30-table / 419-row database; reuse it without reset or migration |
| Frontend build tooling | Vite is the default candidate | Verify compatibility and propose pinned versions in preflight |
| Frontend package manager | npm or pnpm | Inspect installed tooling; choose the least disruptive supported option and document it before creating a lockfile |

Do not pin arbitrary "latest" dependency versions. Check compatibility, select supported versions, pin them and document why. Do not perform broad upgrades unrelated to the skeleton.

## 4. Suggested module boundaries

Keep these as internal packages in one backend deployment. Codex must propose a concrete directory tree before creating it.

- `identity` — future auth integration seam; no provider implementation before ADR-0006. Phase 1 must not expose authenticated user-data routes.
- `conversation` — conversation/message use cases; Phase 1 only creates the package boundary.
- `trip` — structured trip requirements/constraints; Phase 1 only creates the package boundary.
- `catalog` / `knowledge` — approved destination read contract and provenance boundary.
- `retrieval` — stable `RetrievalPort` seam and a fake for tests only if needed; do not implement RAG.
- `decision` — deterministic eligibility/scoring/ranking boundary; no recommendation algorithm in Phase 1.
- `recommendation` — use-case boundary; no feature implementation in Phase 1.
- `itinerary` — simple 1–3 day boundary; no itinerary generator in Phase 1.
- `integrations` — typed provider adapter boundaries; fake/no-op only, no live provider call.
- `observability` — request ID, structured log and safe error contracts.

Do not create one service/container per module. Do not add Redis, a queue, event bus, Kubernetes, vector database or agent orchestrator.

## 5. Database integration constraints

The owner has completed the local database gate on 2026-11-05:

- PostgreSQL 17, PostGIS 3.6.4, pgvector 0.8.7;
- 30 project-owned tables and 419 rows;
- all SQL checks 000 through 008 and exact row-count report passed;
- production destination/retrieval views are empty;
- persistent embedding spaces/vectors and real AI usage records are intentionally empty.

Codex must:

1. Inspect the existing Compose/package and connection instructions before writing any database configuration.
2. Use the application role for normal runtime access; never use the migration/owner role in the application.
3. Reuse the existing database service and local port/volume. Do not run `down -v`, reset, drop, reinitialize, rename or recreate it.
4. Avoid schema changes in Phase 1. If a change is demonstrably necessary, stop and propose a migration plus tests; do not apply it without owner approval.
5. Never make raw tables/credentials directly accessible from the PWA.
6. Do not insert persistent embeddings or alter the 419-row seed manifest merely to make a demo appear functional.

## 6. Required technical behavior

### Backend

- Validate required environment settings at startup and fail with safe, actionable messages.
- Provide `GET /health/live` and `GET /health/ready`.
- Readiness checks required dependencies with bounded timeouts and returns only a minimal status.
- Propagate a server-generated or validated request ID across logs and response headers.
- Log event name, result, latency and request ID; redact secrets and avoid raw message/PII logging by default.
- Map internal exceptions to stable, safe error envelopes. Never return stack traces, SQL text, credentials or internal hostnames.

### Database

- Build the connection string from environment variables without printing it.
- Validate connectivity through the application role.
- Do not run schema migrations automatically at ordinary app startup unless a separately reviewed operational design explicitly requires it.
- Keep database transaction/session lifecycle scoped and testable.

### Frontend (owner-approved stack; visual quality is an acceptance gate)

- Implement the approved PWA + React + TypeScript stack and follow `docs/design/PWA_VISUAL_DESIGN_BRIEF_v0.1.md` as a binding quality requirement.
- Build an editorial-quality, photo-led Persian RTL experience with deliberate typography, a warm restrained palette, strong composition and varied layouts. It must not look like a generic admin dashboard or generic AI chat clone.
- Deliver Home/discovery plus representative conversation, recommendation and itinerary layouts in the Phase 1 shell; interactions may be limited, but no fake live recommendation data is allowed.
- Implement responsive design at 360/390/430/768/1024/1440 CSS px; capture screenshots and inspect visual defects.
- Use licensed, locally managed or approved CDN photography; optimize image formats/sizes, reserve aspect ratios, lazy-load below-the-fold media and avoid unrelated stock images.
- Provide complete loading, error, empty, warning, offline and image-failure states.
- Respect `prefers-reduced-motion`, keyboard navigation, visible focus, semantic headings/landmarks, and target WCAG 2.2 AA.
- Establish mobile Lighthouse/Core Web Vitals baseline. Target LCP ≤2.5s, INP ≤200ms and CLS ≤0.1 at the 75th percentile; Phase 1 lab target is Lighthouse Performance ≥90 on a documented mobile profile. Record misses honestly.
- Do not request geolocation at initial app load.
- Do not place API keys, DB credentials or long-lived provider secrets in client code/storage.

## 7. Required tests

- configuration fails fast when required settings are missing/invalid;
- liveness and readiness return expected safe response shapes;
- readiness does not leak connection strings or internal exceptions;
- database connectivity uses the application role;
- request ID is present and propagated;
- log/error output redacts secrets and does not include raw message content by default;
- health routes do not make LLM, embedding, weather or maps calls;
- frontend RTL shell renders at narrow viewport with no horizontal overflow;
- screenshot review covers 360/390/430/768/1024/1440 CSS px and checks crop, type hierarchy, whitespace, bidi, contrast and mobile keyboard behavior;
- WCAG 2.2 AA automated/manual checks cover keyboard/focus, labels, contrast, zoom/reflow and reduced motion;
- mobile Lighthouse and Core Web Vitals measurements are recorded against a repeatable profile;
- no production endpoint returns synthetic or `needs_review` catalogue rows;
- all existing database checks remain unchanged and pass when rerun by the owner.

Tests must be local/deterministic. No billable provider calls, model downloads or remote inference in normal tests. Do not overbuild CI.

## 8. Explicit non-goals

- No authentication provider or OTP/email delivery until ADR-0006 is accepted.
- No implementation of `DELETE /api/v1/me` until retention/deletion policy is approved.
- No user-data API shipped anonymously.
- No actual LLM/embedding/RAG pipeline or benchmarking.
- No agent swarm, orchestrator, event bus or async task platform.
- No booking, payment, transaction, refund or ticket state machine.
- No live weather/routing provider selection.
- No new tourism data imports or publication status changes.
- No deployment, production infrastructure, paid subscription or secret rotation.
- No work in other repositories.

## 9. Git and change safety

- Work only on an owner-approved feature branch based on the reviewed project branch. Never edit `main`.
- Inspect branch, HEAD, clean/dirty state and upstream before work. Stop if state is unexpected.
- Preserve all existing work and the prepared database package.
- Do not reset, clean, force-push, rebase shared history, merge or delete branches.
- Do not commit, push, open a PR or deploy unless the owner explicitly authorizes that exact action.
- Keep the implementation in one small vertical slice; do not mix Phase 2+ behavior into Phase 1.

## 10. Definition of Done

Phase 1 is complete only when:

1. The approved client/backend stacks and local workflow are documented.
2. A fresh developer can configure local placeholders, start the existing database and run documented checks without affecting other projects.
3. Liveness/readiness endpoints work and do not leak internals.
4. Backend modules have explicit dependency direction and no cross-module database/secret shortcuts.
5. The PWA shell is visually distinctive, Persian RTL, mobile-first and aligned with the approved visual brief; its page layouts are deliberately composed rather than based on generic dashboard templates.
6. The screenshot pack covers 360/390/430/768/1024/1440 CSS px; no core page has overflow, clipped controls, broken bidi, overlapping composer or unstable image layout.
7. Performance measurements and accessibility checks are recorded; Core Web Vitals targets and WCAG 2.2 AA gaps are reported with remediation plans.
8. App-role DB connectivity is tested; no migration or seed count drift occurred.
9. Deterministic tests pass and commands/results are recorded.
10. `README`, API docs and architecture docs reflect the actual code.
11. No provider costs, model downloads, unrelated repo changes or synthetic/production data boundary violations occurred.

## 11. Exact Codex execution prompt

> Read the repository guardrails and every document listed in section 1 of this packet. Start with a read-only preflight and return the branch/HEAD/status, current tooling inventory, Node/Python/tool versions, proposed directory tree, exact files to change, test plan and remaining owner decisions. The owner has approved PWA + React + TypeScript + FastAPI + Python 3.13 and the visual design brief; do not ask for approval again. After the preflight is clean, implement only Phase 1 from this packet. Follow the Contemporary Iranian Travel Editorial visual direction and every visual/performance/accessibility acceptance criterion. Use the existing 30-table/419-row database without reset or schema change, and use the least-privilege application role. ADR-0006 may remain open; do not implement authentication or expose user-data endpoints until it is accepted. Keep external provider calls fake/disabled in normal tests. Do not work on main, commit, push, merge, open a PR or deploy without explicit authorization. Finish with exact diffs, commands, exit statuses, screenshots, performance/accessibility results, unverified items and next gate. Preserve the already passing 30-table/419-row database; do not reset, recreate, or change its schema. Use the application database role, keep all external provider calls disabled/faked in normal tests, and implement only safe health/readiness endpoints until authentication is approved. Do not work on main, commit, push, merge, open a PR or deploy without explicit authorization. Finish with exact diffs, commands, exit statuses, tests, unverified items and next gate.

