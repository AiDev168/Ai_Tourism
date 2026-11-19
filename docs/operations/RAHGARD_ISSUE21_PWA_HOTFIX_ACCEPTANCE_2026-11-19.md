# Rahgard Issue #21 — PWA hotfix release qualification

**Decision: READY FOR OWNER LIVE-DEPLOYMENT APPROVAL.** This report qualifies an immutable candidate only. The new candidate was not deployed. The active VPS release remains `5e2664fb51e18f52549aa37a8b5793e12ace09b2`.

## Candidate identity

- Branch: `feat/rahgard-national-catalogue-execution-handoff`
- Immutable application/image source SHA: `4a9574ae67056cac9bde1253102d93f4b798910d`
- GitHub build: run [44481724443](https://github.com/AiDev168/Ai_Tourism/actions/runs/44481724443), success; artifact `14508033297` (`rahgard-release-images-4a9574ae67056cac9bde1253102d93f4b798910d-linux-amd64`).
- Artifact: 294,766,655 bytes; GitHub artifact digest and the VPS-downloaded ZIP SHA-256 both `e142eae35f32fbb1f27334b51d41c816ac7a40136e6dfe058d4fa5c8eb177b43`.
- Inner image archive: 294,761,984 bytes; SHA-256 `f4eb07d9816514dfc05282f3d2111273728a6dcd19739f21a01ecd203b74667d`.
- `release-manifest.json` SHA-256: `e119d048504eae041b39c3aafbc1634885ae355135b56173388f2ef9172499ff`.
- Manifest source archive: 219,883,520 bytes; SHA-256 `7bf793f5186b33af003de43d05e93fd69bc30ef0739fe25286bacee0be921dfc`.
- Platform: `linux/amd64`; source revision labels match the candidate SHA; secret scan passed and no runtime secrets were passed to image builds.
- Build-manifest image IDs: API `sha256:70e73fe1f573b103be81cec87f60d67298f9ec4f0ae8689baecbc93835205bed`; Web `sha256:580cb848a91b83cec771a8277cfd57de23c36004d3422a9531888f1dcc345f79`.
- VPS-loaded image IDs: API `sha256:054bc9571acaf080deab44ab4e9da31f7def30219721fd9eb42d804862d67f5f`; Web `sha256:1cf973251a7a49368e81978de5b497dbd103e27e8192de9b6f1742d4abae3cba`. The corrected verifier confirmed containerd-export equivalence for both images, including config, labels, platform, rootfs DiffIDs and layer content.
- Pinned base RepoDigests: Python `python@sha256:b685a4fa58bb19d1814d78a1ec0f0208f351452724f78b20212c984d6e124a34`; Node `node@sha256:9bef0ef1e268f60627da9ba7d7605e8831d5b56ad07487d24d1aa386336d1944`; Nginx `nginx@sha256:65645c7bb6a0661892a8b03b89d0743208a18dd2f3f17a54ef4b76fb8e2f2a10`.

The build output `SHA256SUMS.txt` was checked on the VPS; the release-image bundle verifier passed before image load and again against loaded tags. The two manifests and inner archive remained protected under `/opt/rahgard-staging/incoming`; no application runtime configuration was changed.

## Defects found and corrected during acceptance

The first final-image rehearsal found three defects in the isolated PWA probe (not in the running release):

1. A network-isolated Nginx config probe could not resolve its configured `api` upstream. The probe now provides only a local `api:127.0.0.1` hosts entry while remaining on Docker `--network none`, with no port, application secret or external network.
2. The Nginx config emitted `user  nginx;` with two spaces; the test required exactly one. The check now accepts valid whitespace.
3. The shell's inline asset-discovery Python expression had unbalanced parentheses. It now extracts hashed JS/CSS paths correctly and has a regression test using representative Vite asset names.

The resulting code was committed and pushed. Earlier intermediate image builds failed their rehearsals and are not qualified release candidates. Only SHA `4a9574ae67056cac9bde1253102d93f4b798910d` passed the complete final rehearsal.

## Backup and 20-to-20 restore rehearsal

- Fresh encrypted backup: `rahgard-20261119T072015Z-nj8bwh.dump.enc`.
- Backup SHA-256: `a061731318d38730536b7262e8ba4c9ae7596937df9050b945681a399692e6e7`; it matched the separately stored local copy under `%LOCALAPPDATA%\Rahgard\Issue21\backups`.
- The protected VPS SHA-256 sidecar, HMAC, decryption, and `pg_restore --list` checks passed in the rehearsal wrapper. The encryption/HMAC keys stayed on the VPS; no key or plaintext dump was transferred. The decrypted dump and all temporary containers/network were removed by cleanup.
- Restore source was the just-created backup of the live database already at migration 0021. The rehearsal restored it into disposable PostgreSQL 17 storage on an internal-only Docker bridge, with tmpfs PGDATA, no published ports, bind mounts or persistent volumes.
- The migration ledger stayed at 20 entries. No migration was applied. Checksums for migrations 0018–0021 matched the recorded live checksums using CRLF normalization of the checked-in LF SQL, without accepting other content changes.
- `RESTORE_20_20_PASS`: `no_ddl=true`, aggregate data counts matched the live snapshot, 27 protected RLS tables, 67 policies, app role remained non-superuser and non-BYPASSRLS, candidates/partner rows/publications all zero.
- Preserved aggregate counts: 12 users, 20 sessions, 6 conversations, 42 messages, 6 trips, 1 itinerary, 6 itinerary stops, 2 provisional itineraries, 66 destinations, 58 knowledge sources, 116 destination-source links, 52 documents and 81 chunks.

## Image and application compatibility results

The final script `scripts/ops/verify_and_rehearse_rahgard_hotfix.sh` exited **0** and emitted `HOTFIX_IMAGE_REHEARSAL_PASS`.

- `PWA_IMAGE_PASS`: Nginx ran as configured; public files were readable by the unprivileged `nginx` user; app shell, manifest, service worker and hashed JS/CSS returned HTTP 200 with expected MIME types; missing hashed asset returned 404 (no SPA fallback hiding an asset failure).
- `API_20_20_PASS`: exact candidate API image reached readiness against the restored database; production catalogue count remained 0; auth, Chat, RAG and SMS stayed disabled for this isolated check.
- `WEB_PROXY_20_20_PASS`: exact candidate Web proxy returned the same empty catalogue result over the isolated network.
- `OLD_API_20_20_PASS`: prior live API image `rahgard-api:5e2664fb51e18f52549aa37a8b5793e12ace09b2` became ready against the restored migrated schema; database rollback was not performed.
- Cleanup check: zero containers and zero networks with the `rahgard.test=schema-20-20` label remained.

Focused local validation on the final source SHA:

- `uv run pytest -p no:cacheprovider tests/unit/test_rahgard_release_image_bundle.py tests/unit/test_rahgard_web_image_gate.py -q` — **17 passed**.
- `uv run ruff check scripts/ops/verify_rahgard_release_image_bundle.py tests/unit/test_rahgard_release_image_bundle.py tests/unit/test_rahgard_web_image_gate.py` — passed.
- `bash -n` for `verify_and_rehearse_rahgard_hotfix.sh`, `test_rahgard_web_image_pwa.sh` and `rehearse-20-20.sh` — passed.
- `git diff --check` — passed.

## Dependency assessment

`frontend/package-lock.json` is unchanged from the previously audited d5 release. The existing five high-severity audit entries remain development/build dependency findings in the `picomatch` chain; the prior `npm audit --omit=dev --package-lock-only` returned zero production findings. The final Nginx image contains compiled static assets, not Node/Vite/Vitest or `node_modules`. No dependency versions were changed for this hotfix. The hosted action reported a non-blocking Node 20 deprecation warning for pinned checkout/upload actions; it did not fail the build.

## Live state and authorization boundary

After rehearsal, read-only checks confirmed:

- Live release marker remains `5e2664fb51e18f52549aa37a8b5793e12ace09b2`.
- API, Web and PostgreSQL are still running and healthy. API image ID `sha256:8017e31258b13adc0dcbd9e96e3bb8e40dc874394c4dfb75e391513fc449a3b3`; Web `sha256:b22b15ebd05cdd2bb2e595cdde22b16a2976953cc8e284ede0fe6d729cc4bb3a`; PostgreSQL `sha256:a30c041297b2306a8bb79cc6ed737f16bfca3078a3024324bb8115b302e83535`.
- Live DB still has 20 migrations through `0021_postgis_security_definer_publication`; aggregate counts above are unchanged from the fresh backup/restore comparison.
- No live migration, deploy, restart, database mutation, publication, SMS or RAG activation occurred. The public application continues on the prior release.

This candidate is ready for a separate owner decision to deploy the application-only SHA `4a9574ae67056cac9bde1253102d93f4b798910d`. Such approval must explicitly authorize the maintenance window and rollout. Do not run `deploy.sh` before that approval. No production migration is required for this hotfix.
