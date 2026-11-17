# Partner Data Contract — Logical and Physical Proposal

**Status:** Design proposal only. No partner table, route, role, permission or migration is approved by this package. ADR-0009 through ADR-0013 remain `Proposed — Owner Decision Required`; ADR-0006 authentication/session choices must also be settled before protected partner work.

## 1. Reuse and scope

Reuse `knowledge.destinations` as the canonical national catalogue; partner records may associate to a reviewed canonical destination but may not create/own/publish a second destination identity. Reuse `identity.users` for individual accounts and existing `operations.audit_events` where its contract supports partner actions. Reuse `integration.external_links`/`integration.outbound_clicks` for current allowlisted outbound link behavior. Do not interpret a click as a lead, referral, booking, payment, or partner conversion. No referral/lead tables are in this Stage 2A physical proposal because ADR-0012 explicitly needs a separate owner decision and ADR-0007 amendment if that feature is desired.

Proposed schema is `partner`. Partner tenants are organizations; branches, services, offers, schedules and availability all have explicit `organization_id`. All rows are draft/private unless a publication projection allowlists reviewed fields. Organization verification, participation status, service moderation and publication are separate state machines.

## 2. Logical/physical entities

The normative columns, types, nullability, unique constraints, owner and privacy class are specified in `DATA_DICTIONARY.md` §2.4. This section fixes relations and authorization rules:

| Entity | Relation/owner | Public exposure rule |
|---|---|---|
| Organization | Partner tenant; legal and display identity are distinct | Only reviewed display name and expressly approved profile fields; never legal identifiers by default |
| Membership | Individual `identity.users` membership scoped to one organization | Never public; action permission is matrix-based, not role-name-only |
| Invitation | Organization-scoped, single-use expiring enrollment | Token hash only; email digest/identity data restricted |
| Verification case | Organization application plus restricted evidence references and independent decision | Only approved verification status/badge, never raw evidence |
| Branch | Operating location owned by organization | Per-field review; address/contact and precise location default private |
| Service | Partner-owned service draft linked to optional same-tenant branch | Explicit reviewed allowlist; not a destination record |
| Service localization | Service name and description by supported locale | Locale row only after content review/policy; no automatic factual promotion |
| Service/destination association | Many-to-many explicit relevance relation to existing canonical destination | Public only after partner claim and platform review; relation type distinguishes “at”, “serves”, “near”, route endpoint |
| Offer | Commercial proposal for an organization-owned service, versioned validity | Published only after organization/service/offer gates; no reservation or inventory guarantee |
| Price | Immutable price observations and states, preserving currency and denomination | Return exact approved amount/currency/unit/tax state and timestamp; never convert IRR/Toman implicitly |
| Schedule | Service schedule with IANA time zone where local time applies | Only reviewed and current schedule; unknown is not closed/open |
| Availability snapshot | Immutable currentness observation for one offer | `unknown`/stale never becomes available; no booking semantics |

The physical design uses composite same-tenant keys: child tables store `organization_id`; parent tables expose `UNIQUE (organization_id, child_id)`; composite foreign keys ensure an offer cannot reference a service from a different organization, a service cannot reference another tenant's branch, and an association cannot be attached to a service outside its owner. Use `ON DELETE RESTRICT`; use lifecycle status/withdrawal and retention policy rather than cascaded deletion of evidence/audit.

## 3. Authorization model

### 3.1 Server-side tenant resolution

1. Authenticate the individual through the accepted ADR-0006 mechanism; derive `user_id` only from the validated server-side principal.
2. For each request, query active membership for `(principal.user_id, requested organization selector)`. An organization ID in a URL/body is only a selector, never authority.
3. Resolve the target object using both `organization_id` and its primary key in one authorized transaction. For nested entities, verify organization equality through composite FKs and service-layer authorization.
4. Authorize an explicit action (`service.edit`, `offer.submit`, `membership.invite`, `verification.review`, etc.) against a versioned permission matrix. Do not let a generic “admin” or partner role bypass action scope.
5. Recheck membership and resource status on every write. Revocation takes effect immediately for new requests. Avoid long-lived tenant claims in browser tokens.
6. Use anti-enumeration responses: inaccessible and nonexistent object IDs return the same external result unless policy permits disclosure.

### 3.2 PostgreSQL defense-in-depth

The Stage 1 live snapshot has no enabled/forced RLS tables and no policies. Do not enable RLS on existing schemas in this task. Before partner runtime is implemented, test RLS on the new `partner` tables only:

- least-privilege runtime DB role has neither superuser nor `BYPASSRLS`; migrations use a separate owner role;
- each request transaction sets a transaction-local authenticated actor context after application authentication;
- `USING` and `WITH CHECK` policies join membership to the row's `organization_id`, and separate public read policies expose only approved publication views;
- table owner is not the runtime application role; force RLS on tenant tables if migration/operational roles permit and verify it in integration tests;
- tests connect using the actual application role and attempt cross-tenant SELECT, INSERT, UPDATE, nested-FK substitution and deletion.

RLS is defense-in-depth against query mistakes, not a complete barrier against a compromised backend credential if that credential can set arbitrary actor context. The application remains the trust boundary. A stronger DB identity assertion would require a separately reviewed credential/session design; do not claim it here.

### 3.3 Reviewer separation and governance

The author cannot approve/publish their own submitted service/offer or organization verification. A reviewer must have a separate platform-governance permission, reason, policy version and audit event. Emergency suspension and reinstatement are separate explicit actions. ADR-0008 provider-admin remains separate: partner or platform reviewers do not receive AI provider privileges; provider admins do not receive tenant evidence/referral privileges by default.

## 4. Publication and recommendations

- Partner source/profile values do not overwrite structured canonical destination fields or their claim evidence.
- Service relevance to a destination is a reviewed association, not an identity link.
- Organization verified does not mean partner active. Partner active does not mean service approved. Service approved does not mean offer published. Offer published does not mean currently available.
- Public reads use dedicated reviewed projections and freshness rules; internal moderation notes, evidence refs, legal identifiers, member identities and invitation records are not selected.
- Matching first applies deterministic eligibility: approved/current organization, service, offer, date/schedule compatibility, destination scope, traveler constraints and current explicit availability evidence where required. Unknown/stale values remain unknown and cannot satisfy hard constraints. Ranking follows ADR-0011 only after that ADR is approved and policy weights/tie-break/audit are set.
- Organic destination recommendations and paid/sponsored placement remain distinct. No paid placement may change eligibility or be presented as an organic recommendation. No commercial data is routed through RAG as authoritative availability.
- Clicks remain clicks. Referral/contact leads require explicit traveler consent, recipient/purpose/retention disclosure, operational support and owner-approved ADR-0012/ADR-0007 scope.

## 5. Owner decisions required before implementation

1. Accept/revise ADR-0009 organization lifecycle, invitation authority, role/action matrix, related-company policy and tenant authorization model.
2. Accept/revise ADR-0010 launch service taxonomy, branch address/location privacy, manually entered source states, price denomination/currency/tax semantics, schedule/availability freshness and public fields.
3. Accept/revise ADR-0011 deterministic eligibility semantics, handling unknown/stale fields, ranking objectives, tie-break and paid placement separation.
4. Decide whether referrals/leads are out of scope or approve a bounded consent/data/retention/recipient workflow and ADR-0007 amendment under ADR-0012.
5. Resolve ADR-0013 platform review/bootstrap/recovery, appeal, reviewer staffing, audit retention and separation-of-duty rules, consistent with ADR-0006.
6. Approve the initial partner geography, allowed partner categories, public-data fields, personal/legal data handling, verification-document storage location and retention.

Until these decisions are recorded in the ADRs, do not create partner tables, RLS policies, endpoints or UI. The ERD/dictionary are precise implementation proposals, not accepted changes.
