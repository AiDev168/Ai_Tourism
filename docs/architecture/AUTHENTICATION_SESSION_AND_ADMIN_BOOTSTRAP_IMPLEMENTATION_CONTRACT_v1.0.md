# Authentication, Session, and Administrator Bootstrap Implementation Contract v1.0

- **Status:** Implementation contract — high-level decisions accepted; operational gates remain
- **Owner approval:** Authentication decisions dated 2026-11-07
- **Authority:** [ADR-0006](decisions/ADR-0006-authentication-and-session.md) and [ADR-0008](decisions/ADR-0008-centralized-ai-provider-management.md)
- **Companion analysis:** [Authentication, Session, and Administrator Bootstrap Decision Brief](AUTHENTICATION_SESSION_AND_ADMIN_BOOTSTRAP_DECISION_BRIEF_v1.0.md)

This document is an implementation contract for a later, separately authorized task. It does not itself authorize code, schema, deployment, production SMS, or protected routes. Each requirement is labeled as **Owner-approved decision**, **Required invariant**, **Proposed technical default**, **Unresolved owner decision**, or **Implementation prerequisite**. A proposed default must not be presented as an owner decision.

## 1. Purpose and scope

- **Owner-approved decision:** The initial release targets tourists travelling inside Iran. Initial login supports Iranian `+98` mobile numbers. International tourist authentication is deferred; phone identifiers remain E.164-compatible for future expansion.
- **Owner-approved decision:** Phone OTP over SMS is the sole initial end-user authentication method. Email/password, email magic links, and federated login are deferred.
- **Required invariant:** Phone verification proves control of a phone number at the time of OTP verification only. It does not establish legal identity, age, company ownership, partner legitimacy, or authorization to represent an organization.
- **Owner-approved decision:** SMS integration uses a provider-neutral backend delivery port. No SMS vendor or production credential is selected. Normal automated tests use a deterministic fake delivery adapter.
- **Owner-approved decision:** Sessions are opaque, high-entropy, server-managed and PostgreSQL-backed, with a host-only `Secure`, `HttpOnly`, `SameSite=Lax` browser cookie. No Redis without measured evidence and separate approval.
- **Required invariant:** Authentication establishes identity; authorization independently checks ownership, organization membership, platform capability, or provider-administration capability for each protected operation.
- **Explicit exclusions:** This contract does not implement partner domain permissions, marketplace workflows, referral leads, SMS vendor integration, email/federation, international login, client-side persistence of credentials, or any public/anonymous protected route. Referral leads remain unauthorized under ADR-0007 unless the owner separately approves scope and accepts an ADR-0007 amendment.

## 2. Accepted decisions and traceability

| Decision | Status and source |
|---|---|
| Domestic Iranian initial market; `+98`; E.164-compatible phone representation | **Owner-approved decision**, 2026-11-07; recorded in ADR-0006 |
| SMS phone OTP only for initial login; other methods deferred | **Owner-approved decision**, 2026-11-07; recorded in ADR-0006 |
| Phone verified only after successful OTP; stored phone value alone is insufficient | **Owner-approved decision**, 2026-11-07 |
| Provider-neutral SMS port; no vendor selected; fake adapter for tests | **Owner-approved decision**, 2026-11-07 |
| Representative SMS delivery testing required on MCI, Irancell, and Rightel before vendor approval/production | **Owner-approved decision**, 2026-11-07; no network calls authorized by this contract |
| Opaque PostgreSQL-backed session and host-only `Secure`, `HttpOnly`, `SameSite=Lax` cookie; no Redis absent separate approval | **Owner-approved decision**, 2026-11-07 |
| Unsafe cookie-authenticated requests require explicit CSRF defense | **Owner-approved decision**, 2026-11-07; exact mechanism remains open |
| Shared underlying traveler/partner staff identity permitted; grants remain distinct and independently assigned | **Owner-approved decision**, 2026-11-07 |
| Server-derived identity and organization scope; object/tenant checks | **Owner-approved decision** and **Required invariant** |
| Additional authentication factor required for privileged administrator operations; TOTP preferred candidate | **Owner-approved decision**, 2026-11-07; TOTP lifecycle and assurance details remain open |
| Private, operator-controlled, one-time first-admin provisioning; no public claim endpoint/default/shared admin | **Owner-approved decision**, 2026-11-07; exact ceremony/recovery remains open |
| Only the authenticated and authorized primary system administrator manages AI Provider Gateway | **Owner-approved decision** in ADR-0008; remains authoritative |

## 3. Identity model

### 3.1 Phone normalization

- **Required invariant:** One canonical phone value is used for challenge binding, account lookup, uniqueness, audit correlation, and session identity. It is never inferred from a display name or a submitted `user_id`.
- **Proposed technical default:** Convert Persian and Arabic-Indic digits to ASCII digits, trim surrounding whitespace, and ignore only documented visual separators before parsing. Normalize supported domestic forms such as `09…` and explicit `+98…` to `+98` followed by the national significant number. Persist canonical E.164 form, e.g. `+989xxxxxxxxx` shape, after validating Iranian mobile format.
- **Required invariant:** Reject unsupported country codes, malformed prefixes, extensions, ambiguous or incomplete numbers, and input that cannot be normalized unambiguously. Do not silently reinterpret foreign numbers as Iranian.
- **Implementation prerequisite:** Select a maintained phone-number parsing approach or document a constrained validator, then test local and `+98` forms, localized digits, separators, invalid lengths/prefixes, and future-safe storage. Dependency choice is not made here.
- **Unresolved owner decision:** Policy for phone portability/reassignment, account reuse after deletion, and handling number changes or duplicate existing records.

### 3.2 Relationship to current `identity.users`

The current schema has `user_id`, nullable `auth_subject`, `email`, `phone_e164`, `display_name`, `password_hash`, `account_status`, synthetic classification, and timestamps. It has no phone-verification state, OTP challenge, session, MFA, or recovery aggregate. Email has a case-insensitive uniqueness index; no equivalent verified-phone uniqueness policy is established by this contract.

- **Owner-approved decision:** `phone_e164` presence is not a verified-phone claim.
- **Proposed technical default:** Keep the canonical current phone on the user identity and represent verification evidence/status separately or with a reviewed additive change. A verified phone should identify at most one active account under an explicit uniqueness/reassignment policy. Do not infer verification for legacy or synthetic rows.
- **Implementation prerequisite:** Inspect and reconcile existing data in isolated tests before designing any uniqueness constraint or migration. Do not query or alter the shared database for this task.
- **Required invariant:** Only a successfully verified challenge may establish a phone as login-capable. Account activation must respect existing `account_status`; `disabled`, `pending_deletion`, and `deleted` accounts cannot obtain normal sessions.
- **Unresolved owner decision:** Whether re-verifying a phone attached to a disabled/deleted identity restores it, creates a new identity, or requires support review. No automatic account merge by phone/email match is authorized.

## 4. OTP lifecycle and SMS adapter

### 4.1 State and flow

```text
REQUESTED -> ISSUING -> DELIVERED -> VERIFIED/CONSUMED
    |           |           |             |
    |           |           +-> EXPIRED   +-> account lookup/create eligibility
    |           +-> DELIVERY_FAILED
    +-> RATE_LIMITED

Any non-terminal challenge -> EXPIRED / SUPERSEDED / LOCKED
```

State names are logical contract values, not existing database enums. Verification must be one-time and purpose-bound. The code is bound to challenge ID, normalized phone, and purpose; it cannot be replayed across challenges, accounts, or login/phone-change purposes.

### 4.2 Issue and delivery

1. **Required invariant:** Generate codes with a cryptographically secure random generator. Do not derive the code from time, user ID, phone, or a non-cryptographic PRNG.
2. **Owner-approved decision:** Pass SMS through a provider-neutral adapter with bounded timeout, safe error mapping, and test fake. Domain logic cannot name or select an SMS vendor.
3. **Unresolved owner decision:** SMS vendor, sender/route, credentials, templates, commercial terms, and production operating conditions are not selected.
4. **Implementation prerequisite:** Before real delivery is enabled, test actual delivery and response behavior across representative MCI, Irancell, and Rightel numbers; evaluate delivery time/failure, cost, route limits, support, sender requirements, fraud controls, and recovery impact. Obtain explicit owner authorization after these results.
5. **Required invariant:** Do not persist a plaintext OTP or include it in logs, traces, analytics, audit metadata, exception messages, test snapshots, or public responses. The SMS delivery operation necessarily receives the one-time code in process memory; minimize its lifetime and do not retain adapter payloads.

### 4.3 Low-entropy verifier and verification

- **Required invariant:** A plain hash of a six-digit code is insufficient protection against offline brute force if challenge storage leaks. Store a keyed verifier, not plaintext or an unkeyed digest.
- **Proposed technical default:** Compute an HMAC using a server-held secret and an unambiguous encoded message containing a domain separator, challenge ID, purpose, normalized phone, and code. Keep the HMAC key outside the database and rotate through a key identifier/version. Compare candidate and stored verifier in constant time. The precise algorithm/library and key management require security review; never store the key beside the verifier.
- **Required invariant:** Bind expiration, maximum attempts, consumed/superseded state, purpose, and verifier update atomically. Successful verification consumes the challenge exactly once. Concurrent verification/replay attempts must not both succeed.
- **Proposed initial defaults only:** six numeric digits, five-minute validity, five failed attempts, and a 60-second resend delay. These are not owner-approved immutable values; security review must tune and configure them.
- **Required invariant:** Resend is rate-limited and either invalidates/supersedes previous challenges or follows another explicitly reviewed one-active-challenge policy. A resend never resets cumulative abuse budgets.
- **Required invariant:** On valid OTP, mark verification evidence and then authenticate/create an eligible identity according to account policy. Do not create a verified account merely because SMS dispatch succeeded.

### 4.4 Enumeration-safe responses and errors

- **Required invariant:** Challenge-issue responses do not reveal whether a phone already has an account, is verified, is disabled, or is eligible. Use the same public response shape and safe message for accepted, ineligible, and rate-limited requests where operationally possible; avoid materially different timing.
- **Required invariant:** Verification failures return a stable generic invalid/expired response without indicating whether a phone or account exists. Internal logs use coarse reason codes and redact phone/code.
- **Proposed technical default:** Map adapter timeout/rejection/temporary outage to a provider-neutral retry message and request ID. Do not expose vendor names, route details, credentials, raw responses, or whether the account exists.
- **Unresolved owner decision:** Exact user-facing copy, localized retry behavior, and treatment of SMS delivery failure versus rate limiting.

### 4.5 Abuse controls

- **Required invariant:** Apply bounded rate limits and abuse detection across normalized phone, source IP/network, challenge/account, device/session context where available, and global/provider cost budgets. Avoid a single dimension that permits distributed abuse.
- **Required invariant:** Cap issue/resend/verify attempts, enforce cooldown and challenge expiry, detect replay, and provide operational alarms for unusual volume/provider failure. Avoid permanent phone lockouts that enable denial of service without an approved recovery path.
- **Proposed technical default:** Store privacy-minimized keyed references for rate-limit correlation when raw phone/IP retention is unnecessary; define retention and access before production.
- **Unresolved owner decision:** Exact thresholds, block durations, IP aggregation/privacy policy, CAPTCHA or other friction policy, and abuse-response owner.

## 5. Session model

- **Owner-approved decision:** Session identifiers are opaque, cryptographically high-entropy, server-managed, persisted in PostgreSQL, and never carry user/role claims in client-readable form.
- **Proposed technical default:** Generate at least 256 bits of CSPRNG entropy. Return the raw identifier only in the session cookie. Persist a cryptographic hash of the identifier, not the bearer value; a fast hash is suitable for a uniformly random high-entropy token. Use constant-time comparison where applicable and rotate after authentication/privilege changes to prevent fixation.
- **Required invariant:** On every request, resolve session server-side, reject expired/revoked sessions, verify active account status, and derive the principal from the stored session. Authorization must still check resource ownership and current organization/platform capability.
- **Proposed persistence responsibility:** Session record tracks token hash, user identity, creation/last-seen times, expiry, revocation, and limited non-sensitive device/session metadata. Do not store raw cookie values or unnecessary fingerprinting data.
- **Owner-approved decision:** Logout and revocation are server-side. Logout revokes the current session and clears the cookie. Account disablement and security recovery must revoke all affected sessions within the approved operational bound.
- **Unresolved owner decision:** Idle/absolute lifetimes, rotation triggers, multi-device/session listing, device-level revocation, last-seen update cadence, retention/cleanup, and PostgreSQL outage behavior.
- **Required invariant:** Do not use Redis for sessions absent measured need and separate owner approval. Fail closed if session validation cannot safely be performed.

## 6. Cookie, browser, and CSRF security

- **Owner-approved decision:** Initial cookie is host-only with `Secure`, `HttpOnly`, and `SameSite=Lax`. Do not set a broad `Domain` attribute. Use TLS in production.
- **Proposed technical default:** Use a `__Host-`-prefixed cookie name if deployment can satisfy the prefix requirements (Secure, path `/`, no Domain); otherwise retain a host-only cookie with explicit tests. Cookie lifetime should not exceed server session expiry. Exact name/path/lifetime are not owner-approved.
- **Owner-approved decision:** No long-lived session credential in `localStorage`, IndexedDB, or other JavaScript-readable browser storage.
- **Owner-approved decision:** Every unsafe cookie-authenticated operation has explicit CSRF protection; `SameSite=Lax` alone is insufficient.
- **Proposed technical default:** Synchronizer token: generate a per-session random CSRF token, store its verifier server-side, provide the token to the PWA only through an authenticated same-origin response, keep it in memory, and require it in a custom header on unsafe requests. Validate `Origin` against an exact configured allowlist; use `Referer` as a carefully defined fallback where appropriate. Reject missing/invalid tokens and untrusted origins. Do not put CSRF tokens in URLs.
- **Unresolved owner decision:** Approve or revise the synchronizer-token proposal, Origin/Referer fallback rules, CORS policy, trusted proxy settings, cookie name/path, and HTTPS deployment topology.
- **Required invariant:** Use security headers and safe output handling to reduce XSS. HttpOnly prevents script from reading the session cookie but does not stop an active XSS from issuing authenticated requests.
- **Required tests:** Cross-site form/fetch requests, missing/wrong CSRF token, untrusted Origin, safe-method behavior, same-origin PWA requests, cookie flags, cookie absent from JS storage, and session fixation/rotation.

## 7. Authorization model

### 7.1 Principal and independent capabilities

- **Owner-approved decision:** One underlying user identity may be both a traveler and a partner employee.
- **Required invariant:** A principal contains only server-validated identity and explicitly assigned capabilities. Traveler ownership, partner organization membership, marketplace governance roles, primary platform administration, and AI Provider administration remain separate grants.
- **Required invariant:** A submitted `user_id`, `organization_id`, role, reviewer ID, or admin flag never establishes authority. Treat them only as untrusted selectors, then resolve access from authenticated server state.
- **Required invariant:** Phone OTP proves phone control only. It does not grant partner membership, prove business ownership, verify a company, or grant a marketplace/admin role.

### 7.2 Resource and tenant checks

- Authenticate the session, derive user ID, validate account status, then authorize the requested operation against the resource owner/tenant and current capability.
- For partner resources, resolve active membership server-side for each operation and verify the resource belongs to that organization. Branch/brand relations grant no implicit inheritance.
- Apply object-level checks to every read, create, update, delete, export, referral, and audit action. Deny cross-user and cross-organization guessed-ID access; response behavior must not leak resource existence where sensitive.
- Membership revocation, suspension, organization suspension, account disablement, and admin-role revocation must take effect in active sessions within the owner-approved bound. Do not rely on long-lived cached role claims.
- Marketplace governance is least-privilege and separates verification review, content publication, primary platform role administration, and sensitive data access. A partner cannot approve its own organization/content.
- **Owner-approved decision:** Marketplace or partner administration does not imply AI Provider administration.
- **Owner-approved decision:** Only an authenticated and authorized primary system administrator may manage AI Provider Gateway under ADR-0008. No provider-admin route before approved MFA, bootstrap, recovery, and authorization are implemented and tested.

### 7.3 Existing and future API boundary

The current API runtime has health and publication-gated catalogue reads; future authenticated OpenAPI paths are documentation, not handlers. Do not expose future user/partner/admin routes anonymously. New routes require reviewed request schemas, principal dependencies, object-level checks, negative authorization tests, and safe public projections.

## 8. Administrator security and bootstrap

- **Owner-approved decision:** Privileged administrator operations require an additional authentication factor; phone OTP/passwordless access alone is insufficient. TOTP is preferred for evaluation, not a fully approved enrollment/recovery policy.
- **Required invariant:** Do not claim independent-factor MFA solely because a user completes SMS OTP and a TOTP code: both are possession-channel OTP methods. Security review and owner approval must confirm whether this satisfies the intended assurance or whether a different approved factor is needed. Until resolved and implemented, privileged routes remain disabled.
- **Owner-approved decision:** Partner administration, marketplace governance, primary system administration, and AI Provider administration are distinct capabilities. ADR-0008 controls provider administration.
- **Required invariant:** Admin actions are individually authorized and audited with actor, capability/scope, target, time, result, correlation, reason/policy version, and non-sensitive before/after metadata. Never log OTPs, session tokens, TOTP secrets, recovery codes, provider secrets, or raw private payloads.
- **Owner-approved decision:** First-admin provisioning is private, operator-controlled, and one-time. No public first-user endpoint, hardcoded/default credential, anonymous admin path, or shared admin account.
- **Unresolved owner decision:** Exact operator ceremony, identity proofing, TOTP enrollment, break-glass existence/custodians, first-admin loss recovery, dual approval, notification, and post-event review.
- **Implementation prerequisite:** Do not expose any privileged route until approved MFA assurance, bootstrap, recovery, authorization matrix, audit, and negative tests are complete. ADR-0008 provider management additionally requires its secret protection, redaction, routing, and rollback controls.

## 9. Recovery and phone changes

- **Unresolved owner decision:** Traveler who loses the registered phone; SIM loss/replacement; number recycling/reassignment; phone replacement; duplicate account; phone unlink/change; account deletion/recreation; support-assisted recovery; and whether any secondary account factor exists.
- **Required invariant:** No self-service phone recovery, phone replacement, account merge, or identity transfer may be invented or shipped without an approved policy. Do not treat a support request, phone ownership assertion, or partner verification as proof of account ownership.
- **Implementation prerequisite:** These flows block production launch of account recovery and phone-change functionality. If initial OTP login cannot support safe account recovery, the owner must approve a support procedure or explicitly accept a bounded launch limitation before public activation.
- **Unresolved owner decision:** Admin device replacement, recovery factor reset, primary-admin loss, and emergency access. These block privileged admin routes and AI Provider control.
- **Proposed technical default:** Any approved recovery/change procedure revokes existing sessions, emits a redacted audit event, notifies the prior verified channel where safe, and requires renewed OTP verification of the new phone. This behavior remains proposed until owner approval.

## 10. Configuration and secrets

- **Required invariant:** SMS credentials, HMAC verifier keys, session hashing/key material, TOTP secrets, recovery material, database passwords, and provider secrets stay server-side. Never commit them, place them in a client bundle/browser store, include them in logs/analytics/test fixtures, or return them in public/API error responses.
- **Owner-approved decision:** No SMS vendor credentials are present or authorized by this contract. No external SMS calls occur in normal tests.
- **Proposed technical default:** Configuration is validated at startup; secrets are provided through an approved server-side secret mechanism. Keep key identifiers/version metadata separate from key values. Rotation must preserve valid challenges/sessions only according to explicit expiry/revocation rules.
- **Unresolved owner decision:** Production secret-management technology, key rotation/retention, TOTP encryption-at-rest strategy, and operator access policy.
- **Implementation prerequisite:** Redacted structured logging and secret-scanning checks cover OTPs, phone numbers, session identifiers, cookies, CSRF tokens, TOTP/recovery material, SMS adapter payloads, and provider secrets.

## 11. Database design guidance (no schema approved here)

The current `identity.users` contains `phone_e164` and `account_status`, but no verification marker/challenge/session/MFA lifecycle. Current `identity.user_consents` is not an authentication record. Current `operations.audit_events` is generic and does not by itself establish sufficient security audit policy. The following are persistence responsibilities for a future reviewed design; they are not existing tables and do not authorize migrations:

| Responsibility | Candidate data to persist | Exclusions/security |
|---|---|---|
| OTP challenge | Challenge ID, canonical phone reference, purpose, keyed verifier/key version, issue/expiry/consume/supersede timestamps, attempt counters, coarse delivery status | Never plaintext OTP or HMAC key; minimize IP/device data; atomic consumption and rate limits |
| Phone verification evidence | User ID, canonical phone, verified timestamp, challenge/purpose reference, active/revoked state | Phone value alone is not evidence; no legal identity assertion |
| Session | User ID, token hash, created/last-used/idle/absolute expiry, revoked time/reason, minimal device label, CSRF verifier | Never raw token/cookie; enforce server-side checks and cleanup |
| MFA enrollment | Admin/user ID, factor type/state, encrypted TOTP secret or approved verifier material, enrollment/activation/disable timestamps | Secret is never returned after enrollment or logged; encryption/rotation design remains open |
| Recovery material/events | Only if approved: one-time verifier hashes, expiry/use state, issuer/approver, result, revocation | No plaintext recovery codes; no recovery feature before policy approval |
| Audit/security events | Actor/capability, target, action, outcome, reason, correlation, time, policy version and redacted metadata | Do not store OTP/session/TOTP secrets or excessive personal payload; review whether existing audit model/grants meet requirements |
| Phone uniqueness/account mapping | Canonical verified-phone uniqueness and migration/reconciliation policy | Existing rows are not automatically verified; test duplicate/legacy/synthetic cases in disposable PostgreSQL |

**Implementation prerequisite:** Physical aggregate boundaries, indexes/constraints, retention, concurrency/locking, app-role privileges, migration identifiers, and compatibility with supported database lifecycle states require a separate design and isolated PostgreSQL 17 validation. Do not query or modify `ai_tourism_dev`.

## 12. Testing contract

All default tests use deterministic fakes. No external SMS, identity-provider, paid API, or shared database call is permitted.

### 12.1 Unit tests

- Iranian phone normalization: domestic `09…`, `+98…`, localized digits, separators, malformed inputs, unsupported country code, and canonical equality.
- OTP generation randomness interface, HMAC verifier binding to challenge/purpose/phone, key version handling, constant-time verification wrapper, expiry, single-use, replay, supersession, attempt count and concurrent consume.
- Generic response mapping for existing/new/disabled/unknown phone and provider errors; logs and exceptions redact OTP, phone and adapter payload.
- Rate-limit policy across phone/IP/challenge/global dimensions, resend cooldown, repeated failures, and adapter backpressure.
- Session token entropy/hash, rotation, expiry, revocation, logout, account disablement, and multiple-session policy.
- CSRF token lifecycle, origin policy, unsafe/safe method separation, and failure handling.
- Authorization helpers: server-derived user, own-resource allow, other-user deny, explicit membership allow, inactive/revoked membership deny, unrelated tenant deny, and provider-admin separation.

### 12.2 PostgreSQL integration tests

- Use uniquely named disposable PostgreSQL 17 test environments only; no shared `ai_tourism_dev` access.
- Verify challenge persistence contains no plaintext code/key, verification transaction is atomic, replay cannot authenticate twice, and attempt/expiry state survives process restart as designed.
- Verify token hashes (not raw tokens) are stored, session revocation/expiry/account disablement take effect, and cleanup respects retention policy.
- Verify verified-phone uniqueness/reconciliation policy for duplicate existing identities, disabled users, and synthetic rows without trusting fixture values.
- Verify least-privilege app-role grants for OTP/session/MFA/audit operations and denial of unrelated raw data access.
- Exercise concurrent OTP verification, session revocation, and rate-limit updates for race safety.

### 12.3 API and browser security tests

- Anonymous protected-route requests fail closed; public health/catalogue behavior remains unchanged.
- Cookie has required flags and no Domain; session credential never appears in JSON, headers other than Set-Cookie, browser localStorage/IndexedDB, logs, analytics, or error output.
- CSRF missing/wrong token and untrusted Origin are rejected; same-origin unsafe requests succeed only with valid defense; GET/HEAD do not mutate state.
- Session fixation is prevented; login rotates session; logout, account disablement, phone-security event, and admin-role revocation invalidate expected sessions.
- Cross-user and cross-organization guessed IDs are denied; partner membership and marketplace/admin grants do not imply AI Provider access.
- OTP issuance enumeration, brute force, resend abuse, distributed rate-limit, SMS outage, timeout, duplicate callback, and provider-neutral error handling are tested.
- Admin MFA is required on every privileged operation and step-up expiry/replay is tested. No privileged route is enabled until approved MFA/recovery policy is implemented.
- Bootstrap cannot be invoked publicly or twice; only the authorized private operator procedure can provision the named first admin; audit contains no bootstrap credential.

### 12.4 Operational/security review

Security review must inspect threat model, cookie/CSRF deployment, rate limits/cost ceilings, logging, secret/key lifecycle, account recovery, admin MFA assurance, bootstrap/recovery runbooks, and incident response. Tests passing alone do not authorize production release.

## 13. Operational gates

- **Implementation prerequisite:** Before production SMS: select vendor/route after actual representative testing across MCI, Irancell, and Rightel; review deliverability, cost, rate limits, support, privacy, sender requirements, failure behavior, and recovery implications; owner explicitly authorizes production credentials/use.
- **Implementation prerequisite:** Monitoring for delivery latency/failure, OTP issuance/failure/abuse, rate-limit activity, session validation/revocation errors, and admin events must redact phone, codes, tokens, and secrets.
- **Implementation prerequisite:** Define cost limits, global/provider rate ceilings, safe degradation, vendor outage behavior, credential rotation, escalation, and provider-neutral user messaging.
- **Unresolved owner decision:** Session/OTP retention, alert thresholds, operations owner, on-call/support procedure, and regional delivery fallback. No silent alternate provider or cross-border SMS fallback is assumed.
- **Implementation prerequisite:** Production deployment provides HTTPS, trusted proxy configuration, same-origin or reviewed CORS topology, secure headers, protected secrets, PostgreSQL availability/backup/restore, and tested clock synchronization.
- **Implementation prerequisite:** Admin routes remain disabled until TOTP/MFA policy, private bootstrap, recovery, role matrix, audit review, and security tests are accepted and complete. Provider admin must additionally pass ADR-0008 tests.

## 14. Implementation sequence and acceptance criteria

The following slices are a recommended order for a later authorized Task 2.3. A slice is not permission to start it.

1. **Foundation contract and configuration:** typed identity/session/principal/OTP/SMS ports; settings validation; deterministic fake adapter; no route exposure. **Accept when:** imports are isolated, no provider named in domain logic, and secrets are excluded from logs/client.
2. **Phone and OTP core:** canonicalization, cryptographic issuance, keyed verifier, challenge state, generic errors, configured attempt/rate policies. **Accept when:** unit/security tests cover binding, replay, expiry, enumeration, brute force, resend, and redaction.
3. **Verification/account lifecycle:** verify once, bind phone evidence, handle existing/new/disabled account safely, resolve uniqueness/migration policy. **Accept when:** isolated PostgreSQL tests prove atomic verification and no unverified phone can authenticate.
4. **PostgreSQL session/cookie/CSRF:** token hash persistence, issue/rotate/revoke/expire/logout, cookie flags, synchronizer-token proposal pending approval. **Accept when:** integration and browser tests cover CSRF, session fixation, revocation, account disablement, and no JS-readable credential.
5. **Server-derived principal and authorization seam:** FastAPI dependencies establish principal, with generic ownership/capability helpers; do not implement partner domain membership yet. **Accept when:** cross-user negative tests and fail-closed unauthenticated route tests pass.
6. **Administrator MFA/bootstrap design closure:** owner/security review TOTP factor assurance, enrollment/recovery, private one-time bootstrap, role separation, and break-glass policy. **Accept when:** approved workflows are implemented and negative/positive tests pass; otherwise privileged routes remain disabled.
7. **Production SMS activation gate:** after vendor testing and explicit authorization only, configure provider-neutral adapter in deployment; keep fake adapter as default test path. **Accept when:** network tests and operations/cost controls are reviewed and owner authorizes activation.
8. **Independent security review:** threat model, code/config review, PostgreSQL role audit, recovery and incident runbooks, focused test evidence, and residual risk approval. Only then may the authentication foundation be declared complete.

### Measurable completion criteria

- OTP codes and session credentials are never stored/logged in plaintext; OTP uses a reviewed keyed verifier and sessions store only token hashes.
- OTP issue/verify is enumeration-safe, purpose/phone-bound, expiry-bounded, single-use and rate-limited.
- Session is PostgreSQL-backed, opaque, server-validated, revocable; logout and account disablement have tested effects.
- Cookie has approved flags and unsafe requests pass CSRF/origin checks; long-lived credentials are absent from JavaScript-readable storage.
- Principal and capabilities are server-derived; cross-user and cross-organization negative tests pass.
- Privileged operations require approved and tested additional-factor controls; bootstrap is private, operator-controlled and one-time; provider admin passes ADR-0008 isolation tests.
- Focused unit, API, browser-security, and isolated PostgreSQL 17 integration tests pass; no shared database or real provider calls were used unless separately authorized.
- Vendor/network, operational, recovery, and independent security gates are signed off before production activation.

## 15. Deferred functionality

- Email/password, email magic links, and federated identity.
- International tourist authentication (phone storage remains E.164-compatible).
- Real SMS vendor selection and production delivery until representative testing, review, and explicit owner authorization.
- Any unapproved traveler phone-loss recovery, self-service phone change/reassignment, account linking/merging, or number-recycling flow.
- Administrator TOTP recovery/backup/device replacement until explicitly approved and reviewed.
- First-admin recovery/break-glass details until approved.
- Redis or other new infrastructure for session/rate-limit persistence without measured need and separate approval.
- Partner organization/role implementation (separate Task 3 after Task 2.3 gates), referrals under current ADR-0007, and AI Provider admin routes until all applicable gates are satisfied.

## 16. Owner decisions still required

1. SMS provider/route and production activation after MCI, Irancell, and Rightel testing.
2. OTP length, validity, attempt/resend thresholds, and rate-limit/privacy dimensions.
3. Session idle/absolute lifetime, rotation, multi-device policy, cleanup, and retention.
4. Exact CSRF mechanism and deployment/origin/Referer configuration.
5. Lost-phone recovery, phone replacement/reassignment, account linking, duplicate identities, and deleted-account reuse.
6. TOTP enrollment, recovery, backup, device replacement, and whether TOTP plus SMS satisfies the intended independent-factor MFA assurance.
7. First-admin recovery, two-person controls, emergency access, break-glass, and audit review.
8. Production secrets/key management, operational alert/support owners, retention/deletion, and incident process.

Items 1, 4, and deployment/security controls block production login; item 5 blocks safe recovery/phone change; items 6–7 block all privileged admin and AI Provider routes; item 8 blocks production activation. None may be resolved by silently changing the owner-approved high-level decisions.
