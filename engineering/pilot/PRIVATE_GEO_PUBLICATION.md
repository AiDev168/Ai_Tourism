# Private pilot geographic publication

This is an operator-controlled private-pilot workflow. It is **not** a grant
of approval for any destination. The existing QA packet and isolated fixtures
are test-only. A record becomes visible only after a named owner decision,
an exact signed decision packet, a separately provisioned target authorization,
and the explicit `--apply-approved-geo` command.

## Required private target

Use a separately provisioned private PostgreSQL 17 pilot database with TLS
`verify-full`, a trusted CA, one operator-generated marker row, and a DNS name
or address that resolves only to the approved private network. The application
role must remain read-only for catalogue content. Never use port 55433, a
shared development database, or a database containing QA fixtures. Migration
013 checks the database name, PG version, marker, migration 0012 hash, and
nonprivileged roles. The deployment operator must independently check the
actual host/port before connecting; `inet_server_port()` inside PostgreSQL sees
the server's internal port, not a host-side NAT port.

## Separate roles

Provision credentials through the approved secret manager, never in this file
or shell history. Use separate non-superuser identities:

- `rahgard_pilot_geo_executor`: `NOLOGIN`; only function-required reads of the
  marker, canonical destination/source rows and the new authorization/audit
  tables, plus column-scoped `UPDATE(status, updated_at)` on destinations and
  `INSERT` on the new audit table. The migration operator temporarily needs
  membership and `CREATE` on `operations` to transfer function ownership; the
  database owner must revoke that temporary `CREATE` and membership before
  application use.
- `rahgard_pilot_geo_authorizer`: login role with `USAGE` on `operations`,
  `knowledge`, `public`, and `system`, read-only access to the migration
  ledger and canonical destination/source/marker data, and `INSERT`
  only on `operations.private_pilot_geo_authorizations`. It must not own that
  table, read/write approvals or shared audit, mutate destinations, or be a
  member of the publisher/executor roles.
- `rahgard_pilot_geo_publisher`: login role with `USAGE` on the required
  `operations`, `knowledge`, `public`, and `system` schemas, read-only access
  to migration metadata and `EXECUTE` on the six-argument approval function only. It must
  not own or directly write destination, authorization, or audit tables and
  must not access the shared audit table.
- `ai_tourism_app`: read-only production catalogue access, with no membership
  in any operator role.

The database owner is responsible for provisioning and verifying these
properties. Migration 013 does not create login roles or passwords.

## Commands after owner approval

The offline signer binds the exact decision file bytes and target identity.
The owner-controlled HMAC key is supplied only to the process environment.
The authorization command and publisher each repeat target, marker, source,
identity, role, and migration checks over TLS:

```powershell
uv run python backend/scripts/rahgard_sign_pilot_geo_authorization.py `
  --decisions <reviewed-decisions.json> --host <approved-private-host> `
  --port <approved-port> --database <rahgard_pilot_name> `
  --output <private-authorization.json> --owner-authorizes-target

uv run python backend/scripts/rahgard_private_geo_authorize.py `
  --decisions <reviewed-decisions.json> --target-authorization <private-authorization.json> `
  --provision-owner-authorization

uv run python backend/scripts/rahgard_private_geo_publication.py `
  --decisions <reviewed-decisions.json> --target-authorization <private-authorization.json> `
  --apply-approved-geo
```

The authorization rows expire after 30 minutes and are append-only/one-use.
If a command reports `BLOCKED`, investigate with the database owner; do not
grant broad privileges or bypass checks. Migration 013 is an optional private
pilot migration, not part of the public/shared migration runner. Validate its
SHA-256 in the controlled migration process and record it in the private
target's migration ledger.

## Current execution status

The migration's PostgreSQL 17 role-boundary test passed against a task-created,
loopback-only disposable container and test database. It proved QA-only
activation, audit creation, production-view visibility, no direct publisher
writes, and idempotent retry. The authorizer command has offline guard tests,
but has not been exercised against a persistent pilot database. No actual
destination has owner approval or has been published by this work package.
