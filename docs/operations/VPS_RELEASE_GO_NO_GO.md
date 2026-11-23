> **Issue #24 update (2026-11-23): NO-GO / BLOCKED for V2.** The current legacy SHA, encrypted off-host snapshot, restored-data migration and immutable V2 image results are recorded in the [Issue #24 preparation result](RAHGARD_V2_ISSUE24_PREPARATION_RESULT_2026-11-23.md). The apex currently redirects to www. Owner routing and writer-topology decisions precede a separate activation approval.

> **V2 URL requirement (2026-11-21):** final canonical V2 URL **https://hinaa.ir/**. Domain occupancy, TLS and collision-safe cutover are an additional BLOCKED gate; historical hotfix GO/NO-GO does not authorize replacing the apex website or deploying V2. See [apex-domain runbook](RAHGARD_V2_APEX_DOMAIN_CUTOVER.md).

> **V2 DECISION (2026-11-21): PREPARATION GO / LIVE DEPLOYMENT NO-GO.** This document below is **historical Issue #21 PWA hotfix** evidence, NOT an approval for V2. The current VPS runtime has not been freshly observed in this conversation. Use [V2 readiness and three-environment release gates](RAHGARD_V2_VPS_READINESS_AND_THREE_ENV_SYNC_2026-11-21.md) and [Codex V2 preparation handoff](RAHGARD_CODEX_V2_RELEASE_PREPARATION_AND_ROLLOUT_GATE_2026-11-21.md) before any operator action. An immutable candidate, real-data isolated 0022/0023 rehearsal, off-host HMAC backup, old-code compatibility and a separately approved live maintenance window are required.

---

# Rahgard VPS release decision — 2026-11-19

## Current decision

**READY FOR OWNER LIVE-DEPLOYMENT APPROVAL — NOT DEPLOYED.** The final Issue #21 PWA hotfix candidate passed hosted image verification and a fresh, isolated PostgreSQL 17 20-to-20 restore/runtime rehearsal. No live rollout is authorized by that result.

- Qualified immutable candidate: `4a9574ae67056cac9bde1253102d93f4b798910d`
- Current live VPS application: `5e2664fb51e18f52549aa37a8b5793e12ace09b2`
- Successful hosted build: run `44481724443`, artifact `14508033297`
- Isolated rehearsal: exit 0, `HOTFIX_IMAGE_REHEARSAL_PASS`; migration count stayed 20; no DDL; row counts preserved; PWA assets, API, Web proxy and old-API compatibility passed.
- Fresh encrypted backup `rahgard-20261119T072015Z-nj8bwh.dump.enc` passed checksum, HMAC, decryption, archive readability and isolated restore verification.
- No live application/database operations, migrations, service restarts or publication were performed.

See [the complete Issue #21 acceptance evidence](RAHGARD_ISSUE21_PWA_HOTFIX_ACCEPTANCE_2026-11-19.md). The November 18 d5 deployment history and rollback evidence remain in [the historical live acceptance report](RAHGARD_LIVE_DEPLOYMENT_ACCEPTANCE_2026-11-18.md).

## Approval gate

The owner must separately authorize deployment of the exact candidate SHA and a maintenance/restart window. This hotfix requires no database migration. SMS, RAG and catalogue publication remain disabled and out of scope.
