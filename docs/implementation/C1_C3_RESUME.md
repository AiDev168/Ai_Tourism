# C1+C3 continuation checkpoint

Branch: `feat/c1-c3-internal-installable-mvp-v1`; base HEAD `2937590857134e921ef20121690c093709853ae6`. C1+C3 is incomplete. Preserve all uncommitted files.

## Current changes

- `frontend/public/sw.js`: previous session restricted caching to public shell assets and added a `SKIP_WAITING` message hook. Browser behavior and update UX remain unverified.
- `backend/app/modules/integrations/chat_adapter.py`: draft typed remote Chat transport and `make_chat_gateway` factory. It is not connected to any route. It does not yet have a cross-worker invocation budget, multi-turn history, or a complete requirement contract. Do not enable or expose it before those controls exist.
- `backend/app/core/config.py`: server-only `internal_chat_*` settings, disabled by default and restricted to development/test when enabled.
- `backend/tests/test_chat_adapter.py`: offline transport and settings tests.
- The adapter now exposes `make_chat_gateway(settings)` and settings include endpoint/model/token. No traveler route invokes it.

## Verification

From `backend/`, with a process-only dummy `DATABASE_PASSWORD`: `uv run pytest -p no:cacheprovider tests/test_chat_adapter.py -q` exited 0: 7 passed. `uv run ruff check app/core/config.py app/modules/integrations/chat_adapter.py tests/test_chat_adapter.py` exited 0. `git diff --check` passed. A frontend build passed in an earlier session; no browser acceptance, live provider or database test has run for this work.

## Next concrete edit

Implement an additive migration for a durable cross-worker Chat budget and idempotent turn reservation; the existing OTP rate-limit dimensions are OTP-specific. Extend repository transactions so a reservation/budget is acquired before the provider call and both user and assistant messages are saved with version/owner checks. Add explicit user consent to remote processing before sending request text. Then wire a CSRF-protected route, failure/replay tests, and the PWA. Never infer confirmed requirements or publication from model output.

Remaining: full Checkpoint A, all Checkpoint B (icons, update UX, UI and browser checks), and Checkpoint C integrated acceptance. Live Chat and physical-device acceptance remain unverified. No root `.env`, shared DB, live provider, commit, push, merge or deployment was used.
