# Issue #27 — Owner Control Center delivery and acceptance

## Implemented

- Added `/admin` to the existing React shell and derives navigation from authenticated server-side grants, never from `auth_method`, client state, or a public role parameter.
- Reused the existing catalogue review/publication panel and partner verification APIs. Extracted the company review queue so it remains available in `/partners` and is also reused under `/admin`.
- Added an aggregate-only owner overview for account/grant counts, company/destination counts, PostgreSQL/migration status, configured release identity and honest backup-evidence availability. No user rows, credentials, secrets, impersonation, or arbitrary SQL are exposed.
- Added bounded company review audit-history read, guarded by the same organization-review grant and existing row-level security.
- Added additive Migration 0025 for `admin_overview_read`, an operator grant audit table and a capability-gated aggregate function. The normal application role cannot read the grant audit or mutate grants.
- Added `backend/scripts/provision_platform_capability.py`; it verifies the private-pilot marker, PostgreSQL 17, exact migration hashes/ledger and privileged DB role. Dry-run is the default, self-grants are rejected, changes require explicit operator confirmation, and no public grant API exists.
- Provider administration remains local-pilot only and unavailable in public staging. High-impact partner and catalogue actions fail closed in public environments until a separately approved platform reviewer MFA step-up exists. Local/test acceptance continues through existing capability-checked, audited routes.

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

Focused tests: backend owner/admin/provisioning/partner/catalogue set **40 passed**; frontend **207 passed**; Ruff, Python compilation, Node syntax check and `git diff --check` passed. Migration 0025 isolated PostgreSQL 17 rehearsal passed with 24 ledger entries and app-role grant/audit privilege assertions.

## Live deployment decision

**NOT DEPLOYED.** No VPS or live database operation was performed. The last documented live revision is `9b5b07d0786578abdfac56848baf3c6d1260832e`; migration 0024 has not been proven live and 0025 depends on it. The public reviewer MFA/step-up contract is also not available, so consequential public writes fail closed. Do not claim live owner/company/candidate acceptance or SHA parity from the isolated run.
