# Rahgard V2 — Direct assistant engineering work, staged review
Date: 2026-11-21  
Branch: `feat/rahgard-unified-travel-v2`  
Owner instruction: **no Codex; no VPS/DNS; preserve permanent local pilot at 8443/8800/55439**.

## Scope and root-cause audit
The owner-provided mobile/desktop screenshots show poor contrast because later dark CSS overlaid earlier hardcoded light surface colors and vice versa. The partner inbox also directly enumerated `confirmed_requirements` object keys, exposing internal `confirmation_source`, provenance and raw nested values. The synthetic browser journey appended literal `acceptance revision` to `soft_preferences`, which then appeared in the actual user's QA trip form. Company "links" previously displayed only protected snapshots without real company action. The existing sharing API supported a maximum of ten explicitly named companies.

All changes below are **committed source changes**, not proven local runtime acceptance. Development can proceed through Windows owner-led testing; do not infer deployment or a production release.

## Stage 1 — Contrast, theme and mobile PWA shell
- `frontend/src/theme/ThemeSwitcher.tsx` + test: explicit day/night switch in the top bar, local storage preference, OS preference fallback, runtime document color scheme and PWA meta theme-color update.
- `frontend/src/styles.css`: high-contrast paired foreground/background surfaces for conversations, profile fields, errors, saved stops, provisional plan, partner cards, link views and form controls. Light palette reverses the former fixed dark-only shell; mobile controls at least 44px, vertical layouts for narrow widths, iOS safe areas, color-correct calendar/placeholder.
- `frontend/index.html`, `frontend/public/manifest.webmanifest`: viewport-fit, standalone mobile metadata, consistent light install theme.
- **Required check**: 390px and 1440px real Chromium screenshots, keyboard focus and contrast auditing, date inputs, PWA installation/offline shell on a phone. These have **not** been run on the revised SHA.

## Stage 2 — Company comprehension and protected link UX
- `frontend/src/partners/partnerRequestDisplay.ts` + test whitelists and localizes genuine traveler fields. Never display `traveler_reviewed`, `field_provenance`, consent metadata, or arbitrary nested JSON as partner textboxes.
- `PartnerWorkspace.tsx`: requests/inbox first, primary company picker, dedicated request/itinerary links, technical organization/services/schedules/offers/prices/availability under an optional disclosure with concise explanations.
- Company proposal and provisional itinerary pages display days, stops and notes; avoid dumping `JSON.stringify(days)` for principal itinerary view. Older inline inbox details remain as supplementary technical information.
- `frontend/scripts/traveler-e2e.mjs`: replaced the English test revision text `acceptance revision` with a natural Persian travel preference.
- **Required check**: manually use the company A/B browser roles and evaluate readability, actual links, mobile view, revoked company access.

## Stage 3 — Company accept-as-requested / counter-offer / traveler decisions
- Additive `engineering/pilot/sql/023_partner_trip_responses.sql`:
  - Guarded migration (marker, predecessor 0022 hash, PG17, no live migration); `partner.trip_company_responses` tied to immutable `share_id` and `revision_id`, idempotent client_request_id, company/traveler identities, price in **TOMAN**, dates, notes, response kind and traveler decision.
  - RLS and column-limited update grants, tenant membership and no revoked share reads; original traveler itinerary cannot be silently mutated by a company's proposal.
  - Operator-governed `partner.organizations.is_test` flag; existing eligible-company view excludes explicitly test and closed companies.
- `backend/app/api/partners.py`: authenticated/CSRF protected POST of company accepted-as-requested or counter-offer, GET of private company/traveler replies, and traveler accept/decline decision. Enforces current share revision, partner roles, eligibility, valid dates, proposal changes, idempotent response IDs and refusal of stale decisions.
- `frontend/src/partners/CompanyResponseActions.tsx`: simple two-action company response UI. `frontend/src/trip/TravelerCompanyResponses.tsx`: traveler response inbox with explicit acceptance/rejection and explanations that no itinerary is automatically modified.
- Delivery is **in-app only**. `accepted_as_requested` means company declares willingness to fulfill the request as written, not a legally binding booking/confirmed quote. No email, SMS or payment is claimed.
- **Required checks**: disposable PG17 migration/roles/RLS and full authenticated Chromium paths; two company roles, outsider deny, stale revision denial, traveler accept/decline, revocation. No live DB is authorized.

## Stage 4 — Explicit consented mass distribution to current eligible companies
- Existing named-recipient flow remains.
- New `recipient_mode='all_eligible'` is only possible with both normal sharing consent and `broad_sharing_consent_confirmed=true`, plus user-visible final confirmation. Raw original request is **forbidden** in this mode; only the reviewed trip and shared itinerary are included.
- Backend evaluates the current `share_eligible_organizations` view at request time, enforcing approved/verified/active, not closed, not test. Existing share uniqueness deduplicates requests and keeps revisions attached to the same trip.
- **Explicit limit of 500 recipients per atomic request**. Above 500 fails before inserting anything; this is intentionally NOT a complete scaling solution to unlimited companies. No automatic sharing with companies that enroll later.
- No public broadcast endpoints or anonymous bearer links are created. Company members must log in, and RLS rechecks authorization.

## Tests added (execution not assumed)
- `backend/tests/test_partner_share_contract.py`: named recipient and broad consent, raw text denial, accepted-as-requested cannot alter terms, counter proposal requires actual changed terms.
- `frontend/src/partners/partnerRequestDisplay.test.ts`: private key omission and Persian labels.
- `frontend/src/theme/ThemeSwitcher.test.ts`: persisted day/night and PWA meta.
- `frontend/scripts/traveler-e2e.mjs`: guarded disposable PG17+LM Studio journey now tests duplicate-free bulk 2-company sharing, company acceptance, counter offer, traveler decision, immutable trip revision, stale proposal denial and cross-tenant forbidden write.
- `engineering/pilot/Run-National-Catalogue-Browser-E2E.ps1`: applies migration 0023 only in disposable PG17, with migration checksum/RLS/privilege checks. The old persistent private local pilot remains at migration 16 and MUST NOT be upgraded by this script.
- New `.github/workflows/rahgard-v2-local-code-quality.yml`: isolated Linux Node22+Python3.13 no-secret typecheck, frontend tests/build/PWA packaging and partner Pydantic/Ruff checks; this CI is *not* an end-to-end PostgreSQL browser/provider qualification.

### Current evaluation / acceptance gates
| Gate | Status as of code commit |
| --- | --- |
| GitHub V2 code changes | Committed |
| New fixture/test and migration scripts | Written, not yet run locally |
| Frontend TS build, Vitest, PWA package | Pending CI/local result |
| Backend focused tests and Ruff | Pending CI/local result |
| Disposable PostgreSQL migration 0023 and RLS | UNVERIFIED until actual run |
| Local LM Studio authenticated browser E2E on this SHA | UNVERIFIED until owner run |
| Mobile physical device PWA and WCAG contrast | UNVERIFIED |
| Remote `TaHa1_VL` API path | BLOCKED by absent authorized runner key |
| Source-backed real recommendation and verified itinerary | NOT PROVED; approved catalogue empty |
| VPS, DNS, permanent DB | UNCHANGED / forbidden |

## Owner-only Windows check sequence
1. `cd C:\Projects\Ai_Tourism`; inspect `git status --short`; `git fetch origin`; `git pull --ff-only origin feat/rahgard-unified-travel-v2`; `git rev-parse HEAD`. Do not pull over uncommitted local work.
2. From repo root, `& .\.venv\Scripts\python.exe -m pytest backend/tests/test_partner_share_contract.py -q` and `& .\.venv\Scripts\python.exe -m ruff check backend/app/api/partners.py backend/tests/test_partner_share_contract.py`. Substitute the actual project venv only if different; never use random OS Python.
3. From `frontend`, `npm.cmd test` and `& .\node_modules\.bin\tsc.cmd -p tsconfig.json --noEmit`; `node --check scripts/traveler-e2e.mjs`. Do **not** run a production build in the legacy pilot's shared `frontend/dist` without first isolating it.
4. Run the guarded disposable LM Studio browser script using the proven `04-Open-V2-Interactive-Demo.ps1` helper that checks V2 Git SHA parity, once the tests pass; this will now apply 0023 only inside the disposable database. The helper's source-structure markers must still match. Verify traveler, company A, revoked company B, links, proposals and theme before finalizing.
5. Record sanitized browser screenshots and exact runtime output. Any mismatch or test failure leaves status **LOCAL NO-GO**, regardless of commits.

## Unresolved decisions / boundaries
- Automatic mass share does **not** attach future partners; distribution to newly registered companies would require an independent recurring preference with renewed/controlled consent and notification frequency.
- Batch count 500, not unlimited; no background queue or retry mechanism for very large populations.
- Provider output can be provisional; company proposal is not a source-verified travel quote. Real price/hours/road times and source-backed catalogue need separate quality controls.
- No notification by external email/SMS; only authenticated in-app inbox. No legal booking/payment flow.
- No Codex tasks created; no VPS, DNS, permanent database or external server code changes.

## Post-implementation update — code validation and proposal deep links

- Current validated source commit **`28317cf518e9495498add16663ff780d214ce77f`**. Isolated GitHub Actions run [44908261788](https://github.com/AiDev168/Ai_Tourism/actions/runs/44908261788) finished **SUCCESS**: frontend Vitest **199 passed**, strict TypeScript production build **PASS**, static PWA build packaging **PASS**, focused Python partner contracts **5 passed**, Ruff and Python compilation **PASS**. No secrets, production deployment, or persistent database access occurred in CI.
- Previous CI runs did catch and force repair of TypeScript `unknown` JSON-to-JSX rendering problems and required new component props. Those are now fixed in the passing SHA.
- The partner inbox no longer displays original raw JSON `<pre>` snapshots in its inline collapsed detail. It directs the company to the separately authenticated request and itinerary link views, with a concise Persian help/glossary and translated company type/schedule/availability choices.
- Each company response history contains a **copyable private link** `/?trip=<uuid>&company_response=<uuid>`. On opening that URL, a signed-in traveler is loaded through the **existing authenticated traveler trip and response APIs**; the specific reply scrolls into view. URL contains no bearer credential. This link is NOT an SMS/email, and only the trip owner can retrieve the response data.
- The request/itinerary link remains scoped to the selected organization's membership, revision and unrevoked share. Company accept/reply calls are CSRF checked, latest-revision checked and duplicate `client_request_id` with changed terms is rejected `409`.
- The expanded Chromium journey script now asserts broadcast+dedup to two QA companies, stale and unauthorized response denial, accepted-as-requested, counterproposal, traveler decision, and nonmutation of canonical trip profile. **It is written but HAS NOT run against PostgreSQL/LM Studio on the new commit yet.**

### Revised status labels
**CODE-QUALITY PASS** at the above SHA. **LOCAL END-TO-END NO-GO/UNVERIFIED** pending guarded PG17 migration **0023**, real role-based Chromium UI, real LM Studio provider, PWA mobile/contrast inspection, and company response lifecycle. The old `8443` pilot remains 16 migrations and must not be used to validate 0023 features. No remote production rollout authorized.


## Owner-run isolated local acceptance — 2026-11-21 (evidence received)

**Acceptance source:** owner-provided Windows PowerShell terminal output, not an independently collected CI artifact. Source SHA at test time: `8d3a4a1e32d1f572698b553e14614f15df677a0f`; `node --check frontend/scripts/traveler-e2e.mjs` completed without error. Local Node.js 26.13.0 was confirmed in the preceding Windows run.

**Command executed:**

```powershell
& .\engineering\pilot\Run-National-Catalogue-Browser-E2E.ps1 `
  -ChatProvider lm_studio `
  -ChatLoopbackPort 1234 `
  -ChatModel 'qwen3-8b-abliterated'
```

**Observed terminal result:** `status=passed`, `provider=lm_studio`, `model=qwen3-8b-abliterated`, `invocationAttempts=3`, `successfulInvocations=3`, `extractionPath=llm`, `correctionTurn=true`, `itineraryGenerated=true`, `persistedAndReopened=true`. Final runner line: `PASS: authenticated real-provider Chromium journey via lm_studio completed on disposable PG17; no persistent database or VPS was used.`

**Database evidence:** Guarded disposable PostgreSQL 17 bootstrapped migrations 0000–0012. The successful enclosing runner applies 0013–0023, including migration 0023 checksum, RLS and application grants assertions before starting the browser journey. The database used an assigned loopback port (55823 in this run). No migration was applied to permanent pilot, operational VPS or live data.

**Company/permission assertions in the successfully completed `runRealProviderJourney` code path:** two approved test companies plus an ineligible company, consented named and `all_eligible` sharing with two deduplicated recipients and original-text exclusion, separate trip share revisions, authenticated company request/itinerary links, cross-tenant and anonymous access denial, stale revision refusal, idempotency conflict denial, `accepted_as_requested`, changed-price/date `counter_offer`, traveler acceptance without changing the canonical trip profile, company B revocation and company A continued access. The code path includes browser UI selectors and authenticated FastAPI/PG17 requests; these assertions are inferred from a successful complete run, not separately itemized in the printed terminal summary.

**Local artifacts:** `artifacts/visual-qa-task15d/run-2026-11-21T14-14-47-416Z-35124/` on the owner's Windows machine. The script writes `real-chat-lm_studio.json`, `issue23-jalali-calendar.png`, `real-chat-lm_studio-390.png`, `real-chat-lm_studio-1440.png`. These files were not uploaded or visually reviewed as part of this report. Do not copy authentication tokens, private prompts or personal data into GitHub documentation.

**Updated gate decision:** CODE QUALITY **PASS** (prior Windows + Linux CI); LOCAL PG17/MIGRATION 0023 **PASS in disposable acceptance**; LOCAL REAL-PROVIDER CHROMIUM E2E **PASS** on tested source SHA; production deployment **NOT AUTHORIZED**. Visual day/night contrast, typography, company and traveler responsive layout, real physical mobile/PWA install/offline behavior, external service delivery, scale >500 recipients, and recovery on a different server remain unverified. The verified test uses synthetic company identities and a test-only itinerary fixture; it is not verification of public production-catalogue coverage or a source-backed commercial booking.

**Next gate:** visually inspect redacted screenshots and the in-app partner/traveler views in both day/night themes at mobile (390 px) and desktop (1440 px), assess WCAG text contrast, and conduct physical-device PWA acceptance before any production rollout. Current test artifacts already include the two traveler screen widths, but neither day/night nor all company screens have been independently reviewed.


## Post-acceptance screenshot review — 2026-11-21, preliminary visual gate

**Source images inspected in conversation:** owner-uploaded `real-chat-lm_studio-390(1).png` (rendered image file 65×2047) and `real-chat-lm_studio-1440.png` (351×2048). Their names refer to original Playwright viewport widths of 390 and 1440 px, but these chat uploads are strongly downscaled full-page exports. Pixel-perfect typography, color-contrast ratios, and text transcription **cannot** be certified from these copies. The actual original screenshots on the owner's laptop are higher-resolution artifacts.

**Grounded observations and source cross-check:**
- The captured traveler screen uses a largely light palette and includes progress, chat/profile, and a long multi-day provisional itinerary editor. A dark-mode screenshot was not supplied. The company workspace is not pictured; the separately generated Jalali calendar screenshot is also not supplied.
- The itinerary edit area stacks multiple fully expanded per-day edit cards and many labeled fields vertically. The full-page scroll is extremely long on mobile. The desktop screenshot retains broad margins around the day-editor column. This is a UX density/navigation issue, **not** a demonstrated data-loss or functionality defect.
- Current `frontend/src/trip/TravelerJourney.tsx` renders `provisionalDays.map(day => ...)` as all expanded `.itinerary-day` sections, while `frontend/src/styles.css` gives each `.provisional-stop` a full grid of inputs. A future accordion/summary-per-day pattern should keep edits in React state when collapsed, keep day numbers and unplanned-day indicators visible, preserve keyboard accessibility, and not silently discard unsaved entries.
- Some existing helper text styles use 10–13 px fonts. Prioritize an actual rendered CSS/computed-style review at 390 px and test legibility and contrast; apparent tiny text in the downscaled upload alone is **not** evidence of a contrast failure.
- Browser E2E screenshot code clears all `input`/`textarea` values and redacts chat text before screenshot; blank values in these captured images therefore do not prove unexpected empty application fields.
- The successful real-provider E2E asserts no horizontal overflow at 390 and 1440 px and checks distinguishing Jalali today/selected-day visual state. It does **not** automatically establish WCAG AA color contrast or test both theme appearances on every page.

**Priority acceptance backlog (not yet implemented):**
1. Re-capture original-resolution 390 px and 1440 px images, each in **light and dark**, in authenticated traveler and company views; upload cropped/native-width frames rather than downscaled full-page images, remove private data first.
2. Run a computed-style / axe-core WCAG 2.2 AA audit for contrast, field labels, focus, alerts and form targets at 390/1440 px; distinguish real issues from screenshot scaling artifacts.
3. Prototype collapsible itinerary day cards with an always-readable day summary, explicit edit action, stable React identity and preserved unsaved edits; add keyboard and persistence regression tests.
4. Review actual company inbox and protected links in both themes; this cannot be inferred from traveler-only captures.
5. Check physical Android/iOS PWA installation, keyboard, safe area, native select/date controls and offline shell.

**Gate:** browser/API/PG17 **PASS** on source SHA `8d3a4a1...`; preliminary screenshot review **PARTIAL**; visual accessibility and physical-device PWA **UNVERIFIED**. No production deployment authorization and no changes to VPS/permanent pilot.\n\n## Superseding owner direction: release preparation and Codex (2026-11-21)\n\nThe original **no Codex / no VPS** directive in the historical implementation header described that earlier development phase. The owner has subsequently **authorized Codex release-preparation implementation** and requested readiness documentation and three-environment synchronization. This does **not** constitute blanket authorization to change the running VPS, live migration, permanent local pilot, DNS, publication or production secrets.\n\nRead [V2 readiness decision](../operations/RAHGARD_V2_VPS_READINESS_AND_THREE_ENV_SYNC_2026-11-21.md) and [the actionable Codex mission](../operations/RAHGARD_CODEX_V2_RELEASE_PREPARATION_AND_ROLLOUT_GATE_2026-11-21.md). The successful owner-run isolated LM Studio/PG17 E2E on `8d3a4a1...` supports **invitation beta release preparation**, not a verified catalogue-backed public travel launch. Current live release SHA remains **unverified** after the last historical 2026-11-19 report. Source branch will advance with documentation; no three-way parity is claimed.\n