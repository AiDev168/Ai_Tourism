# Issue #24 recovered-file reconciliation

Updated 2026-11-23 on `feat/rahgard-unified-travel-v2`; current branch HEAD at the
time of this update is `7cbcb851d925357d1a58a46e1ca8981c1379b95e`.

The original recovery copy remains intact at
`%LOCALAPPDATA%\Rahgard-Untracked-Recovery-940c8c4e38c9438ca3a1c751389330e7`.
Its manifest hashes were checked against the seven checkout files before edits.
The screenshot is deliberately not tracked: its pixels contain a traveler draft
request and account/workspace state. Its original and checkout SHA-256 are
`13976bdbc9efe9dcf4d2a199a9ca3b7a93703f8a7339f7ebfbbc8b0b7a40f688`.

| Recovered path | Recovery SHA-256 | Current checkout SHA-256 | Disposition |
|---|---|---|---|
| `docs/operations/evidence/issue24/live-v2-mobile-390.png` | `13976bdbc9efe9dcf4d2a199a9ca3b7a93703f8a7339f7ebfbbc8b0b7a40f688` | `13976bdbc9efe9dcf4d2a199a9ca3b7a93703f8a7339f7ebfbbc8b0b7a40f688` | Retained owner-private; not staged or published. No redacted derivative created. |
| `frontend/scripts/issue24-live-apex-acceptance.mjs` | `82a2950b35629279220869f0d279b158e4865c0fe5d43791670ee983178d5ec8` | `6232fc11bb3d4f02e1d667e0508e6b63b58ddda2b6cb6c5cbe777243653a3845` | Reworked with consent gates, non-PII API diagnostics, Unicode request coverage, private-only screenshots and persistence checks; corrected budget-shape and documented HTTP 201 recommendation contract. The scenario has not passed on the live site. |
| `frontend/scripts/issue24-public-intake-diagnostic.mjs` | `e478e94e9a6f49963c7d12b4a9af261843847e172f1e27e1354bc5400c09f6b8` | `a6218af5290db9a565230dee4876d9d6b2e174653bef3aba143401ce1a7595d5` | Converted to a strictly read-only public UI/asset diagnostic; it never fills or submits the form. |
| `frontend/scripts/issue24-requirements-shape-check.mjs` | `bc6421055213d42d7a07c1f367bd1da34a559ac86f961b7a720e8cee62f7b4ab` | `468be1cf62a1bb050934638bff90a2b04341aff079bb2217333d361ba22bfca0` | Bounded stdin and removed exception detail that could echo traveler input. |
| `scripts/ops/execute_rahgard_v2_live_migrations.py` | `e35cf9524f3ea701feaeaab18aa43d5701d1c0f89bf487a00900f53120473aa3` | `f7c03be31f15f6207fd293bb44db5355f89e0ea4825f93113b1c2866dca1b28a` | Replaced DDL executor with a pinned, read-only ledger/runtime verifier; reports `ALREADY_APPLIED_NO_DDL` only for the exact 22-row 0022/0023 state. |
| `scripts/ops/freeze_rahgard_v2_live.sh` | `08fb676983000673ebb5ba1c04af4c757347bf6e32c5ad6b2789e3313b7cd719` | `b51de55c6032d0df9b695a75c96c6e62e586184da4e04f0b75943d5250bf79e2` | Reworked for exact apex SNI/Host and V2 listener; default is read-only plan. Freeze distinguishes maintenance, stopped writers, drained DB work, and saved/restored config. Never run against the VPS during this task. |
| `scripts/ops/prepare_rahgard_v2_live_env.sh` | `4fa0e869f27f2fe02d7382aef6c58f8d41426c6af83acf1e91685d25f6da96c4` | `32072b2451145a3e56fe7b9a8508a257f007da14f119b0893b339619c4c16092` | Added repeat-safe verify-only behavior for existing `.env.v2`; first creation is exclusive 0600; no secret values are printed. |

## Added isolated regression harnesses

- `scripts/ops/tests/test_rahgard_v2_readonly_migration_audit.py`: 7 tests, including 0023 already applied/no DDL, exact live ledger attestation, immutable image mismatch, volume mismatch, owner mismatch, and configuration permissions.
- `scripts/ops/tests/test_freeze_rahgard_v2_live.sh`: real Bash process rehearsal over a temporary Nginx config and disposable command shims; covers apex freeze/restore, repeat operation, legacy-only rejection, unexpected writer, SHA/volume/image mismatch, interrupted state and failed-health restoration.
- `scripts/ops/tests/test_prepare_rahgard_v2_live_env.sh`: temporary env/config fixture verifies 0600 creation, secret redaction, repeat verification without rewrite, and mismatch rejection.

## Observed live state (read-only)

- PostgreSQL 17 database `rahgard_pilot_vps_staging`, owner/current role `ai_tourism_owner`, persistent volume `rahgard_staging_pgdata`.
- Migration ledger: 22 rows; exact 0022 SHA-256 `e6b7db49abc0ff76c2620b2cc8d5dded0f4255f8533efd20bd5b402a0ba57eda`; exact 0023 SHA-256 `deef8c5016f26aa646b9ff22346fad4ade3c6780ff447f701aa9e8a8e28571ac`; full captured ledger SHA-256 `515809c472a735018f939d8777a0a864188d13c0e870db32d0af6aef0e12782a`.
- Exactly one Rahgard API container was in `docker ps`, paired with one Web container; both healthy and tagged `36625ecf269c2a3d5590528257d32af2b6f47dd0`. Their inspected image IDs were `sha256:2c814062db391b3b484b8c45b622329e9f8519a1bf0cc1627828744b23ab497e` (API) and `sha256:44fb963eea6b5fa0dbd2a876036906c15581eec8677e34f3111781229eabd375` (Web).
- The V2 runtime config has exact apex host, release SHA, port `18081`, volume, signup, and no-build values; file mode was 0600. Legacy `current/RELEASE_COMMIT` remains `5e2664fb51e18f52549aa37a8b5793e12ace09b2`; this legacy symlink is not used as the active V2 image identity.
- The apex Nginx TLS vhost is `hinaa.ir` on 63202, exact SNI/Host guarded, proxying to `127.0.0.1:18081`.
- External read-only probes: `https://hinaa.ir/` returned 200 and Chromium loaded current hashed CSS/JS without page errors or horizontal overflow. `https://www.hinaa.ir/` and `https://rahgard.hinaa.ir/` currently returned 503 with `Retry-After: 120`. No live Nginx or database changes were performed.

`shellcheck` is not installed. Static shell parsing and the full isolated shell rehearsals ran under the already-installed WSL Ubuntu Bash.

All seven entries were rechecked against the private recovery manifest. The six
reviewed source files are tracked in the V2 branch; the original screenshot
remains the only untracked artifact and is intentionally private. The detailed
acceptance and release boundary is recorded in
`2026-11-23-closeout.md`.
