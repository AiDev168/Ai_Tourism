# Rahgard V2 Issue #24 preparation

The [apex authentication follow-up](RAHGARD_V2_ISSUE24_APEX_AUTH_GATE.md) records the runtime origin check, the exact-host rehearsal and the password-compatible successor to the candidate documented below.

**Decision: NO-GO / BLOCKED.** The release candidate, encrypted off-host snapshot, restored-data migrations and local browser journey passed the checks below. Live apex cutover requires the owner’s routing decision and the remaining deployment checks. The sole canonical target is **https://hinaa.ir/**.

## Current state and apex ownership decision

On November 23 the VPS ran `5e2664fb51e18f52549aa37a8b5793e12ace09b2` in both Rahgard API and Web tags. The three containers reported healthy. PostgreSQL 17.11 used `rahgard_staging_pgdata`, the database marker matched and the full 20-entry ledger through 0021 matched the candidate’s historical CRLF SQL bytes. A repeat read-only probe at 03:19:25 UTC returned the same SHA and 20 ledger rows. Legacy root, service worker and manifest each returned HTTP 200. The [read-only baseline](evidence/issue24/R0-baseline.json) carries the exact hashes, image identities, SSH host fingerprint and aggregate counts.

Arvan DNS serves apex, www and the legacy subdomain. The public apex certificate covers `hinaa.ir`. An HTTPS GET to the apex returned Arvan HTTP 301 to `https://www.hinaa.ir/`, which returned HTTP 502 on the same probe. The redirect is in use. Its intended owner and www upstream cannot be established from public DNS or this VPS’s Nginx configuration. The owner must decide whether the apex redirect can be replaced and identify any service that needs to retain it. Dashboard settings and edge-to-origin certificate verification remain unverified.

The existing HTTPS origin listens on port 63202 as a default server for `rahgard.hinaa.ir`, forwarding to loopback 18080. Its origin certificate only covers that subdomain. The [separate apex vhost](../../deploy/staging/nginx-apex-v2.conf.template) adds exact apex SNI and Host on the same HTTPS listener without claiming the default server. It forwards to a separate loopback port 18081 and keeps the legacy config and upstream. The candidate TLS test with a disposable certificate returned apex 200, legacy 200, mismatched SNI 421 and 404 for admin, local-owner and OTP paths. The real apex origin still needs a trusted apex SAN certificate and an approved Arvan HTTPS origin mapping with matching SNI, Host and certificate verification.

## Backup, migration and rollback evidence

Fresh snapshot `rahgard-20261123T030841Z-97fd9c17.dump.enc` was streamed from a read-only live `pg_dump`, encrypted on the VPS without writing a backup there, and authenticated and retained on Windows under a restricted ACL. The key and archive directories are separate. SHA-256 is `1efc1760cfac0d64a1cc9173717209b326ae9ce05825a184879bc268aa37167f`. The restore checked SHA-256, HMAC, decryption and `pg_restore --list`. Archive and keys remain outside the repo. Independent custody beyond this off-host workstation was not demonstrated.

The isolated PG17 rehearsal used the actual snapshot, a newly created networkless Docker container, tmpfs and zero published ports. The ledger advanced from 20 to 22 entries. The two migrations took 0.164 s and 0.156 s respectively in this replay. These are measured SQL execution times, not a downtime estimate.

| Migration | Exact candidate blob SHA-256 |
| --- | --- |
| 0022 | `e6b7db49abc0ff76c2620b2cc8d5dded0f4255f8533efd20bd5b402a0ba57eda` |
| 0023 | `deef8c5016f26aa646b9ff22346fad4ade3c6780ff447f701aa9e8a8e28571ac` |

All 23 measured relation counts were preserved, including 12 user accounts, 21 sessions, six trips, six conversations, 42 messages, one itinerary and two provisional plans. There were zero published destinations and zero new share/response rows. The rehearsal caught table-level grants inherited from 0019 that would have allowed the app role to write `partner.organizations.is_test`. Migration 0023 now uses grants limited to pre-existing columns for INSERT and UPDATE. The corrected replay verified the restricted flag, RLS, no bypass by the app role and no direct insert on revisions or inbox. Negative preflight checks rejected marker, volume, altered ledger, and pre-existing schema object mismatches.

Both the live API image and the candidate API image reported ready on the same migrated clone and agreed on zero published destinations. The API probes did not enable auth or exercise legacy writes. Code rollback health and catalogue access passed. Old authenticated write compatibility and a dual-writer design are unresolved. If an approved cutover encounters a critical regression, halt candidate traffic and preserve the database. Restore the prior apex route and use a code-only rollback only within the proven compatibility scope. Any live data recovery or forward fix requires a separately reviewed incident plan. See [migration evidence](evidence/issue24/R2-restore.json).

## Immutable release and browser verification

The immutable application candidate is `cb5952bac5d13753e41b5845b1d3663eae4c0708`. [GitHub Actions run 45104565876](https://github.com/AiDev168/Ai_Tourism/actions/runs/45104565876) built and archived both Linux AMD64 images. Artifact 14787231271 was downloaded before expiration and retained off-host. Its outer SHA, both inner checksums, both source labels, base digests and loaded image identity passed verification. Docker Desktop reported different manifest IDs from the hosted builder, and the verifier proved config and uncompressed layer equivalence by exporting the loaded tags. [Image evidence](evidence/issue24/R3-images.json) records both ID sets.

The exact verified Web image served root, manifest, service worker and referenced hashed CSS/JS as the Nginx worker with expected MIME and 404 for missing assets. The local production Vite build and both PWA asset injection tests passed. This verifies the image and offline shell build. Physical installation and service-worker updating from the public apex remain unverified.

The local browser run used real FastAPI, Chromium, disposable PostgreSQL 17 through the corrected 0023, and LM Studio. Three inference calls succeeded. It verified traveler correction, provisional itinerary edit/save/reopen, two protected company deep links, consented bulk selection, revision, company response and counteroffer, traveler acceptance, revocation and tenant denial. The restored-data probes were run separately from this synthetic browser journey.

- Backend regression: **504 passed, 18 skipped**. Frontend: **199 passed**. Build/typecheck, Ruff and harness syntax passed. PWA asset injection: **2 passed**.
- Native 390 and 1440 px traveler and company viewports passed no-overflow checks in both themes. The keyboard-operated theme toggle had an accessible name, a visible focus indicator and at least 44×44 CSS pixels. Measured toggle text contrast was 11.67:1 in light and 15.39:1 in dark. The dark traveler capture still shows a light progress card. This sample is not a full WCAG audit.
- Existing collapsible day tests passed, including collapse/reopen with an unsaved stop edit. The final browser itinerary edit persisted. Full keyboard and long-itinerary checks across 4/15/30 days remain unverified.
- [Sanitized Chromium trace and screenshot names](evidence/issue24/R4-browser.json), [traveler dark 390](evidence/issue24/release-traveler-dark-390.png), [company dark 390](evidence/issue24/release-company-dark-390.png), [traveler light 1440](evidence/issue24/release-traveler-light-1440.png), [company light 1440](evidence/issue24/release-company-light-1440.png).

## Reproduce preparation

From a Windows checkout containing the preparation tooling, use separate ACL-restricted backup and key directories outside Git. Use the immutable candidate SHA to select the SQL and images, even if the branch advances with reports or tests.

```powershell
$candidate = 'cb5952bac5d13753e41b5845b1d3663eae4c0708'
$live = '5e2664fb51e18f52549aa37a8b5793e12ace09b2'
$baseline = 'docs/operations/evidence/issue24/R0-baseline.json'
python scripts/ops/check_rahgard_v2_ledger.py $baseline $candidate
python scripts/ops/capture_rahgard_v2_backup.py $live $protectedArchives $protectedKeys
python scripts/ops/rehearse_rahgard_v2_migrations.py $baseline $candidate $encryptedArchive $protectedKeys --openssl $opensslExecutable --runtime-image "rahgard-api:$live" --runtime-image "rahgard-api:$candidate"
python scripts/ops/test_rahgard_apex_routing.py "rahgard-web:$candidate" "rahgard-api:$candidate" --openssl $opensslExecutable
$env:RAHGARD_RELEASE_THEME_QA = '1'
.\engineering\pilot\Run-National-Catalogue-Browser-E2E.ps1 -ChatProvider lm_studio
```

Check the hosted ZIP against the GitHub artifact digest before extraction and verify the inner SHA-256 list before any Docker load. With the file names from the artifact, the exact image checks are:

```powershell
python scripts/ops/verify_rahgard_release_image_bundle.py verify --source-sha $candidate --image-archive $verifiedTar --manifest $verifiedManifest
docker image load --input $verifiedTar
python scripts/ops/verify_rahgard_release_image_bundle.py verify --source-sha $candidate --image-archive $verifiedTar --manifest $verifiedManifest --check-loaded-images
```

## Stop before rollout

1. Obtain the exact owner decision about replacing the current apex redirect. Verify the Arvan dashboard’s current origins and decide how the existing subdomain stays available while preserving one authoritative writer for traveler data.
2. Obtain and verify the exact apex origin certificate and independently rehearse the candidate’s combined origin, API and Web traffic with same-origin secure sessions and CSRF. The isolated TLS probe used fixture upstreams and the browser run used the local test origin.
3. Complete reviewed production migration execution, maintenance and rollback tooling after the domain and data-writer topology are approved. The checked-in tooling applies DDL only to an owned disposable restore. The existing live upgrade script stops at 0021. The existing default vhost installer and `deploy.sh` for the legacy stack cannot safely activate this apex route.
4. Once those gates pass, submit the release SHA, protected artifact, fresh final backup and restore proof, maintenance window, write controls and candidate-specific apply/rollback commands for separate live approval. Authorized activation must be followed by exact apex HTTPS/auth/PWA and legacy health checks, then `scripts/Verify-RahgardRelease.ps1` for real three-way parity.

Windows and GitHub held the same immutable candidate at build time. The branch subsequently records test and evidence changes. The running VPS still holds the legacy SHA. Three-environment synchronization has not occurred.
