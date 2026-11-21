# Rahgard V2 real-provider acceptance

## Decision

**LOCAL NO-GO for the requested dual-provider release gate.** The local LM Studio route passed an authenticated browser journey. The separate remote vLLM route is **BLOCKED before network access** because the approved token is not present in the runner's process environment. One provider result cannot substitute for the other.

This acceptance was performed on `feat/rahgard-unified-travel-v2`, after safely fast-forwarding the local branch to baseline `f9942f169b2aaa58f70c593d50d95ac0c618b938`. The tested implementation/evidence commit is **`9fa72d4c27d2a258730c0763868a0169cbe7f3a7`**; this report-only commit follows it. No VPS, DNS, remote application, shared/persistent database, SMS, RAG service, or live deployment was accessed or modified.

## Provider outcomes

### Local LM Studio — PASS for the exercised journey

- Route: actual OpenAI-compatible loopback HTTP, `127.0.0.1:1234`.
- Model reported by the loaded LM Studio server: `qwen3-8b-abliterated`.
- The V2 PWA submitted authenticated turns through FastAPI's assistant endpoint and the production `RemoteChatAdapter`; a guarded PostgreSQL 17 database persisted the trip, conversation, revisions, recommendations, and itineraries.
- 3 actual provider invocations, 3 successful adapter responses, 0 failures. Sanitized adapter latencies: **10,721 ms; 10,763 ms; 16,744 ms**.
- The response contract included structured keys for origin, destination, duration, traveler count, budget, interests, relative date, and explicit date endpoints. The accepted profile in this run marked the seven exercised fields (origin, destination, duration, traveler count, budget, interest, relative departure) as `llm` sourced. The relative departure offset was 1 day. Travel start/end remained `missing`; the application did not invent an end date.
- Follow-up correction completed through the provider. A manual origin edit remained authoritative. Explicit profile confirmation preserved that edit.
- The production catalogue did not resolve the requested destination identity. Recommendation truthfully returned `needs_confirmation` with `destination_resolution` unresolved and zero real recommendations. The provider then generated an editable `provisional_unverified` itinerary, which was saved and reopened in the traveler UI after reauthentication.
- A separately labeled test-only catalogue dependency override exercised a positive deterministic recommendation and itinerary persistence through real FastAPI/PG17. It used synthetic E2E identities/evidence only inside the disposable server process. The normal published catalogue endpoint's identities were unchanged before and after; no canonical destination was published.
- Two isolated test companies exercised traveler-authorized sharing of the confirmed request and itinerary, a same-trip revision/inbox event, anonymous access denial, and cross-tenant inbox/workspace/write denial. Those companies and rows existed only in the disposable PostgreSQL run.

The adapter sets `temperature: 0` for reproducible structured extraction. Local HTTP is permitted only for an explicitly configured matching development/test loopback host and port. Staging/local-pilot HTTPS policy remains unchanged; HTTPS requests keep their 15-second request/20-second overall bounds. The local loopback bound is 45 seconds/50 seconds overall.

### Remote vLLM — BLOCKED before any request

- Required route/model: `https://llm.hinaa.ir/v1/chat/completions`, `TaHa1_VL`.
- `Run-National-Catalogue-Browser-E2E.ps1 -ChatProvider remote_vllm` stopped before disposable database startup or provider network access with: `Remote vLLM acceptance is blocked: no authorized provider token is configured in the process environment.`
- No vLLM invocation was made. No key was read from `.env`, printed, or added to artifacts.
- To unblock, make the already authorized key available privately to the local runner as `RAHGARD_REAL_CHAT_TOKEN` or `INTERNAL_CHAT_TOKEN`, then run the documented `remote_vllm` mode. Never send the key in chat or commit it.

## Forced-outage fallback

A separate authenticated Chromium/FastAPI/PG17 run targeted a deliberately closed local provider port:

- 1 adapter attempt, 0 successes, 1 safe failure; no automatic retry.
- Deterministic fallback populated and persisted origin, destination, duration, travelers, budget, and relative date; a manual origin correction persisted.
- Saved trip/conversation state reopened from the isolated database.
- This is an outage/fallback test, not model inference.

## Executed validation

| Validation | Observed result |
|---|---:|
| `uv run pytest -q -p no:cacheprovider backend/tests/test_chat_adapter.py backend/tests/test_trip_requirements_interpretation.py` | 75 passed |
| `uv run ruff check` on changed backend/config/adapter/parser/test files | Passed |
| `python -m py_compile backend/tests/traveler_e2e_server.py` | Passed |
| `npm --prefix frontend test -- --run` | 21 files, 192 tests passed (prior focused worktree run) |
| `npm --prefix frontend run build` | Passed; existing Vite chunk-size advisory (>500 kB) |
| `node --check frontend/scripts/traveler-e2e.mjs` | Passed on final harness |
| `-ChatProvider lm_studio` authenticated Chromium + FastAPI + disposable PG17 (run `03-50-46-197Z-38916`) | Passed; 3/3 real calls; extraction, correction, manual-edit precedence, provisional save/reopen, fixture-backed recommendation/itinerary, sharing/revision, and tenant controls passed |
| `-ChatProvider forced_outage` authenticated Chromium + FastAPI + disposable PG17 | Passed; 1 safe failure, fallback persistence and manual correction passed |
| `-ChatProvider remote_vllm` preflight | Blocked before network call; process token unavailable |
| `git diff --check` | Passed before commit; staged diff check passed |

Both browser runs used the guarded disposable PostgreSQL 17 runner on loopback, not port `55433`. Its container was removed by the runner after each run. No persistent data was changed.

## Evidence

Sanitized acceptance reports and screenshots are in [`evidence/issue22/`](evidence/issue22/):

- [LM Studio report](evidence/issue22/lm-studio-acceptance.json)
- [LM Studio browser screenshot](evidence/issue22/lm-studio-browser.png)
- [Forced-outage report](evidence/issue22/forced-outage-acceptance.json)
- [Forced-outage browser screenshot](evidence/issue22/forced-outage-browser.png)
- [Evidence SHA-256 list](evidence/issue22/SHA256SUMS.txt)

Artifacts contain only test outcomes, model/route identity, schema key names, numeric latency, coarse field provenance, and synthetic acceptance values. They do not contain raw prompts, provider reply text, secrets, or browser tokens. The normal catalogue endpoint remained unchanged while the test-only recommendation dependency was enabled.

## Remaining gaps

- **Blocks dual-provider/local GO:** remote vLLM requires the authorized token in the private runner environment and a complete separate E2E rerun.
- **Catalog-backed traveler recommendations remain unavailable for this request:** no eligible published Shiraz destination identity was resolved. The accepted flow produced an honest provisional plan and a separately labeled test-only recommendation-path exercise; it did not establish real-destination recommendation quality.
- **Not assessed here:** physical Android installation, public/persistent deployment, disaster recovery, or other language/provider-specific acceptance cases beyond the enumerated Persian run.

Overall: **LOCAL NO-GO** for Issue #22's dual-provider completion requirement. The LM Studio route is independently demonstrated; remote vLLM remains untested, not failed.
