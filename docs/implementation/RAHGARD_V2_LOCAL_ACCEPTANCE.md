# Rahgard V2 local acceptance

## Decision

**V2 LOCAL ACCEPTANCE: NO-GO for the complete mission.** The integrated
isolated application journey passed. Live-provider semantic extraction was
not exercised, so the LLM-primary acceptance condition remains unverified.
This result does not authorize or imply a VPS deployment.

## Implemented and exercised

- Initial request and authenticated conversation are presented in one traveler
  workspace. AI processing is described with a non-blocking notice; there is
  no separate AI opt-in checkbox. The intake timezone selector and manual
  location-as-origin control were removed while ISO date handling remains.
- Typed trip requirements carry difficulty, weather preferences and local
  cuisine. Confirmed profiles retain provenance, revision identity and the
  user's original message. Manual corrections remain authoritative.
- Migration 0022 adds immutable requirement snapshots and explicit,
  organization-selected request sharing, revocation, revisions and an
  authenticated company inbox. It uses existing partner organization identity,
  membership and authorization boundaries. No public links, SMS or outbound
  email were added.
- Recommendation validation accepts V2 confirmed-profile metadata and does not
  report known traveler fields as missing when destination metadata is absent.
- The guarded browser runner used archive-backed candidates and a test-only
  publication in a disposable PostgreSQL 17 database. It did not promote data
  to a persistent catalogue.

## Integrated acceptance evidence

Executed the guarded isolated command:

```powershell
$env:DATABASE_PASSWORD='unit-test-only-not-a-secret'
./engineering/pilot/Run-National-Catalogue-Browser-E2E.ps1 -ArchivePath 'C:\Users\coole\Downloads\Tourism_Database\دیتابیس - توریسم.zip'
```

Observed result: `status=passed`, migrations 0013–0022, archive staging
`167` destination identities and `533` discovery leads, `2` isolated
published destinations. Operator, partner and traveler browser workflows all
passed against FastAPI and disposable PostgreSQL 17. Partner cross-tenant
access was denied; selected sharing, profile/itinerary revisions, revocation,
and itinerary reopening in a newly authenticated session passed.

The browser acceptance used an **in-process simulated AI Gateway**. It made
zero live-provider calls. It proves persistence and application integration,
not live model quality or actual vLLM semantic extraction.

Sanitized screenshots are under:

`artifacts/visual-qa-task15d/run-2026-11-19T11-02-08-726Z-40712/`

Files include operator staging/review, persisted partner workspace and
reopened traveler itinerary screenshots. They are local test artifacts and
are not part of this source commit.

## Checks actually run

- Backend focused tests: **27 passed**.
- Backend suite: **494 passed, 18 skipped**.
- Frontend suite: **191 passed across 21 files**.
- Frontend production build and TypeScript build: **passed**. PWA shell
  `rahgard-shell-42abe75690c5e252`; the build emitted the existing large
  JavaScript chunk advisory.
- `uv run ruff check backend`: **passed**.
- `node --check frontend/scripts/traveler-e2e.mjs`: **passed**.
- `git diff --check`: **passed**.
- Final integrated Chromium/FastAPI/PG17 run: **passed**.

The frontend build, Ruff and diff check were rerun after the final API typing
correction. The correction gives the request-revision endpoint its actual
response type instead of reusing the richer inbox-event type.

## Database and release boundary

Migration `engineering/pilot/sql/022_traveler_company_requests.sql` has
SHA-256:

`E6B7DB49ABC0FF76C2620B2CC8D5DDED0F4255F8533EFD20BD5B402A0BA57EDA`

It was applied only in the disposable PG17 acceptance database. No persistent
or live migration, database write, VPS access, provider call, publication, or
deployment occurred. Existing production catalogue publication controls were
not changed.

## Remaining gate

To claim full V2 acceptance, run the same semantic-intake journey with an
authorized private vLLM development endpoint and observe a real structured
provider extraction updating the editable profile. The current run did not
inspect provider credentials or make an external call. Until that evidence is
available, only the isolated engineering/integration journey is accepted;
live LLM-first behavior remains unverified.
