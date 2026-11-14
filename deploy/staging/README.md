# Rahgard private Ubuntu staging

This package is an isolated, invitation-only staging deployment. It uses a new
named PostgreSQL volume (`rahgard_staging_pgdata`), an application-only DB role,
private Compose networking, and a static PWA reverse proxy. The API, database,
and model ports are not published by Compose. The web container binds only to
127.0.0.1 on the VPS. Existing Nginx sites, LiteLLM, vLLM, databases, and
volumes are not changed by these scripts.

## Current access gate

The owner-selected browser hostname is `rahgard.hinaa.ir`. The Arvan edge
currently presents HTTPS but returns 502 because its origin route is not ready.
The existing Nginx listener on port 63201 serves unrelated sites over HTTP and
is directly Internet-reachable; Rahgard must never use that plaintext hop.
Rahgard's origin listener is isolated on TLS port 63202, with a valid
certificate for the exact host. Arvan must use HTTPS to the origin, and NAT
must map its origin port to local 63202. Port 80 is not used.

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
  PBKDF2 using a host-only passphrase, then writes a SHA-256 sidecar. Copy both
  files off-host through an approved protected channel. Keep the passphrase
  independently backed up; losing it makes backups unrecoverable.
- `restore.sh <encrypted-backup> rahgard_pilot_vps_staging` verifies/decrypts
  and checks the dump, makes a fresh encrypted pre-restore backup, stops only
  this deployment's web/API containers, and restores only to the exact staging
  DB. Rehearse only against an isolated disposable copy before a real recovery.

The current automatic DB initialization is for the initial empty staging
volume only. Its verified ledger contains 15 rows: baseline 0000 through 0012, private
geo boundary 0013, and staging invitation auth 0016. It does not install local
owner or provider-admin schemas. The new migration 0016 adds invitation auth; no subsequent schema
upgrade runner is included because no later migration is authorized. Future
migrations require a reviewed, separately guarded upgrade procedure and backup.

## Important boundaries

- No production/shared DB, Windows pilot database, public HTTP, admin routes,
  local-owner login, OTP debug route, SMS, paid model endpoint, RAG API, or
  unapproved destination publication is included.
- The ordinary production destination view remains empty unless a separately
  approved publication action is performed. A successful health check or empty
  catalogue is not evidence of a real destination recommendation.
- This staging deployment is not a public launch. Physical Android install,
  reconnect, and traveler-flow acceptance still require the owner's device.
- Compose uses Docker secrets sourced from protected host files. The DB and API
  have no `ports:` mapping. `staging_private` is an internal network.
