# Private pilot backup and restore rehearsal

These commands are **prepared, not persistent-pilot-verified**. They do not provision a database or schedule jobs. Use only after the owner authorizes the exact private target and storage. Never use a shared/development database. The operator must select retention, encryption, monitoring, incident ownership and a recovery target separately.

## Required preparation

- Provision a stable, private PostgreSQL 17 endpoint with a trusted certificate. `PGSSLROOTCERT` must identify the trusted CA file. Both commands force `verify-full` TLS. Use a single-server endpoint rather than a load-balanced target that may change between guard and dump/restore connections.
- Install the PostgreSQL 17 client tools `psql`, `pg_dump`, and `pg_restore` on the authorized operator's `PATH`; these scripts do not install packages.
- The persistent pilot database must be named `rahgard_pilot_<identifier>` (lowercase ASCII, digits or underscore; identifier length 3–40). Port 55433 is rejected. A pre-provisioned `public.rahgard_private_pilot_marker(marker_value TEXT NOT NULL)` table must contain exactly one operator-generated 32–128-character hexadecimal marker.
- Provision `ai_tourism_backup` as a non-superuser without CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS, elevated-role membership, or database CREATE. It needs CONNECT plus the read privileges required for `pg_dump` and the marker. Do not use the application role or an owner/superuser for backup.
- Provision a POSIX backup directory outside this repository, owned by the operator with no group/other permissions (mode 0700 or stricter). Archives use owner-only file mode. Protect archives at rest and in transit using the owner's approved key and storage controls. Listing a dump checks archive readability; it is not a restore test.
- Provide `PGPASSWORD` or `PGPASSFILE` through the approved secret mechanism and keep it out of source files, command history and logs. The scripts never read `.env`. Set `RAHGARD_PILOT_PGHOST`, `RAHGARD_PILOT_PGPORT`, `RAHGARD_PILOT_DATABASE`, `RAHGARD_PILOT_DATABASE_MARKER`, `RAHGARD_PILOT_BACKUP_DIR`, and `PGSSLROOTCERT` in the operator process.

### Windows 11 NTFS preparation

Use a **new, empty directory outside the Git checkout** for backups and another
new, empty directory for restore spooling. The following example creates only
the named user-local backup directory and restricts its ACL to the current
Windows user and LocalSystem. Do not run it against a directory containing
existing user files. If `icacls` reports errors, stop and investigate; do not
disable the program's ACL checks.

```powershell
$BackupDir = Join-Path $env:LOCALAPPDATA 'Rahgard\PrivateBackup'
New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
$OwnerSid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
icacls.exe $BackupDir /inheritance:r /grant:r "*${OwnerSid}:(OI)(CI)F" '*S-1-5-18:(OI)(CI)F'
```

Create and secure the restore spool directory the same way at a distinct
path. Before writing a dump, the Python commands inspect each path component
for reparse points and query NTFS ownership, DACL protection, ACE type, SID,
inheritance flags, and complete access masks via Windows PowerShell/.NET.
Only explicit owner and LocalSystem Full Control ACEs are accepted. Backup
files and restore spool files receive a protected owner/LocalSystem ACL and
are checked before use; a failed ACL check blocks the operation. Windows
restore spooling uses an ACL-protected named temporary file and removes it
after closing it, since Windows cannot safely unlink an open file as POSIX
can. This does not itself encrypt archives; storage encryption and key
management must be approved and configured by the operator.

From `backend/`, after setting those process variables:

```powershell
uv run python ..\engineering\pilot\persistent_backup.py --confirm-private-pilot
```

The command verifies database identity, marker, PG version and role before invoking `pg_dump` and checks the custom archive with `pg_restore --list`. On Windows `pg_dump` streams directly into bounded Windows DPAPI `CurrentUser`-encrypted frames; no plaintext dump staging file is written. The encrypted partial is ACL-protected and renamed to `.dump.dpapi` only after DPAPI decrypt/hash verification and a `pg_restore --list` check fed through an OS pipe. An interrupted run can leave only encrypted partial bytes. The envelope records format, protection scope, plaintext byte count, frame count, and creation time, not credentials or key material. Only the same Windows user/profile can restore it. POSIX behavior remains a `.dump` protected by the private directory/file-system ACL. The command does not prune previous backups or set a retention period.

## Isolated restore rehearsal

For the standalone script, the operator must pre-create a separate **empty, disposable** database named `rahgard_restore_<12 lowercase hex characters>` and pre-provision `public.rahgard_restore_rehearsal_marker(marker_value TEXT NOT NULL)` with exactly one independently generated marker. Provision `ai_tourism_restore` without superuser, CREATEDB, CREATEROLE, REPLICATION, BYPASSRLS or elevated-role membership; grant database CREATE only on this rehearsal database and SELECT on its marker. The script rejects existing application schemas or non-extension public objects. The Windows local-pilot wrapper creates a fresh candidate and marker, then preinstalls only PostGIS 3.6 and pgvector 0.8.7 as the operator before invoking the restore script. The restore guard rejects missing/wrong extension versions, extra extensions, and non-extension objects; the restore role is never elevated.

Set process variables `RAHGARD_RESTORE_PGHOST`, `RAHGARD_RESTORE_PGPORT`, `RAHGARD_RESTORE_DATABASE`, `RAHGARD_RESTORE_MARKER`, `RAHGARD_RESTORE_ARCHIVE`, `RAHGARD_RESTORE_ARCHIVE_SHA256`, `RAHGARD_RESTORE_EXPECTED_MIGRATIONS`, `RAHGARD_RESTORE_SPOOL_DIR`, `PGSSLROOTCERT`, and `PGPASSWORD` or `PGPASSFILE`. The spool directory must meet the same POSIX owner/mode requirements and be outside the repository. Obtain the SHA-256 from the exact archive using an approved local checksum tool. Set expected migrations to the actual source ledger count; the current minimum is 13.

```powershell
uv run python ..\engineering\pilot\persistent_restore_rehearsal.py --confirm-isolated-restore
```

The command copies the archive to an exclusive private spool while hashing it. On Windows, both the encrypted input spool and the DPAPI-decrypted plaintext spool have verified operator/LocalSystem-only NTFS ACLs. Decryption happens only in the private restore spool. The envelope is bound to the current Windows profile; invalid DPAPI authentication fails closed. POSIX keeps the unlinked-FD behavior. The hash check and restore use only the private spool, so replacing the original archive path cannot change restored bytes. Spool cleanup failure is a failed command and is surfaced; it is never silently reported as success. It verifies target identity, role and empty target, then runs `pg_restore` in one transaction without `--clean` or `--create`. It checks the migration count and core table presence afterward. It does **not** restore ownership or ACLs, compare application row counts, validate extensions comprehensively, or delete the rehearsal database. A failed post-restore check leaves that isolated target for authorized operator inspection; do not retry on a populated target. A complete recovery rehearsal still requires approved role/ACL recreation, data checks, application startup and owner verification.

Observed on 2026-11-11: the isolated local pilot database and DPAPI-encrypted backup were exercised successfully. The restore rehearsal passed into candidate `rahgard_restore_6a3631cc42be`, verified the recorded 15 migration count and core tables, and reported `active_database_unchanged=true`; the candidate was not activated. The wrapper creates a fresh marker-protected candidate, installs only the extensions in the source database, gives the non-superuser restore role narrowly scoped candidate permissions, and excludes only the extension DDL/schema/configuration entries supplied by the matching extension versions. Failed earlier candidate rehearsals remain preserved for inspection. Owner login bootstrap, authenticated traveler save/reopen, Windows reboot recovery, and physical-device acceptance remain unverified.
