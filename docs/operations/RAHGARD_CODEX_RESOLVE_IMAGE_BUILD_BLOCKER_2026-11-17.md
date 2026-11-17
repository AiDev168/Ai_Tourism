# Codex — resolve the pinned Docker image build blocker, without deployment

## Current status and scope

Previous preparation report: `docs/operations/VPS_RELEASE_GO_NO_GO.md` at commit `30881f164c17236499327a3c2c5f1dfc41222e84`.

- **Prepared immutable source release:** `d5d9847373b20087a8a866449c6550d306f45b63`.
- **Live VPS release, DO NOT CHANGE:** `5e2664fb51e18f52549aa37a8b5793e12ace09b2`.
- **VPS database:** 16 migrations through 0017; named PostgreSQL volume `rahgard_staging_pgdata`; live data must remain unchanged.
- **Successful isolated acceptance:** existing encrypted off-host backup verified, restored in disposable PG17, additive migrations 0018–0021 passed, database counts retained, old and candidate API readiness passed.
- **Remaining failure:** standard API build cannot fetch pinned `python:3.13.9-slim-bookworm` from Docker Hub because registry manifest HEAD returns HTTP 403. Standard API and web image pair was not produced.

The owner authorizes **technical blocker remediation and non-live image/package validation only**. This is NOT authorization for live migration 0018–0021, application deployment, restart, public publication, modifying running services, DNS/Nginx, or changing production data.

## Single focused mission

1. Reproduce and identify the specific registry-access failure *without leaking tokens or credentials*. Distinguish 403 from access policy, authentication, hub-rate/geographic/network controls, proxy/mirror configuration, and unavailable tag/digest. Inspect safe Docker/BuildKit daemon and client configurations and which pinned base images and immutable digests are already available locally on the owner Windows machine or VPS.

2. Prefer an **approved, reproducible offline path**: acquire the pinned trusted base images on a machine/network that can legitimately access an approved registry, verify architecture, canonical names and immutable content digests, transfer only checksummed OCI/Docker image bundles over the existing authorized SSH channel, and load these into Docker on the VPS without modifying running Rahgard containers. Required Dockerfile parents:
   - API build and runtime: `python:3.13.9-slim-bookworm`
   - Web build: `node:22.14-alpine`
   - Web runtime: `nginx:1.27-alpine`

   Do not silently substitute newer/unpinned images or an untrusted mirror. If external npm/PyPI/uv package download is also blocked, resolve with a similarly approved, reproducible lockfile-based cache/bundle; do not relax `uv.lock`, `package-lock.json` or dependency integrity controls.

3. Build **both** `rahgard-api:d5d9847373b20087a8a866449c6550d306f45b63` and `rahgard-web:d5d9847373b20087a8a866449c6550d306f45b63` from the previously prepared immutable release. Confirm source `RELEASE_COMMIT` and artifact checksum, exact image tag->ID mapping, parent base image digests, correct architecture, expected entrypoints, no secrets copied into layers, and that the persistent PostgreSQL volume and active service containers remain untouched. Do not change the deployable source SHA without an explicit documented new source build/review cycle.

4. Run **isolated** API and PWA smoke and compatibility validation on a disposable restored database including migrated schema. Verify API readiness, partner/source permission gates, published catalogue empty baseline, web static assets, reverse proxy and browser served by the built web image, and former-app compatibility with the migrated schema. Do not rely on the earlier derived temporary API image as proof of a normal target build. Verify image availability for the no-build deployment mode and correct `RAHGARD_BUILD_IMAGES=false` semantics, without changing live `.env`.

5. Record commands, exact digests/hashes, evidence, and any remaining blockers in an updated `docs/operations/VPS_RELEASE_GO_NO_GO.md` and sanitized evidence. Do not commit base-image archives, release tarballs, credentials, encrypted DB backups or generated screenshots to the public repo. If a trusted registry cannot be accessed, finish with BLOCKED and one concrete alternate approved transport option rather than bypassing integrity checks.

## Delivery and hard STOP

Commit and push only source/documentation changes needed for reproducible image building, preferably retaining immutable target source SHA. Return:
- final Git HEAD and **actual deployable** source SHA;
- exact API/web image identity and tested base digests;
- isolated image + DB compatibility test results and backup/restore status;
- changes, if any, to runtime configuration and whether the currently live stack was touched (expected **NO**);
- `READY FOR OWNER DEPLOYMENT APPROVAL` or `BLOCKED`, with precise reason.

**STOP before live migrations, `deploy.sh`, application restarts, symlink changes, registry credentials injected into production services, or public publication.** The owner must explicitly approve a separate, exact-SHA rollout once image preparation succeeds.
