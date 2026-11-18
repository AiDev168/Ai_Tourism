# Rahgard live deployment acceptance — 2026-11-18

## Decision

**LIVE NO-GO / SAFE APPLICATION ROLLBACK.** The explicitly approved target was deployed briefly after all backup and migration gates passed, but its public PWA manifest and service worker returned HTTP 403. The cause was verified inside the target Web image: both files were packaged with mode `0600` and were unreadable to the Nginx worker. The guarded application deployment path was used to restore the previously active application SHA. PostgreSQL was not rolled back. The live database is now migrated through 0021 and the previous application is healthy against it.

No catalogue content was published. SMS and RAG remain disabled. No production data was reset, restored over, imported, or deleted.

## Release identity and actions

Execution window: approximately 2026-11-18 08:55–09:04 UTC. Existing SSH host alias `rahgard-vps` and the authorized `zoneroot` account were used; no credential values were read into the report.

| Item | Observed result |
|---|---|
| Approved immutable target | `d5d9847373b20087a8a866449c6550d306f45b63` |
| Pre-rollout live application | `5e2664fb51e18f52549aa37a8b5793e12ace09b2` |
| Target deployment attempt | Guarded `deploy.sh d5…` passed container health checks; d5 was then running briefly |
| Target Web acceptance | **Failed:** `/manifest.webmanifest` and `/sw.js` returned 403 both from the public URL and from the VPS Web upstream |
| Verified cause | In d5 Web image, both static files had mode `0600 root:root`; the Nginx worker could not read them. In the previous Web image they were readable (`0755`) |
| Rollback | Guarded application-only `deploy.sh 5e…` completed successfully; no database rollback |
| Current live application SHA | `5e2664fb51e18f52549aa37a8b5793e12ace09b2` |
| Current branch documentation HEAD | `7f7fb927d2baa7d27feda8120f9dd688f6ea9286` on Windows and `origin/feat/rahgard-national-catalogue-execution-handoff` before this report commit |
| Database volume | Same `rahgard_staging_pgdata`; PostgreSQL container ID remained `8eb0c092272ae2109ca425478ba380382769776cf27ecdc5669afb7d4eaa6aab` |

The target source SHA was already present in the local Git object database and in the protected VPS release directory. The preloaded `linux/amd64` target image tags matched the verified hosted artifact. Target image IDs observed before rollout were API `sha256:88d060821b6d2bce3be3426b8012c76a411d68682939d9ca22f2947d861a2674` and Web `sha256:14d97ad5616921231912ef4dd9e698140202d4017a1d07c3e9228163dfbc14d1`.

## Fresh backup and isolated restore

- Fresh encrypted backup: `rahgard-20261118T085804Z-Qern0p.dump.enc`.
- SHA-256: `8f130852de5341910f9224cfc6343644aaa3c2dbda820423b518ebdf9927b388`.
- Copied over the authenticated SSH channel to an off-host Windows `%LOCALAPPDATA%\Rahgard\Issue20\backups` directory. Its ACL was restricted to the owner account, SYSTEM, and Administrators. The off-host copy SHA-256 matched the server-generated sidecar.
- The existing protected-key procedure verified the backup HMAC; decryption to tmpfs and `pg_restore --list` passed.
- `rehearse-018-021.sh` restored this fresh backup to a disposable, network-isolated, tmpfs-only PostgreSQL 17 container. It preserved the baseline counts, applied migrations 0018–0021 with the exact checksums below, passed security checks, and verified API readiness/catalogue access plus previous API compatibility. Temporary containers/network and decrypted dump were removed. The fresh-run output did not include a Web-image acceptance line; see the precise command result below.

## Migration result

The guarded live migration command advanced the ledger from 16 entries through 0017 to 20 entries through 0021. Each SHA-256 matched the reviewed d5 SQL source:

| Migration | SHA-256 | Result |
|---|---|---|
| `0018_national_catalogue_ingestion` | `f5fc0cb3e3fcf61b36a5d21f9c98c3d75e04581cb19d4e22ad1754d53480dd36` | Applied and verified |
| `0019_partner_workspace` | `8f7c745e128faf0d9d91bf808159367a7a2636ac31b4544147619a9af751dd56` | Applied and verified |
| `0020_archive_candidate_publication` | `b6822a3401cef3f7ac8c85ce0577eb71d0373bc34bf4ec2d8c65b0a812f13326` | Applied and verified |
| `0021_postgis_security_definer_publication` | `bc0b6abb335549ddff91a811aeeca30bc5ba75d3e3f5f3fe81f7ded4b3bee650` | Applied and verified |

Post-migration security checks: 27 RLS-enabled protected tables, 67 policies; `ai_tourism_app` remains neither superuser nor `BYPASSRLS`.

## Data preservation and non-publication

Read-only aggregate counts immediately before migration and after application rollback:

| Data | Before | After |
|---|---:|---:|
| Users | 12 | 12 |
| Sessions | 19 | 19 |
| Conversations / messages | 6 / 33 | 6 / 33 |
| Trips | 6 | 6 |
| Canonical itineraries / stops | 1 / 6 | 1 / 6 |
| Provisional itineraries | 2 | 2 |
| Destinations / destination-source links | 66 / 116 | 66 / 116 |
| Knowledge sources | 58 | 58 |
| Documents / chunks | 52 / 81 | 52 / 81 |
| Published catalogue view | 0 | 0 |
| Destination candidates / candidate evidence / publication events | Not present before migration | 0 / 0 / 0 |
| Partner organizations / services / schedules / offers / prices / availability | Not present before migration | 0 / 0 / 0 / 0 / 0 / 0 |

Runtime remained `APP_ENV=staging`; SMS adapter is disabled and `TOURISM_RAG_ENABLED=false`. No content publication, SMS activation, RAG activation, or import occurred.

## Live checks after safe rollback

From an external Windows client, HTTPS returned:

| Request | Result |
|---|---|
| `/` | 200 |
| `/manifest.webmanifest` | 200 |
| `/sw.js` | 200 |
| `/api/v1/auth/method` | 200; OTP and staging-invitation methods reported; SMS delivery unavailable |
| `/api/v1/catalog/destinations?limit=1` | 200; count 0 |
| `/api/v1/auth/me` without a session | 401, expected |

The current API, Web, and PostgreSQL containers report healthy. Internal API `/health/ready` returned 200. The previous release serves hashed JS/CSS assets with HTTP 200. The target d5 Web image did not pass PWA acceptance, so it is not the active release.

Authenticated traveler/browser login, Chat, and itinerary acceptance were **not performed**: no specifically authorized test account/invitation was available for use under the runbook, and no existing user's private account was accessed.

## Commands executed

All remote commands used the existing batch-mode `zoneroot@rahgard-vps` SSH connection. Relevant commands:

- `preflight-018-021.sh` — PASS before backup, before migration, and after migration.
- `backup.sh` — PASS; generated the fresh encrypted backup and authentication/checksum sidecars.
- `rehearse-018-021.sh rahgard-20261118T085804Z-Qern0p.dump.enc` — PASS on isolated PostgreSQL 17; restore, exact migrations, data counts, and RLS passed. The recorded fresh-run output showed isolated API readiness/catalogue and previous-API compatibility; it did not emit a fresh Web-image acceptance line. The prior hosted-image rehearsal documented exact target Web static-shell/proxy checks, but the live d5 Web image subsequently failed the manifest/service-worker permission check.
- `upgrade-018-021.sh 5e2664fb51e18f52549aa37a8b5793e12ace09b2 d5d9847373b20087a8a866449c6550d306f45b63 rahgard-20261118T085804Z-Qern0p.dump.enc OFFHOST_AND_ISOLATED_RESTORE_VERIFIED OWNER_APPROVED_APPLY_018_021` — PASS; ledger 20/20.
- `deploy.sh d5d9847373b20087a8a866449c6550d306f45b63` — container health PASS; PWA check then failed on manifest/service-worker 403.
- `deploy.sh 5e2664fb51e18f52549aa37a8b5793e12ace09b2` — guarded application-only rollback PASS; DB retained.
- External HTTPS probes — shell, manifest, service worker, auth method, and legacy catalog PASS; anonymous `/auth/me` correctly returned 401.

## Required follow-up

The d5 application SHA is **not** the active VPS SHA. Correct the static-file packaging permissions in a new reviewed release, rebuild and verify the Web image, then rehearse and obtain separate owner authorization for any further live rollout. Migrations 0018–0021 are already applied and must not be rerun; future preflight should recognize the 20-entry ledger. The current 5e application remains live and healthy against the migrated schema. Do not restore the pre-migration database over live data.
