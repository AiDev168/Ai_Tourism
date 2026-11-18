# Rahgard hosted images — isolated release rehearsal (2026-11-18)

## Decision

**READY FOR OWNER PRODUCTION APPROVAL.** This is approval readiness only. No live deployment, live migration, application restart, persistent database write, or catalogue publication was performed or authorized.

Prepared source: `d5d9847373b20087a8a866449c6550d306f45b63`.
Active VPS release remained `5e2664fb51e18f52549aa37a8b5793e12ace09b2`.
Successful GitHub Actions run `44228225648`, artifact `14393716721`.

## Artifact verification

| Evidence | Result |
|---|---|
| Artifact ZIP | 292,687,935 bytes; SHA-256 `956d3dd173e97f3d9f28cc530d18e434132d08eafac83e10db820ad8b10dd614` |
| Inner image archive | 292,683,264 bytes; SHA-256 `7977f63c5594f0586730984440ba8fbac181b9c0716094ba59f5e9171a44603b` |
| Release manifest | SHA-256 `d98566dd9526e0ed01d8e1218a6f9a07567a562f22c21418c1215ec9c72cbce7` |
| API handoff config ID | `sha256:5973182df93899773a67ccc2f6429942560403a1120a2ba9ebe9c430dc6accdd` |
| Web handoff config ID | `sha256:23632593de6b81908b247f2b76fe70b719d12c1db4e3081d1f89022cab921bea` |
| Platform / revision | `linux/amd64`; both labels identify the exact d5 source SHA |
| Base RepoDigests | Python `b685a4fa…`; Node `9bef0ef1…`; Nginx `65645c7b…` (full values retained in the verified manifest) |
| Secret scan | Passed; no secret files, credentials, or secret-named runtime environment variables in the image archive |

The bundle and inner checksums were verified on Windows and again on the VPS. The source SHA in the manifest, image labels, and successful build run all match d5. The source archive itself is not included in the image artifact, so its manifest-recorded archive digest was not independently re-hashed during this handoff.

The VPS runs Docker Engine 29.7.2 with its containerd image store. Its `docker image inspect .Id` values differ from classic-store config IDs even though exporting each exact loaded tag reproduces the handoff config SHA and all rootfs DiffIDs. The corrected verifier now requires that exported-config and layer equivalence when this known ID representation difference occurs; it also checks the loaded image platform, complete config, labels, entrypoint, command, rootfs DiffIDs, and hashes each layer tar against its declared DiffID. The VPS’s observed image IDs were API `sha256:88d060821b6d2bce3be3426b8012c76a411d68682939d9ca22f2947d861a2674` and Web `sha256:14d97ad5616921231912ef4dd9e698140202d4017a1d07c3e9228163dfbc14d1`.

This behavior is documented by Docker for its containerd image store and by the Docker CLI project ([Docker containerd image store](https://docs.docker.com/engine/storage/containerd/), [Docker CLI issue #6670](https://github.com/docker/cli/issues/6670)).

## Backup restore and migration rehearsal

The existing encrypted backup `rahgard-20261117T075028Z-Tbh9jK.dump.enc` was verified in place. SHA-256 matched `a464e750fd7902d82eed56b94d420449d70c9d12a4f31161907b6e1b79ef7e2f`; the backup HMAC, decryption, `pg_restore --list`, and restore into an isolated PostgreSQL 17.11 instance all passed.

The rehearsal used tmpfs-only PGDATA and a labelled Docker `--internal` bridge with no external route, published ports, bind mounts, or persistent mounts. It restored the backup copy, then applied only in that copy:

| Migration | Result | SHA-256 |
|---|---|---|
| `0018_national_catalogue_ingestion` | PASS | `f5fc0cb3e3fcf61b36a5d21f9c98c3d75e04581cb19d4e22ad1754d53480dd36` |
| `0019_partner_workspace` | PASS | `8f7c745e128faf0d9d91bf808159367a7a2636ac31b4544147619a9af751dd56` |
| `0020_archive_candidate_publication` | PASS | `b6822a3401cef3f7ac8c85ce0577eb71d0373bc34bf4ec2d8c65b0a812f13326` |
| `0021_postgis_security_definer_publication` | PASS | `bc0b6abb335549ddff91a811aeeca30bc5ba75d3e3f5f3fe81f7ded4b3bee650` |

The restored migration ledger advanced from 16 rows (through 0017) to 20. All tracked data counts remained unchanged. The post-migration copy had 27/27 protected tables with RLS, 67 policies, and the application role remained non-superuser and non-`BYPASSRLS`. No candidates, partner rows, or publication events were added.

The exact hosted API image became ready against the migrated copy; its catalogue count was 0, matching the restored publication view. The exact Web image served the application shell, both hashed assets, and the catalogue reverse-proxy request. The previous API image `rahgard-api:5e2664fb51e18f52549aa37a8b5793e12ace09b2` also became ready against the migrated copy and returned the same catalogue count, supporting application-only rollback without reversing database migrations.

The initial rehearsal attempts exposed and fixed three test-runner issues before the passing run: Docker 29 image-ID representation, incompatible `--network container` plus `--add-host` options, and Nginx's restricted startup capabilities. The final test uses the isolated internal bridge, retains read-only container filesystems, and grants only `CHOWN`, `SETUID`, and `SETGID` to the temporary Web container. All labelled test containers, network, and decrypted dump were removed by the cleanup trap; the encrypted backup remains retained.

## npm audit impact

The exact d5 `frontend/package-lock.json` reports five high-severity affected package entries and zero critical entries. The entries are all `dev: true`:

| Package | Locked version | Dependency path |
|---|---:|---|
| `picomatch` | 4.0.7 | affected package; GHSA-fc5q-39xc-vjpf |
| `fdir` | 6.5.0 | depends on affected `picomatch` |
| `tinyglobby` | 0.2.17 | depends on affected `fdir` / `picomatch` |
| `vite` | 6.4.5 | direct development dependency; affected transitively |
| `vitest` | 4.1.12 | direct development dependency; affected transitively |

The underlying advisory is [GHSA-fc5q-39xc-vjpf](https://github.com/advisories/GHSA-fc5q-39xc-vjpf), a high-severity ReDoS in `picomatch` for vulnerable repeated extglobs. `npm audit --omit=dev --package-lock-only` returned exit code 0 with zero production findings. The Web Dockerfile installs these packages only in its Node build stage and copies only `dist/` into the final Nginx image; Vite, Vitest, and `node_modules` are not present in the served runtime image. Therefore the finding is a development/build-input risk, not an exposed dependency path in the deployed Web image. Do not silently update d5's lockfile; review and patch the development dependency chain in a separate release.

## Live VPS unchanged check

After the rehearsal, read-only verification found:

- Release marker unchanged: `5e2664fb51e18f52549aa37a8b5793e12ace09b2`.
- API remained on image `sha256:8017e31258b13adc0dcbd9e96e3bb8e40dc874394c4dfb75e391513fc449a3b3`; Web on `sha256:b22b15ebd05cdd2bb2e595cdde22b16a2976953cc8e284ede0fe6d729cc4bb3a`; PostgreSQL on `sha256:a30c041297b2306a8bb79cc6ed737f16bfca3078a3024324bb8115b302e83535`. All three containers remained running and healthy.
- Persistent database volume remained `rahgard_staging_pgdata`.
- Migration ledger remained at 16, through `0017_provisional_itineraries`.
- Aggregate counts remained: users 12; sessions 19; conversations/messages 6/33; trips 6; canonical itineraries/stops 1/6; provisional itineraries 2; destinations 66; destination-source links/sources 116/58; documents/chunks 52/81; published view 0.
- No isolated rehearsal containers or networks remained.
- No live migration, deployment, service restart, configuration change, or publication occurred.

## Commands and validation

Focused local checks:

- `uv run pytest -p no:cacheprovider tests/unit/test_rahgard_release_image_bundle.py -q` — **9 passed**.
- `uv run ruff check scripts/ops/verify_rahgard_release_image_bundle.py tests/unit/test_rahgard_release_image_bundle.py` — **passed**.
- `git diff --check` — **passed**.
- `bash -n` for the final rehearsal script on the VPS — **passed**.
- `python scripts/ops/verify_rahgard_release_image_bundle.py verify ...` — **passed** locally and on the VPS.
- `scripts/ops/verify_and_rehearse_rahgard_image_bundle.sh /opt/rahgard-staging/incoming/rahgard-release-images-d5d9847-linux-amd64 rahgard-20261117T075028Z-Tbh9jK.dump.enc` — **exit 0**, `HOSTED_IMAGE_REHEARSAL_PASS`.
- `npm audit --package-lock-only --json` on the exact d5 package metadata — exit 1 due the five high entries; `npm audit --omit=dev --package-lock-only --json` — **exit 0**, zero production findings.

## Owner approval gate

**The release is ready for owner production approval; production rollout is still not authorized.** The owner must separately approve the exact application SHA `d5d9847373b20087a8a866449c6550d306f45b63`, migrations 0018–0021, a maintenance/restart window, and the verified backup/rollback plan before any live deployment. Published content remains a separate approval.
