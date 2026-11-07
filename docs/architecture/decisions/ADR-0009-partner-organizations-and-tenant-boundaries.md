# ADR-0009: Partner Organizations and Tenant Boundaries

- **Status:** Proposed — Owner Decision Required
- **Decision date:** Not accepted
- **Scope:** Logical organization, membership, tenancy, and audit requirements for a future partner marketplace
- **Related:** [Marketplace decision package](../PARTNER_MARKETPLACE_ARCHITECTURE_DECISION_PACKAGE_v1.0.md), [marketplace architecture proposal](../PARTNER_MARKETPLACE_AND_ADMIN_PLATFORM_ARCHITECTURE_v1.0.md), [ADR-0006](ADR-0006-authentication-and-session.md), [current ERD](../ERD_MVP_v0.1.md)

## Context

The current physical ERD documents identity and user-owned travel data, but no partner organization, branch, staff membership, or tenant domain. This proposal defines logical boundaries only. It does not claim those entities or controls exist, and it does not prescribe tables or migrations.

ADR-0006 remains open. An organization model cannot make protected partner functionality safe without an approved authentication/session design and separately specified authorization behavior.

## Decision drivers

- Prevent access across partner organizations, including through guessed or substituted identifiers.
- Support a company with branches, brands, or related operating entities without assuming they share legal ownership or permissions.
- Make membership lifecycle and privileged actions auditable.
- Keep traveler identities and partner staff identities distinct in authorization, even if a person could hold both roles.
- Preserve a modular monolith and the least-privilege database boundary.

## Options considered

| Option | Benefits | Costs and risks |
|---|---|---|
| One organization record with informal shared logins | Small initial operational burden | No individual accountability, weak revocation, and poor tenant isolation |
| Organizations with explicit individual memberships and scoped roles | Clear ownership, revocation, and audit; supports multiple organizations per person | Requires authentication, invitation lifecycle, role policy, and careful object-level checks |
| Separate partner identity system or service | Could isolate a large partner ecosystem | Premature infrastructure and identity duplication for the current modular monolith |

## Proposed decision

Adopt the second option as the recommended logical direction, subject to owner approval:

1. A partner organization is the tenant boundary and owns partner-managed profiles, services, offers, schedules, and referrals according to explicit policies.
2. Organization lifecycle should distinguish at least application/review, verified, active, suspended, and closed states. Verification and participation status are separate. Verification does not publish services or offers.
3. Branches are subordinate operating locations. Brands and related companies require explicit, reviewed relationships with declared relationship type and scope; they do not inherit access automatically.
4. Each staff member has an individual account and explicit membership in each organization. Recommended least-privilege roles are owner, manager, catalogue editor, and referral operator. Permissions should be action-based; role names alone are not authorization checks.
5. Invitation acceptance must be attributable to the invited identity and organization. Invitations expire and are single-use. Membership revocation removes access promptly and retains appropriate audit history. Account suspension blocks authentication or protected actions according to the future identity policy; it must not silently erase organization data.
6. Every request derives the actor from a validated server-side principal. The backend resolves tenant membership and resource ownership; client-supplied organization IDs are selectors at most, never authority.
7. Cross-organization reads and writes are denied by default. Explicit shared-brand or group access requires an approved relationship and narrow capability; no implicit parent/child inheritance.
8. Traveler and partner roles are separate authorization grants. A person may have both only through explicit, independently checked role assignments. Traveler-owned trip data is not visible to a partner by virtue of staff membership.
9. Audit organization creation/status changes, invitations, membership grants/revocations, role changes, verification decisions, sensitive reads where policy requires, and administrative overrides. Record actor, target, action, timestamp, result, reason/reference, and policy version while minimizing personal payloads.
10. Keep partner identity and authorization inside the modular monolith initially. Do not create a separate identity service without measured need and owner approval.

## Consequences

- **Security/privacy:** Partner functions require authentication, per-request tenant resolution, object-level authorization, anti-enumeration behavior, and auditable privilege changes. Public partner content must be an explicit allowlist, not ORM serialization.
- **Operations:** Staff invitations, account recovery, ownership changes, organization closure, and emergency suspension need support procedures.
- **Migration:** No schema change is authorized by this proposal. The current ERD has no partner tenancy model. Any physical model requires a later reviewed design and isolated migration tests.
- **Compatibility:** This extends the product beyond the existing public catalogue and link-only MVP. Scope expansion requires explicit approval and reconciliation with ADR-0007.

## Open owner decisions

- Whether an individual can belong to multiple organizations and hold traveler and staff roles under one identity.
- Whether brands and related legal entities are in pilot scope, and which relationship types confer any shared permissions.
- Which membership roles and actions are required for the initial pilot.
- Who may invite the first owner, recover ownership, and suspend an organization.
- Organization evidence and identity verification policy by target geography.
- Audit retention, privileged-read logging, and appeal access policy.
- Whether invitations require administrator review or organization-owner approval.

## Implementation gate

Do not implement protected partner routes, invitations, memberships, tenant data, or partner UI until ADR-0006 authentication/session choices are accepted and the authorization matrix, administrator bootstrap/recovery, organization verification, privacy, and audit policies are approved. No placeholder authentication or admin bypass is permitted. Follow-up physical data design requires owner review; this ADR does not authorize tables or migrations.

## Revisit conditions

Revisit before the first partner onboarding pilot, if the selected identity design cannot safely support dual roles or membership revocation, or if evidence demonstrates a need for separate legal-entity/brand tenancy.
