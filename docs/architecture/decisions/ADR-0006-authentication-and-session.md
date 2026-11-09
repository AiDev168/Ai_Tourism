# ADR-0006: Authentication and Session Strategy

- **Status:** Accepted for the initial domestic MVP; implementation remains subject to the execution and security gates below.
- **Decision date:** 2026-11-07 (initial owner choices); implementation/security details remain gated
- **Sources:** Owner-approved authentication decisions dated 2026-11-07; `docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.5.md`; current `identity.users` schema.
- **Implementation contract:** [Authentication, Session, and Administrator Bootstrap Implementation Contract v1.0](../AUTHENTICATION_SESSION_AND_ADMIN_BOOTSTRAP_IMPLEMENTATION_CONTRACT_v1.0.md)

## Context

The initial release targets tourists travelling inside Iran. Identity schema flexibility is not itself an authentication decision. The owner has approved the initial authentication and high-level session direction below; operational parameters, recovery details, and deployment/security controls remain open and are implementation gates.

## Accepted owner decisions (2026-11-07)

1. **Geography and phone representation:** initial authentication supports Iranian mobile numbers using `+98`; international tourist authentication is outside the initial release. Store/canonicalize phone identifiers in an E.164-compatible form so future international expansion does not require replacing the identity representation.
2. **Initial login:** phone OTP delivered by SMS is the primary and only initial login method. Email/password, email magic links, and federated login are deferred.
3. **Verification meaning:** a phone is verified only after successful OTP verification. Presence of `phone_e164` in `identity.users` alone is not verification. Phone verification does not prove legal identity, age, company ownership, or partner legitimacy.
4. **Delivery boundary:** SMS delivery is behind a provider-neutral adapter. No vendor or production credentials are selected. Normal automated tests use a deterministic fake adapter. Production vendor selection requires representative delivery testing with MCI, Irancell, and Rightel and review of deliverability, cost, rate limits, operational support, and recovery impact. No SMS call is authorized by this ADR alone.
5. **Session direction:** use an opaque, high-entropy, server-managed session persisted in PostgreSQL, conveyed by a host-only browser cookie with `Secure`, `HttpOnly`, and `SameSite=Lax`. Validate, expire, log out, and revoke sessions server-side. Do not put long-lived session credentials in `localStorage` or other JavaScript-readable browser storage. Do not add Redis for sessions without measured need and separate owner approval.
6. **CSRF:** unsafe cookie-authenticated requests require explicit CSRF defenses. The specific mechanism and its deployment settings remain subject to the implementation/security review; see the implementation contract for the proposed technical default and tests.
7. **Identity and authorization:** a traveler and partner employee may share one underlying user identity, but traveler permissions and partner capabilities are independently granted. Partner permissions require explicit organization membership and role assignment. The backend derives identity and scope from validated server state; client-supplied `user_id`, `organization_id`, role, or admin flags never establish authority. Enforce object ownership and tenant boundaries server-side.
8. **Privilege separation:** traveler permissions, partner memberships, marketplace governance, primary platform administration, and AI Provider administration are distinct authorization capabilities. A marketplace or partner administrator does not thereby receive AI Provider administration. [ADR-0008](ADR-0008-centralized-ai-provider-management.md) remains authoritative for AI Provider Gateway administration; only an authenticated and authorized primary system administrator may manage it, subject to ADR-0008's controls.
9. **Administrator assurance:** privileged administrator operations require a second authentication factor; passwordless/OTP access alone is insufficient. TOTP is the preferred candidate, but enrollment, recovery, backup-code, and device-replacement policies are not yet approved. No protected administrator route may be exposed before MFA, authorization, bootstrap, and recovery controls are approved, implemented, and tested.
10. **First administrator:** provisioning must be private, operator-controlled, and one-time. No public first-user claim endpoint, hardcoded/default credentials, anonymous access, or shared administrator account. Detailed ceremony, recovery, and emergency-access procedures remain open.

## Deferred authentication methods

Email/password, email magic links, and federated identity are not part of the initial release. Adding a method later requires a separate review of account linking, recovery, security parity, delivery/issuer dependencies, and owner approval. International tourist login is also deferred, although the phone representation remains E.164-compatible.

## Remaining owner decisions and implementation gates

- SMS vendor, sender/route, production credentials, commercial terms, and successful representative network delivery testing.
- OTP defaults: six digits, five-minute validity, five failed attempts, and a 60-second resend interval are proposed starting values only, not immutable approved settings.
- OTP issuance/verification rate limits and global abuse budgets must be security-reviewed and configured before real SMS is enabled.
- Session idle/absolute lifetime, rotation triggers, concurrent-device policy, and retention/cleanup.
- Exact CSRF mechanism, trusted-origin/Referer policy, cookie deployment details, TLS termination, and proxy trust.
- Traveler recovery after loss of the registered phone, phone replacement/reassignment, and duplicate/account-linking behavior. No self-service recovery flow is implied.
- Exact administrator TOTP enrollment, factor-independence assurance, recovery, backup-code, and device-replacement policy.
- Security confirmation that the selected administrator step-up satisfies the intended factor assurance; SMS OTP and TOTP are both possession-channel OTP methods.
- Detailed first-administrator recovery and break-glass process, including authority, separation of duties, audit, and revocation.

The implementation sequence and acceptance tests are specified in the [authentication implementation contract](../AUTHENTICATION_SESSION_AND_ADMIN_BOOTSTRAP_IMPLEMENTATION_CONTRACT_v1.0.md). These open items must not be silently filled by an implementation default.

## Options considered before owner decision

| Option | Advantages | Questions / costs |
|---|---|---|
| Phone OTP | Familiar in some target markets; phone-based identity | SMS provider, delivery reliability, cost, SIM-swap/account-recovery risks and regional availability |
| Email/password or email magic link | Broad provider choice; no SMS dependency for every login | Email delivery, password security or link expiry, account recovery and abuse prevention |
| Federated identity | Less password handling | Provider availability, account linking, data transfer and region compatibility |

The owner selected the PostgreSQL-backed server-managed session and secure-cookie direction above for the initial PWA. Carefully scoped short-lived access tokens with refresh-token rotation are not the initial session architecture; reconsider only through an explicit owner decision if client topology materially changes.

## Required security invariants (independent of the selected mechanism)

1. Every user-owned resource is protected by authentication and object-level authorization.
2. User identity is derived from the validated server-side session/token, never trusted from a client-supplied `user_id`.
3. A user cannot read or mutate another user's profile, conversations, trips, itineraries, feedback or click history.
4. Session expiry, logout, revocation, credential recovery and account disablement have explicit behavior.
5. Browser storage must not contain provider secrets or long-lived credentials that are accessible to script.
6. Rate limits and abuse controls protect login, OTP/magic-link issuance, message submission and expensive provider calls.
7. The administrator interface for AI provider management requires a separately approved administrator authentication and authorization policy. Ordinary-user identity and anonymous sessions never imply administrative access; no provider-management route may ship before the admin policy is accepted and tested.

## Implementation gate

The high-level choices in this ADR are accepted, but no authentication/session implementation is present by acceptance of this document. Before protected user, partner, marketplace-admin, or AI Provider routes are exposed, implement the authentication/session foundation from the linked contract and pass its required tests, including OTP security, PostgreSQL session lifecycle, CSRF, logout/revocation, account disablement, server-derived authorization, and cross-user/cross-organization isolation.

The partner foundation (roadmap Task 3) cannot begin until that authentication/session foundation and required security tests are complete. Production OTP delivery additionally requires owner-approved vendor selection after representative Iranian network testing and explicit production authorization. Privileged operations additionally require approved and tested administrator MFA, private first-admin provisioning, authorization, and recovery controls. Until then, expose only infrastructure/publication-gated routes that do not reveal protected user or admin data; do not use placeholder authentication.
