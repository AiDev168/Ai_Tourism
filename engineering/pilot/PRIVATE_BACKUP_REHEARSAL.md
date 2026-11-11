# Private pilot backup and restore rehearsal

These commands are **prepared, not pilot-verified**. They currently fail closed on Windows because native ACL verification is not implemented. They do not provision a database or schedule jobs. Use only after the owner authorizes the exact private target and storage. Never use a shared/development database. The operator must select retention, encryption, monitoring, incident ownership and a recovery target separately.

## Required preparation

- Provision a stable, private PostgreSQL 17 endpoint with a trusted certificate. `PGSSLROOTCERT` must identify the trusted CA file. Both commands force `verify-full` TLS. Use a single-server endpoint rather than a load-balanced target that may change between guard and dump/restore connections.
- Install the PostgreSQL 17 client tools `psql`, `pg_dump`, and `pg_restore` on the authorized operator's `PATH`; these scripts do not install packages.
- The persistent pilot database must be named `rahgard_pilot_<identifier>` (lowercase ASCII, digits or underscore; identifier length 3–40). Port 55433 is rejected. A pre-provisioned `public.rahgard_private_pilot_marker(marker_value TEXT NOT NULL)` table must contain exactly one operator-generated 32–128-character hexadecimal marker.
- Provision `ai_tourism_backup` as a non-superuser without CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS, elevated-role membership, or database CREATE. It needs CONNECT plus the read privileges required for `pg_dump` and the marker. Do not use the application role or an owner/superuser for backup.
- Provision a POSIX backup directory outside this repository, owned by the operator with no group/other permissions (mode 0700 or stricter). Archives use owner-only file mode. Protect archives at rest and in transit using the owner's approved key and storage controls. Listing a dump checks archive readability; it is not a restore test.
- Provide `PGPASSWORD` or `PGPASSFILE` through the approved secret mechanism and keep it out of source files, command history and logs. The scripts never read `.env`. Set `RAHGARD_PILOT_PGHOST`, `RAHGARD_PILOT_PGPORT`, `RAHGARD_PILOT_DATABASE`, `RAHGARD_PILOT_DATABASE_MARKER`, `RAHGARD_PILOT_BACKUP_DIR`, and `PGSSLROOTCERT` in the operator process.

From `backend/`, after setting those process variables:

```powershell
uv run python ..\engineering\pilot\persistent_backup.py --confirm-private-pilot
```

The command verifies database identity, marker, PG version and role before invoking `pg_dump`, checks the resulting custom archive with `pg_restore --list`, and renames its own new partial file only after that check succeeds. It does not prune previous backups or set a retention period.

## Isolated restore rehearsal

The operator must pre-create a separate **empty, disposable** database named `rahgard_restore_<12 lowercase hex characters>` and pre-provision `public.rahgard_restore_rehearsal_marker(marker_value TEXT NOT NULL)` with exactly one independently generated marker. Provision `ai_tourism_restore` without superuser, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS or elevated-role membership; grant database CREATE only on this rehearsal database and SELECT on its marker. The script rejects existing application schemas or non-extension public objects. Extensions and their permissions may require separate preparation; an extension or permission failure is a failed rehearsal.

Set process variables `RAHGARD_RESTORE_PGHOST`, `RAHGARD_RESTORE_PGPORT`, `RAHGARD_RESTORE_DATABASE`, `RAHGARD_RESTORE_MARKER`, `RAHGARD_RESTORE_ARCHIVE`, `RAHGARD_RESTORE_ARCHIVE_SHA256`, `RAHGARD_RESTORE_EXPECTED_MIGRATIONS`, `RAHGARD_RESTORE_SPOOL_DIR`, `PGSSLROOTCERT`, and `PGPASSWORD` or `PGPASSFILE`. The spool directory must meet the same POSIX owner/mode requirements and be outside the repository. Obtain the SHA-256 from the exact archive using an approved local checksum tool. Set expected migrations to the actual source ledger count; the current minimum is 13.

```powershell
uv run python ..\engineering\pilot\persistent_restore_rehearsal.py --confirm-isolated-restore
```

The command copies the archive to an exclusive unlinked private spool while hashing it. The hash check and both `pg_restore` invocations use that same open spool, so replacing the original archive path cannot change the restored bytes. It verifies target identity, role and empty target, then runs `pg_restore` in one transaction without `--clean` or `--create`. It checks the migration count and core table presence afterward. It does **not** restore ownership or ACLs, compare application row counts, validate extensions comprehensively, or delete the rehearsal database. A failed post-restore check leaves that isolated target for authorized operator inspection; do not retry on a populated target. A complete recovery rehearsal still requires approved role/ACL recreation, data checks, application startup and owner verification.

No actual persistent database, backup, restore, or deployment has been exercised by these scripts in this workstream.
