# Rahgard V2 apex authentication and cutover decision

**NO-GO / BLOCKED for live activation.** The immutable candidate is `36625ecf269c2a3d5590528257d32af2b6f47dd0`, which supersedes the previous images. The exact-host isolated auth gate passed. Public Arvan routing and the legacy traffic policy require the owner’s decision before final activation can be authorized.

## Live observations and scope of the 401 diagnosis

The running legacy API image, on `5e2664fb51e18f52549aa37a8b5793e12ace09b2`, reported the two permitted values:

```text
STAGING_PUBLIC_HOST=rahgard.hinaa.ir
AUTH_ALLOWED_ORIGINS=https://rahgard.hinaa.ir
```

Apex `GET /api/v1/auth/method` and empty JSON POSTs to staging login, register and redeem returned **301** to the corresponding www paths. Redirects were left unfollowed. The legacy subdomain returned **200** for GET and **422** for those empty POSTs. Empty POST payloads cannot reach password or session handling. The owner’s earlier methods response is a separate observation and may reflect different edge routing at that time.

The old API image returned **401** for correctly shaped synthetic apex login and registration when running with the measured legacy origin configuration in isolation. It rejected 8 and 15 characters and accepted a 16-character password at the matching legacy origin. This confirms the behavior of both gates. The public probe did not reproduce the owner’s exact 401, and used no credentials or cookies.

## Exact apex TLS rehearsal

The [sanitized R5 evidence](evidence/issue24/R5-apex-auth.json) uses the off-host VPS backup restored to the exact PG17 image, migrated through 0023, and served privately by the verified V2 API and Web images. The runner uses port 443, SNI and Host `hinaa.ir`, a fixture certificate verified by the HTTP client and a private loopback network namespace with no published Docker ports. Chromium used a loopback CONNECT tunnel permitting only `hinaa.ir:443` and pinned to that namespace. Direct DNS resolution of apex was disabled. Chromium accepted the fixture certificate in its temporary context. This does not establish public edge-to-origin trust.

| Check | Result |
| --- | --- |
| Exact HTTPS root, manifest, service worker, hashed assets and missing-asset behavior | Pass in isolation |
| Existing account rows and staging credential contents | Pre/post migration fingerprints matched. The report records a boolean only |
| Compatibility | A fixture credential created using the legacy API signed in using V2 without a password change |
| Signup off | Uninvited signup 401. Invitation redemption and login with an 8-character Persian password passed |
| Signup on | Registration lengths 7 and 257 returned 422. Lengths 8, 24, 25 and 256 returned 200 and all resulting accounts signed in |
| Auth protections | Secure, HttpOnly, host-only cookie, legacy Origin rejection, authenticated session read, missing CSRF denial, logout and session revocation passed |
| Exact-host Chromium | Invitation-only UI hid open registration and signed in the old-image fixture. Signup UI rejected 7 and 257 supplementary Unicode characters before any request and sent all 256 valid characters. Both modes preserved the secure session on reload and verified the manifest root URL |
| External services | SMS unavailable. SMS, RAG and external model calls disabled for this rehearsal |

Focused backend authentication regressions passed **28 tests**. All **200 frontend tests** and both PWA build tests passed. The form now counts Unicode code points to match the server and avoid silently truncating long pasted passwords. The real API accepted 8 and 256 supplementary code points and rejected 7 and 257. The guarded local LM Studio journey passed again with three successful model calls, saved itinerary and company sharing. It used a separate synthetic PostgreSQL database.

[Hosted build 45112204219](https://github.com/AiDev168/Ai_Tourism/actions/runs/45112204219) created both exact candidate Linux AMD64 images. The off-host copy passed outer and inner checksums, image secret scanning and loaded image equivalence. The Nginx worker passed the PWA asset/MIME checks, and the shared TLS listener fixture passed the apex, legacy and wrong SNI checks. [R6 image identities](evidence/issue24/R6-apex-images.json).

Run from the Windows checkout using the protected backup, key directory and verified local image tags identified in the [preparation result](RAHGARD_V2_ISSUE24_PREPARATION_RESULT_2026-11-23.md):

```powershell
$legacy = '5e2664fb51e18f52549aa37a8b5793e12ace09b2'
$candidate = '36625ecf269c2a3d5590528257d32af2b6f47dd0'
python scripts/ops/rehearse_rahgard_v2_migrations.py docs/operations/evidence/issue24/R0-baseline.json $candidate $encryptedArchive $protectedKeys --openssl $opensslExecutable --runtime-image "rahgard-api:$legacy" --runtime-image "rahgard-api:$candidate" --apex-auth-images "rahgard-api:$legacy" "rahgard-api:$candidate" "rahgard-web:$candidate" --apex-browser
```

## Owner decision and the single-writer gate

The preview uses a separate V2 runtime configured for only `hinaa.ir`, invited access by default and a disposable clone. The legacy runtime and its permanent data remain available during preparation. Keeping two writable production databases would split accounts, trips and consent history. Concurrent legacy and V2 writes to one permanent database have not been qualified.

The proposed sequence is a verified maintenance freeze followed by one handoff of the authoritative database writer to V2. The old service stays available until the freeze. Its domain behavior after the handoff needs a separate decision. An owner-approved redirect to the apex after the handoff is compatible with one writer. Continuing independent legacy sign-in and writes requires a different reviewed topology. Apex cookies are host-only, so travelers sign in at the new origin.

1. Confirm whether the apex-to-www redirect can be replaced, whether an existing service depends on it, and how the legacy subdomain should behave after the handoff.
2. Verify the Arvan origin settings and provision a trusted apex origin certificate. The isolated Chromium proof establishes the candidate origin behavior. Public signed-in acceptance through Arvan remains a post-authorization check. Keep open signup off unless expressly authorized.
3. Review the freeze, final fresh backup, guarded migration, monitored switch and rollback. The checked-in code applies migrations only to a disposable restore. The live 0022–0023 executor remains pending.

Final activation requires separate explicit authorization for the exact SHA, window, routing and migrations. This follow-up made no live configuration, DNS, Nginx, service or database changes.
