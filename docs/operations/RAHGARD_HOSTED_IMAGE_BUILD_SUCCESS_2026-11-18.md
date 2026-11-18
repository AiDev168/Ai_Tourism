# Rahgard hosted release image build — verified GitHub Actions result (2026-11-18)

## Build result: PASS (not a production deployment approval)

Run: https://github.com/AiDev168/Ai_Tourism/actions/runs/44228225648
GitHub Actions run ID: `44228225648`; event: push on `main`, Git SHA `c3fe90fde021c5858601d4e66ff0fd93ce566fa0`.
Approved immutable **application source**: `d5d9847373b20087a8a866449c6550d306f45b63`.

All pinned parent images were pulled successfully by GitHub-hosted runner. Docker image build of API and Web, strict image bundle verification, and artifact upload all passed. Build log reported:

- API image ID: `sha256:5973182df93899773a67ccc2f6429942560403a1120a2ba9ebe9c430dc6accdd`
- Web image ID: `sha256:23632593de6b81908b247f2b76fe70b719d12c1db4e3081d1f89022cab921bea`
- Parent pulls (see manifest for canonical image names and RepoDigests): `sha256:b685a4fa58bb19d1814d78a1ec0f0208f351452724f78b20212c984d6e124a34`, `sha256:9bef0ef1e268f60627da9ba7d7605e8831d5b56ad07487d24d1aa386336d1944`, `sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`. These are pull log digests; the downloadable `release-manifest.json` should be used for strict name/digest validation.

- Bundle validator: `IMAGE_BUNDLE_PASS source=d5d9847373b20087a8a866449c6550d306f45b63 platform=linux/amd64 api_web_tags=exact checksums=pass secret_scan=pass`
- Uploaded GitHub artifact name: `rahgard-release-images-d5d9847-linux-amd64`
- Artifact ID: `14393716721`
- Artifact link: https://github.com/AiDev168/Ai_Tourism/actions/runs/44228225648/artifacts/14393716721
- Artifact ZIP size reported: 292,687,935 bytes; ZIP SHA-256 from upload log: `956d3dd173e97f3d9f28cc530d18e434132d08eafac83e10db820ad8b10dd614`
- Artifact expiration: 2026-11-25 03:08:43 UTC (7-day retention).

## Root cause and corrections

Rerunning older GitHub workflow runs kept using the old Git SHA before PR #19; the PR #19 filename correction was not present in those attempts. A new workflow run at `870971e...` showed the original config-path problem resolved but falsely flagged a base-image standard `var/backups` directory. Subsequent new runs identified public CA trust-store PEM files in Debian/Alpine and pip/certifi packages. The scanner was corrected with narrowly enumerated public-trust-store exceptions, preserving rejection of private PEMs, `.env`, keys, backup files, and runtime secret paths. The final run at `c3fe90f...` fully succeeded.

## Known limits — DO NOT DEPLOY YET

- GitHub-built artifact is **available** but has not been transferred to VPS or loaded there, and its manifest has not been independently inspected on the VPS.
- Isolated PostgreSQL restored-database rehearsal using **these exact API/Web images** still must pass (use `docs/operations/RAHGARD_HOSTED_IMAGE_BUILD_HANDOFF.md` and `scripts/ops/verify_and_rehearse_rahgard_image_bundle.sh`).
- Existing encrypted off-host backup and 0018–0021 isolated migration rehearsal remain reported successful in `docs/operations/VPS_RELEASE_GO_NO_GO.md`; do not confuse those previous rehearsals with running the final hosted images.
- The npm build logged five high-severity dependency audit findings; assess production relevance independently instead of silently upgrading immutable locked dependencies. Image build success is not a security acceptance or deployment authorization.
- Live VPS is still expected to be on `5e2664fb51e18f52549aa37a8b5793e12ace09b2`; not rechecked by this GitHub-only operation. No live migration, deployment, restart or publication was performed.

## Next exact step

Download the successful artifact before expiration, verify the zip/inner checksums, securely transfer it via approved SSH and perform the **isolated** restore/image rehearsal without touching running services or persistent DB. Only then request a separate precise owner GO for migrations 0018–0021 and deployment of immutable source SHA `d5d984...`.
