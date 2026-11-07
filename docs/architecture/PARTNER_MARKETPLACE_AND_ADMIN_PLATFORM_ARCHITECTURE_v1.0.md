# AI Tourism — Partner Marketplace and Administrative Platform Architecture

**Document ID:** AI-TOURISM-ARCH-PARTNER-001  
**Version:** 1.0  
**Status:** Proposed architecture — owner review required before implementation  
**Prepared:** 2026-11-07  
**Repository:** `AiDev168/Ai_Tourism`  
**Reference repository revision reviewed:** `4e9b76a66a922981c72bfee04c6484735d8206c2`  
**Target repository location:** `docs/architecture/PARTNER_MARKETPLACE_AND_ADMIN_PLATFORM_ARCHITECTURE_v1.0.md`

---

## 1. Purpose

This document defines the missing commercial partner domain of AI Tourism: tourism companies and service providers, their organizations and staff, their service catalogues and time-bound offers, their schedules and availability, the matching of those offers to a traveler's trip plan, and consent-based introductions/referrals.

The product is intended to be more than a destination recommender. It should help a traveler move from an expressed need and a proposed itinerary to relevant, explainable services offered by legitimate tourism companies. Examples include guided tours, local experiences, accommodation, transport, activities and other travel-related services.

This is an **independent domain architecture**. It does not replace the destination/knowledge catalogue, RAG, trip-intake or recommendation architecture. It introduces a distinct commercial domain that can be integrated with those capabilities through explicit contracts.

This document is a design proposal. It is not authorization to modify `main`, merge branches, apply migrations to a shared database, activate real provider integrations, collect payments, or implement transactional booking.

## 2. Source baseline and scope reconciliation

The project documents describe two different levels of scope. Both must be respected rather than silently treating the broader reference design as current MVP authorization.

| Existing source | What it establishes | What it does not authorize by itself |
|---|---|---|
| `docs/reference/AI_Travel_Advisor_Reference_Architecture.md` | The product vision includes travelers, tourism agencies/companies and service providers; it describes supplier interactions, service availability/pricing, booking-related workflows and business models such as commissions and B2B services. | It is not an implementation-ready schema or an instruction to implement all future booking/payment workflows in the first release. |
| `docs/reference/ARCHITECTURE_ANALYSIS.md` | It proposes broader logical boundaries, including a conceptual `booking` domain and service/provider-related data. | Conceptual tables are not physical tables and must not be treated as existing implementation. |
| `docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.5.md` | It narrows the initial MVP and emphasizes a modular monolith, a mobile-first multilingual PWA, source-backed data, deterministic controls and external links. | Its external-link-only booking boundary does not provide the complete company/service marketplace described by the product vision. |
| `docs/architecture/decisions/ADR-0007-mvp-external-integrations.md` | It limits MVP booking integrations to allowlisted outbound links and click tracking; no live inventory, reservations, tickets, payment, cancellation or refund. | It does not define company onboarding, provider-owned offers, time-based availability, lead referrals or partner operations. |
| `docs/architecture/ERD_MVP_v0.1.md` | The current physical project-owned database model contains 30 tables across the currently documented schemas. | There is no implemented organization, partner staff, service offer, schedule/availability, lead/referral or commission domain in that ERD. |
| `ADR-0006` and `ADR-0008` | User and administrator authentication remains an explicit design gate; AI provider control is a separate protected administrative function. | The partner portal or platform-admin portal must not be implemented with placeholder or anonymous authentication. |

### 2.1 Resolution proposed by this document

1. **Add the partner marketplace as a first-class product domain.** It is not merely a list of external links and is not part of `knowledge.destinations`.
2. **Introduce a non-transactional partner marketplace pilot before integrated booking.** The pilot can support verified companies, structured services/offers, manually maintained schedules and prices, transparent matching, outbound actions and consent-based contact/referral requests.
3. **Keep transactional booking out of this release.** No inventory hold, reservation confirmation, ticket/voucher issue, payment processing, cancellation, refund, settlement or financial ledger is implied.
4. **Retain ADR-0007's security and transaction boundary.** Its allowlisted redirect requirement remains applicable. Its statement that the MVP is link-only should be revisited through a separately accepted ADR/addendum before partner marketplace implementation expands the MVP scope.
5. **Do not change the existing 30-table model casually.** Partner domain entities must be designed as a separate logical boundary and introduced only through reviewed migrations and isolated-database validation.

## 3. Product outcomes

The platform should support the following end-to-end outcome:

1. A traveler describes a trip, dates or date flexibility, party size, destination preferences, budget and interests.
2. AI Tourism clarifies missing trip requirements and creates or updates a structured trip plan. Unknown information remains unknown.
3. The system proposes destinations and an itinerary using the approved destination catalogue and knowledge/RAG layer.
4. For relevant itinerary stops, dates and time windows, the system finds eligible partner services and offers.
5. The system filters offers using deterministic requirements and ranks the remaining offers using transparent relevance and quality criteria.
6. The traveler can inspect the company, the service, price basis, applicable dates, schedule, last update, important conditions and why the offer matches.
7. The traveler chooses an allowed next action: visit the partner's approved external page, use published contact information, or explicitly request an introduction/contact from the partner.
8. The platform records the permitted click/referral event and can measure partner performance without silently transferring a traveler's private trip details.

The AI assistant may explain and contextualize results, but it must not invent prices, capacity, schedules, policies, company credentials or availability. Deterministic backend rules remain authoritative for hard constraints and offer eligibility.

## 4. Actors and product surfaces

### 4.1 Traveler

- Uses the public PWA in Persian (`fa-IR`), English (`en-US`) or Arabic (`ar`).
- Creates a trip request and itinerary.
- Sees relevant companies and offers with the data freshness and conditions visible.
- Chooses whether to open an external partner page or share specific contact/trip information for a referral.
- Can distinguish an organic recommendation from a sponsored placement.

### 4.2 Partner organization

Examples: travel agencies, tour operators, accommodation providers, local guides, activity providers, transport companies and other approved tourism businesses.

- Applies to become a partner and submits organization evidence.
- Creates and maintains its company profile, branches/contact points, services, offers, dates, schedules, prices, capacity statements and policies, subject to its assigned permissions.
- Submits content for platform review/publication.
- Receives only leads/referrals explicitly released to it by the traveler and permitted by the applicable policy.
- Views scoped performance and referral status; it does not see other companies' private data.

### 4.3 Partner staff

- Belongs to one or more organizations through explicit memberships.
- Receives organization-scoped roles such as owner, manager, catalogue editor or referral operator.
- Cannot access another organization's data by changing a URL, identifier or request body.

### 4.4 Platform administrator / reviewer

- Verifies organizations and reviews company profiles, services and offer content.
- Approves, rejects, suspends or requests changes with an auditable reason.
- Manages taxonomy, publication policy, platform-wide moderation, partner eligibility and operational reporting.
- Does not automatically gain access to AI provider secrets merely by being a content reviewer.

### 4.5 System administrator for AI infrastructure

The AI Provider Gateway and its secrets remain a separate protected control plane under ADR-0008. Partner administration and content review do not grant provider-configuration privileges.

## 5. Domain boundaries

The product remains a modular monolith. These are logical modules and ownership boundaries, not a mandate to create microservices.

```text
PWA
 ├── Traveler experience
 │    ├── Trip intake and clarification
 │    ├── Destination / knowledge exploration
 │    ├── Itinerary
 │    └── Partner offers and referrals
 │
 ├── Partner workspace (authenticated, organization-scoped)
 │    ├── Organization profile and staff
 │    ├── Service catalogue
 │    ├── Offers, prices and schedules
 │    └── Referral inbox and performance
 │
 └── Platform administration (protected)
      ├── Organization verification
      ├── Service/offer moderation
      ├── Taxonomy and publication policy
      ├── Referral oversight and audit
      └── Operational reporting

Backend modular monolith
 ├── identity / authorization
 ├── travel / trip planning / itinerary
 ├── knowledge / RAG / destination catalogue
 ├── recommendation / deterministic matching
 ├── partner organizations
 ├── partner services and offers
 ├── offer schedule / pricing / availability snapshots
 ├── referral / attribution
 ├── external integrations
 ├── audit / operations
 └── AI Provider Gateway (separate protected control plane)

PostgreSQL remains the initial persistence platform. New domains are logical schemas/modules,
not separate databases or services unless evidence later justifies that change.
```

### 5.1 Destination knowledge versus commercial offer

These are distinct data classes and must not be merged:

- **Destination/knowledge:** places, attractions, editorial facts, source-backed descriptions, tags, coordinates, documents/chunks and RAG content.
- **Partner/company:** legal or operating organization, verification, memberships, branches and contact points.
- **Service:** what a company offers (for example, a guided walking tour or airport transfer).
- **Offer:** the commercial conditions under which a service can be purchased or requested during a defined period or on defined dates.
- **Availability/schedule:** date/time/capacity statements and their freshness.
- **Referral:** the traveler's explicit action to contact or be introduced to a company.

A destination can exist without a partner. A company can offer services at multiple destinations. Multiple companies may offer comparable services at one destination. Partner data must never be inserted into `knowledge.destinations` merely because it is geographically associated with a place.

### 5.2 RAG boundary

RAG remains a high-priority product capability for source-backed destination and travel knowledge. Dynamic partner values (price, schedules, capacity, availability, publication state) must be stored and queried as structured operational data, not treated as timeless facts in semantic chunks.

The matching pipeline may combine:

- deterministic SQL/domain queries for current company, offer, price, time and eligibility data; and
- approved RAG retrieval for descriptions, destination context, policy explanations and other source-backed narrative information.

A retrieved chunk must not override a current structured price, availability state or policy record. RAG must preserve source provenance and retrieval/version metadata as defined by the existing knowledge/retrieval contracts.

## 6. Partner organization lifecycle

Suggested organization lifecycle:

```text
DRAFT -> SUBMITTED -> UNDER_REVIEW -> VERIFIED -> ACTIVE
                         |                  |
                         +-> CHANGES_REQUESTED
                         +-> REJECTED        +-> SUSPENDED
                                             +-> CLOSED
```

Rules:

1. `VERIFIED` means the submitted organization evidence passed the platform's defined checks; it does not automatically publish every offer.
2. `ACTIVE` means the organization is currently eligible to participate. It may still have individual offers awaiting review.
3. Suspension blocks new publication, new referrals and new recommendation exposure according to a documented policy. Existing audit history is retained.
4. Verification decisions require reviewer identity, timestamp, evidence references, policy/version and reason.
5. The platform must support re-review and expiry of time-sensitive evidence where legally or operationally required.
6. Partner-provided descriptions and claims are not treated as independently verified facts merely because the organization is verified.

The exact identity evidence, regional legal requirements and verification workflow remain configurable product/policy decisions; do not hard-code unverified legal assumptions.

## 7. Service catalogue and offer model

### 7.1 Service definition

A service is the reusable description of what the partner provides. Typical attributes:

- owning organization and optional branch;
- service type and controlled taxonomy;
- localized title and description (`fa-IR`, `en-US`, `ar`);
- service location or linked destination identifiers;
- delivery mode and meeting/location details where appropriate;
- duration and activity characteristics where known;
- participant/age/accessibility constraints where explicitly supplied;
- media and evidence references;
- service status and moderation state.

Examples include a city walking tour, a local food experience, a museum guide, a transfer service, an accommodation property or a multi-day tour package. Service-type-specific fields should be modeled deliberately; do not build an unrestricted JSON blob as the sole business contract.

### 7.2 Offer definition

An offer is a time- and condition-bound commercial presentation for a service. It can contain:

- the service and owning partner;
- validity window and/or specific service dates;
- schedule/departure/slot references;
- price amount, ISO currency, pricing unit and included/excluded components;
- minimum/maximum party size;
- stated capacity/availability and how it was obtained;
- cancellation/change conditions supplied by the partner;
- booking/contact mode (external link, published contact, or referral request);
- source/update/verification metadata;
- publication and moderation state.

Do not conflate a service's usual descriptive attributes with an offer's current commercial terms. A service can have multiple offers over different dates or from different branches.

### 7.3 Price representation

A price must be explicit about:

- amount and currency;
- pricing basis (per person, per room/night, per vehicle, per group, per service, or another controlled unit);
- applicable date/time or validity period;
- taxes/fees/inclusions/exclusions when known;
- whether it is an exact provider-confirmed price, a partner-entered indicative price, or a sourced estimate;
- when it was last updated and when it expires or becomes stale.

Rules:

1. Never infer an exact total by multiplying an ambiguous unit price.
2. Never compare amounts in different currencies as if they were the same currency.
3. Currency conversion may be introduced only through a selected, source-backed rate with rate timestamp and display disclosure.
4. Missing taxes, fees or price basis must be displayed as unknown/not supplied, not silently assumed to be included.
5. A price change after a user viewed an offer must be handled as a changed/updated offer, not as an immutable promise.

### 7.4 Schedules and availability

Availability may initially be manually maintained by the partner. It must include:

- the applicable service date or date range;
- start/end time and timezone where relevant;
- capacity value or a clearly stated capacity class;
- availability status (`available`, `limited`, `unavailable`, `on_request`, `unknown`);
- who or what supplied the information (partner manual entry, approved feed, or platform import);
- `observed_at`, `updated_at`, and freshness/expiry policy.

`unknown` is not `available`. A stale snapshot must not be presented as live availability. The interface must label freshness in understandable language.

### 7.5 Publication state

Service and offer content needs a lifecycle separate from organization verification, for example:

`DRAFT -> SUBMITTED -> IN_REVIEW -> APPROVED -> PUBLISHED -> EXPIRED/PAUSED/REJECTED`.

An organization being verified does not bypass offer moderation. A published offer must still satisfy its required data completeness and freshness policy.

## 8. Matching partner offers to a trip

The matching engine is a deterministic domain service behind the existing recommendation architecture. The LLM may explain the results but may not decide whether a hard constraint is satisfied.

### 8.1 Inputs

- selected destination and itinerary stop identifiers;
- planned date/time window or explicit flexibility;
- trip duration and participant count;
- budget range and currency;
- expressed interests and service preferences;
- explicit accessibility/age/other constraints supplied by the traveler;
- currently eligible organizations, services and published offers;
- offer schedules, price basis and freshness metadata.

### 8.2 Hard eligibility filters

Apply before soft ranking. Depending on service type, include:

1. Organization is verified and active.
2. Service and offer are approved and published.
3. Offer is valid for the itinerary destination and relevant travel date/time.
4. Schedule is compatible with the planned itinerary window, including a configured and disclosed buffer where necessary.
5. Party size is within the explicitly stated limits.
6. Capacity is sufficient only when a sufficiently fresh, explicit capacity statement exists; otherwise mark availability unknown or route to request confirmation.
7. Price basis/currency is sufficiently clear for the requested comparison.
8. Explicit traveler hard constraints are not violated.
9. The offer is not expired, suspended, withdrawn or blocked by moderation policy.

A high score must never override failed hard eligibility. If a relevant field is unknown, do not silently treat it as a pass; classify the result as `needs_confirmation` or exclude it according to the product policy for that field.

### 8.3 Soft ranking

Among eligible offers, ranking can consider:

- fit to traveler interests and trip purpose;
- geographic fit to itinerary stops;
- schedule convenience;
- price fit after comparable price units/currencies are established;
- service quality/reliability signals with defined provenance;
- completeness and freshness of partner data;
- traveler feedback, with anti-abuse controls and sufficient sample handling;
- distance/travel-time only when a verified map/directions provider supplies the value.

The algorithm version, filters, score components and explanation inputs should be recorded as part of recommendation traceability, consistent with the existing recommendation architecture.

### 8.4 Commercial neutrality and sponsored placement

Commission, subscription tier or payment to the platform must not silently change organic recommendation rank. If paid placement is introduced:

- it must be explicitly labeled as sponsored;
- it must not bypass hard eligibility filters;
- the placement policy and ranking influence must be documented;
- an organic alternative must remain distinguishable;
- analytics must separate organic and sponsored outcomes.

This document does not select a commission rate, subscription tier or advertising policy.

### 8.5 User-facing offer card

At minimum display:

- company and verification/publication status in understandable terms;
- service title/type and relevant description;
- date/schedule applicability;
- price amount, currency and pricing unit;
- freshness/last-updated indicator;
- availability state (`available`, `limited`, `on request`, `unknown`);
- important conditions and exclusions;
- why it matches the trip;
- clear next action and whether the action leaves AI Tourism;
- sponsored label, if applicable.

Do not display internal review notes, private company evidence, staff identity, provider credentials or internal infrastructure fields.

## 9. Referral, introduction and attribution

### 9.1 Supported actions

The initial partner pilot can support two non-transactional routes:

1. **Outbound action:** redirect to a stored, allowlisted partner URL or show an approved contact channel. The backend resolves a known link identifier; the client must never submit an arbitrary redirect URL.
2. **Traveler-requested introduction:** the traveler explicitly asks AI Tourism to share a defined set of contact/trip details with a selected partner. This is a lead/referral request, not a reservation or booking.

The UI must clearly distinguish these actions and must not imply that the partner accepted a booking.

### 9.2 Consent and data minimization

Before any personal or trip information is sent to a partner:

- identify the selected partner and the purpose of the transfer;
- show exactly which data fields will be shared;
- request an affirmative, purpose-specific consent action;
- record the consent text/policy version, timestamp, actor, recipient organization and data categories;
- send only the selected minimum fields;
- provide a clear confirmation that the information has been sent or a safe failure state;
- do not disclose the full conversation transcript by default.

A click on an external link is not consent to disclose the user's identity or trip details. No lead is created merely because an offer was shown.

### 9.3 Referral lifecycle

Suggested non-transactional lead state:

`DRAFT -> CONSENTED -> SUBMITTED -> DELIVERED -> PARTNER_ACKNOWLEDGED -> CONTACTED -> CLOSED`

Additional terminal/exception states can include `WITHDRAWN`, `DELIVERY_FAILED`, `REJECTED` and `EXPIRED`.

The state describes contact/referral handling only. It must not be named or interpreted as booking, reservation or payment status.

### 9.4 Attribution and commercial measurement

Record the minimum identifiers needed to understand the path from recommendation to user action:

- recommendation/offer identifier and version;
- trip/itinerary correlation where authorized;
- partner organization and campaign/reference identifiers;
- action type and timestamp;
- referral consent record when applicable;
- delivery outcome and partner status updates where available.

Click attribution and lead attribution are distinct. Do not count a click as a booking or sale. Commission calculation, settlement, invoicing and payout are explicitly deferred to a later approved financial domain.

## 10. Portals and administration

### 10.1 Partner workspace

The partner workspace should enable authorized company staff to:

- manage the organization's profile and evidence submissions;
- invite/manage staff if that capability is approved;
- manage branches and approved contact information;
- create/edit services and offers;
- set dates, schedules, price units, capacity statements and freshness windows;
- submit changes for review and see review feedback;
- pause/withdraw an offer;
- receive and manage consented referrals;
- view scoped clicks/referrals and summary performance.

The company must not be allowed to directly publish content that requires platform approval or change its own verification state.

### 10.2 Platform administration

The platform admin surface should support:

- organization application review and verification evidence handling;
- organization suspend/reactivate/close actions with reasons;
- service and offer review, approval, rejection and publication;
- controlled taxonomy and required-field policies;
- freshness policies by offer/service type;
- abuse reports and partner quality issues;
- referral delivery oversight and disputes;
- audit search and operational summaries;
- sponsored placement policy only if separately approved.

### 10.3 Separate AI infrastructure administration

The AI Provider Gateway/admin area remains separate under ADR-0008. Partner content reviewers, partner managers and ordinary system operators receive no provider secrets or model-routing control unless an explicit separate privilege grants it.

## 11. Security, identity and tenancy

Authentication and authorization are implementation blockers for protected portals until ADR-0006 is accepted and its required invariants are implemented.

Required controls:

1. No placeholder authentication and no anonymous partner/admin writes.
2. Partner data access is scoped by a verified organization membership on every request.
3. Organization IDs supplied by the browser are not trusted as authorization; the backend derives accessible organizations from the authenticated principal and checks the requested resource's ownership.
4. Roles are least-privilege and action-specific. Example permissions: view organization, edit profile, manage service, submit offer, view referrals, process referral, review partner, publish offer, suspend organization.
5. Platform-admin privileges are separate from partner roles and separately audited.
6. AI provider administration is separately protected under ADR-0008.
7. Private organization evidence, contact details and referral payloads are not exposed through the public catalogue endpoint.
8. The public traveler API exposes only approved/published fields and safe identifiers.
9. Secrets, credentials and internal endpoints must never enter client bundles, logs, public responses or RAG chunks.
10. Consent, data export/deletion, retention and audit behavior must align with the project's privacy/security boundaries.
11. Rate limiting, anti-spam and abuse detection protect organization onboarding, public enquiries and referral endpoints.
12. Cross-organization and cross-user object authorization tests are mandatory.

Database access must preserve the existing principle that the public application role reads approved publication views rather than unrestricted raw tables. Partner write operations should use separately designed backend privileges and narrowly scoped transactions. Do not broaden `ai_tourism_app` raw-table grants to shortcut implementation.

## 12. Proposed logical data model

The following is a logical model for design and review. These are **not existing tables** and are not exact migration instructions. Final names, types, constraints, indexes and deletion semantics require a reviewed data contract and ADR.

### 12.1 `partner` domain candidates

| Conceptual entity | Responsibility |
|---|---|
| `organizations` | Partner identity, public profile, legal/operating metadata and lifecycle state. |
| `organization_memberships` | User-to-organization relationship, role, status and membership dates. |
| `verification_cases` | Verification review, evidence references, outcome, reason and policy version. |
| `branches` | Optional company locations/contact/service branches. |
| `services` | Reusable service catalogue owned by a partner. |
| `service_destinations` | Association between services and canonical destination identifiers. |
| `offers` | Commercial presentation, validity and publication state for a service. |
| `offer_schedules` | Date/time/departure/slot data. |
| `availability_snapshots` | Time-stamped capacity/availability statement and freshness metadata. |
| `offer_prices` | Currency, amount, unit, inclusion/exclusion and applicability. |
| `service_media` | Controlled references to approved media, not arbitrary executable content. |
| `publication_reviews` | Review actions and feedback for organization/service/offer publication. |
| `partner_agreements` | Approved commercial/legal terms references and version metadata, if needed for the pilot. |

### 12.2 `referral` domain candidates

| Conceptual entity | Responsibility |
|---|---|
| `referral_requests` | Traveler-initiated request to contact/introduce to a selected partner. |
| `referral_consents` | Purpose-specific consent, exact data categories, policy version and recipient. |
| `referral_deliveries` | Delivery attempt, outcome, timestamps and safe error metadata. |
| `referral_status_events` | Append-only state history for referral handling. |
| `offer_interactions` | Click/view/CTA attribution with minimal context. |
| `partner_campaigns` | Optional later campaign attribution; do not add unless a real use case requires it. |

The existing `integration.external_links` and `integration.outbound_clicks` should be assessed for safe reuse. Do not duplicate click tracking without documenting why the current records cannot support the partner use case. Do not force lead/referral payloads into outbound-click rows.

### 12.3 Data lifecycle and deletion

- Keep moderation and verification history auditable.
- Preserve the minimum evidence required for decisions while applying retention and deletion policy to personal data.
- A company closure or suspension must not erase old referral/click audit facts needed for accountability.
- Personal lead payloads require stricter retention and access than public company/service data.
- Referential delete behavior must be designed explicitly; avoid cascading deletion that destroys audit/consent evidence.

## 13. API boundary proposal

These are conceptual route families, not a committed final OpenAPI contract:

### Public/traveler read APIs

- `GET /api/v1/partners` — search approved public organizations, subject to publication policy.
- `GET /api/v1/partners/{partner_id}` — public organization profile.
- `GET /api/v1/partner-services` — filter published services by destination/type.
- `GET /api/v1/partner-offers` — filter eligible published offers by destination/date/party/price parameters.
- `POST /api/v1/trips/{trip_id}/partner-matches` — calculate matches from an authorized trip context; do not accept arbitrary owner IDs as authority.
- `POST /api/v1/partner-offers/{offer_id}/outbound-action` — resolve a known, allowlisted destination and record the action.
- `POST /api/v1/referrals` — submit an explicitly consented contact/introduction request.

### Partner workspace APIs (authenticated and organization-scoped)

- organization/profile and membership operations;
- service CRUD and submission;
- offer/price/schedule/availability updates;
- referral inbox and status updates;
- scoped performance summaries.

### Platform administration APIs (separately authorized)

- verification review;
- moderation and publication;
- suspend/reactivate;
- taxonomy/policy management;
- audit and platform reports.

Public response schemas must be explicit allowlists, not ORM serialization. Internal state, evidence, personal referral data and admin notes must not leak.

## 14. Integrations and data acquisition

The first partner pilot should support controlled manual data entry and moderation. External feeds can be added behind replaceable server-side adapters only after a specific partner/provider, contract, credentials, allowed fields, update cadence, failure behavior and regional compatibility are approved.

Integration principles:

- no provider credentials in the PWA;
- no external network calls in ordinary unit tests;
- fake adapters for deterministic tests;
- record source, observation time, update time and freshness;
- validate and quarantine malformed/stale imports;
- do not silently overwrite editorially reviewed partner content;
- distinguish partner-entered claims from independently verified facts;
- fail closed when an integration's freshness or authenticity cannot be established.

## 15. Operational metrics

Potential measures for the pilot:

- partner applications submitted, approved, rejected and suspended;
- time from application to review;
- active partners and published services/offers by category/destination;
- offer completeness and freshness distribution;
- match eligibility, no-match and needs-confirmation rates;
- organic recommendation impressions and offer actions;
- outbound clicks and consented referrals separately;
- referral delivery failure, acknowledgement and contact outcome;
- traveler feedback and complaints;
- data-quality and abuse incidents.

Metrics must not imply that a referral or click is a confirmed booking or revenue. Financial metrics require a later approved accounting/settlement model.

## 16. Delivery phases and scope gates

| Phase | Outcome | Included | Explicitly excluded |
|---|---|---|---|
| 0 — Baseline and decisions | Verified current state and accepted domain decisions | Read-only repo/worktree audit, scope reconciliation, ADR proposals, data/role contract | Runtime code or database changes |
| 1 — Partner foundations | Secure organization and verification foundation | Organization model, membership/role matrix, verification workflow, partner/admin UX specification | Public offer ranking, payment, booking |
| 2 — Service catalogue | Company-owned service and offer management | Services, localized content, offers, publication review, basic manual operation | Live API integrations, reservation state machine |
| 3 — Schedule, price and availability | Comparable, freshness-aware commercial data | Schedule windows, price units/currency, availability snapshots, staleness behavior | Inventory holds or guaranteed availability |
| 4 — Traveler discovery and matching | Offers matched to real trip plans | Deterministic filters/ranking, explanations, multilingual offer cards, itinerary integration | LLM-invented facts; pay-to-rank organic results |
| 5 — Partner introductions | Measurable, consent-based action | Safe outbound actions, explicit-consent leads/referrals, attribution and partner inbox | Booking confirmation, payment, commission settlement |
| 6 — Pilot hardening | Controlled operational pilot | Security/E2E, audit, abuse controls, data-quality and observability, operator runbooks | Broad public rollout without approval |
| Future — Transactional commerce | Full booking lifecycle if separately approved | Provider inventory, reservation/hold, payment, cancellation/refund, settlement | Not part of this architecture's first implementation scope |

Each phase must be separately accepted before Codex starts the next. The roadmap file defines the proposed Codex task sequence and verification gates.

## 17. Explicit non-goals for the first partner pilot

- No integrated reservation or booking confirmation.
- No payment gateway, card handling, refunds, cancellation or ticket/voucher issuance.
- No inventory hold or guarantee that an offer remains available at the time the traveler acts.
- No commission calculation, payout, settlement, tax invoice or financial ledger.
- No unrestricted public partner registration/publishing without review.
- No automatic transfer of chat transcripts or personal trip data to partners.
- No silent use of a provider's API, external feed or paid service.
- No separate microservices, message broker, Kubernetes, Redis or extra infrastructure without measured need and owner approval.
- No synthetic/test partner or offer data in production recommendations.
- No partner service, price or capacity fields inserted into destination knowledge tables or RAG chunks as a substitute for structured commercial records.

## 18. Decisions required before implementation

The following decisions must be recorded in ADRs or explicit owner-approved product policies:

1. **MVP scope expansion:** approve partner catalogue + non-transactional referral as a pilot capability and define how ADR-0007 is amended without enabling transactional booking.
2. **Identity and tenancy:** accept ADR-0006 authentication/session choices and approve organization-scoped authorization, staff invitation, recovery and platform-admin bootstrap policies.
3. **Partner verification policy:** determine accepted evidence, reviewer process, validity/renewal and suspension rules for target jurisdictions.
4. **Service taxonomy:** select the first supported categories and their type-specific required fields.
5. **Offer freshness policy:** define maximum age by service/price/availability type and how stale data is displayed or excluded.
6. **Referral data policy:** approve data categories, consent copy/versioning, retention, partner delivery channel and user withdrawal behavior.
7. **Commercial model:** decide whether the pilot is neutral/free, subscription-based or includes labelled paid placements. Commission/settlement remains deferred.
8. **Currency and comparison policy:** supported currencies, conversion provider and whether comparison is allowed when rates or pricing units differ.
9. **Partner content moderation:** rules for images, claims, complaints, ratings and disputes.
10. **Pilot geography and partner categories:** choose a limited operational scope for testing rather than attempting every tourism category at once.

## 19. Acceptance criteria for this architecture

This architecture is ready to guide detailed implementation only when:

- the owner accepts the partner marketplace/referral scope and explicit non-goals;
- ADR-0007's relationship to the expanded scope is recorded;
- user and admin authentication/authorization gates are resolved;
- organization roles and tenant isolation are specified;
- initial service categories and offer/price/availability contracts are approved;
- data-sharing consent and retention policy are approved;
- the implementation plan preserves existing trip, destination, RAG and catalogue work;
- all database changes are designed as additive, reviewed migrations and tested in disposable databases before any shared database action.

## 20. Repository references

All references below point to the repository revision reviewed for this proposal:

- [Reference Architecture](https://github.com/AiDev168/Ai_Tourism/blob/4e9b76a66a922981c72bfee04c6484735d8206c2/docs/reference/AI_Travel_Advisor_Reference_Architecture.md)
- [Architecture Analysis](https://github.com/AiDev168/Ai_Tourism/blob/4e9b76a66a922981c72bfee04c6484735d8206c2/docs/reference/ARCHITECTURE_ANALYSIS.md)
- [MVP Codex Handoff v0.5](https://github.com/AiDev168/Ai_Tourism/blob/4e9b76a66a922981c72bfee04c6484735d8206c2/docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.5.md)
- [ADR-0006 — Authentication and Session](https://github.com/AiDev168/Ai_Tourism/blob/4e9b76a66a922981c72bfee04c6484735d8206c2/docs/architecture/decisions/ADR-0006-authentication-and-session.md)
- [ADR-0007 — External Integrations in the MVP](https://github.com/AiDev168/Ai_Tourism/blob/4e9b76a66a922981c72bfee04c6484735d8206c2/docs/architecture/decisions/ADR-0007-mvp-external-integrations.md)
- [ADR-0008 — Centralized AI Provider Management](https://github.com/AiDev168/Ai_Tourism/blob/4e9b76a66a922981c72bfee04c6484735d8206c2/docs/architecture/decisions/ADR-0008-centralized-ai-provider-management.md)
- [MVP ERD v0.1](https://github.com/AiDev168/Ai_Tourism/blob/4e9b76a66a922981c72bfee04c6484735d8206c2/docs/architecture/ERD_MVP_v0.1.md)

---

**End of document.**
