# Issue #27 — Owner Control Center delivery and acceptance

## Implemented

- Added `/admin` to the existing React shell and derives navigation from authenticated server-side grants, never from `auth_method`, client state, or a public role parameter.
- Reused the existing catalogue review/publication panel and partner verification APIs. Extracted the company review queue so it remains available in `/partners` and is also reused under `/admin`.
- Added an aggregate-only owner overview for account/grant counts, company/destination counts, PostgreSQL/migration status, configured release identity and honest backup-evidence availability. No user rows, credentials, secrets, impersonation, or arbitrary SQL are exposed.
- Added bounded company review audit-history read, guarded by the same organization-review grant and existing row-level security.
- Added additive Migration 0025 for `admin_overview_read`, an operator grant audit table and a capability-gated aggregate function. The normal application role cannot read the grant audit or mutate grants.
- Added `backend/scripts/provision_platform_capability.py`; it verifies the private-pilot marker, PostgreSQL 17, exact migration hashes/ledger and privileged DB role. Dry-run is the default, self-grants are rejected, changes require explicit operator confirmation, and no public grant API exists.
- Provider administration remains local-pilot only and unavailable in public staging. High-impact partner and catalogue actions fail closed in public environments unless an authorized platform reviewer has completed a fresh, session-bound TOTP step-up.

## How an approved owner enters

After a reviewed deployment, open `https://hinaa.ir/admin` and sign in with an existing owner/reviewer identity that has been granted the relevant capability. Account creation does not confer administrative access. See [the Persian operator guide](RAHGARD_OWNER_CONTROL_CENTER_FA.md) for provisioning, section permissions and current public-runtime limits.

## Isolated acceptance

On 2026-11-24 the guarded runner used the supplied archive only after matching its documented SHA-256. It created a new disposable loopback PostgreSQL 17 database, launched the real FastAPI application and Chromium, applied migrations through 0025, and removed the disposable container afterward.

Observed result: `full_application_archive_operator_partner_traveler_isolated_acceptance` **PASS**. Staging contained 700 candidate rows (167 destination identities and 533 discovery leads) and 257 source rows. The browser operator reviewed sources/field evidence and published two supported destinations. Company workflow persisted one organization, service, destination association, schedule, offer, price and availability; the independent reviewer completed the verification/application/activation sequence and three audit events persisted. Cross-tenant read returned no rows and unauthorized write returned 403. Traveler search, recommendation, itinerary persistence and reopen after a new authentication passed. OTP used the fake test adapter; Chat used the in-process simulated gateway; no live provider calls occurred. Test records and publication exist only in the disposable database.

The admin UI matrix covers fa-IR, en-US and ar; light/dark themes; 390px and 1440px. All 12 measured cases reported no horizontal overflow, zero computed text-contrast violations, visible keyboard focus and labeled controls. Sanitized screenshots are in `evidence/issue27/`; the company queue image contains only the synthetic disposable acceptance company, not a live partner or personal account.

- [Persian, dark theme, 390px](evidence/issue27/admin-fa-IR-dark-390.png)
- [English, light theme, 1440px](evidence/issue27/admin-en-US-light-1440.png)
- [Synthetic company review queue, 1440px](evidence/issue27/admin-company-review-1440.png)
- [Full responsive/accessibility matrix](evidence/issue27/admin-ui-matrix.json)
- [Sanitized isolated acceptance summary](evidence/issue27/acceptance-summary.json)

Focused tests on the MFA implementation: backend owner/admin/MFA set **27 passed, 1 skipped**; frontend **208 passed**; Ruff passed. The full backend suite passed **505 passed, 19 skipped**. The guarded PG17/FastAPI/Chromium run applied migrations 0013–0026 to a disposable database and passed the operator, partner, traveler, MFA, RLS, audit and browser accessibility journeys. The MFA-specific PostgreSQL test exercised real application routes under the app role, TOTP enrollment and replay rejection, one-use recovery, session expiry/revocation and RLS. Chat and OTP were simulated; no live provider calls occurred. Production build and `git diff --check` passed. The E2E artifacts are local/ignored and contain no release approval.

## Live deployment decision

**NOT DEPLOYED — LIVE OWNER ACCESS NOT ACCEPTED.** The current implementation adds migration `0026_platform_reviewer_mfa`, TOTP enrollment, recovery, rate limiting and five-minute session-bound step-up. No VPS or live database mutation was performed. The read-only VPS observation for this task found PostgreSQL 17 on the existing persistent volume, 22 migration rows through `0023_partner_trip_responses`, 22 users, 36 sessions, 16 trips, 16 conversations, 1 itinerary, 1 organization and 0 published destinations. The observed running API/Web image tags were `9b5b07d0786578abdfac56848baf3c6d1260832e`; the legacy release marker was `5e2664fb51e18f52549aa37a8b5793e12ace09b2`. These values are not a claim of V2 release parity.

The required fresh encrypted live-data backup restore and sequential rehearsal of 0024–0026 against that snapshot were **not completed** in this task. The repository's earlier backup/rehearsal helpers target an older 0021 baseline and are not safe to run unchanged. No permanent 0024–0026 migration authorization or current production MFA secrets were verified. Do not deploy or provision a live reviewer until an updated, checksum-pinned backup/restore rehearsal passes, the owner authorizes the additive live DDL, server-side MFA keys are injected through the approved secret mechanism, and the exact candidate is reviewed. Existing live users and all data were left untouched. No SMS/RAG/provider setting was enabled.
