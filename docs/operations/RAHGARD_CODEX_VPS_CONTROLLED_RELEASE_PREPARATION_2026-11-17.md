# Codex mission — VPS release preparation and explicit deployment gate (2026-11-17)

## Authorization boundary and frozen baseline

Owner has **authorized preparation of a controlled VPS rollout**, with preservation of existing production/pilot data. **The owner has NOT authorized actual rollout, SQL migrations, publishing new catalogue records, changing running containers, DNS, Nginx, secrets or externally visible services.** Stop at a documented release approval gate before any such action.

Accepted isolated integration baseline: `e54ccabca57a272f5065c963b074319b0174c5db` on `feat/rahgard-national-catalogue-execution-handoff`. The tested flows are operator publication, partner cross-tenant lifecycle, and traveler archive-backed itinerary save/reopen, on disposable PostgreSQL 17 and Chromium. The isolated acceptance used fake OTP and simulated Chat; these are **not** production credentials/provider validation.

Read the exact implementation acceptance at `docs/implementation/RAHGARD_NATIONAL_CATALOGUE_INTEGRATED_ACCEPTANCE_2026-11-16.md`, `docs/operations/RAHGARD_RELEASE_SYNC_AND_PORTABLE_MIGRATION.md` and `deploy/staging/README.md` before acting.

## One execution-oriented preparation mission

1. **Inspect without mutation** the current managed Rahgard VPS deployment using the existing authorized operator access. Confirm SSH host identity, current `/opt/rahgard-staging/current/RELEASE_COMMIT`, Compose project, database-marker identity, PG17 version/image, persistent volume name, service/health state, public HTTPS endpoints, active API/WEB release, existing migration ledger IDs/checksums, PostgreSQL RLS/grants and aggregate counts of user/trip/itinerary, destinations, publication, source, partner and conversation data. Never output user-level rows, secrets, credentials, tokens or private conversations. Verify actual deployment rather than assuming GitHub HEAD equals VPS release.

2. **Inventory additive compatibility** for migrations 0018, 0019, 0020, 0021 and their prerequisites, accounting for the *actual live ledger*. Inspect SQL for extension/schema dependencies, PostGIS security-definer function behavior, protected publication grants and RLS, existing row preservation, and code backward/forward compatibility. Do not rely solely on the disposable 0013–0021 clean-install path. Existing `deploy/staging/upgrade-017.sh` is explicitly a **one-time upgrade to 0017**, not an upgrade path for 0018–0021. Build or correct a guarded, idempotent, checksum-pinned upgrade procedure in the repository; fail closed on unexpected ledger prefixes or partially applied state. Test on **restored disposable copy**, not live database.

3. **Protect recoverability**: inspect the existing protected backup mechanism `deploy/staging/backup.sh`, `restore.sh`, `rollback.sh`, and portable restore tooling. Prepare a verified, encrypted, authenticated pre-release backup and off-host retention plan. If existing operator authorization explicitly permits creating a routine encrypted backup, do so without modifying application data, prove integrity and rehearse restore only on a disposable isolated DB with restricted credentials; otherwise prepare the exact backup/restore commands and identify the single authorization needed. Snapshot safe aggregate counts and ledger checksums before and after rehearsal. Never publish backup archives or crypto keys; never attempt a destructive restore on the live database.

4. **Rehearse exact-release deployment**: build the immutable release at the accepted SHA or a deliberately reviewed successor SHA, prepare `git archive`, SHA-256 manifest, image tags/bundle, runtime/config compatibility and migration artifacts. Exercise guarded migrations 0018–0021, app startup, production-view permissions, partner isolation, archive-ledger publication gates, authentication, multilingual PWA routes, and itinerary persistence on disposable/isolated infrastructure. Confirm schema-compatible application-only rollback **or** document precisely when rollback is unsafe and a forward-fix is required. Don't assume database migrations can be rolled back by redeploying old code.

5. **Production readiness differences**: determine whether real invitation login / SMS and remote LLM/RAG are configured; report private provider settings only as present/absent/validated (no secrets). Stage a realistic post-deploy smoke-test plan that tests HTTPS, valid invitation authentication, published catalogue read, private partner access and traveler save/reopen without exposing other users' records. SMS may legitimately remain disabled; do not enable it without authorization. Preserve user-password registration rule 8–256 Unicode chars and the distinct local-owner admin policy.

6. **Keep imported archive candidates separate from production**. The 700 candidates, 257 source candidates, and reviewed test publication existed in disposable acceptance only. Do not assume those rows exist on live VPS; do not copy isolated QA fixture rows into live; do not bulk-publish 533 discovery leads. Production publication remains a separate owner-authorized content action.

## Required deliverable and STOP gate

Commit and push an implementation-ready release-preparation package on the same branch: guarded versioned upgrade/validation scripts (if required), preflight checklist, evidence of **disposable** rehearsal with restore validation, and a concise `VPS_RELEASE_GO_NOGO.md` with:
- current live SHA/DB ledger safely observed, target immutable SHA and diff,
- migration checksum/ordering/capability and data-preservation checks,
- backup off-host/restore rehearsal status,
- schema-compatible rollback or forward-fix plan,
- real provider (SMS/LLM/RAG) validation scope and limitations,
- precise post-release browser smoke tests,
- residual risks and exact operator commands for a **separate explicitly approved** deployment.

Return **PREPARED / BLOCKED** or **PREPARATION NO-GO**, never claim production GO or imply live change. **At the deployment gate, stop and request explicit authorization** with immutable SHA, backup proof, exact proposed changes, expected downtime/risk and fallback. Do not run `deploy.sh`, the live migration/upgrade script, `docker compose up` for application services, `initialize-db.sh`, `docker compose down -v`, `docker volume rm`, Nginx/DNS changes or publish content before that approval. Never overwrite or reset existing live traveler or partner data.
