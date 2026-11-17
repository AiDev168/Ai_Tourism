# Rahgard private Ubuntu staging

This package is an isolated, invitation-only staging deployment. It uses a new
named PostgreSQL volume (`rahgard_staging_pgdata`), an application-only DB role,
private Compose networking, and a static PWA reverse proxy. The API, database,
and model ports are not published by Compose. The web container binds only to
127.0.0.1 on the VPS. Existing Nginx sites, LiteLLM, vLLM, databases, and
volumes are not changed by these scripts.

## Current access gate

The owner-selected browser hostname is `rahgard.hinaa.ir`. The dedicated
origin listener uses TLS on port 63202; Arvan must use HTTPS to that origin,
and NAT must map its origin port to local 63202. Port 80 is not used. The
current public homepage was independently checked over HTTPS and returned
HTTP 200 on 2026-11-15. This does not prove authenticated traveler acceptance.

Before installing the Rahgard vhost, obtain and install a trusted certificate
for `rahgard.hinaa.ir` using DNS-01 (the hostname resolves through Arvan, so
HTTP-01 is unavailable). The operator helper refuses installation without a
valid certificate whose SAN and key match the hostname. It adds one new vhost
file, tests it, reloads Nginx, and verifies local origin TLS; existing vhosts
are not replaced or modified.

## First install

All commands below run on the Ubuntu host as the dedicated operator. Keep
`/opt/rahgard-staging/.env`, `/opt/rahgard-staging/secrets`, state, backups,
and release files owner-only. Do not paste values from those files into tickets
or logs.

1. `prepare-host.sh` creates the isolated directories and random runtime
   secrets. It does not change Nginx, start containers, or initialize a DB.
2. `RAHGARD_PUBLIC_HOST` in `.env` must be `rahgard.hinaa.ir`.
   Keep `RAHGARD_SECRET_DIR` and `RAHGARD_STATE_DIR` at their configured paths.
   Review whether the existing vLLM instance is reachable from Docker through
   `host.docker.internal:8000`; no other model endpoint is allowed by staging
   settings. The configured model name must match the already loaded model.
3. Export the exact tested source commit on the Windows development machine:

   ```powershell
   git archive --format=tar <tested-commit-sha> | gzip -n > rahgard-<tested-commit-sha>.tar.gz
   Get-FileHash -Algorithm SHA256 rahgard-<tested-commit-sha>.tar.gz
   ```

   Transfer that archive and its hash through the approved authenticated SSH
   channel. Do not transfer `.venv`, virtual environments, `.env`, or secrets.
4. Run `fetch-release.sh <tested-commit-sha> <archive-path> <archive-sha256>`.
   This validates the archive digest and path names before extraction, then
   makes non-secret source files readable to container users while preserving
   executable script modes. Do not put secrets in a release archive.
5. From the extracted release's `deploy/staging` directory, start only its
   dedicated DB service:

   ```bash
   docker compose --env-file /opt/rahgard-staging/.env -f compose.yaml up -d --build db
   ```

   On a host without registry access, load the separately checksummed image
   bundle first (`gzip -dc rahgard-images.tar.gz | docker load`), then omit
   `--build` from the command above.

   Wait for its health check, then run `initialize-db.sh` exactly once. It
   refuses an existing/partial ledger, checks database name and PostgreSQL 17,
   creates an isolated marker, applies the baseline plus private migrations
   0013 through 0016 (omitting owner-only admin/publication migrations), checks
   every checksum, removes temporary grants, and verifies the production
   destination view is empty. It does not publish the
   research/geo packet. If interrupted, do not reset or recreate the volume.
   The guarded initializer resumes only when its protected claim matches and
   the ledger is the exact checksum-verified prefix 0000–0006; other partial
   states stop for manual review.
6. By default, `deploy.sh <tested-commit-sha>` builds from the exported source,
   starts the API/PWA, and checks the loopback web response. It preserves the
   database volume and rolls the application symlink back on a failed health
   check. On a host without registry access, first load a checksummed image
   bundle containing `rahgard-api:<sha>`, `rahgard-web:<sha>`, and
   `rahgard-postgres:17-postgis36-vector087`, then set
   `RAHGARD_BUILD_IMAGES=false` in the private host config. The script checks
   all exact image tags before starting. Once the trusted origin certificate and Arvan HTTPS-origin/NAT route
   are confirmed, run `install-nginx-vhost.sh` and verify
   `https://rahgard.hinaa.ir` from outside.
7. Create a short-lived traveler invitation with
   `/opt/rahgard-staging/current/deploy/staging/invite-traveler.sh`.
   It is single-use and printed once. Deliver it only over the owner's chosen
   private channel. Do not create local-owner or provider-admin identities in
   this Internet staging deployment. Phone OTP explicitly reports unavailable
   because no SMS provider is configured; the application never fabricates a
   code.

## Operations

- `status.sh` reports container state and migration count; it prints no secret.
- `stop.sh` stops services without deleting the persistent volume.
- `deploy.sh <sha>` updates application code from a previously verified release;
  it never runs migrations or initializes the DB.
- `rollback.sh <old-sha> schema-compatible` rolls back application code only.
  The operator must verify old-code compatibility with the present migration
  ledger before confirming. It does not revert the database.
- `backup.sh` makes a custom-format `pg_dump`, encrypts it with AES-256-CBC and
  PBKDF2 using `backup_encryption_passphrase`, and creates an HMAC-SHA-256
  encrypt-then-MAC sidecar using the independent
  `portable_bundle_hmac_key`. It also writes a SHA-256 transfer-check sidecar;
  SHA alone is not authenticity evidence. Keep both keys outside the backup
  and independently protected. `restore.sh` authenticates HMAC before
  decryption. Historical backups without `.hmac` remain on disk but this
  guarded restore refuses them.
- `restore.sh <encrypted-backup> rahgard_pilot_vps_staging` verifies/decrypts
  and checks the dump, makes a fresh encrypted pre-restore backup, stops only
  this deployment's web/API containers, and restores only to the exact staging
  DB. Rehearse only against an isolated disposable copy before a real recovery.

The automatic DB initialization is only for an initial empty staging volume.
It must never be rerun against an existing database. The original verified
ledger has 15 rows: baseline 0000 through 0012, private geo boundary 0013,
and staging invitation auth 0016. Migration 0017 adds owner-scoped provisional
itineraries; it does not publish catalogue records or modify existing trips.

For an existing pilot, use the separate one-time `upgrade-017.sh` from the
exact reviewed release. It refuses anything except the exact checksum-verified
15-row ledger, the original persistent PostgreSQL 17 volume, and the protected
pilot marker. Before DDL it creates a new encrypted database backup, verifies
the SHA-256 and independent HMAC, decrypts into a mode-0600 temporary file, and
checks the archive with `pg_restore --list`. It then applies only migration
0017 and verifies a 16-row ledger, migration checksum, new table, and unchanged
counts for users, conversations/messages, trips, canonical itineraries/stops,
and published destinations. It never initializes, restores, recreates or
deletes the database volume. If any precondition fails, stop and preserve the
database and backup for review; do not retry initialization.

Operator sequence for a reviewed release:

1. Transfer and validate the release archive with `fetch-release.sh`.
2. Run the new release's `deploy/staging/upgrade-017.sh` while the currently
   deployed application is still serving. The runner uses the persistent DB
   container and verifies a fresh authenticated backup before applying DDL.
3. If the migration reports PASS, run `deploy.sh <tested-commit-sha>` to
   activate the application release. Application deployment remains separate
   from schema migration and preserves the named PostgreSQL volume.
4. Verify status, readiness, the HTTPS homepage, and owner-scoped traveler
   behavior. Roll back application code only if needed; migration 0017 is
   additive and existing application rows are unchanged.

### Preparing the national catalogue migrations (0018–0021)

`upgrade-017.sh` is **not** valid for the national catalogue. Use
`preflight-018-021.sh` to read-only verify the current managed release, marker,
PostgreSQL 17 image and persistent volume, and compare the entire migration
ledger against source checksums. It accepts only an exact, contiguous migration
prefix from the 0017 baseline through 0021, and checks that schema objects agree
with the recorded ledger. It does not modify the database or services.

`rehearse-018-021.sh <encrypted-backup-basename>` authenticates and decrypts a
routine database backup only into a mode-0700 `/run` temporary directory. It
restores into a uniquely named PostgreSQL 17 container using `--network none`,
no published ports or persistent mounts, and a `tmpfs` PGDATA. It verifies the
restored 0017 ledger and privacy-safe critical row counts, applies migrations
0018–0021 only to that disposable copy, and confirms all retained counts are
unchanged, the new candidate/partner/publication data stays empty, and the
container is removed. No production service is stopped or restarted.

`upgrade-018-021.sh` is the future, separately approved live-schema command.
It refuses to run without the expected current SHA, the explicitly approved
target release SHA, a named authenticated backup, an off-host-and-isolated-
restore attestation, and the explicit `OWNER_APPROVED_APPLY_018_021` argument.
It rechecks the exact migration prefix,
database marker, PostgreSQL image/volume and backup HMAC/SHA/decryptability
before each migration. It applies DDL only; it does not deploy or restart the
API/PWA. The owner must separately authorize application deployment after the
schema upgrade and smoke checks. Do not provide the approval arguments until
the separate release decision is made.

## Release synchronization and server portability

For a machine-readable release snapshot, use
`scripts/Verify-RahgardRelease.ps1 -VpsSshTarget <operator@host> -ManifestPath <private-report-path>`.
It records local/GitHub/VPS source SHAs, Compose digest, running image IDs and
the exact migration ledger. This is not a restore/data-equivalence proof.

The portable export is a write-frozen cutover snapshot. Stop writes, create
`/opt/rahgard-staging/state/WRITE_FREEZE`, stop only this Compose project's
`api` and `web`, then run:
`bash deploy/staging/export-portable.sh --cutover-frozen`.
The encrypted archive uses an independent HMAC key; `.sha256` alone is not
authenticity evidence. Keep encryption and HMAC keys off-bundle and transfer
them separately. Inspect with the passphrase file, HMAC-key file, and a new
destination path, then use the guarded `restore-portable.sh` only with a fresh
PostgreSQL 17 `tmpfs` container and bootstrap role `ai_tourism_owner`. The
restore compares the exact migration ledger and privacy-safe counts for users,
conversations/messages, trips/itineraries/stops, and published destinations.
Follow it with `restore-portable-app-check.sh` to build and start the archived
API release against the restored isolated database, verify readiness and
catalogue count, then clean only its own containers, image and secret volume.
These commands do not exercise interactive authentication or change the live
stack; see the portable migration runbook for complete acceptance.

See `docs/operations/RAHGARD_RELEASE_SYNC_AND_PORTABLE_MIGRATION.md`.
Do not run database initialization on existing volumes or allow simultaneous
writes to old and new servers.

## Important boundaries

### Owner-authorized live SMS.ir OTP (staging only)

Live delivery is disabled by default. It can be enabled only with
`APP_ENV=staging`, invitation staging auth enabled, the exact public HTTPS
origin, a non-sandbox `RAHGARD_SMS_PRODUCTION_TEMPLATE_ID`, and the
`sms_ir_live_staging` adapter. The API key is never stored in the deployment
`.env`; it is mounted read-only from
`/opt/rahgard-staging/secrets/sms_ir_production_api_key` and is read only when
the live adapter is selected. Keep the SMS.ir Verify template parameter name
`Code`, as expected by the existing OTP integration. The hard-coded Sandbox
template `123456` is rejected by live mode.

To provision the credential, send exactly one key line to
`provision-sms-secret.sh` through an encrypted, non-echoing SSH channel using
stdin. Do not put the value in a command, terminal history, environment file,
image, log, or repository. The script refuses to replace an existing nonempty
key, installs it with group GID `999` and mode `0640` inside the owner-only
secret directory, and prints no credential. Keep `RAHGARD_SMS_ADAPTER=disabled`
until the owner-supplied production template ID is configured and public HTTPS
to the dedicated TLS origin is verified. Limit the first real delivery test to
the owner's opted-in phone and at most three messages; invitation login remains
available as the staging fallback.

- No production/shared DB, Windows pilot database, public HTTP, admin routes,
  local-owner login, OTP debug route, SMS, paid model endpoint, RAG API, or
  unapproved destination publication is included.
- The ordinary production destination view remains empty unless a separately
  approved publication action is performed. A successful health check or empty
  catalogue is not evidence of a real destination recommendation.
- This staging deployment is not a public launch. Physical Android install,
  reconnect, and traveler-flow acceptance still require the owner's device.
- Compose uses Docker secret file mounts from a `0700` host directory. Secret
  files are `0640` with group 999 for the non-root container service accounts;
  the host directory prevents other host users from traversing them. The DB and
  API have no `ports:` mapping. `staging_private` is an internal network.
