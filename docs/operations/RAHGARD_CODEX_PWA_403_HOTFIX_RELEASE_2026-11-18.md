# Codex outcome mission — fix PWA 403 and qualify a new immutable Rahgard release

## Incident and scope

Owner-approved release `d5d9847373b20087a8a866449c6550d306f45b63` failed live PWA acceptance because `/manifest.webmanifest` and `/sw.js` in the final Web image were `0600 root:root`, unreadable by the Nginx worker. Application-only rollback was successful. See `docs/operations/RAHGARD_LIVE_DEPLOYMENT_ACCEPTANCE_2026-11-18.md` at commit `c7c0fd86c80c5daa881cd48a3128e5d49edd5af2`.

Actual last reported live state:
- **Application:** `5e2664fb51e18f52549aa37a8b5793e12ace09b2`, healthy after rollback.
- **Database:** already at **20 migrations through 0021**, persistent volume preserved. **NEVER rerun 0018–0021** or restore the pre-migration backup over newer live data.
- **Data:** aggregate counts unchanged (12 users, 6 trips, 66 destinations, 0 published), SMS and RAG disabled.
- Old authorized immutable d5 SHA is now a **failed release**; do not redeploy d5 or reuse its image tags for a changed build.

The assistant has already committed a minimal proposed packaging fix at `02dbdff9a9f559b3f8c0086769b110bca593a4dd` on this feature branch: `deploy/staging/Dockerfile.web` normalizes directory modes 0755 and static file modes 0644 **inside the runtime Nginx image**. Treat as a proposal requiring test, not proof of correctness.

## One complete execution goal (no production changes)

1. Inspect and independently validate the root cause, PWA generator, Docker `COPY` behavior, and actual Nginx worker permissions. Confirm the minimal packaging fix preserves static content bytes and exact hashed assets. Consider adding a focused reproducible test that builds a fake dist with mode 0600/0700 and checks that the **built runtime Web image** serves `/`, `/manifest.webmanifest`, `/sw.js`, its referenced hashed JS and CSS as HTTP 200 when Nginx runs as configured. Include a negative regression test or explicit file-mode checks (manifest and sw readable as Nginx worker) and guard against `403` or accidental SPA HTML fallback for asset URLs. Do NOT fix by running Nginx as root or widening access to private files.

2. **Prevent a repeat of the incident:** enhance the isolated release-image Web acceptance and deployment gates to check manifest, service worker and hashed JS/CSS both via upstream and intended proxy, checking body/content type and actual unprivileged read access, not merely homepage health. Upgrade/release guard should refuse to switch live symlink if essential PWA assets are unreadable. Document the distinction between image/container health and functional readiness.

3. Produce a **new immutable source SHA** after code/testing changes. Never mutate/rewrite d5 history, mislabel new image as d5, substitute test-image layers or silently change locked dependencies. The existing hosted builder and bundle verifier on `main` are hard-pinned to d5, so prepare a **reviewable, SHA-parameterized or explicitly re-pinned hosted workflow** with strict explicit approved SHA and same read-only permissions and checksum/digest verification. Prefer a narrowly scoped PR to `main` rather than merging the entire 194+ commit feature branch. Do not turn on permanent automatic deployment. If a one-time test build is needed, use existing GitHub-hosted runner and a separate artifact name reflecting the new SHA.

4. Build and securely verify new API/Web images for the new SHA, then run full isolated PostgreSQL 17 restored-database test against the **already 20-migration** live schema (not the old 16-migration snapshot unless separately needed for compatibility). The strict test must **not attempt to apply 0018–0021 again**. Check 27 protected RLS tables/67 policies, publication remains 0, source/partner isolation, old API compatibility, PWA manifest/sw and hashed assets, API readiness, Web catalogue proxy, and no data loss. If current rehearsal scripts only accept 16→20, implement a separate guarded **20→20 no-op** rehearsal/preflight, preserving old history.

5. Refresh backup restore evidence and privacy-safe actual VPS ledger/status read-only. Do not fetch or use user private content or secrets. Analyze existing release config and `RAHGARD_BUILD_IMAGES=false` expected mode without touching live .env. Preserve the November 18 encrypted off-host backup; don't publish it.

6. Prepare clear `LIVE_HOTFIX_READY_OR_BLOCKED` report with exact new application SHA, image manifest IDs and checksums, runnable regression tests, isolated 20→20 rehearsal, PWA availability checks, and a short, schema-preserving app-only rollout/rollback plan. Push all scripts/docs to GitHub and keep Windows checkout synced with the branch. Record limitations including absence of authorized authenticated test account.

## Authorization STOP

**THIS TASK DOES NOT AUTHORIZE A SECOND LIVE DEPLOYMENT.** The owner approved one exact prior d5 SHA, and that deployment was attempted and safely rolled back. Any new SHA and target image must receive **separate explicit owner approval** before live `deploy.sh`, restarts, app symlink switch, config changes or publication. Migrations 0018–0021 **already exist live**; do not rerun. No catalogue publication, SMS/RAG activation, nginx/DNS or unrelated work. Don't modify persistent database except explicitly authorized backup/read-only inspection. Report BLOCKED rather than weakening security gates.

After completing build and isolated acceptance, stop at owner approval, report exact new SHA and propose a brief maintenance window. Deliver actual checks, no invented claims.
