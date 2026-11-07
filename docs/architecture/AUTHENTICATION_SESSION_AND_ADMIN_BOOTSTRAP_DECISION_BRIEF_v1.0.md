# Authentication, Session, and Administrator Bootstrap Decision Brief v1.0

- **Status:** High-level owner decisions recorded; operational and security details remain open
- **Prepared:** 2026-11-07
- **Scope:** Read-only implementation inventory and documentation-only options/recommendations for ADR-0006 and the administrator-authentication gate in ADR-0008
- **Historical repository baseline for the original implementation audit:** `fix/initialize-database-powershell-inspect-v1` at `6f62daca62cbd70ce7fdad885f1b5d040c3227b1`; this is not a claim about the current checkout

## Executive summary

Authentication remains **unimplemented**, but the owner has now selected the high-level initial domestic authentication and session direction. The schema has identity/contact fields and a password-hash slot, but there is no login or verification flow, session/token implementation, role or membership authorization, administrator bootstrap, recovery process, or auth test coverage. The API contract documents authentication as a future gate; it does not implement that gate.

**Owner-approved direction:** Iranian phone OTP over a provider-neutral SMS boundary; opaque PostgreSQL-backed server sessions in a host-only `Secure`, `HttpOnly`, `SameSite=Lax` cookie; separate scoped identity/authorization capabilities; mandatory additional authentication for privileged administrator operations, with TOTP preferred for evaluation; and private, operator-controlled, one-time first-admin provisioning. No SMS vendor is selected.

The detailed boundaries and unresolved gates are recorded in [ADR-0006](decisions/ADR-0006-authentication-and-session.md) and the [implementation contract](AUTHENTICATION_SESSION_AND_ADMIN_BOOTSTRAP_IMPLEMENTATION_CONTRACT_v1.0.md). ADR-0008 remains authoritative for AI Provider administration. The marketplace ADRs remain proposals. **Protected Task 3 is not ready** until the authentication/session foundation and required security tests are implemented and operational gates are resolved.

## Owner decision outcome — 2026-11-07

This section records decisions explicitly approved by the owner on 2026-11-07. It supersedes only the matching open questions/recommendations in the earlier option analysis; it does not imply that implementation or unresolved operational details are approved.

### Accepted owner decisions

- Initial authentication supports tourists travelling inside Iran using Iranian `+98` phone numbers, represented in E.164-compatible form. International tourist authentication is deferred.
- SMS phone OTP is the primary and only initial login method. Email/password, email magic links, and federated login are deferred.
- A phone number is verified only after successful OTP verification. A stored `phone_e164` value does not itself prove verification and phone verification does not prove legal identity or company ownership.
- OTP delivery uses a provider-neutral SMS adapter. Automated tests use a deterministic fake adapter. No SMS vendor, credentials, or production calls are selected/authorized. Vendor selection requires delivery tests across MCI, Irancell, and Rightel and review of deliverability, cost, rate limits, support, and recovery implications.
- Sessions are opaque, high-entropy, server-managed and PostgreSQL-backed. The browser receives the identifier only in a host-only `Secure`, `HttpOnly`, `SameSite=Lax` cookie. Validation, expiry, logout, and revocation are server-side. No Redis without measured evidence and separate approval. No long-lived JavaScript-readable session credential.
- Unsafe cookie-authenticated requests require explicit CSRF protection.
- A traveler and partner employee may share one user identity, but traveler rights and partner membership/roles are independently granted. Partner authority requires explicit organization membership. Client-supplied IDs/roles/admin flags never establish authority; enforce object ownership and tenant isolation in the backend.
- Privileged administrator operations require an additional authentication factor; SMS/passwordless OTP alone is insufficient. TOTP is the preferred candidate, but enrollment/recovery/backup/device replacement details are not approved.
- Primary platform administration, marketplace governance, partner membership, traveler permissions, and AI Provider administration are separate capabilities. ADR-0008 remains authoritative for AI Provider control.
- First-admin provisioning must be private, operator-controlled, and one-time. No public first-user claim endpoint, default credential, anonymous admin, or shared admin account.

### Technical recommendations (not additional owner decisions)

- Use the same-origin PWA/API topology where practical to simplify cookie scope and CSRF/origin controls.
- Use a typed server-derived principal followed by explicit object, tenant, and capability checks.
- Consider a synchronizer CSRF token held server-side and in client memory, sent in a custom request header, alongside strict Origin validation for unsafe requests. Exact mechanism remains open.
- Use a private, attributable enrollment ceremony with expiry/replay protection and audited disablement for first-admin bootstrap; the owner approved the private/operator-controlled/one-time boundary, not a particular command, deployment console, or credential technology.

### Open operational and security decisions

- SMS vendor, sender/routes, commercial terms, production credentials, representative-network test results, and explicit production activation.
- OTP settings: six digits, five-minute validity, five failed attempts, and 60-second resend are proposed defaults only. Rate-limit dimensions and budgets also require security review.
- Session idle/absolute lifetimes, rotation triggers, concurrent-device policy, and cleanup/retention.
- Exact CSRF mechanism, Origin/Referer policy, trusted proxy/TLS setup, and cookie deployment configuration.
- Traveler phone-loss recovery, phone replacement/reassignment, duplicate accounts, and phone/account linking. No self-service recovery flow is approved.
- Administrator TOTP enrollment, recovery, backup codes, and device replacement. Security review must also confirm whether SMS OTP plus TOTP meets the intended independent-factor assurance; both are possession-channel OTP methods, so do not claim independent-factor MFA without that review.
- Detailed first-admin recovery and break-glass controls, including approvers, separation of duties, audit and revocation.

### Implementation gates

- No protected user, partner, marketplace-admin, or provider-admin operation until the authentication/session foundation and relevant security tests are implemented.
- No production SMS delivery until vendor selection follows the required network tests and the owner explicitly authorizes production use.
- No privileged admin routes until mandatory additional-factor behavior, private first-admin provisioning, recovery, role authorization, and audit controls are approved, implemented, and tested.
- Partner Task 3 waits for Task 2.3 completion, production-capable OTP delivery testing/authorization, admin gates, and cross-user/cross-organization authorization tests.

## 1. Status vocabulary and evidence

- **Implemented:** present in executable repository code or schema and verified by source inspection.
- **Documented:** specified in an architecture/API/security document, without corresponding runtime behavior.
- **Proposed:** recommendation in this brief, ADR-0008, or partner marketplace proposals; not accepted merely by appearing here.
- **Absent:** no implementation was found in the inspected repository paths.

### 1.1 Identity schema inventory

The authoritative inspected definition is `engineering/database-prep/sql/001_core_schema.sql`.

| Item | Status | Observed contract and limitation |
|---|---|---|
| `identity.users` | Implemented schema | `user_id`, nullable `auth_subject`, `email`, `phone_e164`, `display_name`, `password_hash`, `account_status` (`active`, `disabled`, `pending_deletion`, `deleted`), synthetic flag and timestamps. A row requires at least email, phone, or auth subject. Email has a case-insensitive unique index. This does not prove that any value is verified or usable for login. |
| `identity.user_consents` | Implemented schema | User-linked consent type and policy version, grant/revoke timestamps, source, and synthetic flag. It is not a login/session store and does not define marketplace referral consent policy. |
| `identity.user_preferences` | Implemented schema | User-keyed preferences. It does not establish identity authentication or authorization. |
| Session, credential, recovery, OTP, magic-link, or MFA records | Absent | No session/token lifecycle schema was found in the current ERD/migrations. This brief does not propose a migration. |
| Partner organizations, membership, platform roles | Absent | No current partner tenancy/role model exists in the current ERD. ADR-0009 through ADR-0013 remain proposals. |

The nullable `password_hash` column is a storage affordance, not a choice of password login, password hashing algorithm, reset flow, or credential ownership. `auth_subject` is an external-subject mapping affordance, not a selected identity provider or federation contract. `phone_e164` is not proof of phone verification.

### 1.2 Backend, frontend, test, and deployment inventory

| Area | Status | Findings |
|---|---|---|
| Identity application module | Partially present as a seam | `backend/app/modules/identity/__init__.py` explicitly says authentication is gated by ADR-0006. No identity service, principal type, credential verifier, session repository, or authorization policy was found. |
| Runtime API | No authentication implemented | `backend/app/main.py` registers health and catalogue routers. Runtime request middleware assigns request IDs and redacts failures; it does not authenticate or authorize. The catalogue route uses a settings dependency, not a user-principal dependency. |
| API dependencies | No auth dependencies found | No OAuth2 bearer, HTTP bearer, cookie API-key, principal/current-user dependency, role dependency, or object-ownership dependency was found. FastAPI is installed; no authentication-specific package is declared in `pyproject.toml`/`uv.lock`. No provider or identity SDK was installed or contacted for this audit. |
| Settings/configuration | No auth settings | `backend/app/core/config.py` configures app/log/database settings and enforces the least-privilege DB role. It has no issuer, audience, cookie, session, signing, CSRF, OTP, email, or admin-bootstrap settings. |
| Frontend | No login/session flow found | The React PWA has locale and trip-intake behavior; no login, logout, account recovery, token storage, or protected-route behavior was found. The trip draft is explicitly client-transient and not sent or saved. |
| Tests | No authentication tests | `backend/tests/test_api.py` covers liveness, request IDs, readiness, settings role validation, redacted logging, and sanitized errors; catalogue tests cover its read boundary. No login, session, CSRF, revocation, recovery, role, admin bootstrap, or cross-object authorization tests exist. |
| OpenAPI | Documented future gate | `docs/api/openapi-mvp-v1.yaml` marks future user-owned routes as authentication-required and says the mechanism is unresolved. These declarations do not correspond to runtime user-data routes or auth handlers. |
| Security documentation | Documented requirements | `docs/security/SECURITY_PRIVACY_BOUNDARIES_v0.1.md` calls for server-derived identity, object-level authorization, secure session handling, rate limiting, and a separate provider admin boundary. |
| Deployment configuration | Development database only | Inspected deployment/container files include `engineering/database-prep/compose.yaml` and its PostgreSQL Dockerfile. They configure the local DB, not an application ingress, HTTPS/reverse proxy, app runtime, auth secrets, mail/SMS delivery, or administrator recovery channel. No deployed topology was accessed or inferred. |
| RAG/catalogue | Existing separate boundary | Destination publication reads and retrieval contracts remain separate from identity. No authentication change or partner logic may bypass production catalogue views or the owner's replaceable RAG boundary. |

No database was accessed. This is a source/configuration inventory only; it does not assert live database state or deployment behavior.

## 2. End-user authentication options (historical comparison before owner decision)

No provider availability, delivery pricing, or regional reachability is assumed. These must be checked against the owner-selected pilot geography, legal/privacy requirements, and actual delivery contracts before selection.

| Option | User experience | Implementation and recovery | Abuse/security considerations | Regional/operational dependency | Assessment for this product |
|---|---|---|---|---|---|
| Phone OTP | Familiar where phone identity is expected; no password to remember; requires access to the number at sign-in | Requires number verification, code lifecycle, resend/retry support, number-change and lost-number recovery; phone recycling and account linking must be handled | SMS pumping, brute force, SIM swap, number reassignment, interception, enumeration, and denial-of-wallet risks; strict rate limits, risk controls, code expiry/single use, and generic responses needed | Requires an approved delivery provider/route, sender registration where applicable, deliverability monitoring, cost controls, support for blocked/roaming numbers, and regional reachability verification | Viable only if phone-based onboarding is desired and delivery, recovery, cost, and SIM-swap risks are acceptable in the selected region |
| Email/password | Familiar and independent of OTP delivery after registration | Adds password creation, secure password hashing, reset, change, compromised-credential handling, and support. Recovery depends on secure email ownership | Credential stuffing, phishing, weak/reused passwords, brute force, reset-token theft; require established password hashing, rate limits, breach response, and generic errors | Requires email delivery for verification/recovery and mailbox reachability; no provider/cost assumed | Operationally self-contained at login but creates ongoing credential and recovery responsibilities |
| Email magic link | Low-friction sign-in without a memorized password | Requires secure one-time link/code issuance, expiry, replay prevention, account lifecycle, cross-device handling, and mailbox recovery | Mailbox compromise is account compromise; link forwarding, phishing, scanners/prefetch, replay, enumeration, and delivery abuse need mitigations | Requires reliable email delivery and safe link routing in PWA/deep-link contexts | Reduces password burden but makes email access and link handling central to account security |
| Federated identity | Convenient for users who already trust and can access a supported identity provider; may reduce credential handling | Requires OIDC/OAuth flow validation, callback and state/nonce handling, account linking, provider subject mapping, unlinking, and recovery when provider access is lost | Misconfigured callbacks, account-linking takeover, token handling, provider compromise, and overbroad profile scopes; use exact issuer/audience/nonce validation and minimal scopes | Provider accessibility, terms, regional reachability, privacy/data transfer, and stability are unknown until selected and tested | Could reduce first-party credential burden, but creates external dependency and account-linking policy requirements |
| Deliberately limited combination | Can offer a fallback or gradual migration if users have different access needs | More flows and support cases; linking, duplicate accounts, recovery precedence, and factor changes must be explicit | Multiple paths enlarge attack surface and can enable weaker-path account takeover; controls must be equivalent and recovery must not downgrade assurance | Every channel/provider must be verified for the target region and supported operationally | Recommend one primary method chosen by the owner, with no secondary method initially unless a measured access need justifies it; add a second method only with explicit account-linking and recovery rules |

### 2.1 Decision implications

**Technical facts:** Phone and email methods depend on external delivery channels for verification/recovery. Federated identity moves some authentication responsibility to an external issuer but does not remove application authorization obligations. Adding methods increases account-linking and recovery complexity.

**Assumptions:** The first client is a same-origin PWA. User access patterns, delivery providers, cost tolerances, and detailed legal/privacy requirements still require validation. The owner has selected domestic Iranian tourist scope; this does not establish delivery-provider reachability.

**Owner decisions recorded above:** Iranian phone OTP as the only initial method, E.164-compatible `+98` representation, PostgreSQL-backed opaque sessions in the specified cookie direction, independent scoped authorization, mandatory additional administrator authentication, and private one-time first-admin provisioning. **Still open:** vendors, operating parameters, recovery/account-linking rules, CSRF details, session lifetimes, and detailed administrator MFA/recovery policy.

## 3. Session architecture options (historical comparison before owner decision)

| Dimension | Secure HttpOnly cookie with server-managed session | Short-lived access token with refresh-token rotation |
|---|---|---|
| Browser exposure | `HttpOnly` prevents JavaScript from reading the session cookie; XSS can still issue authenticated same-origin actions while it runs | A bearer token readable by JavaScript can be stolen by XSS. Keeping access tokens in memory reduces persistence but does not stop active XSS. Avoid localStorage for long-lived credentials |
| CSRF | Browser attaches cookies automatically, so state-changing requests require CSRF defenses plus strict `SameSite`, origin and content-type policy; `SameSite` is defense-in-depth, not the sole check | Explicit Authorization header is less exposed to classic cross-site form CSRF if tokens are not ambient cookies; refresh credentials in cookies reintroduce CSRF considerations |
| Revocation | Server-side session lookup supports per-session logout, account-wide revocation, and membership/account-disable checks. Requires a server-side session store and defined outage behavior | Access token may remain valid until expiry unless each request checks revocation/version. Refresh rotation and reuse detection revoke token families but add storage and concurrency semantics |
| Expiration | Server can enforce idle and absolute expiry; cookie expiry should align but server remains authoritative | Access and refresh lifetimes must be chosen. Rotation, replay detection, token-family revocation, clock skew, and concurrent refresh races need policy and tests |
| Logout/account disable | Revoke server session(s), clear cookie, and invalidate relevant cached authorization. Account disable must block all sessions on subsequent checks | Revoke refresh family and clear client tokens; short access-token lifetime or online revocation check determines disable latency |
| Concurrent devices | Natural model of independent server-side sessions with device/session listing and individual revocation if approved | Multiple refresh-token families/devices need storage, enumeration, revocation, rotation, and recovery handling |
| React PWA compatibility | Strong fit for a same-origin PWA/API; browser manages cookie and JavaScript never handles credential value | Works across clients and separated origins but adds token lifecycle code and a decision about safe browser storage |
| Operational cost | Session storage availability, cleanup, key/cookie configuration, CSRF policy, and session monitoring | Token signing/verification key lifecycle, refresh store, rotation/reuse response, revocation policy, and potentially online lookups |
| Cross-origin/API clients | Same-origin deployment is simplest. Cross-origin credentials require exact CORS/origin/cookie configuration | Bearer tokens can suit multiple clients, but issuers/audiences/scopes and secure token distribution still need design |

### 3.1 Owner-approved session direction and open implementation details

The owner approved an **opaque, high-entropy server-managed session persisted in PostgreSQL**, delivered through a host-only `Secure`, `HttpOnly`, `SameSite=Lax` cookie and validated/revoked server-side. Do not add Redis without measured evidence and separate approval. Unsafe requests require CSRF defenses. Session lifetime, rotation triggers, device listing/revocation policy, exact CSRF mechanism, and deployment attributes beyond this baseline remain open.

This direction fits a same-origin React PWA and modular monolith because it keeps long-lived credentials out of JavaScript and makes server-side revocation straightforward. It does not prevent XSS from making requests as the user, so CSP/output safety and least-privilege APIs remain necessary. It does not prevent CSRF unless CSRF defenses are correctly implemented. If the owner prioritizes multiple native clients or cross-origin APIs, short-lived access tokens with rotated refresh credentials remain a viable alternative, subject to equivalent browser-storage and revocation protections.

Regardless of choice, identity comes from a validated session/token, never a body/query `user_id`. Apply owner checks to every object read/write/export/delete. Logout, account disablement, password/identity recovery, organization membership revocation, and admin role revocation must have defined effects on active sessions and authorization caches.

## 4. Administrator bootstrap and recovery

### 4.1 Distinct privileged principals

These are separate logical capabilities, not one universal “admin” flag:

| Principal/capability | Responsibility | Must not imply |
|---|---|---|
| Primary platform administrator | Establishes initial platform governance access, grants/revokes platform roles, oversees privileged access and recovery | Routine unrestricted access to traveler referral payloads or provider secrets by default |
| Marketplace verification reviewer | Reviews partner identity/evidence and records verification decisions for assigned cases | Content publishing, unrestricted platform role management, or provider administration |
| Content moderator/publisher | Reviews and publishes organization/service/offer content under policy | Self-approval, unrelated verification, or AI provider access |
| Partner organization owner/staff | Manages that organization’s scoped profile/content/referrals according to memberships | Other organizations’ records, platform-wide moderation, or traveler data without approved consent |
| AI Provider administrator | Manages provider profiles, model/capability configuration, secrets, activation, rollback and routing under ADR-0008 | Partner governance or personal referral access merely by holding provider authority |
| Traveler | Owns personal conversations/trips/preferences and controls any future disclosure | Partner or platform administrative access |

ADR-0008 requires the primary system administrator to be authenticated and authorized before managing the AI Provider Gateway. That provider-control privilege remains distinct from marketplace reviewer/publisher roles. Whether one human may hold multiple capabilities, and what separation-of-duties rules apply, require explicit owner approval.

### 4.2 First-administrator bootstrap options

| Option | Strengths | Risks/requirements | Recommendation status |
|---|---|---|---|
| Public “first user becomes admin” endpoint | Easy initial setup | Race-to-claim, internet exposure, deployment misconfiguration, and permanent privilege capture | Reject; prohibited by this brief |
| Hardcoded/default admin credential or shared account | Simple in a demo | Secret leakage, no attribution, difficult rotation/revocation, and unsafe recovery | Reject; prohibited |
| Direct database role/row edit | Can work during emergency operations | Bypasses application policy and may omit audit/verification; schema/role semantics are not designed | Not a routine bootstrap path; do not use without a separately approved and audited break-glass procedure |
| Operator-controlled one-time provisioning ceremony | Private, attributable, can avoid a public claim endpoint | Requires a secure operator channel, proofing of the intended identity, a controlled deployment procedure, audit, expiry/replay protection, and reliable disablement | Owner-approved boundary; exact command/deployment procedure, proofing, recovery, and audit details remain open |
| Pre-provisioned trusted identity-provider group/claim | Can centralize workforce identity and strong authentication | Depends on selected provider, issuer configuration, group lifecycle, outage/recovery, regional availability, and correct claim mapping | Viable alternative if an approved identity provider and organization policy are selected |

**Owner-approved boundary; implementation details open:** first-administrator provisioning is private, operator-controlled, and one-time. There must be no anonymous/public HTTP bootstrap path, default credentials, or hidden bypass. A named identity must be verified through the eventually approved authentication/MFA process; the owner has not selected whether the operator mechanism is a local command, deployment console action, or another private control, nor the detailed proofing, recovery, audit, expiry, or disablement procedure.

### 4.3 Recovery and emergency access options

- **Ordinary recovery:** Use the approved identity method’s verified recovery channel, require equivalent assurance to enrollment, notify the account through an independent channel where available, revoke affected sessions, and audit the event. Avoid knowledge-based questions and support-only identity overrides.
- **Primary administrator loss:** Viable options are a second pre-authorized administrator with tightly scoped recovery authority; a two-person operator-controlled recovery process; or an owner-controlled identity-provider group. The owner must select the organizational control. Recommended default is two-person approval, independently verified identity, time-limited elevation, mandatory session revocation, and retrospective review.
- **Emergency access:** If required, define named custodians, sealed/managed break-glass material or an equivalent controlled process, alerting on every use, minimum permissions, short duration, and post-event review. Do not create a permanent shared superuser or a bypass route. Whether emergency access exists at all is an owner/security decision.
- **Provider administration:** AI provider secret recovery, credential rotation, profile rollback, and gateway recovery remain governed by ADR-0008. Marketplace governance or partner ownership must not unlock provider secrets.

Bootstrap, recovery, and emergency-access choices are implementation gates for protected platform-admin and provider-admin functions. This brief does not select identity assurance levels, vendors, or secret-storage products.

## 5. Authorization boundaries and role model

### 5.1 Request-time invariants

1. Authentication establishes a principal; authorization separately checks a capability and target resource on every protected request.
2. Derive `user_id` and platform capabilities from validated server-side identity/session data. Never trust client-supplied actor, organization, owner, role, or reviewer IDs as authority.
3. Resolve an actor’s active partner memberships server-side. Every partner query and mutation is scoped to the permitted organization/resource relation. Deny cross-organization access even if the caller guesses a valid ID.
4. Recheck membership and account/organization status on protected access. Revocation and suspension must take effect within an owner-approved bound; avoid stale authorization caches unless invalidation semantics are proven.
5. Use explicit resource ownership checks in addition to route-level authentication. A logged-in user does not thereby own every `trip_id`, recommendation, referral, or organization ID supplied in a request.
6. Keep public catalogue projections separate from partner-private drafts and platform-admin evidence. Public reads return an allowlist of approved fields only.
7. Separate partner roles, marketplace governance roles, and AI Provider roles. No role grants another domain’s access implicitly.
8. Apply separation of duties: a partner submitter cannot approve/publish its own content; reviewer identity and privileged action are audited. Emergency overrides require a stated reason and review.
9. Treat invitation credentials, recovery links/codes, session credentials, provider secrets, and signing material as secrets: never place them in normal API responses, browser storage accessible to script, logs, analytics, or unrelated audit metadata.
10. Log security-relevant decisions and outcomes with actor, capability/scope, target, timestamp, correlation, and reason/policy version as appropriate; minimize personal payload and restrict audit readers.

### 5.2 Logical role separation (proposal)

| Boundary | Logical roles | Scope and checks |
|---|---|---|
| Traveler | Anonymous public visitor; authenticated traveler | Anonymous access limited to explicitly public/published content and currently accepted outbound actions. Authenticated traveler may access only own personal resources. No provider or marketplace admin capabilities. |
| Partner tenant | Organization owner, manager, catalogue editor, referral operator (only if leads approved) | Each membership is organization-scoped and revocable. Resource ownership and allowed actions checked per request. No cross-tenant inheritance from branch/brand relationships. |
| Marketplace governance | Verification reviewer, content moderator/publisher, platform governance administrator | Platform-wide authority is granted explicitly and least-privilege. Reviewer may access only assigned evidence/cases; publisher cannot approve own submission. Primary admin role assignment and emergency access are separate protected capabilities. |
| AI Provider control plane | AI Provider administrator under ADR-0008 | Separate protected control plane for provider/model profiles and secrets. No ordinary user, partner staff, or marketplace reviewer access by default. |

The role names and exact permission matrix in the [Partner Marketplace Domain Contract](PARTNER_MARKETPLACE_DOMAIN_CONTRACT_v1.0.md) remain proposed. No role is implemented in the current application.

## 6. Security risks and minimum mitigations

| Risk | Minimum mitigation before protected release |
|---|---|
| Account takeover, SIM swap, mailbox compromise, or identity-provider compromise | Select channel based on risk; rate limit and monitor; secure recovery; notify on sensitive changes; revoke sessions; define stronger assurance for privileged roles |
| Account linking takeover or duplicate identities | Link only after proving control of both the existing and new identity; define canonical account identifier, unlink/recovery behavior, conflict handling, and audit; do not merge by matching email/phone alone unless verified and policy-approved |
| OTP/magic-link abuse and enumeration | Generic responses, bounded issuance and verification attempts, resend cooldown, expiry/single use, abuse monitoring, and cost/rate controls |
| Password compromise | If password auth is selected, use a maintained password hashing scheme with parameters reviewed for deployment hardware, secure reset, credential-stuffing defenses, and no plaintext logging/storage; exact algorithm/library requires security review |
| XSS credential theft or action abuse | Prefer HttpOnly session credential; enforce output encoding, CSP and dependency hygiene; recognize XSS can still perform actions while active; never put long-lived bearer credentials in localStorage |
| CSRF against cookie session | CSRF token or equivalent robust defense for state-changing requests, strict origin validation, appropriate SameSite/Secure/host-only cookie settings, and tests; do not rely on SameSite alone |
| Broken object/tenant authorization | Server-derived principal; per-operation ownership and active membership checks; deny-by-default queries; negative tests for guessed IDs and cross-organization reads/writes |
| Stale sessions after logout, account disablement, role revocation, or membership suspension | Server-side revocation/versioning; recheck high-risk state; defined cache invalidation; tests for existing sessions after each revocation event |
| Admin bootstrap takeover | No public bootstrap route or default credentials; operator-controlled one-time process, verified target, expiry/replay protection, audit, disablement, and recovery procedure |
| Privilege aggregation and insider misuse | Separate marketplace and provider capabilities; least privilege, reviewer assignment, separation of duties, time-bounded elevation where justified, periodic access review, and tamper-resistant audit operations |
| Invitation/recovery credential leakage | One-time/short-lived policy, recipient-bound use, no token in lists/responses/logs/analytics, redacted audit, and revocation on membership or account change; mechanism remains for ADR-0006/security review |
| Secret exposure in logs/config/browser | Secret management chosen before deployment; configuration redaction; allowlisted structured logging; no auth/provider tokens in URLs, client bundles, analytics, or error responses |
| Deployment origin/proxy misconfiguration | Production HTTPS, trusted proxy configuration, secure headers, exact origin/CORS policy, cookie scope review, no mixed-content paths, and deployment-level tests |

## 7. Accepted baseline and proposed technical details

1. **Accepted:** Iranian `+98` phone OTP via a provider-neutral SMS adapter is the sole initial login method; other login methods and international authentication are deferred.
2. **Accepted:** sessions are opaque, high-entropy, server-managed, PostgreSQL-backed and delivered in a host-only `Secure`, `HttpOnly`, `SameSite=Lax` cookie. No Redis without separate approval.
3. **Accepted:** identity and permissions are server-derived; traveler, partner membership, marketplace governance, and AI Provider administration are distinct scoped capabilities with object/tenant checks.
4. **Accepted:** privileged administrator operations require additional authentication; TOTP is preferred for evaluation, with detailed MFA lifecycle open. First-admin provisioning is private, operator-controlled, and one-time.
5. **Proposed technical default:** use the same-origin PWA/API where practical; this is not an existing deployment fact and needs deployment review.
6. **Proposed technical default:** use a synchronizer CSRF token held server-side and in client memory, sent in a custom header, and validate Origin on unsafe requests. Exact mechanism remains open for security review.
7. **Open:** OTP parameters, SMS provider, session lifetimes/rotation, CSRF deployment details, phone recovery/replacement, TOTP lifecycle, and first-admin recovery/break-glass controls.
8. **Required boundary:** no anonymous user-data routes, referral leads remain outside ADR-0007, and no provider-admin route is exposed until ADR-0008's separate gates pass. Catalogue and RAG boundaries remain unchanged.

The cookie-session direction aligns with a browser-first PWA, keeps the session credential out of JavaScript, and provides a server-side revocation point. It does not select an identity/SMS vendor. A bearer/refresh architecture is not the approved initial direction; revisit only through an explicit owner decision if client topology changes.

## 8. Remaining owner decisions and implementation checklist

### 8.1 Unresolved decisions required before production authentication or privileged access

- [ ] Select SMS vendor/routes/terms and approve representative MCI, Irancell, and Rightel delivery results before production SMS.
- [ ] Approve OTP digits, validity, attempt/resend budgets and rate-limit dimensions; six digits/five minutes/five failures/60 seconds remain proposed defaults.
- [ ] Set session idle/absolute expiry, rotation triggers, multi-device policy, and PostgreSQL retention/cleanup.
- [ ] Approve exact CSRF mechanism, Origin/Referer checks, trusted-proxy/TLS configuration, and cookie deployment settings.
- [ ] Decide lost-phone recovery, phone replacement/reassignment, duplicate account, and account linking. No self-service path is approved.
- [ ] Approve administrator TOTP enrollment, recovery, backup-code, device replacement, and intended factor assurance. Confirm whether two possession-channel OTP mechanisms meet the intended MFA requirement.
- [ ] Define first-admin recovery, approvers, audit, emergency/break-glass policy, and post-use review.
- [ ] Approve privacy notice, data retention/deletion, support/incident ownership, audit access, and required operational controls.

High-level choices already accepted by the owner are listed in the outcome section; they are not reopened by this checklist.

### 8.2 Infrastructure and implementation prerequisites

- Deployment topology identifies the public origin, TLS termination, trusted proxy headers, and same-origin routing. Current repository configuration only documents a local database container; it does not satisfy this prerequisite.
- Secret/configuration handling is defined for identity-client secrets, session secrets if any, email/SMS credentials, and provider secrets; values are never committed, logged, or sent to the PWA.
- Database/session persistence and migration ownership are defined without using the owner role for application runtime. Required app-role grants and retention/deletion semantics are tested in an isolated environment before any shared DB application.
- Structured audit sink and operational access are available; failures do not silently grant access or leak secrets.
- Abuse controls include per-account/per-destination/network limits and monitoring, with privacy-preserving telemetry and an operational response owner.
- Automated tests use fake identity/delivery adapters; no paid or real provider calls occur by default.

### 8.3 Features that may be deferred after secure baseline

Subject to threat/risk approval, the following may be deferred without weakening the minimum gates: multiple federated providers, self-service linking of several identities, social login, advanced device analytics, broad admin analytics, automated partner-feed identities, sophisticated risk scoring, and a multi-region session topology. Passwordless/passkey options are not analyzed here because they are outside the requested comparison; they require a separate decision if considered.

Do not defer object-level authorization, tenant isolation, session revocation/disablement, recovery ownership, secure admin bootstrap, secret redaction, rate limiting for selected login flows, or tests for privileged boundaries.

## 9. Task 3 readiness verdict

### Verdict: **High-level decisions accepted; Task 3 remains blocked pending Task 2.3**

The repository has an identity schema seam, least-privilege database configuration, request-ID/error-redaction middleware, health routes, and documentation stating the security gates. It still does not have an authentication flow, authenticated principal, authorization dependencies, session lifecycle, admin MFA/bootstrap implementation, or corresponding tests. The owner has accepted the high-level initial authentication/session decisions and ADR-0006 is being updated accordingly; implementation and operational gates remain. ADR-0008 continues to gate provider control on approved admin MFA, authorization, bootstrap, and recovery. The partner-marketplace ADRs remain proposals.

| Task 3 capability | Required before implementation | May be designed/deferred |
|---|---|---|
| Organizations | ADR-0006 identity/session and principal semantics; tenant owner; cross-org deny-by-default policy; organization state/verification policy; audit requirements; isolated test plan | Full partner self-service UI; branch/brand complexity beyond approved pilot; automated legal verification feeds |
| Memberships and roles | Approved role/action matrix; invitation recipient and expiry policy; credential secrecy; acceptance/revocation/suspension and immediate effect; owner/admin recovery; dual-role account-linking policy | Multi-identity linking; advanced membership analytics; delegated administration beyond pilot |
| Verification cases | Evidence categories and privacy/retention; reviewer assignment and separation of duties; outcome/reason/policy-version audit; appeal/re-review/suspension policy | Automated evidence checks; third-party verification providers; advanced reviewer queues |
| Audit events | Actor identity/capability/tenant/resource/action/time/result/correlation/reason policy; redaction and retention; restricted audit access; tamper/availability expectations | Analytics dashboards and long-term reporting beyond security/operational needs |
| Cross-organization isolation tests | Authenticated test principals/memberships; positive same-org and negative other-org/guessed-ID cases; revoked/suspended membership tests; public-field projection tests; admin role boundary tests | Load/performance tests beyond expected pilot scale; broader fuzzing can follow the initial adversarial suite |

**Readiness gate:** Task 3 must wait until ADR-0006 is accepted, Task 2.3 authentication/session implementation and required security tests are complete, an owner-approved production-capable OTP path is tested and authorized, admin bootstrap/MFA/recovery/authorization gates are satisfied, and cross-user/cross-organization authorization tests pass. No protected route is authorized by this brief. Do not start Task 3 automatically.

## 10. Open questions for the owner

1. What is the first pilot geography and which user identity/contact channels are reliable and appropriate there?
2. Is one primary sign-in method sufficient for the initial product, and what accessibility or account-recovery requirements demand another method?
3. Should traveler and partner staff identities share an account subject with separate scoped grants, or use separate identity realms? What account-linking proof is acceptable?
4. What session lifetime, concurrent-device, and revocation behavior is required for traveler, partner, marketplace admin, and AI Provider admin capabilities?
5. Who is authorized to nominate and verify the first primary platform administrator, and what two-person or organizational controls apply?
6. Who can grant/revoke verification, moderation, publisher, security-admin, and provider-admin roles? Which combinations require separation of duties?
7. Is emergency access required? If yes, who holds it, how is it protected, and what post-use review is mandatory?
8. What audit and personal-data retention periods, deletion process, privacy notice, and incident support ownership apply?
9. What hosting/origin/TLS/proxy topology will support same-origin cookies and CSRF defenses? The current local database Compose file does not answer this.
10. Do partner referrals remain out of scope under ADR-0007, or will the owner consider a separate consent/retention and ADR amendment decision?

## 11. Source references

- [ADR-0006 — Authentication and Session Strategy](decisions/ADR-0006-authentication-and-session.md) — open owner decision and implementation gate.
- [ADR-0008 — Centralized AI Provider Gateway](decisions/ADR-0008-centralized-ai-provider-management.md) — accepted provider-management requirement with protected admin-auth gate.
- [Repository instructions](../../AGENTS.md) — modular-monolith, trust, privacy, least-privilege, and delivery boundaries.
- [MVP Codex Handoff v0.5](../implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.5.md) — current product scope, authentication phase gate, deployment and provider constraints.
- [Partner Marketplace Architecture](PARTNER_MARKETPLACE_AND_ADMIN_PLATFORM_ARCHITECTURE_v1.0.md) — proposed partner and governance domains; remains unaccepted.
- [Partner Marketplace Domain Contract](PARTNER_MARKETPLACE_DOMAIN_CONTRACT_v1.0.md) — proposed lifecycles and role matrix; remains unaccepted.
- [OpenAPI MVP draft](../api/openapi-mvp-v1.yaml) — future auth annotations, not runtime authentication.
- [Security and Privacy Boundaries](../security/SECURITY_PRIVACY_BOUNDARIES_v0.1.md) — server-derived identity, object checks, secure sessions, and privacy gates.
- [Current MVP ERD](ERD_MVP_v0.1.md) and `engineering/database-prep/sql/001_core_schema.sql` — current identity columns and the absence of implemented auth/session/partner-role aggregates.

## 12. Decision gate and next approval

The owner-approved high-level choices are recorded above and in ADR-0006; unresolved operating, recovery, MFA-assurance, CSRF, and deployment details remain open. ADR-0008 remains unchanged and authoritative for AI Provider Gateway administration. The owner should review the [implementation contract](AUTHENTICATION_SESSION_AND_ADMIN_BOOTSTRAP_IMPLEMENTATION_CONTRACT_v1.0.md), resolve its production and privileged-access gates, and separately authorize Task 2.3. Task 3 remains blocked until Task 2.3 and the roadmap prerequisites are complete. This brief does not authorize implementation.
