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

`Upgrade -ConfirmPrivatePilot` updates the app/PWA bundle only after checking the migration ledger and recorded SQL checksums. New migration files are blocked until an explicit reviewed runner registration is added. No automatic down-migration is attempted.

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
