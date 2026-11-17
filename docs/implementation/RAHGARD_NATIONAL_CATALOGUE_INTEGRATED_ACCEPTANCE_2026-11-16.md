# Rahgard national catalogue integrated acceptance — 2026-11-16

## Decision

**GO for the isolated development acceptance scope in this task.** The operator, partner and traveler journeys passed using the real FastAPI application, Chromium and a guarded disposable PostgreSQL 17 database. This is not approval to publish the test record or deploy to the live pilot.

## Browser and database result

Runner: `engineering/pilot/Run-National-Catalogue-Browser-E2E.ps1`, invoked with the owner archive path. Final runner output: `status=passed`, mode `full_application_archive_operator_partner_traveler_isolated_acceptance`. Browser: Chromium 157.0.8103.40. PostgreSQL: 17, loopback-only disposable container, database-marker guard passed; shared port 55433, live database and VPS were not accessed. No live model/RAG/SMS calls were made. OTP was a test adapter and Chat was simulated in-process.

The archive SHA-256 matched the previously verified owner archive: `7e9a27654535590f593aeea8e9f7ba9422fb128ca2c4fc93129061c544aff397`.

Post-journey staging counts: 700 destination candidates (167 identities and 533 discovery leads), 257 source candidates, and 7 import batches. All 533 discovery leads remained unpublished. The operator directly inspected three source records, recorded four field-level claims (identity, province, coordinates and description), approved one new identity and published one archive-backed destination in the isolated database. The post-flow database had two published rows total: this one plus the separate existing isolated geographic test row. No other archive candidate was promoted.

### Operator

PASS. The authenticated browser uploaded the selected archive (202), opened the candidate review queue, registered and reviewed three HTTPS source records (201 each), attached four evidence claims (201 each), approved the candidate (200), and published it (201). The published record was found through the public catalogue endpoint. Synthetic rows were excluded and a review check confirmed discovery leads remained unpublished.

### Tourism company

PASS. Through the partner forms, the browser created one organization, one service, one link to the published canonical destination, one schedule, one offer, one price and one availability record. Each record remained present after workspace reload. A second tenant received zero rows when reading the first tenant's workspace; a forged cross-tenant write returned 403. The database contained two organizations (the first company and the isolation-test company).

### Traveler

PASS. A newly authenticated traveler searched for the archive-backed canonical name, selected the published destination, created a two-day trip, received an available deterministic recommendation, saved an itinerary with one stop, and reopened the same trip, conversation and itinerary after a new authenticated session. All persistence and recommendation requests used the real FastAPI routes and disposable PostgreSQL; no response interception was used. The isolated database held two itineraries total, including its pre-existing test row.

## Fixes made during execution

- Publication had failed because the legacy destination-location trigger referenced PostGIS `geography` without schema qualification. The security-definer publication function uses a restricted search path, so publication failed with SQLSTATE `42704` (`type geography does not exist`). Added guarded migration `0021_postgis_security_definer_publication.sql`, which fully qualifies PostGIS objects in the existing trigger rather than widening the security-definer search path.
- After publication succeeded, the API attempted to read `knowledge.destinations` directly, which the application role is correctly denied. Publication now resolves its returned key and confirms visibility through `knowledge.production_destinations`.
- Partner workspace destination details likewise used a direct canonical-table join denied to the application role; it now reads those details via the production view.
- Browser acceptance now uses the archive's canonical Persian display name for catalogue search, uses stable test IDs for partner selectors, and scopes repeated sign-in buttons correctly after logout/login.
- Archive upload now sends a fixed ASCII transport filename because a Persian filename in an HTTP header is rejected by Chromium. The selected ZIP bytes and content hash remain unchanged. A component regression test covers this behavior.
- Regular-user staging password creation and invitation redemption now accept 8–256 Unicode characters. Credential derivation uses the same bounds. The owner administrative credential policy, OTP length and invitation-token policy were not changed.

## Password validation

PASS. Backend boundary regression accepts lengths 8, 24, 25 and 256 and rejects 7 and 257, using Persian/Unicode strings. Frontend signup limits are 8 and 256, with localized minimum-length text in Persian, English and Arabic.

## Evidence files

Sanitized, local-only screenshots and machine-readable runner report are under:

`artifacts/visual-qa-task15d/run-2026-11-16T17-53-12-364Z-38900/`

- `report.json`
- `national-catalogue/operator-before-staging.png`
- `national-catalogue/operator-candidate-review.png`
- `national-catalogue/partner-workspace-persisted.png`
- `national-catalogue/traveler-archive-itinerary-reopened.png`

The report records exact request paths/statuses and database counts. These artifacts contain generated test accounts and public destination evidence only; no credentials, private conversation text, or provider secrets. Artifact files are git-ignored and were not added to the repository.

## Checks actually executed

- Full isolated PG17 + Chromium acceptance through migrations 0013–0021: **PASS**; all three browser journeys passed, 0 page errors and 0 external requests.
- Focused backend staging-auth, national catalogue workflow and partner destination-association tests: **16 passed** (one existing Starlette deprecation warning).
- Frontend suite: **190 passed, 21 test files**.
- Ruff on touched backend files: **passed**.
- Frontend production build: **passed**, TypeScript and Vite build. CSS `index-C1A8jo42.css`; JS `index-oueDWZ02.js`.
- `git diff --check`: **passed**.

## Scope and limits

All publication and partner records above were created only in the isolated disposable database. The QA-only geographic approval used to satisfy an existing database fixture was explicitly marked test-only. No live data, live VPS, public production catalogue, SMS provider, LLM or RAG service was used. This report does not claim live-provider quality or production readiness.
