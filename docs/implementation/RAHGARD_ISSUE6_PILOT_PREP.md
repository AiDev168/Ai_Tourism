# Rahgard Issue #6 — Pilot preparation status

This file is preparation, not deployment approval. It records a side-effect-free readiness gate and the exact external items still needed before an owner-authorized pilot.

## Implemented readiness helper

`backend/app/core/pilot_readiness.py` provides two pure checks:

- `evaluate_pilot_readiness(...)` requires approved HTTPS origin/region/TLS, managed secrets, isolated private database and tested backup restore, approved production SMS/auth recovery/admin security, private HTTPS owner-RAG topology, at least one approved content record, authorized/consented bounded remote Chat, and physical-device acceptance.
- `evaluate_single_chat_smoke(...)` checks the prerequisites for exactly one isolated staging call, including server-side credential presence, owner authorization, traveler processing consent, approved budget and a bounded output limit.

The checks return stable blocker codes. They do not access environment files, validate or reveal secrets, contact providers, connect to a database, provision infrastructure, or enable any runtime capability. A green unit fixture demonstrates the validator logic only; it is not deployment or live-provider evidence.

## Current blockers and required owner inputs

1. Choose and approve pilot host/domain, hosting region, network topology, TLS termination/trusted proxy and outbound destinations.
2. Supply an approved production SMS provider/contract and credentials through a managed secret store; authorize the bounded test. No real SMS adapter is currently approved by this task.
3. Approve authentication recovery, administrator MFA/bootstrap, privacy/retention and incident ownership.
4. Approve managed secret storage, least-privilege database provisioning, backup retention policy, restore target and rollback owner.
5. Approve owner-RAG private HTTPS service topology and endpoint; the existing loopback URL is development-only.
6. Approve source-backed content and publication decisions, remote Chat provider/data-processing terms, traveler consent copy, a fixed call budget and server-side credential provisioning.
7. Provide a real HTTPS origin, physical Android/iOS device and test SIM/account for installation, update, offline/reconnect, RTL and authenticated save/reopen acceptance.

## Safe validation

From `backend/` (where `backend/.env` is absent), run:

```powershell
$env:DATABASE_PASSWORD = 'test-only-not-a-secret'
uv run pytest -p no:cacheprovider tests/test_pilot_readiness.py -q
```

The test inputs are inert `example.invalid` values. They do not make network calls. Do not populate production configuration based on the test fixture.

No environment/deployment files, application configuration, migration, shared database, service, cloud resource, SMS, or live provider was changed or invoked by this preparation.
