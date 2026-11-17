# Issue 6: isolated local pilot stack

This is a **loopback-only engineering deployment exercise**, not a public or owner-authorized pilot. It reuses the existing guarded disposable PostgreSQL runner and serves the Vite production build through a short-lived self-signed HTTPS origin. API, Chat, owner RAG, and authentication stay disabled. The real SMS provider, content publication, external provider calls, and shared database are not used.

## Start and verify

From the repository root in PowerShell:

```powershell
.\engineering\pilot\Start-Issue6-LocalPilot.ps1
```

The script builds the PWA, runs `engineering/database-prep/scripts/Start-Disposable-Mvp-E2E.ps1` (fresh PostgreSQL 17/PostGIS/pgvector, tmpfs, generated owner/app roles, loopback-only dynamic DB port, migrations 0000–0012, explicit safety marker), starts FastAPI and a minimal local HTTPS static/API proxy, and verifies both `/health/ready` and the HTTPS-proxied readiness path. It prints a state-file path outside the repository under the current user's temporary directory. The generated certificate, process logs and state stay in the task-specific temporary folder. The state has no credentials.

The local TLS certificate is self-signed, valid for `localhost`, and is not a production certificate or trusted CA. Browser/manual inspection can use `https://localhost:8443/` (or the configured port) with the expected local certificate warning. The proxy binds only to `127.0.0.1`; it serves the built app and forwards `/api/*` and `/health/*` only to FastAPI on loopback. It does not log request bodies or query text. API responses keep the backend's `no-store` headers.

Optional database backup/restore acceptance, while the stack is running:

```powershell
.\engineering\pilot\Test-Issue6-BackupRestore.ps1 -StatePath '<STATE path printed by Start-Issue6-LocalPilot.ps1>'
```

It performs `pg_dump -Fc` and restores into a new, exact-name database inside the same task-created container, verifies the 13-migration ledger and safety marker, then drops the restore database and removes the dump. No shared or pre-existing database is targeted.

Stop and remove only the recorded task resources:

```powershell
.\engineering\pilot\Stop-Issue6-LocalPilot.ps1 -StatePath '<STATE path printed by Start-Issue6-LocalPilot.ps1>'
```

Rollback is stop followed by rerunning the start command. PostgreSQL uses tmpfs, so stop removes its data. The backup/restore exercise is a disposable proof; it is not an operational backup policy.

## Pilot activation decision inputs

The owner must provide and approve all of the following before a real pilot configuration is created:

| Decision/input | Current local exercise | Required before pilot |
|---|---|---|
| Hostname, hosting region, TLS termination and trusted-proxy chain | `localhost`, self-signed certificate | Owner-selected HTTPS host/region and deployable certificate chain |
| Database | Random guarded PG17 tmpfs instance; app connects as `ai_tourism_app`; migration 0012 applied | Separately provisioned private database, restore-tested backup/retention and cutover approval |
| Authentication/SMS | Disabled | Approved SMS provider, managed credentials, auth recovery, admin MFA/bootstrap and explicit bounded live test authorization |
| Chat | Disabled | Provider/data-processing approval, traveler consent copy, model/profile, managed credential, fixed one-call budget, explicit authorization |
| Owner RAG | Disabled; local adapter remains available | Approved private HTTPS topology and secret delivery; never expose its token to PWA |
| Content | Existing review queue only; no publication | Per-claim owner/editor decisions, source terms/attribution, locale review, and controlled publication/index snapshot |
| Operations | Process health and disposable restore check | Monitoring/redaction, on-call owner, incident/rollback procedure and production restore rehearsal |
| Device | Not exercised by this script | Owner-supplied phone/SIM and real HTTPS PWA install/update/save/reopen test |

Do not set production `AUTH_ENABLED`, `INTERNAL_CHAT_ENABLED`, or `TOURISM_RAG_ENABLED` based on this local run. Current settings intentionally reject the owner loopback HTTP RAG endpoint outside `development`/`test`; pilot RAG requires a private HTTPS endpoint and a separately reviewed configuration change. No public deployment or deployment secrets are supplied here.
