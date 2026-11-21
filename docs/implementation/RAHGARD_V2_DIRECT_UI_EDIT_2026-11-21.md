# Rahgard V2 — Direct assistant implementation, no Codex (2026-11-21)

## Owner request
Replace the fragmented first travel-description screen and follow-up chat with **one consistent, conversational, Persian RTL chat experience** inspired by the owner's dark screenshot; make **two company links** highly visible and separately addressable. Keep architecture/backend unchanged. Owner specifically asked for real code, not image mockups.

## Actual changes committed on `feat/rahgard-unified-travel-v2`

- `frontend/src/pages/App.tsx`: first trip description is a chat-style welcome/composer, with true status values `connected/configured/loading/disabled/unavailable/quota_exhausted`, shown prominently, not falsely claiming `configured` means live connected. For authenticated active conversations, the initial composer disappears and the existing persisted `TravelerJourney` continues in the **same overall visual shell**. Hide competing local regex preview when AI is active; keep fallback preview when AI unavailable. Required initial minimum advertised: **destination and duration**, rather than falsely requiring all other fields. Enter sends; Shift+Enter inserts newline.
- `frontend/src/trip/TravelerJourney.tsx`: Enter sends the existing authenticated assistant turn; Shift+Enter still adds a newline. This reuses existing LLM-first adapter, confirmation, manual edit protections, trip IDs, versions and provisional itinerary API.
- `frontend/src/styles.css`: modern dark purple RTL chat shell, conversation bubbles and accessible status, responsive extracted profile review alongside the same conversation, visually distinct required/optional fields, clear calendar and two company links. Existing provider handshake indicator remains visible for prior acceptance.
- `frontend/src/partners/PartnerWorkspace.tsx`: for each recipient's existing authenticated inbox revision, add **two distinct deep-link URLs** (`view=request` and `view=itinerary`), with readable dedicated request / itinerary views. Both views pull fresh data from the existing organization's inbox API and require a valid signed-in organization membership; the URL is merely a resource locator, never a bearer permission. The backend's `partner.traveler_request_revisions` RLS restricts the joined inbox after revocation. No public/signed/anonymous endpoint was created.
- `frontend/src/partners/PartnerWorkspace.test.ts`: tests for independent URL views, stable company/share/revision identity, and absence of token/query credentials.

## Validation status, precisely

- **PASS**: files were actually written as GitHub commits to V2 feature branch and read back; static string-contract checks confirmed initial panel switch, new link paths, new URL access using returned inbox data, and CSS presence.
- **PASS**: local external QA demo launcher syntax (`node --check`) after updating its formerly SHA-pinned launcher to check that Windows HEAD matches the fetched GitHub remote branch; helper supplied separately for operator.
- **NOT RUN here**: `npm run build`, `npm test`, real Chromium/LM Studio/PG17 after these new frontend commits. No access to owner's Windows runtime from this chat. Do not report V2 end-to-end GO until owner executes these.
- **UNMODIFIED**: FastAPI routes, PostgreSQL schema/migrations, real catalogue content, old persistent `https://localhost:8443` pilot, SSH/VPS, DNS, real SMS/email, remote model configuration.
- **PENDING**: end-to-end Chromium assertion for the two new dedicated company deep links is now added to `frontend/scripts/traveler-e2e.mjs`, including revoked-recipient denial; it has not yet been executed on Windows. Dedicated provisional itinerary view now renders day/stop cards (not JSON).\n- **PENDING**: separate real remote vLLM acceptance remains blocked without privately provided token; production catalogue still empty and full source-backed travel-planning quality not demonstrated. A provisional itinerary must stay explicitly unverified.

## Owner-local acceptance recipe (without Codex)

1. In `C:\Projects\Ai_Tourism`: `git status --short` (inspect if nonempty); `git fetch origin`; `git pull --ff-only origin feat/rahgard-unified-travel-v2`; `git rev-parse HEAD`.
2. In `frontend`, first run `npm.cmd test` for unit coverage. **Do not run `npm.cmd run build` in the same working tree while the legacy 8443 pilot serves `frontend/dist`**, because it may change the files served by that older instance. The provided V2 browser runner starts **Vite dev on port 4181**, not the shared `dist`, allowing independent source-level browser acceptance. A production build can be tested later in a separately prepared copy/worktree with dependencies installed, or after a deliberate protected local-pilot shutdown/backup—not implicitly.
3. Use updated headed demo package (not the previous SHA-locked package). It requires a clean V2 branch and match with fetched `origin/feat/rahgard-unified-travel-v2`; runs the guarded real LM Studio Chromium E2E with disposable PG17 and migrations through 0022. For first chat verify dark welcome and connected status; for ongoing trip verify same conversation UI/profile, manual edits, and confirmed request.
4. Switch to company A inside headed demo. Each revision card should display **two distinct link buttons**. Open them, verify link changes URL, shows either request or itinerary only, and both display the correct revision. Switch to revoked company B and check that links no longer expose content. Cross-tenant/anonymous access should deny, not show a stale snapshot. UI E2E on this code is still required.
5. Only after full successful local acceptance consider any separate release task; NEVER deploy by implication.

## Safe limits
No Codex tasks were requested or assigned. No SSH, live VPS changes, DB imports, persistent PG migrations or destructive operations have been performed. If builds/tests fail, return exact compiler/test output for direct repair.
