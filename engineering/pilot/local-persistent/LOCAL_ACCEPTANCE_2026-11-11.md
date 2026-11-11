# Local private pilot acceptance — 2026-11-11

## Observed environment

- Repository branch at verification: `feat/rahgard-issue6-launch-v1` (starting commit `1055ba511165e15c0ab3a863a5dfd6ce276d9c85`).
- Task-owned persistent runtime: container `rahgard-local-pg17-ed735a549bba`, database `rahgard_pilot_local`, PostgreSQL 17, bind-mounted under `%LOCALAPPDATA%\Rahgard\Issue6Pilot\postgres-data`.
- Database/API/HTTPS bind only to loopback ports 55439/8800/8443. Current-user localhost certificate trust was verified. Chat and RAG remain disabled.
- The production catalogue has four owner-approved Fars destination identities. Their coordinates are approximate map-reference points, not verified visitor entrances. Unknown hours, access and travel times remain unknown.

## Persistence, backup and recovery evidence

- The lifecycle `Stop` completed with `database_data_preserved=True`.
- A fresh `Start -ConfirmPrivatePilot` completed after a bounded readiness wait. Final `Status` reported PostgreSQL running, API ready, HTTPS listening on loopback, trusted localhost certificate, and 15 migrations.
- Read-only counts before and after the stop/start cycle were identical: `production_destinations=4`, `local_owner_credentials=0`, `travel.trips=1`.
- `curl.exe https://localhost:8443/` returned HTTP 200 (1,007 bytes); `http://127.0.0.1:8800/health/ready` returned `ready`.
- A DPAPI CurrentUser backup was created and verified at `rahgard-pilot-20261111T072449Z-a0cc9aa67c9f4a99b5db7128617ad3e5.dump.dpapi`, 316,160 bytes, SHA-256 `71a28226d0a7e2b0087a3b74b8108a0383e493f6d7e270a5474e865af0739a55`.
- Restore rehearsal succeeded into isolated candidate `rahgard_restore_6a3631cc42be`, verified 15 migrations and required core tables, and reported `active_database_unchanged=True`, `candidate_activated=False`. The rehearsal does not restore ownership/ACLs and is not an active-database cutover. All failed rehearsal candidates were preserved for inspection.
- The restore runner preinstalls and checks the source database's exact extension versions on each fresh candidate, stages the filtered TOC only inside the exact task-owned container, and keeps `ai_tourism_restore` non-superuser. Candidate-only `tiger`/`topology` grants are not part of live application roles.

## Verification commands and results

| Command | Result |
| --- | --- |
| `uv run pytest -p no:cacheprovider test_persistent_backup.py test_persistent_restore_rehearsal.py -q --basetemp ..\..\backend\.venv\pytest-pilot-final-20261111` from `engineering/pilot` | Exit 0; 34 passed |
| `$env:DATABASE_PASSWORD='test-only-not-a-secret'; uv run pytest -p no:cacheprovider tests/test_local_owner_auth.py tests/test_local_owner_auth_api.py tests/test_auth.py -q --basetemp .venv/pytest-localowner-final-20261111` from `backend` | Exit 0; 42 passed; one upstream Starlette/AnyIO deprecation warning |
| `npm exec -- vitest run src/auth/AuthPanel.test.tsx src/auth/AuthPanel.delivery.test.tsx` from `frontend` | Exit 0; 5 passed |
| Focused `uv run ruff check ...` for modified backend and backup/restore modules | Exit 0; all checks passed |
| `powershell -NoProfile -ExecutionPolicy Bypass -File engineering/pilot/local-persistent/Test-LocalPilotStatic.ps1` | Exit 0; 3 PowerShell files parsed; 5 unsafe roots rejected; no Docker/database access by this static test |
| `git diff --check` | Exit 0 |

`Upgrade -ConfirmPrivatePilot` also completed without applying a database migration and refreshed the recorded application/PWA checksums. The production frontend build completed successfully during local pilot initialization and subsequent upgrade.

## Remaining acceptance gates

- **Owner login not activated:** the database currently has zero local owner credentials. The owner must run `BootstrapOwner -ConfirmPrivatePilot` and choose their own password. No default or test password was created. Until then, authenticated browser trip save/edit/reopen was not executed.
- **Windows reboot not tested:** PostgreSQL uses a persistent NTFS bind mount and Docker restart policy `unless-stopped`; Stop/Start recovery was observed, but an actual Windows reboot and Docker Desktop auto-start were not.
- **Physical device not tested.** The HTTPS PWA was checked from the local Windows host only.
- DPAPI backup encryption is bound to the creating Windows user/profile; separate off-device recovery remains an owner responsibility. The candidate restore is not activated.
- Live Chat/RAG, SMS, cloud services and public networking remain disabled. No public deployment was performed.

## Owner next action

Run the interactive `BootstrapOwner -ConfirmPrivatePilot` command in the documented local pilot guide, then verify the login and authenticated trip save/edit/reopen in the real PWA. Separately confirm Windows/Docker startup policy and perform an owner-supervised reboot recovery check before relying on boot persistence.
