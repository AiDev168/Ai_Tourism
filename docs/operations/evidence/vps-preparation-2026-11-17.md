# VPS release-preparation evidence — 2026-11-17

## Identity and state

- Branch: `feat/rahgard-national-catalogue-execution-handoff`
- Source release under rehearsal: `d5d9847373b20087a8a866449c6550d306f45b63`
- Active VPS release before and after rehearsal: `5e2664fb51e18f52549aa37a8b5793e12ace09b2`
- Target extracted at `/opt/rahgard-staging/releases/d5d9847373b20087a8a866449c6550d306f45b63`, inactive; current symlink unchanged.
- Active/target Compose SHA-256: `60bc1c55d70d42d0388cf806f95152e966bd9e3aadac1c02decaf3c78a1858e2` (identical).
- Source archive: 566 entries, 2,960,848 bytes, SHA-256 `66f31920440aef7bbf4547048856f12e3c7524e0dbcd1f095c1565891f5d9c15`.

## Backup record

- Command: `bash /opt/rahgard-staging/current/deploy/staging/backup.sh`
- Backup: `rahgard-20261117T075028Z-Tbh9jK.dump.enc`
- Remote path: `/opt/rahgard-staging/backups/rahgard-20261117T075028Z-Tbh9jK.dump.enc`
- Off-host encrypted copy: `C:\Projects\Ai_Tourism\artifacts\live-acceptance\vps-release-prep-2026-11-17\rahgard-20261117T075028Z-Tbh9jK.dump.enc`
- Size: 310,736 bytes.
- SHA-256: `a464e750fd7902d82eed56b94d420449d70c9d12a4f31161907b6e1b79ef7e2f` (local hash matched both the local and remote SHA sidecar).
- Remote HMAC-SHA256 verification: passed. The HMAC itself and both keys/passphrase remain private and are not included here.
- Decryption: passed only inside a mode-0700 directory on `/dev/shm`; PostgreSQL archive list check: passed.

## Isolated restore and migration results

The backup restored into a new one-run PostgreSQL 17 container with `--network none`, no published port, no bind mounts, no persistent volume, and tmpfs PGDATA. Before migration the copied ledger had 16 rows through `0017_provisional_itineraries`. After 0018–0021 it had 20 rows. The retained user, trip, knowledge and publication-view count checks matched exactly before and after.

| Migration | SHA-256 | Result |
|---|---|---|
| `0018_national_catalogue_ingestion` | `f5fc0cb3e3fcf61b36a5d21f9c98c3d75e04581cb19d4e22ad1754d53480dd36` | pass |
| `0019_partner_workspace` | `8f7c45e128faf0d9d91bf808159367a7a2636ac31b4544147619a9af751dd56` | pass |
| `0020_archive_candidate_publication` | `b6822a3401cef3f7ac8c85ce0577eb71d0373bc34bf4ec2d8c65b0a812f13326` | pass |
| `0021_postgis_security_definer_publication` | `bc0b6abb335549ddff91a811aeeca30bc5ba75d3e3f5f3fe81f7ded4b3bee650` | pass |

Post-migration checks in the clone: critical counts unchanged; destination
candidates 0; partner organizations 0; publication events 0; published view
0; 27 newly protected tables use RLS; 67 policies are present; app role is not
superuser and does not bypass RLS. The migration run completed and the clone,
derived image, containers, test-only secret files, and plaintext dump were
removed. The encrypted backup was retained.

## Application readiness and rollback rehearsal

- Normal Dockerfile build: failed before producing an image because Docker Hub returned HTTP 403 for the pinned `python:3.13.9-slim-bookworm` manifest request. This is the remaining image-production blocker.
- Candidate API source rehearsal: pass. The active runtime image was identified by immutable image ID; target and active `uv.lock` plus entrypoint were byte-identical. A temporary local image layer copied the exact target backend source and archive-preflight helper. It ran with the restored database, a network-isolated namespace, test-only tmpfs secrets, and auth/Chat/RAG/SMS disabled. `/health/ready` returned 200 and `/api/v1/catalog/destinations` returned 200 with count 0.
- Previous active API rollback rehearsal: pass against the same migrated clone. `/health/ready` returned 200 and catalogue count 0. No database rollback was performed.
- Image/container cleanup: pass; final query found no `rahgard.restore.target=isolated` containers or `rahgard-restore-api:*` images.

This validates source startup and previous-app compatibility against the cloned
schema. It does not produce the release API/web images needed for deployment,
nor does it exercise invitation login or a user journey.

## Read-only production checks after rehearsal

The active API, web, and database container IDs and image IDs were unchanged
from the initial inventory. All three remained running/healthy. PostgreSQL
remained 17.11 with named volume `rahgard_staging_pgdata`, ledger 16, tip
checksum `4576f4e1390de68345866e0d99815d1644833f577266539d47075da26776de6d`.
Aggregate counts remained: users 12, sessions 19, conversations 6, messages
33, trips 6, interests 3, constraints 3, itineraries 1, stops 6, provisional
itineraries 2, destinations 66, source links 116, sources 58, documents 52,
chunks 81, published view 0. No user-level records were read.

- Internal `/health/live` and `/health/ready`: 200.
- External `https://rahgard.hinaa.ir/`: HTTP 200 (`curl.exe` exit 0).
- External `/api/v1/catalog/destinations`: HTTP 200, count 0.
- Runtime flags observed only: Chat enabled, RAG disabled, SMS adapter disabled. No provider call or authenticated session was performed.

## Commands and observed exits

| Command/check | Exit/result |
|---|---|
| Git Bash `bash -n` on preflight, rehearsal and upgrade scripts | 0 |
| `git diff --check` | 0 |
| Source archive list and secret/artifact path scan | 0; 566 entries, no forbidden paths |
| `fetch-release.sh` for target SHA | 0; archive digest verified and inactive release extracted |
| `preflight-018-021.sh` | 0; 16/20 migrations, 4 pending |
| `rehearse-018-021.sh` final run | 0; restore, all migrations, target API and rollback API passed |
| HTTPS homepage request | 0; status 200 |
| HTTPS catalogue request | 0; status 200/count 0 |
| Standard Dockerfile API build attempt | nonzero; Docker Hub HTTP 403 as documented |

An initial run of the new rollback probe exposed an unset `current_sha` variable;
the cleanup trap removed the isolated resources, the script was fixed and
repackaged, and the final complete rehearsal then passed. No corresponding
failure occurred against the live database or services.
