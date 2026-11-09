# ADR-0013: Partner and Platform Administration Governance

- **Status:** Proposed — Owner Decision Required
- **Decision date:** Not accepted
- **Scope:** Logical partner workspace, platform review, and privileged governance requirements
- **Related:** [Marketplace decision package](../PARTNER_MARKETPLACE_ARCHITECTURE_DECISION_PACKAGE_v1.0.md), [marketplace architecture proposal](../PARTNER_MARKETPLACE_AND_ADMIN_PLATFORM_ARCHITECTURE_v1.0.md), [ADR-0006](ADR-0006-authentication-and-session.md), [ADR-0008](ADR-0008-centralized-ai-provider-management.md), [ADR-0009](ADR-0009-partner-organizations-and-tenant-boundaries.md)

## Context

The marketplace proposal includes a partner workspace and platform administration, neither of which exists in the current runtime. ADR-0006 remains open for authentication/session design. ADR-0008 separately governs the AI Provider Gateway and administrator control plane; marketplace review privileges must not imply AI provider privileges.

## Decision drivers

- Separate partner self-service from platform review and privileged administration.
- Enforce organization scope for partner actors and least privilege for platform staff.
- Make verification, moderation, publication, suspension, and appeal decisions traceable.
- Avoid protected routes without an accepted identity and authorization design.
- Keep AI infrastructure administration separate from commercial/content governance.

## Options considered

| Option | Benefits | Costs and risks |
|---|---|---|
| One shared admin interface and broad administrator role | Simple initial UX | Excessive privilege and unclear audit ownership; can expose provider controls to marketplace reviewers |
| Separate partner workspace, platform governance, and AI provider control plane | Clear scope and privilege boundaries | Requires explicit role matrix and separate authorization testing |
| Build public/admin surfaces with temporary or placeholder authentication | Fast mock demonstration | Creates unsafe routes and false assurance; explicitly unacceptable |

## Proposed decision

Recommend three logically distinct surfaces/authority sets within the modular monolith:

1. **Partner workspace:** organization-scoped profile, staff, service/offer draft and submission, update/pause, and consented referral operations. It cannot approve its own verification or publish content requiring platform review.
2. **Platform governance:** partner application and evidence review, organization verification/suspension, service and offer moderation/publication, taxonomy and freshness policy administration, appeals, referral oversight, and platform audit/reporting. Each action has explicit permission and reason requirements.
3. **AI Provider administration:** remains the separate ADR-0008 control plane for provider profiles, secrets, activation, routing, and rollback. Marketplace/platform reviewers receive no provider capability by default; provider administrators do not automatically receive partner-lead data access.
4. **Workflow controls:** organization verification, service/offer moderation, publication, suspension, and appeal are distinct states and decisions. The author of submitted content cannot approve that content; emergency suspension and reinstatement require auditable reasons and review paths.
5. **Permission scope:** partner grants are constrained to memberships and organization-owned records under ADR-0009. Platform-wide actions are separately granted, least-privilege, time-bounded where feasible, and checked on every request. No role is inferred from a URL, email domain, or client field.
6. **Audit:** record actor, authority scope, action, resource, timestamp, result, reason, before/after non-sensitive metadata, and policy version for privileged operations. Protect evidence and referral payloads with stricter access than public content.
7. **Appeals:** rejected/suspended organizations and content need an owner-approved process, status visibility, reviewer separation where practical, and preserved decision history.
8. **No implementation shortcut:** logical roles may be documented, but no protected route, placeholder login, anonymous admin endpoint, backdoor, or bypass is authorized.

## Consequences

- **Security/privacy:** Admin and partner permissions need independent positive/negative tests, tenant isolation, privileged-operation audit, and data minimization.
- **Operations:** Define reviewer staffing, escalation, evidence retention, appeals, emergency suspension, and access reviews.
- **AI separation:** This proposal does not weaken ADR-0008. Partner administration cannot configure models, endpoints, keys, fallback, or provider routing.
- **Migration:** No role tables, admin pages, or protected routes are authorized. No current implementation should be inferred from this logical proposal.

## Open owner decisions

- Platform roles and exact action matrix, including who can verify, publish, suspend, and reinstate.
- Separation-of-duties requirements and emergency override policy.
- Reviewer evidence access, retention, appeal deadlines, and dispute process.
- Administrator bootstrap, recovery, strong-authentication, and audit review design (must be resolved through relevant ADR-0006 decisions).
- Whether partner workspace and governance are one PWA with protected routes or separate deployment surfaces; no separate service is implied.
- Which roles may access aggregate referral metrics and whether personal lead data is needed for each role.

## Implementation gate

ADR-0006 authentication/session and the relevant authorization, administrator bootstrap/recovery, and audit decisions must be approved before any partner or platform-admin route or UI is implemented. ADR-0008 remains the independent gate for provider administration. This document does not create an admin bypass or authorize protected functionality.

## Revisit conditions

Revisit before the first partner/admin workflow, after a security review identifies role conflicts, or when organizational scale provides evidence for a separate administrative deployment.
