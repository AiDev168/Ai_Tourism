# Partner Marketplace Architecture Decision Package v1.0

- **Status:** Proposal package — Owner Decision Required
- **Prepared:** 2026-11-07
- **Scope:** Documentation-only decisions and gates for a possible tourism partner marketplace
- **Baseline:** Branch `fix/initialize-database-powershell-inspect-v1`, HEAD `4e9b76a66a922981c72bfee04c6484735d8206c2`

This package organizes proposed decisions; it does not accept the marketplace architecture or authorize implementation. Recommendations below are not owner decisions. The existing marketplace architecture remains a proposal until the owner explicitly accepts the relevant decisions.

## 1. Decision package

| Proposal | Subject | Recommended direction |
|---|---|---|
| [ADR-0009](decisions/ADR-0009-partner-organizations-and-tenant-boundaries.md) | Organizations, relationships, memberships, and tenant isolation | Explicit organizations and individual organization-scoped memberships; deny cross-tenant access by default |
| [ADR-0010](decisions/ADR-0010-partner-services-offers-pricing-and-availability.md) | Services, offers, price, schedule, availability, and freshness | Separate structured service and time-bound offer data; manually maintained and moderated for a bounded pilot |
| [ADR-0011](decisions/ADR-0011-partner-offer-matching-and-ranking.md) | Eligibility and ranking | Deterministic hard filters followed by versioned, explainable organic ranking; sponsorship separate and labeled only if approved |
| [ADR-0012](decisions/ADR-0012-partner-referrals-consent-attribution-and-commercial-model.md) | Contact/referral and commercial concepts | Preserve outbound click as distinct; consider explicit-consent lead referral only after policy/scope approval; no booking or settlement |
| [ADR-0013](decisions/ADR-0013-partner-and-platform-admin-governance.md) | Partner and platform governance | Separate scoped partner workspace, platform review, and AI provider control plane; no protected implementation before auth approval |

Each ADR is marked **Proposed — Owner Decision Required**. A recommendation becomes a decision only after explicit owner acceptance and any required amendment to existing scope decisions.

## 2. Decision matrix

| Concern | Option A | Option B | Option C | Recommended default (proposal only) |
|---|---|---|---|---|
| Partner identity | Shared accounts/informal access: low setup, poor accountability | Individual staff memberships per organization: clear revocation and audit, requires auth and tenant checks | Separate partner identity service: stronger isolation, premature duplication | B, inside the modular monolith, gated by ADR-0006 |
| Company relationships | Flat organization only: simple, weak branch/brand support | Explicit branch and related-entity relationships: flexible, requires scoped semantics | Implicitly inherit parent access: convenient, risks cross-tenant leakage | B; relationship does not imply permission inheritance |
| Commercial data | Store in destination/RAG records: reuses current domain, mixes volatile commercial terms with editorial place facts | Separate structured service/offer contract: explicit ownership and freshness, new domain work | Live partner feeds first: potentially fresh, high integration/operational burden | B, initially manual and reviewed |
| Availability | Treat missing as available: apparent coverage, unsafe claims | Unknown/stale is explicit and excluded or requires confirmation: conservative, may reduce results | Live inventory integration: fresher, requires contracts and adapters | B; C is later and separately approved |
| Matching | Model-selected ranking: flexible, non-reproducible and may invent facts | Deterministic eligibility then transparent ranking: auditable, needs policies and tests | Paid position blended into organic score: monetization, hidden bias | B; any sponsored placement separate and labeled only if accepted |
| Traveler action | Allowlisted outbound link/click under ADR-0007: low data exposure, no lead workflow | Consented contact/referral: useful attribution, adds personal-data and operational obligations | Integrated booking/payment: high conversion potential, large legal/financial scope | A remains current scope; evaluate B only after explicit ADR-0007 scope decision; C excluded |
| Administration | Shared broad admin role: simple, excessive privileges | Separate partner, platform governance, and provider-control roles: clearer boundaries, more policy work | Placeholder/public admin: quick demo, unacceptable security | B, with protected implementation blocked by ADR-0006 and ADR-0008 gates |
| Commercial model | Neutral/free pilot: simple, limits revenue learning | Subscription/affiliate/commission concepts: business flexibility, disclosure and accounting decisions | Commission settlement in product: operational/legal/financial system | Neutral/free pilot is the low-risk proposal; no financial settlement in this package |
| Delivery architecture | Microservices/event bus/cache: independent scaling, operational cost | Modular monolith with explicit modules: fits current baseline, requires disciplined boundaries | One undifferentiated module: initial simplicity, weak ownership | Modular monolith; no new infrastructure absent measured need |

## 3. Source-derived requirements versus recommendations

### Source-derived constraints

- The repository is a modular-monolith MVP; do not infer authorization for microservices or infrastructure expansion from a conceptual diagram. See [ADR-0001](decisions/ADR-0001-mvp-modular-monolith.md) and the [MVP handoff](../implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.5.md).
- The current catalog is the unified `knowledge.destinations` domain with explicit provenance/publication boundaries. See [ADR-0004](decisions/ADR-0004-hierarchical-destination-catalog.md).
- RAG/embedding behavior is replaceable and owner-controlled; storage tests do not establish semantic retrieval. See [ADR-0003](decisions/ADR-0003-ai-and-rag-provider-boundaries.md).
- Authentication/session strategy is open; protected user-data routes are blocked until ADR-0006 decisions are made and implemented safely. See [ADR-0006](decisions/ADR-0006-authentication-and-session.md).
- ADR-0007 currently permits allowlisted outbound links and click tracking; it excludes live inventory, reservation confirmation, tickets, payment, cancellation, and refunds. See [ADR-0007](decisions/ADR-0007-mvp-external-integrations.md).
- Provider management is a separate administrator-only control plane, and future AI calls must use the server-side gateway. Marketplace roles do not confer provider access. See [ADR-0008](decisions/ADR-0008-centralized-ai-provider-management.md).
- The [current ERD](ERD_MVP_v0.1.md) describes 30 current tables and has no partner organization, membership, service, offer, schedule, lead, or commission domain. It is schema-derived, not a proposal for new schema.

### Recommendations in this package

- Pilot verified organizations with explicit memberships, manual services/offers, moderated publication, and category-specific freshness rules.
- Keep commercial data structured and distinct from destination identity and RAG content.
- Use deterministic eligibility followed by transparent, reproducible ranking; keep commercial placement separate.
- Keep the current outbound-link boundary unless and until the owner approves a separately scoped, consent-based referral expansion.
- Defer automated feeds, live availability integration, transactional booking, payment, refunds, settlement, and advanced commercial optimization.
- Keep all proposals in the modular monolith until evidence and an accepted decision justify another boundary.

## 4. Owner decisions requiring explicit approval

1. **Scope:** Whether the marketplace is an MVP/pilot scope expansion and whether ADR-0007 receives a narrow amendment for consented partner referrals. This package does not amend ADR-0007.
2. **Identity and tenant policy:** Authentication method/session, account recovery, administrator bootstrap, organization-scoped permission matrix, multiple memberships, dual traveler/staff identity, invitation and revocation. ADR-0006 remains open and must not be weakened.
3. **Organization governance:** Acceptable verification evidence by pilot geography, reviewer responsibilities, renewals, suspension, appeals, and retention.
4. **Taxonomy:** Initial service categories and type-specific required fields/localized content policy.
5. **Commercial data:** Price provenance/basis, currency and conversion policy, schedules/time zones, freshness thresholds, stale-data behavior, and manual update ownership.
6. **Matching:** Hard constraints per category, handling of unknown data, score factors/weights/tie-breaks, quality evidence, audit retention, and evaluation gate.
7. **Commercial neutrality:** Whether the pilot is neutral/free, subscription-funded, affiliate, or otherwise; whether labeled sponsorship is permitted. No organic ranking manipulation by commission.
8. **Referral/privacy:** Whether lead referrals exist in pilot, authentication requirement, precise consent language/data categories/recipients, retention, withdrawal, delivery/response SLA, reporting, and dispute handling.
9. **Geography and partner scope:** Pilot region, categories, operational capacity, and locale coverage.
10. **Financial boundary:** Confirm that booking, payment, cancellation/refund, commission settlement, payout, and financial ledger remain deferred; any expansion needs separate product, legal, and architecture review.

## 5. Dependencies and implementation order

```text
Owner scope decision + ADR-0006 authentication/session decisions
              │
              ├── ADR-0009 organizations, memberships, tenant authorization
              │       └── ADR-0013 protected partner/platform governance
              │
              ├── verification, taxonomy, privacy and operating policies
              │       └── ADR-0010 structured services/offers/freshness
              │                └── approved production commercial data
              │                         └── ADR-0011 eligibility and ranking
              │
              └── ADR-0007 scope review + consent/retention/recipient rules
                      └── ADR-0012 referral/attribution pilot

ADR-0008 remains a separate gate for all provider control and AI traffic.
ADR-0004 catalogue identity and the owner's RAG boundary remain unchanged.
```

Recommended order: owner accepts/revises the proposal package; settle scope and identity/security decisions; approve organization verification and operations; define service taxonomy and freshness; design the physical model in a separate reviewed task; implement partner foundations; add moderated services/offers; validate real eligible data; then implement matching and (if separately accepted) referral. Each phase needs its own authorization and tests. Do not start implementation Task 2 automatically from this package.

## 6. Traceability

| Source | Traceability and boundary |
|---|---|
| [Reference architecture](../reference/AI_Travel_Advisor_Reference_Architecture.md) | Establishes broader product vision for travelers, companies/providers, services, availability, business models, and future booking. Its conceptual scope does not itself authorize MVP transactions. |
| [Architecture analysis](../reference/ARCHITECTURE_ANALYSIS.md) | Contains broader logical/conceptual options, including proposed booking/provider concepts. Conceptual entities are not current physical schema. |
| [MVP handoff](../implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.5.md) | Modular monolith, deterministic decision core, privacy and source-backed facts; keeps implementation bounded and gates identity/RAG/provider work. |
| [ADR-0004](decisions/ADR-0004-hierarchical-destination-catalog.md) | One hierarchical destination catalogue, provenance, publication status, and coordinate semantics. Partner company/services/offers must remain a separate commercial domain. |
| [ADR-0006](decisions/ADR-0006-authentication-and-session.md) | Open authentication/session choice and mandatory user/object-level authorization invariants. Protected traveler, partner, and admin functionality is blocked pending approval and safe implementation. |
| [ADR-0007](decisions/ADR-0007-mvp-external-integrations.md) | Accepted allowlisted outbound links/clicks only for current MVP booking integration. Referrals require explicit owner scope decision; no transaction expansion is implied. |
| [ADR-0008](decisions/ADR-0008-centralized-ai-provider-management.md) | Separate protected provider control plane; all future AI calls through server-side gateway; marketplace administration has no provider privilege by default. |
| [Current ERD](ERD_MVP_v0.1.md) | Describes current 30-table model and confirms the partner commercial domain is absent. It does not prescribe new tables. |
| [Partner architecture proposal](PARTNER_MARKETPLACE_AND_ADMIN_PLATFORM_ARCHITECTURE_v1.0.md) | Source proposal for partner outcomes, domain separation, conceptual lifecycles, and scope decisions. Remains proposed pending owner review. |
| [Partner execution roadmap](../implementation/CODEX_EXECUTION_ROADMAP_PARTNER_MARKETPLACE_v1.0.md) | Defines Task 0 audit then owner-gated documentation and implementation tasks. This package completes only Task 1. |

## 7. Implementation blockers and release gates

- Explicit owner acceptance of marketplace scope and resolution of its conflict with current link-only ADR-0007.
- Accepted ADR-0006 authentication/session, account recovery, admin bootstrap, and authorization design before protected user, partner, or admin functionality.
- Accepted tenant, role, invitation, verification, suspension, appeal, audit, and evidence-retention policy.
- Approved initial categories, localization requirements, structured offer/pricing/schedule contracts, currency treatment, freshness thresholds, and manual operational ownership.
- Approved referral consent, data minimization, recipient, retention, delivery, reporting, and dispute policy before any personal-data transfer.
- A separately reviewed physical data design and migration plan, with isolated migration, authorization, provenance, exact-count, and publication-gate tests. No migration is authorized here.
- Real partner onboarding and reviewed/published data before any production matching claim; no synthetic records in user-facing results.
- Deterministic matching tests covering hard eligibility, stale/unknown/conflicting commercial data, reproducibility, and commercial neutrality.
- Independent security review and negative authorization tests for cross-tenant access, partner/admin boundaries, privacy, and privileged audit.
- No integration feed, paid API, AI feature, or provider configuration until its own contracts, costs, secrets, and operational policies are approved. Any AI stays behind ADR-0008.
- No transaction/financial release until a separately accepted architecture and legal/operational decision covers reservations, inventory, payments, cancellation, refunds, settlement, and accounting.

## 8. MVP scope conflict and status

There is a genuine scope conflict, not a technical inconsistency: the broad reference architecture and partner proposal envision commercial partner discovery and possible referrals, while accepted ADR-0007 limits current MVP booking interactions to allowlisted outbound links and click tracking. This package recommends a staged non-transactional pilot but does not resolve that conflict on the owner's behalf. Until explicit approval and any ADR-0007 amendment, current scope remains the accepted link-only boundary.

The current database and runtime lack partner organizations, tenancy, service/offer APIs, marketplace matching, partner portals, referral leads, and platform marketplace governance. Existing outbound-link structures are not a substitute for those capabilities. Current catalogue and RAG boundaries remain intact; semantic retrieval is not claimed as implemented. No code, schema, or runtime capability is authorized by these proposals.

## 9. Current-worktree note

The Task 0 audit reported the canonical roadmap at `docs/implementation/CODEX_EXECUTION_ROADMAP_PARTNER_MARKETPLACE_v1.0.md`. The additional path `docs/CODEX_EXECUTION_ROADMAP_PARTNER_MARKETPLACE_v1.0 .md` was absent during Task 1 preflight, so byte-identity could not be verified. This package leaves both paths untouched and does not create, rename, or remove a roadmap copy.

## 10. Next step

Owner review these five ADR proposals and the decision matrix. Record explicit accept/revise/reject outcomes, especially for MVP scope versus ADR-0007, authentication/tenant policy under ADR-0006, referral consent, pilot geography/categories, and the commercial model. Only after that review should the owner authorize the roadmap's next task. This package does not start Task 2.
