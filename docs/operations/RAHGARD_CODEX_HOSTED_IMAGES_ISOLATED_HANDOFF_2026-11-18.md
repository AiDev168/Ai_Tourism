# Codex one mission — complete hosted-image handoff and isolated VPS compatibility acceptance

## Verified state at handoff (2026-11-18)

A GitHub-hosted run **successfully built both immutable Rahgard release images** and uploaded the checksum-verified bundle. Do not re-run Docker Hub pulls or rebuild unless actual artifact verification fails.

- Successful run: https://github.com/AiDev168/Ai_Tourism/actions/runs/44228225648
- Run ID: `44228225648`; artifact ID: `14393716721`; artifact name: `rahgard-release-images-d5d9847-linux-amd64`.
- Immutable **application release SHA**: `d5d9847373b20087a8a866449c6550d306f45b63`.
- GitHub CI tooling SHA used: `c3fe90fde021c5858601d4e66ff0fd93ce566fa0`.
- Artifact ZIP SHA-256 from upload log: `956d3dd173e97f3d9f28cc530d18e434132d08eafac83e10db820ad8b10dd614`, size 292,687,935 bytes.
- API image ID `sha256:5973182df93899773a67ccc2f6429942560403a1120a2ba9ebe9c430dc6accdd`.
- Web image ID `sha256:23632593de6b81908b247f2b76fe70b719d12c1db4e3081d1f89022cab921bea`.
- Artifact expires **2026-11-25 03:08 UTC**. Download and preserve a private, off-host copy promptly.
- Source archive had been staged as the inactive VPS release; former live release was `5e2664fb51e18f52549aa37a8b5793e12ace09b2`. Reverify live identity read-only; don't assume state unchanged.
- The branch now has the **proven corrected** verifier copied from `main` with the exact same Git blob SHA `6ec5fc8fe1ad3dd877ed72a7b692a45ff78797fa`. Use this corrected file, **not** the outdated verifier in the immutable d5 source tree or earlier tooling copies.

The GitHub success proves build, internal archive scan, two image IDs and artifact upload. It does NOT prove that the package runs against an isolated backup clone on the VPS; it does NOT grant deployment authorization.

## Execute end-to-end without involving owner in manual artifact handling

1. Use the existing authenticated `gh` CLI and authorized Windows-to-VPS SSH operator environment. Download the specific artifact by run ID to the repo-ignored `artifacts/live-acceptance/vps-release-prep-2026-11-17/` directory or a similarly private path. Do **not** commit the artifact or upload it to any public repository. Verify ZIP hash above and interior `SHA256SUMS.txt`, `release-manifest.json`, target image tags, three parent RepoDigests, exact revision label, linux/amd64, image IDs and Dockerfile/lockfile digests. If `gh` authentication fails, examine safe existing access instead of fabricating success. If blocked, report the precise needed owner action.

2. Copy the verified extracted bundle over existing authenticated SSH into the appropriately locked-down `/opt/rahgard-staging/incoming/` directory. Provision only private incoming/tool directories as needed, **without restarting or changing** running application/database containers. Reverify exact content hash on the VPS. Use private operator ACLs and no plaintext secrets in logs.

3. Sync the **current corrected** `scripts/ops/verify_rahgard_release_image_bundle.py`, `scripts/ops/verify_and_rehearse_rahgard_image_bundle.sh`, and `deploy/staging/rehearse-018-021.sh` from this feature branch as expected under `/opt/rahgard-staging/tools/`. Existing handoff instructions in `docs/operations/RAHGARD_HOSTED_IMAGE_BUILD_HANDOFF.md` show layout and the pre-existing backup name `rahgard-20261117T075028Z-Tbh9jK.dump.enc` (verify the name and backup integrity again before use).

4. Execute ONLY the guarded `verify_and_rehearse_rahgard_image_bundle.sh` in its **isolated** mode. It should verify the bundle before and after `docker load`, check image IDs and labels, restore the authenticated encrypted backup to network-isolated tmpfs PostgreSQL 17, apply migrations 0018–0021 on the clone only, run the exact built API/Web against that clone, check web-to-API path, publication/tenant security gates, preserved row counts, and previous API compatibility. Do not accept a runtime-derived temporary API as proof. Docker image loading is permitted so long as no running service is replaced/restarted and no active image ID is overwritten.

5. Investigate the GitHub build's **five high-severity npm audit findings** against the exact immutable `frontend/package-lock.json` and deployed runtime exposure. Produce package names, advisory identifiers, reachable/exploitable risk, affected build-only versus runtime dependencies, and a concrete recommendation. Do not silently run `npm audit fix --force` or change d5's immutable source / lockfiles. If a serious production-reachable vulnerability exists, mark **NO-GO** and propose a separately reviewed new release SHA.

6. Write one concise exact-evidence report under `docs/operations/` and update `VPS_RELEASE_GO_NO_GO.md` to reflect the successful hosted image build and the **actual** strict isolated image/database rehearsal outcome. Record SHA, artifact ID and hashes, image IDs, loaded image IDs, active VPS SHA and data counts (aggregate only), migration and RLS results, npm audit outcome, service unchanged assertions, and evidence of backup/rollback. No sensitive artifacts, credentials, user records, or screenshot dumps in GitHub.

## Hard security / authorization limits

**No live deployment is authorized.** DO NOT run live upgrade/migration 0018–0021, `deploy.sh`, `docker compose up` for live app, `initialize-db.sh`, change `/opt/rahgard-staging/current`, restart live services, modify live config/secrets, run Nginx/DNS changes, or publish any archive content. Preserve every existing user, itinerary, organization, destination, session and source record.

At the end, commit/push tooling corrections and sanitized report to the same feature branch. Return `READY FOR OWNER PRODUCTION APPROVAL` only if all image artifact, restored-database, web/API, rollback, and security gates pass. Otherwise return `BLOCKED`/ `NO-GO` with the exact failure and corrected implementation where possible. The owner must separately authorize any live rollout, with the *exact* SHA and migrations, after reviewing this report. No promise of deferred/background work.
