# CODEX — ONE END-TO-END RAHGARD NATIONAL CATALOGUE + PARTNER IMPLEMENTATION

**This is a single outcome-driven mission. Do the implementation. Do not return another architecture-only packet or ask for a series of micro-task assignments.**

## Authoritative GitHub inputs (read them in the repository)

- Stage 1 live audit: `engineering/database-reconciliation/stage-1/` (audit commit `9557d65a0ad933b84c64aa7096da0eea98b6c057`).
- Stage 2A eight-file package: `docs/architecture/rahgard-national-catalogue-v1/` (commit `ac9f1c0f764a8b37b060b0ab7eb53e3b11831fdc`).
- **Implementation decisions:** `docs/architecture/rahgard-national-catalogue-v1/EXECUTION_DECISIONS.md` (this branch).
- Pre-existing proposed partner architecture and ADR-0009–0013 (do not claim they were accepted).
- Existing owner-RAG adapter contract; never create a second vector engine.
- The owner tourism ZIP: locate locally at the path supplied by owner; if absent state that single input blocker explicitly, but proceed with implementation using harmless fixtures and leave real archive import pending.
- Reuse the in-repo read-only inspector `scripts/rahgard_archive_preflight.py` and its tests as the initial archive preflight, expanding it only where actually needed.

## Required delivered behavior (one continuous mission)

**A. Real safe national ingestion and review:** add only needed migrations for file identity, candidate records, immutable review decisions, idempotent nested ZIP/CSV ingestion and human source/identity approval. Reuse existing import batches and established destination/source/evidence tables. No duplicate Alborz delivery candidates; never merge Imam Mosque or Sheikh Lotfollah Mosque into Naqsh-e Jahan Square. Preserve raw coordinate roles and avoid invented entrances. Stage the owner's 167 unique place identities and 533 national discovery leads in a disposable database first; report exact outcomes. Build a usable Persian operator UI for bulk triage, candidate lookup, source review, accept/reject and approved publication. Do not require one manual confirmation for every simple repeated identity.

**B. National catalogue and real travel planner:** implement filtered, scalable, indexed, cursor-paginated published-place search for thousands of destinations; preserve legacy API compatibility while upgrading frontend and itinerary consumers. Build required additive localization/geographic/access/temporal schema without inventing administrative registry data or reopening old ADRs. Display exact published place names and sourced map points; use real published POIs in editable, persisted, reopenable multi-day traveler itineraries. Preserve the distinct `provisional_unverified` fallback and honest empty/unknown cases.

**C. Company data-entry capability:** implement organization registration/profile, staff membership with tenant isolation, scoped service definitions linked to canonical destinations, reviewed service/offer publication, explicit currency denomination and price unit, dates/schedules and sourced time-stamped availability, with partner workspace and platform-review surfaces. Enforce independent company verification and offer publication. Implement database same-tenant FK/permission defense and test cross-company access, revocation, forged owner IDs, and accidental private-data disclosure. Do **not** implement booking, payments, or automatic traveler referrals. If explicit security/policy approvals for live partner activation are missing, deliver code and realistic isolated E2E demonstration while leaving public activation disabled.

**D. Integration, migration and acceptance:** use disposable PostgreSQL 17/PostGIS for full additive migration and realistic data tests. Test repeated imports, staged vs published views, review workflow, national pagination above 1000 rows, real multilingual browser flow, organization isolation and itinerary save/reopen. Retain all current rows and source/trip identifiers. Run Ruff/tests and provide exact accepted vs blocked functionality. Prepare a production deployment using documented guarded backup/release scripts; never run migrations or upload unreviewed data to live VPS without the required explicit authorization. If authorized for the live catalogue release, back up and verify before deploy, then demonstrate with live browser. Preserve existing untracked acceptance assets and secrets.

## Execution rules

- Work from the correct branch/revision; reconcile current HEAD, Stage 1, and Stage 2A ancestry, rather than overwriting newer live code.
- Make concrete code, migrations, tests, UI and reproducible evidence. Internal commits are fine; deliver one coherent PR/branch.
- Do not block all work for a policy decision that affects only one live feature.
- Do not silently invent official source licenses, live price, current opening hours, accessibility facts, travel time, confirmed entrances, or source verification.
- Never index unapproved candidate records into RAG. SQL handles structured data; approved owner-RAG may enrich narrative only when actually connected.
- Never replace or drop existing databases; no `down -v` or `initialize-db` on production.

## Completion report

Return **one** outcome report with branch and commit SHAs; migration list and scope; actual destination candidate/import/published counts; evidence of source-review process; screenshots for admin/partner/traveler journeys; UI and API E2E checks; tenant-isolation negative tests; whether live VPS was modified; and precise remaining **external** blockers, not a list of newly invented phases.

**Definition of done:** operator can stage/review/publish source-supported national POIs; traveler can find and plan with those published POIs and persist/reopen a journey; verified partner can enter/manage own services in isolated/tested environment. Nothing unpublished leaks into public search or RAG.

## Owner-provided exact local dataset path (2026-11-16)

The authoritative owner-supplied input archive for local Codex execution is:

```text
C:\Users\coole\Downloads\Tourism_Database\دیتابیس - توریسم.zip
```

Read this file directly from the owner's Windows filesystem when Codex runs on that PC. Verify it is present and compare its SHA-256 against the previously audited archive checksum documented in `engineering/database-reconciliation/stage-1/OWNER_ARCHIVE_RECHECK_2026-11-16.md`. Do **not** ask the owner to reupload it, download it from GitHub, or commit the archive to the public repository. Use a disposable PostgreSQL instance first; no automatic publication or live VPS writes.

## User password minimum — corrected owner decision (2026-11-16)

**Supersedes the earlier 8–24 instruction.** Change only the **minimum password length for regular user password registration / invitation redemption / new password creation to 8 Unicode characters**. **DO NOT CHANGE THE EXISTING MAXIMUM**, which is currently 256 characters in the staging-email password path; do not reject 25-character passwords just because they exceed the previously proposed 24-character cap. Tests: 7 rejected; 8, 24, 25, and 256 allowed subject to the existing other validation rules; 257 rejected. Align backend Pydantic validators and `app.modules.identity.staging_auth.password_bytes`, frontend staging-account input constraints and fa/en/ar messages and tests. Do not modify OTP code lengths or invitation tokens.

This correction is explicitly about **user passwords**. The separately controlled **local-owner administrative credential** has its own security policy; leave its length requirements unchanged unless the owner explicitly authorizes changing that administrative flow. Preserve existing password hashes, verification and successful login for pre-existing credentials; keep rate limits, secure hashing, Unicode handling, and never log plaintext passwords.

## Latest outcome and unresolved acceptance at commit 43bd9f (2026-11-16)

**Verified in a disposable PostgreSQL 17 environment:** the owner ZIP with SHA-256 `7e9a27654535590f593aeea8e9f7ba9422fb128ca2c4fc93129061c544aff397` staged 700 candidates (167 identities + 533 discovery leads), and exactly **three** source-backed archive destinations were explicitly published for isolated tests. The ordinary FastAPI catalogue query returned HTTP 200 and those destinations. Source/field evidence-review APIs, migration 0020 and the operator UI were implemented. Isolated partner tenant and publication gates passed. Focused backend 12 passed, frontend 186 passed, production build and Ruff passed. **No live VPS/DB was accessed or changed.**

**Not demonstrated:** (1) an authenticated operator browser session that imports/reviews evidence and publishes an eligible destination; (2) an authenticated partner browser session that creates an organization, service, destination link, schedule, offer, price and availability while proving negative cross-tenant access; (3) an authenticated traveler browser journey that searches actual archive-backed published destinations, creates an itinerary, saves to PostgreSQL, logs in again and reopens it. A separate browser run failed with `duration_null` on conversation creation. No screenshots support these three required journeys. The 533 leads and other unreviewed records must remain unpublished; there is no mandate to bulk-approve them.

**Codex must close these exact gaps, fix genuine product defects, and run all three journeys against the isolated real application and database** (not mocked/intercepted API responses). Do not declare GO based on the publication script or old traveler fixtures alone. Commit and push code and sanitized browser evidence; return exact SHA, counts, pass/fail per journey and blockers. No production deployment without separate authorization.
