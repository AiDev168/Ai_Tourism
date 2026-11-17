# Rahgard VPS release decision — 2026-11-17

## Decision

**PREPARATION: PREPARED WITH A TECHNICAL IMAGE-BUILD BLOCKER.**

**LIVE ROLLOUT: NOT AUTHORIZED / NOT PERFORMED.** This report is not a GO for
production deployment. The current app, database, Nginx, DNS, secrets, and
published catalogue were left as found. The target release is staged but
inactive.

The exact source release prepared and rehearsed is
`d5d9847373b20087a8a866449c6550d306f45b63` on
`feat/rahgard-national-catalogue-execution-handoff`. The active VPS release is
still `5e2664fb51e18f52549aa37a8b5793e12ace09b2`. The prepared GitHub source
archive SHA-256 is
`66f31920440aef7bbf4547048856f12e3c7524e0dbcd1f095c1565891f5d9c15` (566
entries; 2,960,848 bytes). It excludes local artifacts, `.env`, keys, and
database archives. The target release directory's `RELEASE_COMMIT` matches
the target SHA, but `/opt/rahgard-staging/current` was not changed.

The target Compose file is byte-identical to the active Compose file
(SHA-256 `60bc1c55d70d42d0388cf806f95152e966bd9e3aadac1c02decaf3c78a1858e2`).
Relative to the accepted application baseline `e54ccabca57a272f5065c963b074319b0174c5db`,
this preparation release contains only the task specification and guarded
operations scripts/documentation; it does not change traveler or partner
application source. The API Dockerfile adds the candidate's archive-preflight
helper to the image.

## Live state observed read-only

| Item | Observed value |
|---|---|
| Current release marker | `5e2664fb51e18f52549aa37a8b5793e12ace09b2` |
| API | running/healthy; `rahgard-api:5e2664…`; image `sha256:8017e312…` |
| Web | running/healthy; `rahgard-web:5e2664…`; image `sha256:b22b15eb…` |
| Database | running/healthy; PG `17.11`, `server_version_num=170011` |
| Persistent volume | `rahgard_staging_pgdata`, mounted at PostgreSQL PGDATA |
| Migration ledger | 16 entries, through `0017_provisional_itineraries`; checksum `4576f4e1…` |
| Live new candidate/partner migrations | 0018–0021 pending; none were run live |
| Existing publication view | 0 rows |
| Live RLS policies | 0 before 0018; new review/partner RLS exists only in rehearsal |
| Active Compose digest | identical to the inactive target Compose digest above |

Privacy-safe live counts observed before and after rehearsal were unchanged:

| Data | Count |
|---|---:|
| Users | 12 |
| Sessions | 19 |
| Conversations / messages | 6 / 33 |
| Trips | 6 |
| Trip interests / constraints | 3 / 3 |
| Canonical itineraries / stops | 1 / 6 |
| Provisional itineraries | 2 |
| Canonical destinations | 66 |
| Destination-source links / knowledge sources | 116 / 58 |
| Knowledge documents / chunks | 52 / 81 |
| Published destination view | 0 |

The 700 archive candidates, 257 source candidates, and test publications
belong to earlier disposable acceptance only; they were not assumed to exist
or copied to this VPS. The target migrations create candidate/review and
partner structures but did not seed or publish content in rehearsal.

The public HTTPS homepage returned 200 and the public destination-catalogue
endpoint returned 200 with `count=0`. Internal API liveness/readiness both
returned 200. `INTERNAL_CHAT_ENABLED=true`, `TOURISM_RAG_ENABLED=false`, and
`AUTH_SMS_ADAPTER=disabled` were observed as flags only. No SMS, Chat, RAG,
invitation, or traveler-authenticated request was made. A configured Chat flag
is not evidence of a successful live model call.

## Backup and isolated restore

The existing protected `backup.sh` created
`rahgard-20261117T075028Z-Tbh9jK.dump.enc`. The encrypted archive (310,736
bytes) was copied off the VPS into the ignored local preparation directory at
`artifacts/live-acceptance/vps-release-prep-2026-11-17/`. Local SHA-256
`a464e750fd7902d82eed56b94d420449d70c9d12a4f31161907b6e1b79ef7e2f` matches
the VPS sidecar. VPS-side HMAC verification passed; the HMAC value, encryption
passphrase, and key were not copied into this repository or report.

The isolated rehearsal authenticated and decrypted that backup only under a
mode-0700 `/dev/shm` directory, confirmed `pg_restore --list`, and restored it
into a uniquely named PostgreSQL 17 container using `--network none`, no
published ports, no bind/persistent mounts, and tmpfs PGDATA. The original
critical counts above matched in the restored copy. The rehearsal then applied
0018–0021 only to that clone and confirmed 20 ledger rows, unchanged critical
counts, no new candidate/partner/publication records, 27 protected tables with
RLS, 67 policies, and a non-superuser/non-BYPASSRLS application role. It
removed the isolated containers and plaintext dump. The encrypted backup
remains retained off-host and on the VPS.

Migration checksums rehearsed:

| Migration | SHA-256 |
|---|---|
| `0018_national_catalogue_ingestion` | `f5fc0cb3e3fcf61b36a5d21f9c98c3d75e04581cb19d4e22ad1754d53480dd36` |
| `0019_partner_workspace` | `8f7c45e128faf0d9d91bf808159367a7a2636ac31b4544147619a9af751dd56` |
| `0020_archive_candidate_publication` | `b6822a3401cef3f7ac8c85ce0577eb71d0373bc34bf4ec2d8c65b0a812f13326` |
| `0021_postgis_security_definer_publication` | `bc0b6abb335549ddff91a811aeeca30bc5ba75d3e3f5f3fe81f7ded4b3bee650` |

The migrations add review/admin geography, candidate, partner, and publication
structures, a nullable `knowledge.destinations.admin_area_id`, grants and RLS
policies. Migration 0021 replaces the existing destination-location trigger
function with explicitly qualified PostGIS references; it does not backfill
destination rows. Rehearsal also exercised both the target API source and the
currently active API image against the migrated clone. Each returned readiness
200 and catalogue count 0. This supports an application-only rollback; it is
not a reason to reverse database migrations. If an issue occurs after schema
application, keep the schema and use the tested previous app release or a
forward fix.

## Technical blocker: standard image build

The normal Docker build for the pinned base image
`python:3.13.9-slim-bookworm` failed on the VPS with Docker Hub HTTP `403
Forbidden` on the registry manifest HEAD request. No image service was
restarted. The isolated API rehearsal therefore layered the exact target
backend source onto the already-running API image only after confirming that
`uv.lock` and `api-entrypoint.sh` were byte-identical. That candidate API
reached readiness and catalogue successfully, then the old active API also
passed on the migrated clone. The temporary derived image was removed.

The ordinary release API/web images were **not** built or retained. The target
PWA image build is likewise not verified. Resolve the registry gate through an
approved Docker Hub mirror/registry credential or make the pinned base images
available locally, then build both target images and repeat the package/image
identity checks. Until that passes, the source package is staged but the
deployment artifact set is not fully ready to launch.

## Rollback and release procedure

The database upgrade script is fail-closed and requires the exact current SHA,
explicit target SHA, authenticated backup basename, and both literal human
attestations. It does DDL only and never deploys/restarts application services.
It accepts only the expected contiguous checksum prefix and resumes only at a
verified boundary. Do not use the 0017-only upgrade script for this release.

After the image-build blocker is cleared, repeat the source/package and image
checks. Before any rollout, the owner must separately authorize the exact
migration set 0018–0021 and app SHA `d5d9847373b20087a8a866449c6550d306f45b63`.
The guarded migration invocation, if separately approved, is:

```bash
bash /opt/rahgard-staging/releases/d5d9847373b20087a8a866449c6550d306f45b63/deploy/staging/upgrade-018-021.sh \
  5e2664fb51e18f52549aa37a8b5793e12ace09b2 \
  d5d9847373b20087a8a866449c6550d306f45b63 \
  rahgard-20261117T075028Z-Tbh9jK.dump.enc \
  OFFHOST_AND_ISOLATED_RESTORE_VERIFIED OWNER_APPROVED_APPLY_018_021
```

Then, only after reviewing the migration ledger and data counts, the app
deployment requires a separate explicit owner GO and the tested target images.
`deploy.sh <target-sha>` swaps only the application release and updates API/web;
the PostgreSQL named volume remains mounted and is not removed. Expect a brief
API/PWA restart; exact downtime is not measured. If health fails, `deploy.sh`
restores the previous application symlink/services and retains the migrated
database. The `rollback.sh <previous-sha> schema-compatible` command is an
application-only path and never reverses the database.

Post-release smoke checks must verify: container and immutable image identities;
internal readiness; HTTPS homepage; invitation login and `/auth/me`; private
partner access isolation; published-catalogue reads (expected empty unless a
separate content approval exists); and a traveler trip save/reopen. Do not use
test fixtures as production publication evidence.

## Commands and evidence

Final preparation branch HEAD is recorded by Git; the deployable source target
is the immutable `d5d984…` package above. Verified final commands included:

- `bash -n` for `preflight-018-021.sh`, `rehearse-018-021.sh`, and
  `upgrade-018-021.sh`: exit 0.
- `git diff --check`: exit 0.
- Read-only preflight against live DB: exit 0; ledger 16/20, four pending.
- Final restore/migration/API/rollback rehearsal: exit 0.
- Public homepage `curl`: exit 0, HTTP 200.
- Public catalogue request: HTTP 200, count 0.
- Standard Dockerfile base resolution: failed, HTTP 403 as described above.

Detailed sanitized evidence and machine-readable digests are in
[`evidence/vps-preparation-2026-11-17.md`](evidence/vps-preparation-2026-11-17.md)
and [`evidence/vps-preparation-2026-11-17.json`](evidence/vps-preparation-2026-11-17.json).

## Explicit owner decision gate

No deploy, live migration, content publication, app restart, or public change
was performed. Before proceeding, the owner must (1) clear the pinned-image
registry access/build blocker and (2) separately provide explicit approval for
the exact SHA, migrations 0018–0021, short expected restart, and the backup
proof above. Public content publication remains a distinct approval. Until
then, retain the current live release and database unchanged.
