# ADR-0006: Authentication and Session Strategy

- **Status:** Open — owner decision required before authenticated API implementation
- **Decision date:** 2026-11-05
- **Sources:** `docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.3.md` sections 5.1, 9–11 and 17; current `identity.users` schema.

## Context

The schema can associate an identity with `auth_subject`, `email`, `phone_e164` or a password hash. Schema flexibility is not a product decision. The project has not selected an authentication method, identity provider, verification channel, session format, refresh/revocation behavior or account recovery workflow.

## Options to evaluate

| Option | Advantages | Questions / costs |
|---|---|---|
| Phone OTP | Familiar in some target markets; phone-based identity | SMS provider, delivery reliability, cost, SIM-swap/account-recovery risks and regional availability |
| Email/password or email magic link | Broad provider choice; no SMS dependency for every login | Email delivery, password security or link expiry, account recovery and abuse prevention |
| Federated identity | Less password handling | Provider availability, account linking, data transfer and region compatibility |

Session options to compare include secure `HttpOnly` cookies with appropriate `Secure`/`SameSite`/CSRF controls versus carefully scoped short-lived access tokens and refresh-token rotation. Do not select one only because it is convenient for a sample implementation.

## Required security invariants (independent of the selected mechanism)

1. Every user-owned resource is protected by authentication and object-level authorization.
2. User identity is derived from the validated server-side session/token, never trusted from a client-supplied `user_id`.
3. A user cannot read or mutate another user's profile, conversations, trips, itineraries, feedback or click history.
4. Session expiry, logout, revocation, credential recovery and account disablement have explicit behavior.
5. Browser storage must not contain provider secrets or long-lived credentials that are accessible to script.
6. Rate limits and abuse controls protect login, OTP/magic-link issuance, message submission and expensive provider calls.

## Open owner decisions

- Phone OTP, email, federated login or a deliberate combination;
- identity/OTP/email provider and regional reachability;
- cookie-session vs token-based session;
- account linking, recovery, logout and revocation behavior;
- minimum account/profile fields and consent categories.

## Implementation gate

Until this ADR is accepted, implement only infrastructure endpoints that do not expose user data (for example, liveness/readiness). Authenticated API routes may be documented as draft, but must not be exposed as anonymous endpoints or shipped with placeholder authentication.
