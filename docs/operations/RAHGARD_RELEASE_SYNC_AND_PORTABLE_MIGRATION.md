# Rahgard: synchronized releases and lossless VPS migration

**Policy from this change forward:** every completed release has one immutable
Git commit SHA shared by (1) the clean local Windows checkout, (2) the pushed
GitHub branch/ref, and (3) the running VPS deployment. The repository is the
source of truth for application code. The VPS database and private runtime
configuration are *not* copies of GitHub and must never be overwritten merely
to equalize code commits.

## Release gate (Windows -> GitHub -> Ubuntu VPS)

1. Verify which production/staging branch and SHA are running on the VPS:
   `ssh <operator@host> 'cat /opt/rahgard-staging/current/RELEASE_COMMIT'`.
   Do not assume `main` is currently deployed. Create a change branch from
   that SHA, keep it in GitHub, and review the diff.
2. On Windows, fetch and check out the reviewed commit. Run the frontend tests
   and build, and the focused backend tests. Confirm `git status --porcelain`
   is empty and `git rev-parse HEAD` equals the SHA pushed to GitHub.
   Do not force-push the active release branch.
3. Before an upgrade, take `deploy/staging/backup.sh` on the VPS. Confirm
   backup and sidecar checksums, copy encrypted backup **off the VPS**, and
   rehearse restore against a **separate disposable database/server**.
   Record the migration ledger and owner data counts before any action.
4. Export the tested exact Git commit from Windows using the
   `git archive`/SHA-256 procedure in `deploy/staging/README.md`. Transfer
   through SSH, then use `fetch-release.sh` and `deploy.sh` with the
   **same exact 40-character SHA**. Never run `docker compose down -v`,
   `docker volume rm`, `initialize-db.sh` on existing data, or an
   unreviewed schema migration.
5. Verify the HTTPS application, authentication, Persian/English/Arabic
   conversation, date fields, and trip save/reopen. Recheck DB row counts and
   migration ledger. On Windows run:

   ```powershell
   ./scripts/Verify-RahgardRelease.ps1 -VpsSshTarget operator@your-host -ManifestPath .\artifacts\release.json
   ```

   A code SHA match **does not prove** data or model equivalence.
6. Only mark a release accepted when the **same SHA** has passed the local,
   GitHub and VPS gates. If the rollout fails, rollback app code only with
   `rollback.sh` and verify schema compatibility. Do not roll back the
   database by default.

## Moving to a new server without losing traveler data

The portable export is a cutover snapshot and refuses to run unless the
operator has stopped traveler writes, created the protected
`/opt/rahgard-staging/state/WRITE_FREEZE` marker, and stopped this Compose
project's `api` and `web` services. Stop only the Rahgard services using the
exact current Compose file; leave PostgreSQL running for `pg_dump`. Do not
remove the marker or reopen writes until the target is accepted or the source
has been safely resumed.

Create an independent random HMAC key once through a protected operator
channel on the source host; do not commit or bundle it:

```bash
umask 077
openssl rand 32 > /opt/rahgard-staging/secrets/portable_bundle_hmac_key
chmod 0600 /opt/rahgard-staging/secrets/portable_bundle_hmac_key
```

The existing `backup_encryption_passphrase` is used for AES-256-CBC encryption.
The separate `portable_bundle_hmac_key` authenticates ciphertext with
HMAC-SHA-256 (encrypt-then-MAC), checked before decryption. The SHA-256
sidecar detects transfer corruption only and is **not** authenticity evidence.
Transfer the archive, `.hmac`, and `.sha256` together; transfer both keys
separately through approved protected channels. Neither key is in the bundle.
Only the Compose runtime secret allowlist is packaged; the DB backup key, HMAC
key, TLS keys and unrelated secrets are excluded. The bundle still contains
active application/API credentials; handle it as highly sensitive data.

Stop the application services with the exact current Compose project (do not
stop PostgreSQL), drain connections, create the freeze marker, and export:

```bash
compose=(docker compose --env-file /opt/rahgard-staging/.env -f /opt/rahgard-staging/current/deploy/staging/compose.yaml)
"${compose[@]}" stop api web
touch /opt/rahgard-staging/state/WRITE_FREEZE
bash /opt/rahgard-staging/current/deploy/staging/export-portable.sh --cutover-frozen
```

The export checks the marker and confirms both app services are stopped, takes
a transactionally consistent PostgreSQL dump using the Compose bootstrap role
`ai_tourism_owner`, records exact migration IDs/checksums and a privacy-safe
allowlist of critical table/view row counts, and packages them with private
runtime files and the exact release. It also refuses if any other database
session remains. This is
not a background snapshot while writes continue; routine `backup.sh` remains
database-only.

On the isolated destination, authenticate and safely inspect to a new directory:

```bash
bash deploy/staging/inspect-portable.sh \
  <bundle.tar.enc> <passphrase-file> <independent-hmac-key-file> <new-private-directory>
```

Inspection checks the external HMAC before decryption, rejects links, special
files, duplicate/noncanonical paths and unexpected members, extracts only
regular files into a private temporary directory, verifies the internal
manifest, and moves completed output to a nonexistent destination. It does
not connect to PostgreSQL or restore data.

For a disposable restore rehearsal, create a fresh PostgreSQL 17 container
with no published ports, a `tmpfs` data directory, no persistent/bind mounts,
and Docker labels `rahgard.restore.target=isolated` and
`rahgard.environment=restore-test`. The guarded helper requires a new
`rahgard_restore_*` database name and exact confirmation, and refuses an
existing database or a target that fails its isolation checks:

```bash
bash deploy/staging/restore-portable.sh \
  <bundle.tar.enc> <passphrase-file> <independent-hmac-key-file> \
  <verified-extraction-dir> <isolated-postgres-container> \
  rahgard_restore_rehearsal ai_tourism_owner rahgard_restore_rehearsal
```

It repeats HMAC authentication and inspection, compares the provided
extraction with the fresh result, provisions only the required restored
runtime roles, restores with `pg_restore --no-owner` in one transaction, and
compares restored migration IDs/checksums/count and the allowlisted critical
row counts with the frozen source. It never drops a database or targets the
live Compose project. After that command succeeds, build/start the archived
API against the same isolated tmpfs database and verify readiness plus the
approved catalogue endpoint:

```bash
bash deploy/staging/restore-portable-app-check.sh \
  <verified-extraction-dir> <isolated-postgres-container> rahgard_restore_rehearsal
```

The app check builds from the exact archived release, shares only the isolated
container network namespace, publishes no ports, mounts secrets read-only,
and deletes its test API container/secret volume/image on exit. It checks
`/health/ready` and compares the API catalogue count to the restored view.
This check does not prove interactive login or full browser itinerary editing;
those remain separate acceptance evidence.

The existing `backup.sh` backs up **PostgreSQL only**. It does *not* package
application secrets, `.env`, source/image releases, Nginx/TLS configuration,
the external vLLM model, DNS/Arvan, or a separately hosted RAG index. Calling
that single file a complete portable VPS backup would be incorrect.

For migration, keep a protected **migration set** containing:

- Encrypted PostgreSQL `pg_dump -Fc` and verified checksum, plus its external
  encryption passphrase stored separately; verify ability to decrypt and list
  the dump *before* shutting down the old server.
- The private `/opt/rahgard-staging/.env` and
  `/opt/rahgard-staging/secrets/` (transport and store encrypted; never commit
  them to GitHub, messages, or logs); preserve secret consistency so existing
  sessions and password hashes remain valid where applicable.
- `/opt/rahgard-staging/state/` markers, the exact deployed source commit
  and built container image tags/checksums. Build or load the identical image
  versions on the replacement server.
- An inventory of migrations, all persistent Docker volumes and **any** future
  uploaded user files/object storage outside PostgreSQL; back up external
  stores independently. The staging Compose currently defines
  `rahgard_staging_pgdata` for DB persistence.
- Host dependencies requiring reprovisioning: HTTPS origin certificate/private
  key, Nginx config and port mapping, DNS/Arvan HTTPS origin, Docker/Compose,
  VPS firewall, vLLM endpoint/model/cache and any future private RAG service.
  Re-issue the certificate rather than transferring its private key when
  possible, and verify the same host name/allowed origin.

Restore on a **new isolated host** first. Recreate private secrets and
permissions, provision the runtime environment, verify the DB name and
migration ledger, restore with `restore.sh` only against the intended
staging DB, and test login plus complete trip history and saved itineraries.
Run both old and new hosts behind **one write target only** during cutover:
freeze writes on the old site, make a final incremental/fresh full backup,
restore it to the new site, compare counts and checksums, then switch DNS/edge.
Never permit concurrent independent writes into the two PostgreSQL instances.

**Acceptance evidence:** identical release SHA, exact migration ledger,
representative trip/conversation/itinerary records, login, saved/reopened trip,
no volume reset, encrypted backup verified off-host, restore rehearsal, and
external HTTPS successful. Keep the old server read-only until validation
and rollback criteria are satisfied.

## Open limitations

The checker emits a machine-readable JSON release snapshot containing local,
GitHub and VPS SHAs; ahead/behind state; local/VPS Compose digest; running
API/web/PostgreSQL image references and immutable image IDs; and the exact
database migration ledger/count. It fails if release SHAs or Compose digests
differ. It does not prove DB row equivalence, successful backup restore,
provider availability or traveler acceptance. Keep manifests private if
internal image/migration details matter.

These helpers do not create backups on the owner's machines or prove a
zero-data-loss migration. The restore helper accepts only a new non-production
PostgreSQL 17 `tmpfs` container and new database name; it cannot restore over
a live service. The owner/operator must execute and record a complete
isolated restore plus application acceptance before cutover.
Browser GPS only returns coordinates; time zone currently comes from the
device/explicit selector, not a geographic time-zone polygon lookup. A
locality name requires a separate vetted reverse-geocoding provider.
