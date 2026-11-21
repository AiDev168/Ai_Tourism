# Codex mission — Rahgard V2 release hardening, live-data rehearsal, three-environment sync (2026-11-21)

**Owner's current request:** prepare Rahgard V2 for the VPS, update necessary documentation, and enable same exact release SHA across Windows, GitHub and the VPS **without loss of any existing data**. The owner has now authorized Codex **for preparation and implementation**, superseding the historical "no Codex" instruction in `RAHGARD_V2_OWNER_DIRECT_IMPLEMENTATION_REVIEW_2026-11-21.md`. **Live migration/restart/deployment/DNS changes remain gated by a separate, final explicit owner approval after evidence.**

## Source-of-truth and boundaries

- Repo `AiDev168/Ai_Tourism`, branch `feat/rahgard-unified-travel-v2`. The source at handoff (before this documentation commit) is `89fb21c03a120e50b8c9fccadfc94846e6ef75ea`; **fetch and use the actual latest branch HEAD** at start, never assume this SHA remains current. Keep source changes on the V2 branch, no `main` writes and no force/rebase/reset of shared history.
- Begin by reading `AGENTS.md`, `docs/operations/RAHGARD_V2_VPS_READINESS_AND_THREE_ENV_SYNC_2026-11-21.md`, `docs/operations/RAHGARD_RELEASE_SYNC_AND_PORTABLE_MIGRATION.md`, `deploy/staging/README.md`, `docs/implementation/RAHGARD_V2_OWNER_DIRECT_IMPLEMENTATION_REVIEW_2026-11-21.md`, `docs/implementation/RAHGARD_V2_USER_ACCEPTANCE_2026-11-21.md`, and `docs/implementation/RAHGARD_V2_INDEPENDENT_PLANNING_AUDIT_2026-11-21.md` (historical limitations; reconcile with later commits/tests).
- Historical VPS evidence from 2026-11-19: application `5e2664fb51e18f52549aa37a8b5793e12ace09b2`, schema through 0021 (20 ledger entries); **unconfirmed as of now**. GitHub compare to V2 `89fb21c03a120e50b8c9fccadfc94846e6ef75ea`: 142 newer commits touching 148 files. A hotfix image candidate `4a9574ae...` was qualified but not observed deployed in the historical report. Do not assume which build is presently live.
- Protect live `rahgard.hinaa.ir`, `/opt/rahgard-staging`, the named PG17 volume, invitation accounts and existing traveler data. The permanent local Windows pilot (8443/8800/55439) is independent and must not be migrated/resetted as a side effect. No arbitrary model endpoints, hidden mock results, synthetic publication or partner auto-consent.
- Existing `engineering/pilot/sql/022_traveler_company_requests.sql` and `023_partner_trip_responses.sql` were created and tested for disposable acceptance only. The old operational `deploy/staging/upgrade-018-021.sh` stops at 0021. Do **not** run 0022/23 on the live DB until newly reviewed scripts and tests explicitly authorize production use, including checking in-DB marker/ledger/volume identities and compatibility.
- Production model route in `deploy/staging/compose.yaml` may differ from tested local LM Studio; do not equate the 3/3 `qwen3-8b-abliterated` test with verified VPS vLLM readiness.

## Four major outcomes (not small fragmented sub-tasks)

### Outcome A — Immutable baseline and release risk inventory (READ ONLY)

1. Confirm local `git status`, exact V2 branch HEAD/tracking state and current GitHub CI; compare current live marker with target history. If local worktree dirty, preserve it and STOP before modifying anything.
2. Via **already-authorized** SSH account/host identity and *read-only* commands, inspect the actual VPS `RELEASE_COMMIT`, running API/Web/PG images, Compose config digest, health, PWA `/`/`manifest.webmanifest`/`sw.js`/hashed assets, PG17 version, volume name, protected DB marker, migration ledger IDs/sha256, RLS/grants/tenant policy counts, aggregate counts for all critical existing user/organization/trip/conversation/itinerary/source/publication rows. Do not output private user rows, tokens or credentials. If SSH is unavailable, mark BLOCKED instead of guessing.
3. Trace V2 migrations 0022 and 0023 and backend API compatibility with real ledger 0021 and old application. Check ownership/privileges, row preservation, existing partner organizations, rejected/test-company flags, revocation, stale proposal behavior, i18n and PWA SW path. Catalog any breaking change; don't mask with the empty disposable fixture.
4. Record `R0-baseline.json` sanitized evidence and a changed-files/rollout-risk matrix. Produce a single decision: PREPARE / PREPARE-BLOCKED / NO-GO.

### Outcome B — Real-data restored rehearsal and fail-closed migration tooling (ISOLATED ONLY)

1. Add/update `deploy/staging/preflight-022-023.sh`, `rehearse-022-023.sh`, `upgrade-022-023.sh` (names may change for clarity), plus tests and documentation. **The migration executor must not be usable merely by naming the database or bypassing guard flags.** It must check actual exact release SHA, protected pilot marker, PG17 and volume identity, single approved database, full pre-0022 ledger/checksums, exact target SQL hashes, backup sidecars/HMAC, explicit attestation and operator identity. Fail closed on unknown/partial/interrupted states; never reset/recreate a volume.
2. First independently verify a recent encrypted/HMAC-authenticated backup (using `deploy/staging/backup.sh` where authorized), independently retained off-host, and restore into labeled disposable PG17 (tmpfs, no published ports/host data mounts). If creating a new backup needs operator authorization, document the exact gate and do not silently execute it.
3. On **the restored real-data copy**, run the exact ordered 0022 and 0023 migrations in a controlled transaction/preflight sequence, compare row counts, full exact checksum ledger, tenant RLS/denial, old user records, profile/conversation/itinerary reopening, org eligibility, private shares/responses, cancellation, cross-tenant attempts and unknown/partial failure behavior. Preserve nonempty and empty table expectations. Do not insert simulated trip/company records into the live source database.
4. Validate real package release source/image against migrated data, then launch **old** API/Web against the migrated copy to establish code-only rollback feasibility; if incompatible, define verifiable forward-fix and a write-freeze plan. Portably export/restore a full release bundle to a second isolated environment according to existing scripts. Do not expose copied private data through an Internet listener.

### Outcome C — Finish user-facing safeguards and release-grade regression

1. Address the screenshots' principal density issue in `frontend/src/trip/TravelerJourney.tsx` and `frontend/src/styles.css`: replace always-expanded provisional day editor with a keyboard-accessible collapsible day summary/edit interface, preserving unsaved React state, day and stop identity, add/remove/move, note changes and persisted reopen. Avoid API/schema changes for this UI task. Add test coverage for collapse/reopen, 4/15/30 days, keyboard and mobile.
2. Capture fresh **redacted native-resolution**, authenticated traveler and company screenshots at 390 and 1440 px under **both explicit light and dark themes**; assert WCAG 2.2 AA text contrast, focus, label association, accessible target sizes, no horizontal overflow, Jalali current vs selected day. Run PWA offline/install shell checks and check prior 403 regression on final Nginx image. Original heavily downscaled uploads alone are insufficient evidence.
3. Run `npm test`, `tsc --noEmit`, build/PWA, `node --check frontend/scripts/traveler-e2e.mjs`, relevant full Backend/Ruff regression, the guarded PostgreSQL17 LM Studio real-provider browser path, plus explicit `accepted_as_requested`, counterproposal, traveler accepted/declined, revision replay, revocation, deep links, mass-share consent with <=500 current eligible recipients and no future auto-enrollment. No secret or private user text in logs.
4. If production catalogue is empty, present `provisional_unverified` accurately; real source-backed itinerary is a separate NOT PROVED gate. Do not fake travel times, hours, source citations, booking confirmations or deployment readiness from synthetic dependency overrides.
5. Prevent accidental silent change in allowed sharing, test-only partner eligibility or SMS/RAG enablement. Verify privacy/security coverage and data retention behavior. Report if the requirement cannot be tested on a real phone; do not label it PASS.

### Outcome D — Immutable release preparation; STOP before live changes

1. Pin the **final candidate SHA only after** all source/test/migration fixes are merged to the agreed V2 branch. Ensure an operator-clean Windows checkout can fast-forward to it and exact GH remote SHA matches. Build the Linux amd64 API/Web images using `.github/workflows/rahgard-release-image-build.yml` and `scripts/ops/build_rahgard_release_images.sh`; attest content hash, image labels/IDs, PWA SW/manifest/asset MIME/access, Compose digest, no secrets in source/build.
2. Use existing guarded `deploy/staging/fetch-release.sh` and approved image-bundle verifier, not ad-hoc `git pull` on VPS. Stage artifacts without changing `current` symlink, running containers, DNS, Nginx, DB ledger or secrets. Keep code build immutable and independent of migration.
3. Prepare a **two-phase cutover**: (i) a last read-only preflight + fresh off-host backup/restore rehearsal and exact operator approved release; (ii) ONLY AFTER A NEW EXPLICIT OWNER APPROVAL, guarded live schema migration followed by `deploy.sh <same SHA>`, with post-deploy authentication, traveler trip save/reopen, company protected request/plan links, PWA assets via HTTPS and in-app sharing permissions. Confirm full SHA identity by `scripts/Verify-RahgardRelease.ps1` after Windows has fetched pinned HEAD.
4. Test failed-deploy cleanup, old-version compatibility and rollback/forward-fix. Any unexpected row-count drift, migration mismatch, unhealthy instance, PWA 403, shared secret exposure or privacy failure is STOP. Never run `initialize-db.sh` on an existing DB, `docker compose down -v`, `docker volume rm`, uncontrolled `psql -f`, force pushes, or live restore without a separate incident approval.

## Mandatory evidence and final decision packet

Commit/push on V2 and provide:
- A current **LIVE vs CANDIDATE** read-only manifest with timestamps and SSH fingerprint identity (do not disclose secret contents).
- A fresh off-host backup SHA/HMAC verification record, **real-data isolated restore→0023** report with checksums, critical before/after counts, RLS and old/new runtime results. If any evidence absent: BLOCKED.
- Source/image immutable SHA, GitHub Actions links, `PWA_IMAGE_PASS`, local/isolated browser trace, concise visual contrast report, sanitized screenshots or hashes, and verification of permanent pilot unchanged.
- The planned operator commands for that exact target, write-freeze/maintenance/smoke criteria, previous app compatibility/rollback plan, expected migration duration as measured in rehearsal (not guessed), and explicit `READY_FOR_OWNER_APPROVAL` or `NO_GO`.
- Updated `docs/operations/RAHGARD_V2_VPS_READINESS_AND_THREE_ENV_SYNC_2026-11-21.md`, the relevant operational runbook, `docs/operations/VPS_RELEASE_GO_NO_GO.md` and source docs with actual evidence. Link all work in the tracking GitHub issue. Never publish private backups, owner credentials, private chat text, or phone numbers.
- **Stop at the approval boundary. Do not deploy to live, change DNS/Nginx, migrate either permanent PostgreSQL, or assert three-way sync before the owner explicitly approves the frozen release SHA, reviewed backup proof and maintenance operation.**

## Owner decision request template (Codex fills fields; never auto-approves)

```text
Rahgard V2 candidate SHA: <40-hex>
Source branch / Windows SHA / GitHub SHA: <three verified values>
Current LIVE SHA and DB ledger: <fresh read-only observations>
Changes affecting existing users: <code, schema, downtime, rollback>
Fresh encrypted/HMAC backup & independent off-host copy: <verified evidence>
Restored real-data PG17 migration 0021→0023: <PASS + exact hashes/counts or BLOCKED>
Old app against upgraded schema: <PASS/FAIL + safe fallback>
Candidate PWA assets + authenticated traveler/company + privacy tests: <PASS/FAIL>
New records published / SMS/RAG enabled: NONE (unless separately explicitly authorized)
Exact operator commands and freeze/maintenance window: <reviewed>
Decision: REQUEST EXPLICIT OWNER APPROVAL / NO-GO.
```
