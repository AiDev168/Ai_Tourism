# Rahgard — OWNER AUTHORIZED LIVE ROLLOUT mission (2026-11-18)

## Owner's explicit authorization (verbatim meaning)

The owner has explicitly approved **LIVE** deployment of immutable Rahgard application release `d5d9847373b20087a8a866449c6550d306f45b63` and additive database migrations **0018, 0019, 0020, 0021** during a short controlled maintenance/restart window, CONDITIONAL on a **fresh, verified backup**, preserved live data and safe stop/application rollback. **No destination/content publication** and **no SMS enablement** is authorized. This supersedes the earlier *preparation-only* authorization solely within this exact scope.

**Execution responsibility:** Codex/local operator with existing authorized Windows+SSH access to the VPS, not a GitHub CI runner. Do not create an automatically triggered production deployment workflow, do not handle live credentials through GitHub public content, and do not touch unrelated services. This GitHub task is an executable handoff, not proof of execution.

## Immutable identities

- Approved deployable application SHA: `d5d9847373b20087a8a866449c6550d306f45b63` — DO NOT replace with the later task/report branch HEAD.
- Expected pre-change active VPS SHA: `5e2664fb51e18f52549aa37a8b5793e12ace09b2`; read live marker anew. If it differs, STOP.
- GitHub Actions successful release images: https://github.com/AiDev168/Ai_Tourism/actions/runs/44228225648
- Uploaded artifact ID `14393716721`; ZIP SHA-256 `956d3dd173e97f3d9f28cc530d18e434132d08eafac83e10db820ad8b10dd614`.
- Inner image archive SHA-256 `7977f63c5594f0586730984440ba8fbac181b9c0716094ba59f5e9171a44603b`. Both exact tags already successfully loaded/validated on VPS in isolated rehearsal.
- Corrected guarded migration `deploy/staging/upgrade-018-021.sh` must be invoked from the extracted **d5** release, not later documentation HEAD. Exact four migration SQL hashes documented in `docs/operations/RAHGARD_HOSTED_IMAGES_ISOLATED_REHEARSAL_2026-11-18.md`.
- Active PostgreSQL17 `rahgard_staging_pgdata` previously had **16** migrations through 0017, 12 users, 19 sessions, 6 conversations/33 messages, 6 trips, 1 canonical itinerary/6 stops, 2 provisional itineraries, 66 canonical destinations, 0 published. These numbers are historical baseline, not necessarily current. Take a **fresh aggregate snapshot** and ensure no unexplained loss; don't treat legitimate recent writes as failures.

## Single authorized outcome: protected rollout and demonstrable live acceptance

### Gate A — strict fresh preflight; NO writes or restart yet
1. Confirm operator SSH host identity, current managed release, image tags/image IDs and `RELEASE_COMMIT`, healthy API/Web/PG17, original DB volume identity, secrets availability without printing values, exposed HTTPS and auth methods, database marker and exact 16-entry checksum-verified ledger. Confirm the installed d5 target source release and both exact target image tags are present and correctly validated as in rehearsal. If expected identities/schema or any guard fails, STOP/NO-GO with no production mutation.
2. Confirm backup/restore plan, disk space, free memory, no unexpected other operator running deployment, target API readiness model/SMS configuration unchanged, app-only rollback compatibility, and expected short impact on active sessions. Establish a coordinated short maintenance window; do not claim zero downtime.
3. Record privacy-safe baseline aggregate counts for users, sessions, conversations/messages, trips, canonical/provisional itineraries, stops, destinations, sources, partner rows (if tables exist), publication view and migration ledger. Do not reveal personal data.

### Gate B — mandatory new backup before ANY migration/restart
4. Run existing `/opt/rahgard-staging/current/deploy/staging/backup.sh` against existing PostgreSQL only. Record generated basename and SHA-256; verify HMAC authentication, decryption and `pg_restore --list`; copy encrypted backup plus sidecars over approved encrypted/authenticated SSH to off-host protected, repo-ignored location, and re-verify local checksum. Confirm adequate available restore keys privately. Do NOT reuse the November 17 backup as a substitute for this fresh pre-release backup.
5. **Strong preference:** rehearse restore of the new backup into a separate network-isolated/tmpfs disposable PostgreSQL 17 clone and verify aggregate counts and migration prefix before applying it to live. If required safety checks cannot pass, STOP; do not enter Gate C.

### Gate C — LIVE migrations, explicitly approved
6. Re-run `preflight-018-021.sh` against live; validate exact source/hashes and volume; invoke **guarded** `upgrade-018-021.sh` for approved previous SHA, approved target SHA, the exact newly verified backup basename, `OFFHOST_AND_ISOLATED_RESTORE_VERIFIED`, and `OWNER_APPROVED_APPLY_018_021`. Supply these attestations ONLY AFTER actually meeting their conditions. No reset/recreate, volume deletion, initialization, schema drops or bulk data imports.
7. Verify exactly 20 migration ledger rows through 0021, expected checksums, 27 RLS-protected tables and 67 policies where applicable, publication view still 0, and baseline data preserved. Any failure => STOP; do not start new app until root cause and safe forward-fix/compatible previous app state are confirmed. **DO NOT auto-restore old DB onto production** (would erase newer writes).

### Gate D — LIVE application rollout of EXACT d5 images
8. Use existing `deploy.sh d5d9847373b20087a8a866449c6550d306f45b63` from managed release after confirming prebuilt image mode `RAHGARD_BUILD_IMAGES=false` is set safely in protected host config. If it must be changed, back up its pre-change value, avoid leaking secrets, and restore only when appropriate. Verify that the deploy script retains DB container/volume and is able to auto-return the application symlink on health failure. Avoid changing the DB image, Compose project or unrelated services.
9. Confirm exact running API and Web image identities, stable PostgreSQL container/volume identity, HTTPS 200 for shell/manifest/service worker and public catalogue 200 with **count=0**, no content publication, no SMS enablement, auth-method semantics and ready/health checks.

### Gate E — live acceptance, privacy and rollback
10. Under explicit existing test account/invitation authority only, test real authenticated journey (logout/login, create or reopen traveler conversation/trip, save/reopen itinerary), user-password boundaries if safe, operator and partner endpoints with access control and tenant isolation. Do not fabricate fixtures or publish any archive candidates. If a safe authorized authenticated account is unavailable, mark this part **UNVERIFIED** rather than accessing another user's private account.
11. Perform one genuine model/Chat path smoke check only if a safe authorized test account is available and it won't affect quotas/users; report whether real AI response succeeds. Do not enable RAG or SMS, and do not falsely represent their disabled status as failure.
12. Compare fresh pre/post aggregate counts, allow only clearly attributable authorized smoke-test additions, audit database marker/ledger, and confirm same exact release SHA in Windows checkout, GitHub immutable ref and VPS marker (local Windows **may temporarily remain on documentation branch**; check out immutable release source separately without destroying uncommitted user files).
13. If app health/critical workflow fails after successful migrations, roll back **application code only** to previous tested SHA if the migrated schema remains compatible (old API tested against migrated clone). Keep migrated DB intact. If schema/permissions cannot safely support rollback or critical state diverges, halt writes/notify owner, avoid unsafe automatic DB restore. Record precise failure/next action. **Do not rollback database by default**.

## Deliverable

Produce a sanitized `docs/operations/RAHGARD_LIVE_DEPLOYMENT_ACCEPTANCE_2026-11-18.md` (or dated by actual execution), including:
- timestamps/window, operator action/result, old/new SHAs, new backup basename/hash/off-host verify/restore evidence;
- pre/post DB counts and 16→20 migration ledger plus SQL checksums and RLS; exact API/Web image IDs;
- authenticated browser/API, Chat, catalogue 0, HTTPS checks and any unmet acceptance proof;
- explicit `LIVE GO`, `LIVE PARTIAL` or `LIVE NO-GO / SAFE ROLLBACK`, state of persistent DB and sessions, and any needed follow-on.
Commit and push only sanitized report/scripts to the feature branch. Keep backup ZIP/keys, credentials and personal data out of GitHub. **Do not modify release application SHA or retroactively claim a different deployed SHA.**

This mission is authorized to perform the exact live migrations and application restart/deployment **only after mandatory gates pass**. Publication of destinations, bulk import, SMS activation, RAG activation, Nginx/DNS changes, and unrelated releases remain NOT AUTHORIZED.
