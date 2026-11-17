# Rahgard local persistent private pilot (Windows 11)

This package defines an owner-operated, loopback-only private runtime. It uses one new PostgreSQL 17 container with an NTFS bind-mounted data directory; it does **not** use the disposable Issue 6 database runner, a named Docker volume, `tmpfs`, or `--rm`. Nothing here connects to the shared development database. The database name is `rahgard_pilot_local`, the container name is derived from the selected data-root hash, and PostgreSQL is published only to `127.0.0.1:55439`.

The owner-operated local pilot has been initialized and exercised on this Windows 11 machine. The observed database is PostgreSQL 17 with 15 migrations and four approved Fars geographic identities; the localhost HTTPS certificate is trusted by the current Windows user. A DPAPI-protected backup was created and verified, and a restore rehearsal passed into a separate candidate database without changing the active database. The owner login has **not** yet been bootstrapped, so an authenticated traveler journey and recovery after an actual Windows reboot remain unverified. Run the commands below only on the owner's Windows 11 machine after reviewing the data root and ensuring the required image/tools are already installed. The scripts never pull/build an image.

## Requirements and storage

- Windows 11 PowerShell, Docker Desktop already running, repository `.venv`, `uv`, `npm`, Node, and the already-present `ai-tourism-postgres:17-postgis36-vector087` image.
- `backend/.env` must be absent. The runner checks presence only and never reads dotenv content.
- Default persistent root: `$env:LOCALAPPDATA\Rahgard\Issue6Pilot`. A custom root must be a local drive path outside the repository, with no reparse/junction component and no comma. Root, database, secrets, logs and backups receive protected NTFS DACLs with only the current operator and SYSTEM.
- Database files are under `postgres-data\`; a Docker restart policy of `unless-stopped` allows PostgreSQL to return after a machine reboot. The API/PWA start when the operator runs `Start` after sign-in; this package does not install a Windows service or scheduled task.
- DPAPI secrets and DPAPI-encrypted backup archives are bound to the Windows user profile that created them. A different Windows account or PC cannot decrypt them. Retain a separate owner-controlled recovery strategy before treating this as durable business storage.

## First start

From the repository root:

```powershell
& .\engineering\pilot\local-persistent\Rahgard-LocalPilot.ps1 Start `
  -InitializeDatabase -ConfirmPrivatePilot -PublishApprovedGeo
```

This is the explicit operation that creates the local persistent database and applies the exact bundled four-POI owner-approved geographic packet through the target-bound signer/authorizer/publisher. It does not add sources or publish anything else. Coordinates are approximate representative/map points; they are not verified visitor entrances. Opening hours, access modes and road travel times remain unknown. RAG and Chat are disabled; no SMS or paid provider is called.

After successful `Start`, create the sole local password owner interactively:

```powershell
& .\engineering\pilot\local-persistent\Rahgard-LocalPilot.ps1 BootstrapOwner -ConfirmPrivatePilot
```

The password is read twice with `getpass`, never placed on a command line or written to a file; the DB stores only the application verifier. The separate bootstrap DB-role password is DPAPI-protected and is exposed only to this foreground CLI invocation. To recover a forgotten password and revoke sessions, use `ResetOwner -ConfirmPrivatePilot`.

The HTTPS server certificate is self-signed and generated for `localhost`. Trust is a separate, explicit current-user operation:

```powershell
& .\engineering\pilot\local-persistent\Rahgard-LocalPilot.ps1 TrustCertificate -ConfirmPrivatePilot
```

This imports only the recorded public localhost certificate into the current user's Root store. It does not create a public certificate authority. Remove that exact thumbprint with `UntrustCertificate` when the pilot is retired. Then open `https://localhost:8443`.

## Operations

```powershell
& .\engineering\pilot\local-persistent\Rahgard-LocalPilot.ps1 Status
& .\engineering\pilot\local-persistent\Rahgard-LocalPilot.ps1 Stop
& .\engineering\pilot\local-persistent\Rahgard-LocalPilot.ps1 Start -ConfirmPrivatePilot
& .\engineering\pilot\local-persistent\Rahgard-LocalPilot.ps1 Backup -ConfirmPrivatePilot
```

`Stop` stops only processes whose PID/start time/command line (and proxy loopback listener) match the protected state, then cleanly stops only the exact labelled container. It retains the PostgreSQL bind directory. `Status` reads only the exact state/container and checks loopback listeners and readiness. `Start` refuses an untracked container, image mismatch, altered bind mount, unexpected port, failed marker/migration ledger, certificate drift, or source checksum drift. `-WhatIf` applies to every mutating action.

Backups use the least-privilege read-only `ai_tourism_backup` role. On Windows, `persistent_backup.py` verifies the PostgreSQL custom archive and then encrypts it with the current user's DPAPI into the ACL-protected `backups\` directory. The output includes a SHA-256. Keep the archive and its Windows profile safe; DPAPI does not provide cross-account recovery.

Restore is intentionally a **rehearsal**, not a cutover. After `Backup`, use the exact reported file path:

```powershell
& .\engineering\pilot\local-persistent\Rahgard-LocalPilot.ps1 Restore `
  -Archive 'C:\Users\<you>\AppData\Local\Rahgard\Issue6Pilot\backups\<exact-archive>' `
  -ConfirmRestoreRehearsal
```

It creates a uniquely named, isolated `rahgard_restore_<id>` candidate database, preinstalls the exact required extensions using the operator role, then grants the non-superuser restore role permissions on `tiger` and `topology` only within that candidate. It verifies the marker and empty-target contract before restoring. Its filtered archive list excludes only the preinstalled extension DDL, the extension-owned `tiger`/`topology` schema declarations, and PostGIS `spatial_ref_sys` seed data; that reference table is supplied by the version-checked PostGIS extension. Unknown extension entries fail closed. It verifies the archive hash and restored table/migration contract and records the result. It never overwrites or switches the active database. Failed rehearsal candidates are preserved for inspection; never retry into them or remove them as a shortcut. `Rollback` fails closed because there is no reviewed reversible migration or safe active-database cutover contract. A restore candidate requires a separately reviewed owner-operated cutover procedure; do not point the application at it manually.

`Upgrade -ConfirmPrivatePilot` updates the app/PWA bundle only after checking the migration ledger and recorded SQL checksums. Migration 0015 has a separate opt-in step described below. No automatic down-migration is attempted.

## AI provider administration (Migration 0015)

This feature is disabled unless Migration 0015 has been explicitly applied and the local runner starts the app with `AI_PROVIDER_ADMIN_ENABLED=true`. The upgrade first builds the PWA and creates a fresh verified DPAPI backup. Apply the additive migration only to the exact local pilot target:

```powershell
& .\engineering\pilot\local-persistent\Rahgard-LocalPilot.ps1 Upgrade `
  -ConfirmPrivatePilot -ApplyProviderAdminMigration `
  -ConfirmProviderAdminTarget 'rahgard_pilot_local@127.0.0.1:55439'
```

The runner verifies the current 15-migration state and exact Migration 0014 checksum, applies 0015 through the marked loopback PostgreSQL path with a no-login migrator role, revokes temporary DDL/FK grants in `finally`, verifies the resulting checksum, and then restarts only the recorded local API/HTTPS processes. The application is never pointed at a disposable or shared database. If the database is not at the exact recorded 15-migration checkpoint, the command stops.

Grant the separate provider-admin capability to the already existing local owner only after reviewing the target UUID and reason. No account or password is created or modified:

```powershell
& .\engineering\pilot\local-persistent\Rahgard-LocalPilot.ps1 ProvisionProviderAdmin `
  -ConfirmPrivatePilot -ConfirmProviderAdminTarget 'rahgard_pilot_local@127.0.0.1:55439' `
  -ProviderAdminUserId '<existing-local-owner-uuid>' `
  -ProviderAdminReason 'Approved local provider administration'
```

Revoke this capability and invalidate its provider-admin MFA material with `-Action RevokeProviderAdmin` and the same explicit target, user ID, and non-secret reason. Provisioning and revocation use the private local operator connection and are audited. Traveler OTP or local-owner authentication by itself does not grant this capability.

After the operator grant, open `https://localhost:8443/admin/ai-providers`, sign in as the local owner, enroll an authenticator, and confirm the one-time recovery codes. Sensitive mutations require fresh session-bound TOTP step-up; one-time recovery codes provide bounded recovery. Provider API keys are stored as DPAPI CurrentUser ciphertext in the ACL-protected `secrets\ai-provider-vault` folder; PostgreSQL stores only opaque references. Do not copy that vault to another Windows account or machine.

The provider control plane stores independent Chat, Vision, Embedding and Reranking bindings and per-capability fallback policies. A provider is selectable for a capability only when discovery reports that capability as supported; unknown/unsupported bindings cannot be newly activated. Discovery is a non-generative model-catalog request and is reported separately from inference. A successful connection/discovery check is not evidence that a model can perform inference. The administrator must explicitly run the fixed, bounded inference check (maximum 64 output tokens) for each capability/model before activation or fallback selection is accepted. The inference probe does not send traveler text. The existing TourismRagApiV1 HTTP service remains an independent retrieval boundary; configuring an Embedding or Reranking binding does not silently route, replace or reconfigure RAG.

LM Studio is restricted to an explicit numeric loopback address and is not automatically installed or loaded with models. GapGPT is Chat-only until its official account endpoint/capability contract is verified; its endpoint is not guessed by the UI. The currently configured API URL is a candidate contract, not live-verified proof. Route selection is read from the database on the next provider request, without a FastAPI restart. Fallback is disabled by default and is independent per capability.

No provider API key is included in this repository. Do not run a paid/live GapGPT inference until the owner supplies approved credentials and explicitly authorizes the bounded test. A local LM Studio inference requires its server and a model already loaded by the owner. Automated tests use offline mocked transports and prove adapter behavior only; they are not live-provider evidence. As of the last local verification, LM Studio was not listening on its configured loopback port and no GapGPT account credentials or live-test authorization were available.

## Review and recovery boundaries

- `pilot-state.json` is protected and binds the root hash, exact container and image identity, bind mount, marker, migration checksums/count, geo-packet checksum, TLS certificate thumbprint/checksum, app/config and PWA build checksums, process identities and restore candidates.
- Initialization interruption is preserved as `lifecycle=initializing`; the runner does not delete or overwrite partial data. Stop/status remain available. Recovery must inspect exact state, logs and the labelled container before a separately reviewed repair. Never use `docker rm -v`, `docker volume prune`, database reset, or a replacement data root to bypass a guard.
- The legacy immutable 0004 migration refers to the development database name. The runner verifies the source file hash, substitutes that one exact database-name token in memory to grant the local app role on `rahgard_pilot_local`, and records the original file checksum. It never creates or connects to a database named `ai_tourism_dev`.
- The persistent service, migrations, local map publication, HTTPS proxy and PWA have been exercised locally. These checks do not prove owner login, authenticated browser save/reopen, recovery after an actual Windows reboot, successful database restore, or physical-device behavior. Do not infer those gates from service readiness.
- Private owner login is local-only. There is no SMS/OTP, cloud endpoint, live LLM, owner RAG, or public network listener. The API, HTTPS proxy and PostgreSQL bind to loopback only.

## Static validation

From the repository root, run:

```powershell
& .\engineering\pilot\local-persistent\Test-LocalPilotStatic.ps1
```

This parses the scripts, validates allowed/forbidden data-root calculations, and checks key fail-closed source invariants. It does not contact Docker, create a data directory, initialize a certificate, or connect to PostgreSQL.
