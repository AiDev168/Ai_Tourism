# Rahgard V2 — VPS readiness and three-environment release identity (2026-11-21)

**Decision: PREPARATION GO; LIVE DEPLOYMENT NO-GO pending explicit, evidence-based owner approval.**
**Scope:** invitation-only/staging-style V2 application candidate; not a public verified travel-planning launch.
**Working branch:** `feat/rahgard-unified-travel-v2`. **Last screenshot review HEAD (before this documentation commit):** `89fb21c03a120e50b8c9fccadfc94846e6ef75ea`. This document's own commit will advance that SHA; no SHA in this document is authorization to deploy.

## What was actually observed, and what was not

- Owner's Windows source HEAD `8d3a4a1e32d1f572698b553e14614f15df677a0f` passed `node --check` and guarded `Run-National-Catalogue-Browser-E2E.ps1 -ChatProvider lm_studio -ChatLoopbackPort 1234 -ChatModel qwen3-8b-abliterated` on **2026-11-21**. Returned `status=passed`, 3/3 model calls, `extractionPath=llm`, correction, generated itinerary and saved/reopened trip. The runner validates PostgreSQL 17 migrations through 0023, RLS/grants and authenticated company workflows in a disposable database. This is an owner-provided run result, not a new VPS execution.
- The browser code path covers two company recipients, separate authenticated request/itinerary deep links, revised shares, consented all-eligible deduplication, unauthorized/anonymous denial, stale revision and idempotency conflicts, accepted-as-requested and counter-offer, traveler decision without canonical trip mutation, and revocation. The short terminal success line does not enumerate each assertion independently.
- GitHub Actions run `44911656215` on `8d3a4a1...` passed Windows Node26, Linux Frontend/PWA, 199 Frontend tests, focused Backend 5/5 and E2E source syntax. Other historical broader suite counts are **not** asserted as rerun on this exact SHA.
- User supplied redacted mobile and desktop full-page screenshots; review was preliminary due to downscaling. Missing independent WCAG contrast measurements, dark-theme and partner screens, physical-device PWA acceptance.
- This acceptance is mostly a **provisional_unverified** itinerary: the real approved production catalogue is still documented empty. A test-only dependency override is not proof of a source-backed planner. No legally binding booking, price, opening hours, driving times or weather verification has been established.
- **Last documented historical live** observation, `RAHGARD_ISSUE21_PWA_HOTFIX_ACCEPTANCE_2026-11-19.md`: VPS application `5e2664fb51e18f52549aa37a8b5793e12ace09b2`, PostgreSQL 17 migration ledger 20 entries through `0021_postgis_security_definer_publication`. A different hotfix `4a9574ae...` had qualified in isolation but had not been deployed when that report was written. This **is not a current VPS observation**. First action is an authorized **read-only** live inventory.
- Historical-documented `5e2664fb51e18f52549aa37a8b5793e12ace09b2` to V2 `89fb21c03a120e50b8c9fccadfc94846e6ef75ea` compare: **142 commits ahead, 0 behind, 148 changed files** in GitHub at review time; this is a large upgrade, not a routine application-only hotfix.

## Fundamental boundaries and blockers

1. Current live VPS SHA, running images, `RELEASE_COMMIT`, Compose digest, DB ledger/checksums, PG version, volume identity, authorization/RLS, data counts, public PWA endpoints and server resources **must be newly measured**. Never replace this with historical assumptions.
2. `deploy/staging/upgrade-018-021.sh`, `preflight-018-021.sh` and `rehearse-20-20.sh` **do not upgrade an existing VPS from 0021 to V2 0022/0023**. The SQL under `engineering/pilot/sql/022_*.sql` and `023_*.sql` explicitly has an isolated-acceptance authorization boundary. Do not pipe those files into live psql or treat a disposable success as live approval. Write and test newly reviewed, fail-closed operational migration/rehearsal gates first, including recovery from interrupted/partially advanced states.
3. An actual recently taken encrypted, authenticated backup with SHA-256 **and HMAC**, off-host copy, and *isolated restored-copy migration rehearsal* are mandatory. Compare exact ledger hashes and aggregate counts **before/after**; preserve all accounts, sessions, conversations, trips, itinerary data, catalogue, partner records and existing approvals. Never initialize/reset/drop the existing DB or volume.
4. Deploy the **exact source commit** as pinned Git SHA and immutable API/Web image identities; verify Web nginx worker can serve `/`, `/manifest.webmanifest`, `/sw.js`, hashed assets, and correct 404 for missing assets (historical 403 issue). Test both current and candidate app on restored migrated database for backward/forward code compatibility. If rollback of old app is unsafe, require an explicitly reviewed forward-fix, not a fictitious DB rollback.
5. Invited authenticated users only during limited pilot; empty approved catalogue and provisional plan must be labeled truthfully. Do not publish synthetic/catalogue discovery candidates or enable SMS, RAG, mass notifications, public partner signup, marketing, or unrestricted external visibility automatically. All-eligible sharing remains explicit traveler consent, <=500 current eligible companies, no future automatic enrollments.
6. No production environment, DNS, Nginx, secret, running service, app release, data publication or live migration change before a **separate final owner approval** stating the frozen SHA, backup/rehearsal proofs, exact operations, maintenance window, expected impact, rollback/forward-fix and smoke-test identities.

## Outcome-oriented release gates

| Gate | Evidence required | Decision |
| --- | --- | --- |
| R0. Baseline | Read-only VPS manifest + exact ledger/checksums/counts/images/public endpoints; local Git and remote identity | BLOCKED until current inspection |
| R1. Recovery | Fresh authenticated encrypted backup, verified off-host copy; isolated PG17 restore with row-count and object comparison | BLOCKED |
| R2. Migration & compatibility | Restored **actual VPS data** upgraded exactly 0021→0022→0023 (or current measured prefix), integrity/RLS/grants and old/new app compatibility; fail-closed scripts and interruption tests | BLOCKED |
| R3. Candidate image & regression | Immutable SHA/source/image attestation, Linux amd64 PWA/Nginx 200/MIME, full relevant Backend/Frontend tests, real authenticated browser on isolated restored DB, invite flow | BLOCKED |
| R4. UX/privacy | 390/1440 authenticated traveler+company dark/light contrast and focus, accessible long-itinerary interaction, PWA offline install; consent, revocation, partner ACL; clearly provisional plan | PARTIAL |
| R5. Owner decision | Owner approves one explicit immutable SHA, verified backup, proposed live operation and maintenance window | **STOP: no standing authorization** |
| R6. Live release | Only after R5: approved guarded migration and application upgrade, public HTTPS/signed-in smoke, no data-loss counts, `Verify-RahgardRelease.ps1` parity, monitor/recover | NOT STARTED |

**Limited invitation beta** can proceed only through R0–R6; **public verified-planning GO** is a separate product gate requiring a real vetted published catalogue, source-backed planning and travel feasibility evidence.

## Three environments: what "synchronized" actually means

1. **Windows repo checkout:** clean working tree, correct V2 branch, full 40-char SHA, `git fetch`, `git pull --ff-only`, tests and matching GitHub remote branch. Do not silently overwrite uncommitted user changes.
2. **GitHub:** source of truth for exact release SHA, manifests, reviewed scripts, action logs, checksums and sanitized acceptance. No passwords or database/backup copies in Git.
3. **VPS:** `/opt/rahgard-staging/current/RELEASE_COMMIT` and both API+Web deployed images must match the **same immutable Git SHA**, with matching Compose configuration, health, HTTP/PWA assets and passed database ledger. The database itself remains persistent and must never be copied from Windows over the VPS.
4. **Local permanent pilot** (historical `https://localhost:8443`, API 8800, PG 55439): separate deployment and data state. Matching a Windows checkout SHA does **not** prove that pilot's running PWA/API is updated; fingerprint its assets and installed service worker separately. Do not migrate its DB or replace its data automatically. Local pilot upgrade requires its own backup/restore/owner approval and separate acceptance.
5. **Portable recovery:** preserve `deploy/staging/{backup,export-portable,inspect-portable,restore-portable,restore-portable-app-check,rollback}.sh` contracts from `RAHGARD_RELEASE_SYNC_AND_PORTABLE_MIGRATION.md`; off-host keys are transferred securely, never printed or committed. Test a restored copy on another isolated host/container before any server migration.

**Windows preparation commands (read-only until an approved release):**
```powershell
cd C:\Projects\Ai_Tourism
git status --short
git fetch origin
git branch --show-current
git rev-parse HEAD
git rev-parse origin/feat/rahgard-unified-travel-v2
node --check frontend/scripts/traveler-e2e.mjs
# Inspect current VPS marker, without assuming an old release:
ssh rahgard-vps 'cat /opt/rahgard-staging/current/RELEASE_COMMIT'
```
A mismatch at this stage is **expected**, not a reason to force a synchronization. After a separately approved rollout, run `scripts/Verify-RahgardRelease.ps1` from a clean Windows checkout tracking the exact released branch, with authorized SSH target and a *private* output path; it intentionally fails before the release SHAs match.

## Stop / rollback rules

- Stop on changed live SHA/ledger/volume, missing/invalid marker, inconsistent migration hash, incomplete fresh off-host backup or restore test, unexpected data-count differences, unverified tenant isolation, failed old-code compatibility, inaccessible PWA assets, inability to test with authorized accounts, or live operator/owner disagreement.
- Before any live operation, capture a limited-privacy baseline snapshot. After, compare safely aggregated row counts, migration IDs/checksums, object integrity and test-owned session/trip data. Never log actual private trip text.
- If only the application is faulty and the previous image is verified schema-compatible, use an application-only rollback; do **not** restore/drop live PG by default. If schema isn't backward compatible, stop writes and execute a separately reviewed forward-fix or fully governed recovery path.
- No self-triggered release, `git reset --hard`, `git push --force`, `docker compose down -v`, `docker volume rm`, `initialize-db.sh` on existing volume, uncontrolled `psql -f`, exposed temporary database ports, or uploading secrets/dumps to GitHub.

## Deliverables owned by Codex

Execute [the exact V2 Codex handoff](RAHGARD_CODEX_V2_RELEASE_PREPARATION_AND_ROLLOUT_GATE_2026-11-21.md) from the latest reviewed V2 branch. End the preparation with an immutable release candidate, read-only live inventory, reproducible isolated restored-data acceptance, evidence and a **STOP** approval request. Do not construe this document as approval to deploy.
