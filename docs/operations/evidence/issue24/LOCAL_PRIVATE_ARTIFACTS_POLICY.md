# Issue #24 — private local browser evidence (do not publish raw originals)

Two paths intentionally remain private and untracked in the Windows checkout:

- `docs/operations/evidence/issue24/live-v2-mobile-390.png` — real draft trip / UI state, may include personal travel details.
- `frontend/scripts/.issue24-live-apex-interactive.local.mjs` — local-only interactive acceptance runner; may encode machine-local paths, credentials, cookie/session handling or private test-account context.

## Required handling

- Do **not** `git add -A`, force add, or globally ignore other files to hide an unfinished task.
- The PowerShell installer backs up these two files under the user's `%LOCALAPPDATA%` and validates SHA-256 before adding **workspace-only** entries to `.git/info/exclude`. It does not delete, alter or publish either file.
- Codex must inspect the local `.mjs` before deciding whether a *separate sanitized, portable* script should be committed under a normal non-`.local` name; never publish secrets/PII or copy browser cookies/profile credentials into the repo.
- A screenshot derivative may be added only after redaction of all traveler text, account identifiers and session data plus human visual review; original stays private.
- The fact that an original stays untracked is an **intentional privacy decision**, not an incomplete Git sync.
- Keep test account access private. Browser tests should collect only route/status/safe error code and IDs that have been pseudonymized.
