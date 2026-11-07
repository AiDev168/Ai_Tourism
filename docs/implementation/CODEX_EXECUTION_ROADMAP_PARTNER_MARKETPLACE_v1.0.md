# AI Tourism — Codex Execution Roadmap for Partner Marketplace

**Version:** 1.0  
**Date:** 2026-11-07  
**Related architecture:** `PARTNER_MARKETPLACE_AND_ADMIN_PLATFORM_ARCHITECTURE_v1.0.md`  
**Repository:** `AiDev168/Ai_Tourism`  
**Target repository location:** `docs/implementation/CODEX_EXECUTION_ROADMAP_PARTNER_MARKETPLACE_v1.0.md`

## 1. Operating rules for every task

These rules apply to every Codex task below:

1. Work only in the existing local repository and first report the actual branch, `HEAD`, upstream relationship and complete worktree state. The last reported branch/HEAD was `fix/initialize-database-powershell-inspect-v1` / `4e9b76a66a922981c72bfee04c6484735d8206c2`; verify rather than assume it is still current.
2. The latest reported worktree is intentionally dirty and contains uncommitted catalogue API, destination-resolution, trip-intake, database-lifecycle, alias-proposal and visual-QA work. Treat every existing modified or untracked file as user-owned. Do not overwrite, reset, clean, restore, stash, rebase, switch branches, stage, commit, push, merge or delete anything.
3. Do not touch `main`. Do not create or change branches unless the owner explicitly directs it.
4. Do not apply a migration to `ai_tourism_dev` or any shared database. Use a disposable PostgreSQL 17 instance for schema validation only. Do not change migration history or weaken the database lifecycle protections.
5. Do not change or approve the runtime alias manifest. The 12 VisitIran alias proposals remain proposals and must not enter runtime matching until editorial approval.
6. Preserve the existing destination catalogue API and resolver behavior. The recent positive API/proxy test proved one eligible destination resolves through the same-origin path; the available-empty response is 200; unavailable service is 503. Do not replace destination catalogue functionality with partner search.
7. Preserve the RAG/knowledge priority and provenance contracts. Partner prices, schedules and availability are structured operational data, not static RAG facts.
8. No live partner API, external feed, model/provider call, paid service, model download or network-dependent integration test without separate approval. Use deterministic fakes in normal tests.
9. Do not implement booking, payment, inventory hold, ticketing, cancellation, refund, commission settlement or payout in this roadmap.
10. No placeholder authentication, anonymous partner writes, or publicly exposed admin routes. Follow ADR-0006 and ADR-0008 gates.
11. Do not launch the next task automatically. Finish one task, report evidence and blockers, then wait for owner review/authorization for the next task.
12. No scope expansion based only on a Codex assumption. When a policy decision is open, document options and stop at the decision gate.

## 2. Current technical baseline to preserve

The latest Codex report states:

- Branch: `fix/initialize-database-powershell-inspect-v1`.
- HEAD: `4e9b76a66a922981c72bfee04c6484735d8206c2`.
- No changes staged or committed; no shared development database was accessed or modified.
- Frontend destination resolver uses `ApiDestinationCatalogPort` and same-origin `GET /api/v1/catalog/destinations` without traveler text in the request.
- Isolated PostgreSQL 17 test: production view returned only the eligible positive control; ineligible review/synthetic/expired/unverified controls were excluded.
- Browser integration through the Vite same-origin proxy reached the API and resolved the eligible candidate.
- Available-empty is HTTP 200; stopped database produced the expected HTTP 503 response body. One PowerShell wrapper assertion exited 1 because it parsed multiline curl output incorrectly; the response itself showed the expected 503. Treat the wrapper as a test-harness defect to correct only if needed, not as evidence that the API returned the wrong status.
- 52 frontend tests passed; frontend build passed; 18 backend tests passed; Ruff passed; proposal manifest passed schema and Pydantic validation; diff check passed.
- Twelve VisitIran aliases remain `proposed`; runtime manifest remains empty.

Before each task, Codex must collect a fresh baseline. Do not use this historical summary as a substitute for `git status` and current test output.

## 3. Phase and task sequence

### Task 0 — Read-only repository and worktree baseline audit

**Mode:** Read-only. **No file changes. No code edits.**

**Purpose:** Establish exactly what exists and prevent collision with the substantial local worktree changes.

**Codex prompt:**

> Read the complete `PARTNER_MARKETPLACE_AND_ADMIN_PLATFORM_ARCHITECTURE_v1.0.md` and this roadmap. Then perform a read-only repository audit. Report: current branch; exact HEAD; upstream tracking; ahead/behind counts where safely available; complete `git status --short`; tracked diff stat; names of untracked files; and whether any path referenced by the new architecture or upcoming tasks is already modified/untracked. Inspect the current partner-related code/schema/routes/UI, destination catalogue adapter, trip resolver, RAG/retrieval boundaries, current ERD, ADR-0006/0007/0008, root instructions and migrations. Build a source-of-truth map distinguishing implemented, partially implemented, documented-only, proposed and absent capabilities. Identify likely file ownership/collision risks. Validate only existing focused tests if that can be done without shared DB/provider calls; do not rerun unrelated expensive suites. Do not change any file, branch, index or database. Do not stage, commit, push, merge, stash, reset, clean, restore or checkout. Finish with a concise factual report and a recommendation for Task 1.

**Acceptance:**

- A reproducible state report with exact branch/HEAD and full worktree state.
- Existing partner-related code and schema inventory, with file paths.
- A conflict map for all modified/untracked files.
- Clear distinction between source documents, proposals and physical implementation.
- No repository, index, branch or database mutation.

**Gate:** Owner reviews the baseline before any implementation work.

### Task 1 — Architecture consistency and ADR proposal package (documentation only)

**Mode:** Documentation only. No runtime code, schema, migrations or UI implementation.

**Purpose:** Convert the new architecture proposal into repository-local, reviewable decisions without overwriting the existing project handoff.

**Codex prompt:**

> Using the accepted owner-supplied partner marketplace architecture document and the Task 0 inventory, prepare a documentation-only change set. Add the architecture document at `docs/architecture/PARTNER_MARKETPLACE_AND_ADMIN_PLATFORM_ARCHITECTURE_v1.0.md` without rewriting its product decisions. Draft (do not silently mark accepted) an ADR proposing the partner marketplace and non-transactional referral scope, explicitly preserving the no-booking/no-payment boundary in ADR-0007. Draft a second ADR or decision record for partner organization tenancy/RBAC and list the unresolved dependencies on ADR-0006. Add a short scope reconciliation note explaining how the new domain complements rather than replaces `knowledge.destinations`, RAG, `integration.external_links` and `integration.outbound_clicks`. Do not change ADR-0006/0007/0008 status, do not rewrite MVP Handoff v0.5, and do not introduce an implementation commitment. Preserve all dirty/untracked paths discovered in Task 0; avoid collisions by creating new files. Provide a document cross-reference table, list unresolved owner decisions, and run Markdown/link checks only. No code, SQL, migration, database or frontend changes.

**Expected outputs:**

- Architecture document in repository path shown above.
- Draft partner marketplace/referral ADR (suggested next ID: ADR-0009, only after checking numbering).
- Draft organization tenancy/authorization ADR or decision record (next available ID; not assumed).
- Scope reconciliation note / update proposal for handoff (not a silent rewrite).

**Acceptance:**

- The new marketplace is clearly distinguished from destination knowledge and external-link tracking.
- ADR-0007 is not accidentally interpreted as permission for transactional booking.
- ADR-0006 and ADR-0008 security gates remain intact.
- No code/schema/migration changes and no existing dirty file overwritten.

**Gate:** Owner explicitly accepts or edits the ADR package before Task 2.

### Task 2 — Domain contract, state machines and authorization matrix

**Mode:** Design/specification only. No schema migrations or runtime endpoints.

**Purpose:** Make the commercial domain implementable without premature schema design.

**Codex prompt:**

> Based on the accepted architecture and ADR decisions, produce a detailed domain contract for the first pilot. Define the initial supported service categories (propose a narrow pilot list; do not assume all categories are approved), organization and membership states, verification lifecycle, service/offer publication lifecycle, price units/currency contract, schedule and availability snapshot contract, freshness states, referral/consent lifecycle, and exact role/permission matrix. Define which fields are public, partner-private, admin-only and personal/referral-sensitive. Specify deterministic match eligibility outcomes (`eligible`, `needs_confirmation`, `ineligible`) and the hard filters versus soft ranking criteria. Define API request/response examples and OpenAPI-compatible schemas as documentation only. Reuse existing identifiers/relations where justified, and explicitly identify any new aggregate. Do not write database code, migrations, ORM models or API handlers. Do not decide unresolved policy on behalf of the owner; list options and consequences.

**Acceptance:**

- All lifecycle transitions and authorization boundaries are explicit.
- Unknown/stale availability is not treated as available.
- Price amount, currency, unit and applicability are inseparable in contract.
- Referral consent records recipient, purpose, policy version and exact data categories.
- Hard filters cannot be overridden by scoring.
- No schema or runtime changes.

**Gate:** Owner signs off service categories, data contracts, roles, consent and freshness policy.

### Task 3 — Secure partner foundation (organization and verification)

**Mode:** First implementation vertical slice, only after authentication/authorization decisions are accepted.

**Purpose:** Build the secure organization boundary before partner catalogues or offers.

**Codex prompt:**

> Implement only the approved partner organization foundation from the accepted domain contract. Start with the exact current branch/worktree baseline and protect every pre-existing local change. Implement the smallest necessary additive persistence model, repository/service layer, API contracts and tests for organizations, memberships, organization roles, verification cases and audit events. Do not implement services/offers/prices/referrals yet. Enforce organization-level authorization server-side for every read/write; never trust a client-supplied organization ID as authority. Keep partner evidence private. Use the project's approved auth/session mechanism; if ADR-0006 or admin bootstrap is not accepted/implemented, stop and report the blocker rather than adding placeholder auth. Design migrations additively, validate from the supported migration baselines in a disposable PostgreSQL 17 database, and do not apply them to `ai_tourism_dev`. Preserve current database lifecycle checks and least-privilege application-role grants. No branch switch, commit, push or merge.

**Acceptance:**

- Organization and membership lifecycle works under approved auth.
- Cross-organization access attempts fail in tests.
- Verification decisions are audited with reviewer, reason, timestamp and policy version.
- Public API cannot read private verification evidence.
- Isolated migration tests pass; shared DB untouched.

**Gate:** Owner review of security test report and migration impact before Task 4.

### Task 4 — Partner service catalogue and publication review

**Mode:** Bounded implementation slice.

**Purpose:** Allow verified partners to create services and submit them for platform approval.

**Codex prompt:**

> Implement only the approved initial service categories and their structured service data contracts. Add partner-owned service CRUD, localized fields for `fa-IR`, `en-US` and `ar`, destination associations by canonical IDs, media references using the project's approved storage/security rules, and a platform moderation workflow. Keep service data separate from `knowledge.destinations` and RAG document/chunk tables. Only approved/published safe fields may enter public reads. Add tests for ownership, cross-tenant denial, moderation transitions, localization validation, destination foreign keys and public-field allowlists. Do not add offers/prices/schedules/availability or partner API integrations in this task. Validate schema changes only in a disposable DB.

**Acceptance:**

- One organization cannot access or mutate another's services.
- A verified organization does not automatically publish a service.
- Draft/rejected/unapproved services never appear in public catalogue results.
- Service-to-destination relation uses canonical destination IDs without modifying destination source data.
- All three locales have explicit localization behavior; missing translation is not fabricated.

**Gate:** Owner approves the service catalogue and moderation UX before Task 5.

### Task 5 — Offers, schedules, price and availability snapshots

**Mode:** Bounded implementation slice.

**Purpose:** Add commercial terms that can be compared reliably for the traveler's dates and budget.

**Codex prompt:**

> Implement structured offers for approved services using the owner-approved price, schedule and freshness contracts. Support the approved price units and currencies, validity windows, date/time schedules, capacity/availability states, source/update timestamps, stale/expired behavior and offer publication review. Start with partner manual entry; no external live feeds. A partner-entered value must retain its source classification and must not be labelled platform-verified. Do not imply a reservation or hold. Ensure `unknown` and stale availability are never surfaced as available. Do not perform cross-currency comparison unless an approved rate source and timestamp policy exist. Add API schemas and focused tests. Validate migrations in a disposable PostgreSQL 17 DB only.

**Acceptance:**

- Every published offer has a valid approved service and active verified partner.
- Price always has amount, currency, unit and applicability, or is explicitly marked unavailable/unknown.
- Schedules and availability are date/time-specific and freshness-aware.
- Stale/unknown values are safely displayed or excluded according to approved policy.
- No live provider, inventory hold, booking or payment flow exists.

**Gate:** Owner approves real-data display and stale-state behavior before Task 6.

### Task 6 — Trip-to-partner matching and traveler experience

**Mode:** Backend matching plus focused PWA integration.

**Purpose:** Connect structured partner offers to the existing trip and itinerary experience.

**Codex prompt:**

> Implement deterministic matching of published partner offers to an authorized trip/itinerary using the approved hard-filter and ranking contract. Integrate with the existing trip intake, destination catalog and itinerary by canonical IDs and stable interfaces; do not modify or regress the same-origin destination catalogue adapter/resolver. Keep RAG retrieval as a separate source-backed context path. Record algorithm/rule version and explainable score/filter components. Hard constraints (date/time, party size, published status, freshness, known pricing compatibility and explicit traveler constraints) must be evaluated before soft ranking; unknown data must not silently pass. Commission or partner payment must not influence organic ranking. Build localized traveler cards that show provider, service, price basis/currency, schedule, availability freshness, key conditions and why the match fits. Do not send traveler personal text to a catalogue search endpoint. Add deterministic test fixtures only in test scope and prove they cannot enter production publication. No booking/payment.

**Acceptance:**

- Matching is reproducible and versioned.
- Hard-ineligible offers never appear as eligible regardless of score.
- Needs-confirmation cases are distinguishable from eligible cases.
- Prices and availability display with correct units and freshness.
- Destination catalogue and RAG behavior remain unchanged.
- Persian, English and Arabic UI states pass visual/accessibility checks.

**Gate:** Owner approves actual match behavior and user-facing representation before Task 7.

### Task 7 — Safe outbound actions and consent-based referrals

**Mode:** Bounded referral vertical slice.

**Purpose:** Let travelers choose to contact a partner and allow measured referrals without leaking private data.

**Codex prompt:**

> Implement the approved non-transactional outbound/referral flows. Reuse `integration.external_links` and `integration.outbound_clicks` when they satisfy the contract; explain any proposed extension before duplicating them. Outbound requests must use known link IDs and server-side allowlisted URL resolution. Implement referral creation only after an affirmative, purpose-specific consent step that shows the selected recipient and exact data fields. Store consent text/policy version, timestamp, partner recipient and data categories. Send minimum data only; never send a conversation transcript by default. Add partner-scoped referral inbox/status updates, delivery failure behavior, rate limits, audit events and privacy/retention tests. A click is not a lead, and a lead is not a booking or sale. Do not add commission calculation, settlement, payment, booking or automatic personal-data disclosure.

**Acceptance:**

- No external URL can be injected by the client.
- Clicks and referrals are recorded as separate actions.
- No lead is created without explicit consent.
- The exact consented data set is enforced server-side.
- Cross-partner referral access is denied.
- Delivery failures are visible and do not falsely report success.

**Gate:** Owner approves referral privacy and operational behavior before Task 8.

### Task 8 — Pilot hardening, security review and operational readiness

**Mode:** Verification and remediation only within approved scope.

**Purpose:** Make the partner pilot safe to operate with a limited set of real partner organizations.

**Codex prompt:**

> Perform a security, privacy, data-quality, accessibility and E2E verification of the complete approved partner pilot. Test anonymous access, role escalation, cross-tenant object access, public response leakage, verification bypass, unpublished/stale offer visibility, currency/unit mismatches, consent bypass, duplicate referral delivery, open redirects, audit integrity and abuse/rate-limit behavior. Verify logs contain no secrets or unnecessary personal content. Validate all supported migrations in disposable PostgreSQL 17 instances and confirm no shared database was touched. Run focused backend/frontend tests, full relevant suites, lint/type checks and multilingual visual QA. Fix only defects within the approved scope and avoid unrelated refactors. Produce a release-readiness report with blockers, residual risks, exact commands/results and rollback guidance. Do not deploy or publish real partners without explicit owner approval.

**Acceptance:**

- Critical authorization, consent and data-leakage tests pass.
- No stale data is represented as live.
- Audit trail and operational failure states are tested.
- No test provider calls, paid services or shared DB mutations occurred.
- Release report clearly states what is and is not production-ready.

**Gate:** Owner approval required for pilot onboarding/public launch.

### Future Task 9 — Transactional booking and payments (not authorized by this roadmap)

This is a separate product/financial/security project. It requires new owner decisions, selected provider contracts, inventory/price revalidation, idempotency, reservation holds, payment security, cancellation/refund workflows, reconciliation, customer support, dispute handling, finance/accounting, legal/compliance review and operational runbooks. Do not begin it as an extension of Tasks 3–8 without a separate architecture and explicit approval.

## 4. Required Codex report template after every task

Codex must return:

1. **Exact repository state:** branch, HEAD, upstream/ahead/behind, `git status --short`.
2. **Files changed:** added/modified/deleted, with one-line rationale per file.
3. **Pre-existing work preserved:** list any overlapping dirty paths and confirm they were not overwritten.
4. **Implementation completed:** map each change to the task requirement.
5. **Tests and evidence:** exact commands, exit codes, pass/fail/skip counts; separate isolated DB results from shared DB state.
6. **Security/data review:** tenant access, public/private fields, consent, provenance and freshness impact.
7. **Known gaps and risks:** no vague claims such as "production-ready" without evidence.
8. **Next gate:** state whether the task is complete, blocked or needs owner decision. Do not start the next task.

## 5. Recommended immediate sequence

1. Attach/place the architecture and roadmap documents in the project documentation directory without committing them.
2. Run **Task 0 only** to establish the real current worktree and overlap map.
3. Run **Task 1 only** after reviewing Task 0.
4. Owner reviews the ADR package and resolves the decisions in Section 18 of the architecture document.
5. Proceed sequentially through Tasks 2–8 with an explicit owner gate between tasks.

**Important:** The partner marketplace is now a defined product direction, but this roadmap does not grant permission to implement every phase at once. The next safe Codex action is a read-only baseline audit.
