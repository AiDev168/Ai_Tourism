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
