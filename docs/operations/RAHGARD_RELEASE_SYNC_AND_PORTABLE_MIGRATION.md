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
   ./scripts/Verify-RahgardRelease.ps1 -VpsSshTarget operator@your-host
   ```

   A code SHA match **does not prove** data or model equivalence.
6. Only mark a release accepted when the **same SHA** has passed the local,
   GitHub and VPS gates. If the rollout fails, rollback app code only with
   `rollback.sh` and verify schema compatibility. Do not roll back the
   database by default.

## Moving to a new server without losing traveler data

To create one encrypted migration bundle, on the **source** Ubuntu host run
`bash /opt/rahgard-staging/current/deploy/staging/export-portable.sh`.
It exports a consistent PostgreSQL dump, exact release directory, private host
environment, secrets and initialization state. Copy **both** `.tar.enc` and
`.sha256` files off-host; store the encryption passphrase independently.
Before cutover, on the isolated destination host run
`bash inspect-portable.sh <bundle.tar.enc> <passphrase-file> <unused-private-directory>`
to verify the archive, every bundled file checksum and the dump. This
inspection **never restores** or overwrites a live database. The executable
mode of newly created repository scripts is not assumed: invoke with `bash`.

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

This repository change adds the read-only three-way checker, encrypted
portable export/isolated inspection helpers, and this migration procedure.
It does not introduce an unattended destination restore because overwriting
a live database or key directory automatically would be unsafe. It does not have interactive access to the user's
Windows PC or VPS, cannot create a backup on those machines, and cannot
claim a zero-data-loss migration until the procedure has been rehearsed.
Browser GPS only returns coordinates; time zone currently comes from the
device/explicit selector, not a geographic time-zone polygon lookup. A
locality name requires a separate vetted reverse-geocoding provider.
