# Partner Marketplace Domain Contract v1.0

- **Status:** Proposed contract — Owner Decision Required
- **Prepared:** 2026-11-07
- **Scope:** Documentation-only domain, lifecycle, authorization, data classification, and API contract for a possible first partner marketplace pilot
- **Repository baseline inspected:** `fix/initialize-database-powershell-inspect-v1` at `838a613536c322354b91b1577845c54ea2357489`

> This document does not accept ADR-0009 through ADR-0013. Their status remains **Proposed — Owner Decision Required**. The contracts and defaults below are design recommendations for owner review, not implemented behavior or binding policy. No schema, migration, endpoint, handler, model, or UI is specified as approved by this document.

## 1. Authority and current boundaries

### 1.1 Existing accepted requirements

- The application remains a modular monolith. New logical boundaries do not authorize microservices, an event bus, Redis, or other infrastructure by themselves ([ADR-0001](decisions/ADR-0001-mvp-modular-monolith.md)).
- The destination domain is one hierarchical `knowledge.destinations` catalogue with explicit provenance and publication gates. A catalogue identity is a place identity, not a company, service, offer, schedule, or commercial claim ([ADR-0004](decisions/ADR-0004-hierarchical-destination-catalog.md)).
- Retrieval is replaceable and owner-controlled. RAG storage or retrieval does not establish semantic quality, and retrieved text cannot override deterministic hard constraints ([ADR-0003](decisions/ADR-0003-ai-and-rag-provider-boundaries.md)).
- ADR-0006 remains open. No protected user, partner, or admin functionality may be implemented until authentication/session and the relevant authorization decisions are approved and implemented safely ([ADR-0006](decisions/ADR-0006-authentication-and-session.md)).
- ADR-0007 currently allows allowlisted external links and click tracking. It excludes live inventory, reservations, ticketing, payments, cancellations, and refunds ([ADR-0007](decisions/ADR-0007-mvp-external-integrations.md)). A referral lead is not an outbound click and is not currently authorized.
- Future AI traffic must use the server-side AI Provider Gateway. Partner or marketplace administration does not grant provider-management authority; the provider control plane remains gated by its own administrator authentication requirements ([ADR-0008](decisions/ADR-0008-centralized-ai-provider-management.md)).

### 1.2 Proposed architecture recommendations

The [marketplace architecture proposal](PARTNER_MARKETPLACE_AND_ADMIN_PLATFORM_ARCHITECTURE_v1.0.md), [decision package](PARTNER_MARKETPLACE_ARCHITECTURE_DECISION_PACKAGE_v1.0.md), and [ADR-0009 through ADR-0013](decisions/ADR-0009-partner-organizations-and-tenant-boundaries.md) describe a separate commercial domain, manually managed pilot data, deterministic matching, consent proposals, and separated governance. These are proposals, not owner-approved scope.

The current [ERD](ERD_MVP_v0.1.md) has no partner organization, staff membership, service, offer, price, schedule, availability snapshot, referral lead, or marketplace authorization aggregate. Existing `identity.users`, `travel.*`, `knowledge.*`, `recommendation.*`, `integration.external_links`, `integration.outbound_clicks`, and `operations.audit_events` are current concepts/identifiers, not proof that partner behavior exists. This contract does not prescribe how to persist any new aggregate.

### 1.3 Domain separation

```text
knowledge / destination catalogue
  canonical place identity, source provenance, editorial publication, documents/chunks

partner commercial domain (proposed)
  organizations, staff memberships, services, offers, price terms,
  schedules, availability observations, moderation, referrals if approved

recommendation domain
  deterministic hard eligibility, then explainable ranking over permitted candidates

integration domain
  allowlisted external link resolution and click tracking under current ADR-0007

AI Provider Gateway
  separate protected control plane; no partner-role inheritance
```

Partner companies and commercial content must not be placed in `knowledge.destinations`, `knowledge_documents`, or `knowledge_chunks` as a substitute for a commercial domain. A commercial service may reference an approved canonical destination identifier. That reference does not verify the service, its price, or its availability. RAG may provide approved contextual descriptions but cannot supply or override current price, schedule, capacity, publication, or eligibility state. Semantic retrieval is not claimed as implemented.

## 2. Proposed first-pilot service categories

The following deliberately narrow list is a recommendation, not an approved taxonomy:

1. **Guided city and heritage walks** — partner-led tours with a defined meeting area, duration, dates/time slots, party-size limits, and explicit price basis.
2. **Hosted local cultural or culinary experiences** — scheduled, partner-hosted experiences with explicit duration, language where supplied, participant limits, inclusions/exclusions, and any relevant traveler-supplied constraints handled without assumptions.

For a first pilot, defer accommodation, general transport, ticketed admission, multi-day packages, and services requiring live inventory, regulated suitability claims, or extensive category-specific safety/accessibility data. Their omission is a pilot-scope recommendation, not a judgment that they are unsuitable long term. No listed category is approved until the owner chooses geography, partner operations, required fields, and moderation policy.

| Decision | Viable options | Trade-offs | Recommended default (proposal only) | Consequence of choice |
|---|---|---|---|---|
| Pilot categories | One category; the two above; broader accommodation/transport/activities | Narrow scope limits coverage but reduces contract and review burden; broad scope requires more complex requirements and operations | Start with the two listed categories | Establish category-specific contracts and test data only for selected categories |
| Taxonomy ownership | Fixed global taxonomy; platform-curated extensible taxonomy; partner free text | Fixed is simple but restrictive; curated extension supports growth; free text fragments matching | Platform-curated controlled taxonomy with owner-reviewed additions | Requires taxonomy governance and versioning before partner onboarding |

## 3. Domain concepts and relations

These are conceptual aggregates/contracts only, not proposed physical tables or ORM models.

| Concept | Responsibility | Key relationships |
|---|---|---|
| Partner organization | Legal/operating partner identity, lifecycle, verification and participation state | Owns or controls services; has memberships; may relate to branches/brands under explicit relationship rules |
| Organization relationship | Expresses branch, brand, parent/subsidiary, or other reviewed relationship | Connects organizations; grants no access by itself |
| Membership | Individual actor's scoped relationship and permissions for one organization | Connects authenticated identity to organization; revocable independently |
| Verification case | Evidence review, policy version, reviewer decision and re-review | Belongs to an organization; separate from organization participation and content moderation |
| Service | Reusable description of what the partner provides | Owned by an organization/authorized branch; categorized; may reference canonical destinations |
| Offer | Dated/condition-bound commercial terms for a service | Belongs to service and organization; has price terms, applicable dates, schedule and availability evidence |
| Price assertion | Amount and its complete comparison context, provenance, and validity | Belongs to an offer/revision; amount is never separated from currency, unit, applicability and source state |
| Schedule | Service occurrence/date/time window and timezone | Belongs to offer/service; may have one or more availability observations |
| Availability observation | Time-bounded report of availability/capacity from a named source | References a schedule/offer; does not guarantee future availability |
| Moderation decision | Review action with actor, reason, timestamp, policy version and outcome | Applies to organization evidence, service, or offer; distinct from partner authorship |
| Outbound click | Traveler opens an allowlisted external link | Uses current `external_link_id` / `outbound_click_id` concepts; is not a referral or booking |
| Referral and consent | Proposed personal-data disclosure request and its lifecycle, only if separately authorized | Refers to one recipient organization/offer and records purpose and exact disclosed data categories |
| Match decision | Reproducible eligibility outcomes and ranking evidence | References canonical destination IDs and offer revisions; must not persist traveler data before auth/privacy decisions |

## 4. Organization, verification, and membership lifecycles

### 4.1 Organization application lifecycle

Recommended organization application states:

```text
DRAFT -> SUBMITTED -> IN_REVIEW
                       ├-> CHANGES_REQUESTED -> SUBMITTED
                       ├-> REJECTED -> APPEAL_PENDING -> IN_REVIEW
                       └-> VERIFIED
```

- `DRAFT`: partner application not submitted.
- `SUBMITTED`: submitted evidence is fixed as a review version; partner may create a new revision after feedback.
- `IN_REVIEW`: assigned platform review is underway.
- `CHANGES_REQUESTED`: reviewer records required changes and reason; resubmission creates a new reviewable revision.
- `REJECTED`: review declined with reason and policy reference; appeal availability remains an owner policy decision.
- `APPEAL_PENDING`: appeal received; reviewer should differ from the original reviewer where operationally feasible.
- `VERIFIED`: evidence passed the approved verification policy. This does not make the organization commercially active or publish content.

Recommended transition authorities: an authorized partner owner submits and revises; a platform verification reviewer requests changes, rejects, verifies, and records appeal decisions. No applicant may verify itself. Every decision carries actor, timestamp, evidence references, reason, policy version, and review revision.

### 4.2 Participation and suspension lifecycle

Keep participation separate from verification:

```text
NOT_ACTIVE -> ACTIVE -> SUSPENDED -> ACTIVE
     └---------------------------> CLOSED
```

- `NOT_ACTIVE`: includes verified but not yet enabled, and organizations not yet verified.
- `ACTIVE`: eligible for exposure only if its services/offers independently satisfy publication and freshness rules.
- `SUSPENDED`: emergency or policy suspension. Immediately blocks new public offer exposure, new partner actions, and referral delivery; in-flight personal-data handling follows the incident/privacy policy. Preserve audit history.
- `CLOSED`: terminal for ordinary operations. Reopening requires a new, explicit platform decision and may require reverification.

Suspension may be initiated by an authorized platform governance role with a recorded reason and scope. Reinstatement requires an authorized reviewer, resolution evidence, and a new audit decision. Suspension of one organization does not implicitly suspend a related organization unless an approved policy and explicit decision says so.

### 4.3 Membership lifecycle

```text
INVITED -> PENDING_ACCEPTANCE -> ACTIVE -> SUSPENDED
    └-> EXPIRED                         └-> ACTIVE (reviewed reinstatement)
                                           └-> REVOKED
ACTIVE -> REVOKED
```

- Invitations are organization-scoped, addressed to a specific identity/contact, single-use, time-limited, and auditable. Invitation delivery and expiry settings remain owner decisions.
- `ACTIVE` membership grants only its assigned organization-scoped permissions.
- `SUSPENDED` blocks partner access pending review; `REVOKED` ends that membership. Revocation must promptly invalidate access and not delete authored history.
- Account suspension is an identity-wide control under the future ADR-0006 design; it is distinct from one membership suspension.
- A person may hold traveler and partner roles only if the approved identity policy permits it. Each request uses an authenticated principal and explicitly authorized context. Partner membership never reveals that person's traveler trip data.
- Company branch, brand, parent, or subsidiary relationships confer no inherited membership or data access by default.

## 5. Service and offer lifecycles

Service description and offer terms have separate lifecycles. The service can remain published while one offer expires; an offer cannot be exposed if its parent service/organization is ineligible.

### 5.1 Service lifecycle

```text
DRAFT -> SUBMITTED -> IN_REVIEW
                       ├-> CHANGES_REQUESTED -> SUBMITTED
                       ├-> REJECTED -> DRAFT (new revision)
                       └-> APPROVED -> PUBLISHED
PUBLISHED -> PAUSED -> PUBLISHED (review/partner reactivation as policy allows)
PUBLISHED -> WITHDRAWN
PUBLISHED -> EXPIRED (policy/validity driven)
```

- Partner editor creates/edits a draft; an authorized partner manager submits it.
- Platform moderator reviews a frozen revision and approves, requests changes, or rejects with reason.
- Only an approved revision can be published; publication also requires active organization participation and complete mandatory category fields.
- Partner may pause or withdraw its own published service. Platform may pause/suspend it for policy, safety, or data-quality reasons with reason and audit.
- Rejection does not erase history. A materially changed rejected/published service becomes a new revision and requires review.
- `EXPIRED` is reserved for a service with an explicit end-of-life policy; ordinary offer date expiry does not automatically expire the reusable service.

### 5.2 Offer lifecycle

```text
DRAFT -> SUBMITTED -> IN_REVIEW
                       ├-> CHANGES_REQUESTED -> SUBMITTED
                       ├-> REJECTED -> DRAFT (new revision)
                       └-> APPROVED -> PUBLISHED
PUBLISHED -> PAUSED -> PUBLISHED (revalidation as required)
PUBLISHED -> WITHDRAWN
PUBLISHED -> EXPIRED (validity ended)
```

Offer publication requires: active/verified organization under the approved policy; eligible published service; complete required price basis and applicability; schedule or explicit on-request semantics; valid destination relation where required; known moderation approval; and a freshness policy. Offer data revisions that materially change amount, currency, unit, applicability, schedule, capacity, or exclusions must be reviewed/re-published according to a future policy. Never silently mutate the terms a previous response represented.

### 5.3 Transition controls

| Transition/action | Proposed actor | Required evidence/control |
|---|---|---|
| Create/edit draft | Organization owner/manager/editor within membership scope | Organization ownership and editable state checked server-side |
| Submit | Organization manager or explicitly delegated editor | Revision snapshot; required-field validation |
| Request changes/reject/approve | Platform content moderator | Reason, reviewer identity, timestamp, policy version; author cannot approve own submission |
| Publish | Platform publisher/moderator after approval | Recheck organization status, service/offer revision, mandatory fields and publication policy |
| Pause/withdraw own content | Authorized partner manager/owner | Scope check; reason recommended; record status history |
| Suspend content/organization | Platform governance role | Reason and affected scope; prompt removal from future candidates |
| Resume/reinstate | Authorized platform reviewer, separate review if feasible | Revalidation and auditable decision |
| Expire | Deterministic policy process or moderator | Explicit validity boundary and recorded policy/version; expiry is not inferred from absent dates |

## 6. Price, schedule, availability, and freshness contracts

### 6.1 Price assertion

An amount is valid only as this inseparable tuple:

```yaml
amount: "1250000.00"        # decimal string; never binary floating point in the contract
currency: "IRR"             # explicit ISO 4217 code; no inferred rial/toman conversion
basis: "per_person"         # controlled unit
applicability:
  starts_at: "2027-04-01T00:00:00+03:30"
  ends_at: "2027-04-30T23:59:59+03:30"
taxes_fees:
  status: "unknown"         # included | excluded | partial | unknown
  description: null
inclusions: ["guided walk"]
exclusions: ["transport"]
provenance:
  source_type: "partner_manual"
  source_reference: "partner-submission-revision"
  asserted_at: "2027-03-20T10:00:00Z"
  last_verified_at: null
  freshness_expires_at: "2027-03-27T10:00:00Z"
```

This is illustrative contract data, not a real price. Decimal precision, allowed currencies, unit taxonomy, and date semantics require owner approval. A price assertion also requires a provenance class such as partner-entered, approved feed, or platform source. Partner entry is an attributed assertion, not independent verification.

Rules:

- `amount`, `currency`, `basis`, applicability, and provenance are required together for a comparable price claim. If any is missing, price comparison is unknown.
- Basis examples may include `per_person`, `per_group`, `per_room_night`, `per_vehicle`, or `per_service`; the taxonomy must be controlled and category-specific.
- Taxes/fees need `included`, `excluded`, `partial`, or `unknown` status and explanatory text when known. `unknown` cannot be rendered as included.
- Inclusions/exclusions are explicit lists; an empty list means “none supplied” only when paired with an explicit completeness state, not “nothing excluded.”
- Do not calculate a trip total from ambiguous basis, infer adult/child rates, compare unlike units, or convert currencies without a separately approved source-backed conversion contract and timestamp.
- A quote/indicative/partner-confirmed classification must be visible. This classification does not guarantee the partner will honor a price after the stated validity.

### 6.2 Schedule and availability observation

Separate the planned occurrence from its observed commercial availability:

```yaml
schedule:
  schedule_id: "opaque-schedule-id"
  starts_at: "2027-04-08T09:00:00+03:30"
  ends_at: "2027-04-08T11:00:00+03:30"
  timezone: "Asia/Tehran"
  applicability: "specific_departure"
availability_observation:
  state: "unknown"         # available | limited | unavailable | on_request | unknown
  capacity: null
  capacity_unit: "persons"
  source_type: "partner_manual"
  source_reference: "partner-submission-revision"
  observed_at: "2027-04-01T09:00:00Z"
  valid_until: "2027-04-02T09:00:00Z"
  freshness_policy_version: "pilot-policy-version"
```

All timestamps use RFC 3339 offsets; a named IANA timezone is also required for local recurring schedules and daylight-saving interpretation. A date-only schedule must declare its local timezone and date semantics. Do not infer timezone from destination coordinates or browser locale.

`capacity` is nullable and meaningful only with an explicit capacity unit, observation, and source. `available` means the source reported availability at `observed_at` for the stated scope. It is not a hold or guarantee. `limited` requires a partner-supplied/approved explanation or known capacity; do not invent a numeric remainder.

### 6.3 Freshness and conflict states

Freshness is evaluated against owner-approved field/category policies; it is not assumed from a universal hard-coded duration.

| Freshness state | Definition | Safe behavior |
|---|---|---|
| `current` | Required observation exists, is within its policy freshness window, applies to requested time, and no unresolved conflicting assertion exists | May be used for the field only; still not a guarantee |
| `stale` | Observation exists but exceeds its freshness window; explicit validity may remain open | Never state as current; normally `needs_confirmation` or excluded per approved category policy |
| `expired` | Explicit validity end has passed, offer validity has ended, or source explicitly withdrew the assertion | Do not use for positive eligibility; candidate is ineligible for that date/offer |
| `unknown` | No assertion, missing required context, or the assertion cannot be interpreted | Never assume available/within-budget; `needs_confirmation` where it is not already a hard failure |
| `conflict` | Equally applicable assertions disagree and policy cannot deterministically select one authoritative current value | Do not select the favorable value; `needs_confirmation` or ineligible according to the accepted hard rule |

Precedence must be source/policy-based and versioned, not “newest row wins” unless the approved source policy defines that rule. An unavailable database or missing catalogue is not evidence that the partner offer is unavailable; it is a service failure and no positive result may be asserted.

Open freshness decisions include allowed provenance classes, maximum age by field/category, whether partner self-attestation can satisfy publication, conflict precedence, stale-data display/exclusion, and who owns refresh operations. The recommendation is manual review before expiry and fail-closed matching for material stale price/capacity facts.

## 7. Referral and consent contract

### 7.1 Current boundary and proposed expansion

Current ADR-0007 authorizes allowlisted outbound links and click tracking only. An outbound click has no implicit data-sharing consent. It may record a link identifier and permitted minimal attribution context; it must not contain referral payloads.

A platform-mediated contact/referral lead is a proposal only. It requires explicit owner approval of scope and a separately accepted ADR-0007 amendment/addendum before implementation. Until then, the permitted behavior is the current allowlisted outbound action; no lead submission, partner inbox, or personal-data transfer is authorized.

### 7.2 Consent receipt (illustrative)

If the owner separately approves leads, each disclosure must bind to:

```yaml
recipient:
  organization_id: "opaque-organization-id"
  displayed_name: "Partner name shown to traveler"
purpose: "Request that this partner contact me about the selected guided experience."
policy_version: "referral-privacy-policy-version"
data_categories:
  - "contact.email"
  - "trip.destination_ids"
  - "trip.requested_date_range"
consented_at: "2027-03-20T10:00:00Z"
withdrawn_at: null
```

This is a documentation example only. Consent must show the actual recipient, purpose, policy version, and exact data categories before submission. Category names are not permission to include hidden fields: payload projection must include only the selected categories and disclose the exact values/summary being sent. No full conversation, unrelated profile, precise location, or entire trip is shared by default.

### 7.3 Proposed lead lifecycle

```text
DRAFT -> AWAITING_CONSENT -> CONSENTED -> QUEUED -> DELIVERED
                 └-> CANCELLED       ├-> WITHDRAWN (before delivery)
                                     └-> DELIVERY_FAILED -> RETRY_PENDING/FAILED_FINAL
DELIVERED -> ACKNOWLEDGED -> RESPONDED -> CLOSED
DELIVERED/ACKNOWLEDGED -> WITHDRAWAL_REQUESTED -> CLOSED (policy-dependent)
```

- No lead exists before explicit consent.
- Delivery is idempotent; retries cannot create duplicate leads or broaden disclosed data.
- Withdrawal before delivery cancels the transfer. After delivery, the platform can stop future processing and send a deletion/cessation request where policy permits, but cannot promise recall of data already received; this limitation must be disclosed before consent.
- Partner status updates are scoped to a delivered referral; they cannot change consent evidence or claim a booking.
- `RESPONDED` means partner response, not accepted offer, booking, payment, or revenue.
- Retention durations for payload, consent receipt, delivery logs, disputes, and audit are unresolved. Recommended principle: minimize payload retention, publish explicit period/purpose before collection, retain only necessary evidence for the approved period, then delete or de-identify. Do not invent a numeric retention period.

### 7.4 Distinct event semantics

| Event | Meaning | Does not mean |
|---|---|---|
| Outbound click | Traveler opened a server-allowlisted partner link | Consent, lead, availability, booking, or revenue |
| Referral lead | Explicitly consented data was queued/delivered for a stated purpose | Reservation or partner acceptance |
| Partner response | Partner acknowledged or replied to a lead | Booking or payment |
| Confirmed booking | A future external claim or separately authorized transactional fact | In scope for this pilot |

## 8. Proposed authorization matrix

This is a least-privilege proposal, not an approved role system. All protected checks require ADR-0006 authentication/session and authorization decisions. Every request derives actor identity server-side; client-supplied `organization_id`, role, `user_id`, or resource ownership is never authority.

Legend: **Own** = only organization-scoped records the actor can access; **Assigned** = only explicitly assigned review scope; **No** = denied; **Public** = explicitly published allowlist only; **Provider-only** = ADR-0008 control plane.

| Capability | Public traveler/anonymous | Partner owner | Partner manager | Catalogue editor | Referral operator | Organization reviewer | Content moderator/publisher | Platform governance admin | AI Provider admin |
|---|---|---|---|---|---|---|---|---|---|
| Read public published partner profile/service/offer fields | Public | Public + Own | Public + Own | Public + Own | Public + Own | Assigned | Assigned | Policy-scoped | No implicit access |
| Create/edit organization profile and branches | No | Own | Own, delegated | No | No | No | No | Exceptional audited override only | No |
| Invite/revoke staff and assign partner roles | No | Own, owner-level constraints | Delegated if approved | No | No | No | No | Emergency support only, audited | No |
| Edit/submit service and offer drafts | No | Own | Own | Own, category fields | No | No | No | No | No |
| Approve/publish own organization/service/offer | No | No | No | No | No | Organization evidence only | Assigned content only; cannot approve own submission | Exceptional separation-controlled | No |
| Verify/suspend/reinstate organization | No | No | No | No | No | Assigned verification/suspension; no self-review | No unless explicitly granted separate role | Emergency/oversight only with audit | No |
| View consented referral payload | No | Own only if explicitly authorized | Own, policy-limited | No | Own assigned leads only | No by default | No by default | Break-glass only if approved and audited | No |
| Update referral status | No | Own, permitted statuses | Own | No | Own assigned leads | No | No | Oversight only | No |
| View aggregate partner analytics | No | Own aggregates | Own, limited | No | Own referral metrics if authorized | Assigned operations | Assigned moderation metrics | Platform-wide aggregate by policy | No |
| Manage marketplace taxonomy/policy | No | No | No | No | No | No | Assigned policy | Yes, least privilege | No |
| Configure AI providers/models/secrets/routing | No | No | No | No | No | No | No | No by marketplace role | Provider-only under ADR-0008 |

Role definitions are mutually exclusive capabilities, not assumptions that one person has only one role. Separate grants and conflict checks are needed if a person holds multiple roles. Platform role names, emergency access, dual control, and staff separation remain owner decisions. In particular, marketplace governance must never imply AI Provider admin. Anonymous users receive only public allowlisted reads and currently accepted outbound-click behavior; no protected operation or personal referral is available.

## 9. Field-level data classification

Classification is based on the most sensitive constituent field; a container may need field-level projection. Proposed classes:

- **Public:** approved for unauthenticated publication after moderation.
- **Partner-private:** visible only to authorized staff of the owning organization and explicitly authorized platform roles.
- **Platform-admin-only:** restricted review/security/operational data; not partner-visible by default.
- **Personal/referral-sensitive:** traveler-identifying or trip-linked data, consent evidence, and referral payload; narrowly scoped and never public.

| Field/data group | Proposed classification | Exposure rule |
|---|---|---|
| Published organization display name, approved public profile, public contact channel | Public | Only published allowlisted values; exclude private contacts and verification material |
| Organization legal identifiers, ownership evidence, registration documents, reviewer notes | Platform-admin-only; limited evidence references may be partner-private | Never exposed in public catalog or unrelated partner views |
| Branch public name/address/contact | Public after moderation | Do not infer service location or precise operational details from organization address |
| Membership identity, invite token/state, role, access history | Partner-private; token is secret-bearing | Visible only to authorized organization owner/manager and platform support as approved; never return tokens after use |
| Draft/unpublished profile/service/offer content | Partner-private | Owning organization and assigned moderators only |
| Published service description/category/destination IDs/duration/declared language | Public | Only approved revision; factual claims retain source/attribution where applicable |
| Offer amount, currency, unit, applicability, inclusions/exclusions, taxes/fees, freshness | Public if published; Partner-private before publication | Display all comparison context and freshness; never expose internal review fields |
| Raw source/feed credentials and integration secrets | Platform-admin-only / secret | Server-side secret handling; never client, partner API, logs, or RAG chunks |
| Schedule and availability snapshot | Public if approved and currently displayable; Partner-private before publication | State and timestamp disclosed; stale/unknown never shown as available |
| Moderation decision, reviewer identity, rationale, internal flags | Platform-admin-only; limited outcome/revision request may be shared with owner | No leakage to unrelated partners or public users |
| Destination canonical ID/name and approved public aliases | Public according to catalogue boundary | Resolve only through approved production catalogue; destination data is not partner-owned |
| Traveler public-session input without identity | Personal/referral-sensitive if collected | No persistence or sharing under this contract; trip inputs remain subject to existing privacy gates |
| Traveler identity/contact data | Personal/referral-sensitive | No partner transfer absent explicit approved consent and ADR-0006 design |
| Trip destination/date/party/budget/preferences and any summary | Personal/referral-sensitive when associated with a traveler/referral | Share only exact categories and values consented for the named recipient and purpose |
| Consent receipt, withdrawal, delivery status, partner response | Personal/referral-sensitive; selected audit metadata platform-admin-only | Visible to traveler and authorized recipient/operator on a minimum-necessary basis |
| Outbound click identifier and timestamp | Operational; personal/referral-sensitive if linked to a user/trip | Follow current ADR-0007 minimization; do not use as referral payload or cross-site tracking token |
| Match explanation and score components | Public for published offer result; internal snapshot/audit platform-admin-only | Expose user-safe reasons, not private partner signals or personal data of others |
| Platform audit events and security investigations | Platform-admin-only | Restrict, redact payloads, and retain per approved policy |
| Provider profile/model/endpoint/credential/route details | Platform-admin-only under separate ADR-0008 control plane | No marketplace role or ordinary product surface access |

## 10. Deterministic matching contract

### 10.1 Inputs and evaluation order

Evaluate a specific offer revision against explicit trip facts and current approved commercial assertions. Inputs may include canonical destination identity, dates or date flexibility, requested time window, party size, budget amount/currency/basis, service category, and explicit traveler constraints. Unknown traveler values remain unknown. A place name extracted from text must first pass the existing destination resolution/publication contract; it is not independently verified by matching.

Order is mandatory:

1. Check source/publication/organization/service/offer state.
2. Check destination and date applicability.
3. Check category-specific required fields, time compatibility, party-size limits, and explicit hard traveler constraints.
4. Check price comparability and freshness when budget is a hard constraint.
5. Check availability/capacity evidence and freshness where the category policy requires it.
6. Assign deterministic outcome and reason codes.
7. Rank only `eligible` results using approved soft criteria.

### 10.2 Outcomes

| Outcome | Exact rule | User-facing treatment |
|---|---|---|
| `ineligible` | At least one known hard constraint fails, offer/service/organization is not currently publishable, offer is withdrawn/expired, or an explicit conflict proves the hard condition is unmet | Exclude from recommendations; safe reason may be returned where it does not expose private data |
| `needs_confirmation` | No known hard failure, but at least one material required fact is missing, stale, expired-but-correctable, ambiguous, or conflicting such that eligibility cannot be established | Do not rank as eligible or claim availability/price fit; present a confirmation action only if policy and interaction are approved |
| `eligible` | Every mandatory hard predicate is known, applicable, fresh enough under the approved category policy, and satisfied | Candidate may enter soft ranking; still display source/freshness and no guarantee language |

Precedence: **known hard failure wins** (`ineligible`), even if other fields are unknown. Otherwise material uncertainty yields `needs_confirmation`. Only complete satisfied mandatory predicates produce `eligible`. Whether a particular unknown field is material or whether a `needs_confirmation` result is displayed is category policy requiring owner approval.

### 10.3 Hard filters versus soft ranking

Proposed hard filters include active/verified organization, active published service and offer, destination match, date/time applicability, party-size limits, explicit service requirements, non-expired offer, and required freshness/availability/price conditions. Any relevant hard failure cannot be offset by score, popularity, partner payment, or model output.

Soft criteria may include explicit interest fit, non-hard schedule convenience, geographic fit among already eligible destination-linked services, comparable price fit (same currency and comparable basis only), completeness/freshness within the eligible range, and quality/reliability evidence with source and sample sufficiency. Weights, tie-breaks, score range, and feedback anti-abuse remain open. Commission/subscription status is excluded from organic score. If sponsored placement is ever accepted, it is a separate, conspicuously labeled slot that still passes all hard filters.

Every result is reproducible from the input snapshot, candidate revision, observation IDs, policy version, algorithm version, score components, and deterministic tie-break rule. Do not persist traveler-owned snapshots until ADR-0006/privacy decisions authorize it.

## 11. Documentation-only API examples and schema shapes

These examples are OpenAPI-compatible design material only. They do not authorize, declare present, or implement these routes. All protected operations require accepted ADR-0006 identity/authorization and future API review. The only existing traveler-action boundary remains ADR-0007 outbound links/clicks. Referral submission below is explicitly gated by owner approval and an ADR-0007 amendment/addendum.

### 11.1 Proposed public offer query

Illustrative route: `GET /api/v1/partner-offers?destination_id=...&category=...&date=...`

It would return only currently published public fields. It must not return drafts, moderation notes, legal evidence, private contacts, stale availability as current, or raw partner data. Pagination must be stable and bounded. No query parameter may authorize access to a private organization.

### 11.2 Proposed match request and response

```yaml
openapi: 3.1.0
components:
  schemas:
    MoneyConstraint:
      type: object
      required: [amount, currency, basis]
      properties:
        amount: { type: string, pattern: '^[0-9]+([.][0-9]+)?$' }
        currency: { type: string, description: ISO 4217 code; owner-approved supported set required }
        basis: { type: string, description: Controlled comparable unit }
    PartnerMatchRequest:
      type: object
      required: [destination_ids, service_categories]
      properties:
        destination_ids:
          type: array
          minItems: 1
          items: { type: integer, format: int64, minimum: 1 }
        date_range:
          type: [object, 'null']
          properties:
            start_date: { type: string, format: date }
            end_date: { type: string, format: date }
            flexible: { type: boolean, default: false }
        party_size: { type: [integer, 'null'], minimum: 1 }
        budget: { oneOf: [{ $ref: '#/components/schemas/MoneyConstraint' }, { type: 'null' }] }
        service_categories:
          type: array
          uniqueItems: true
          items: { type: string }
        hard_requirements:
          type: array
          items: { type: string, description: Controlled requirement key }
    PartnerMatchResult:
      type: object
      required: [offer_id, outcome, reason_codes, evaluated_at, policy_version]
      properties:
        offer_id: { type: string, format: uuid }
        outcome: { type: string, enum: [eligible, needs_confirmation, ineligible] }
        reason_codes: { type: array, items: { type: string } }
        score: { type: [number, 'null'], description: Present only for eligible candidates ranked under an approved algorithm }
        price_freshness: { type: string, enum: [current, stale, expired, unknown, conflict] }
        availability_freshness: { type: string, enum: [current, stale, expired, unknown, conflict] }
        evaluated_at: { type: string, format: date-time }
        policy_version: { type: string }
        algorithm_version: { type: [string, 'null'] }
```

Example request:

```json
{
  "destination_ids": [2401],
  "date_range": { "start_date": "2027-04-08", "end_date": "2027-04-08", "flexible": false },
  "party_size": 2,
  "budget": { "amount": "3000000", "currency": "IRR", "basis": "per_person" },
  "service_categories": ["guided_city_walk"],
  "hard_requirements": []
}
```

Example response (illustrative only):

```json
{
  "results": [
    {
      "offer_id": "00000000-0000-4000-8000-000000000001",
      "outcome": "needs_confirmation",
      "reason_codes": ["AVAILABILITY_STALE"],
      "score": null,
      "price_freshness": "current",
      "availability_freshness": "stale",
      "evaluated_at": "2027-04-01T10:00:00Z",
      "policy_version": "pilot-policy-version",
      "algorithm_version": null
    }
  ]
}
```

In a future authenticated saved-trip flow, the server must resolve the trip from the authenticated principal; a caller-supplied `trip_id` is never authority. For an ephemeral request, avoid persistence and avoid accepting a complete raw conversation. The eventual choice between these modes is blocked by privacy/session decisions.

### 11.3 Proposed partner submission shape

A future protected operation could accept a service/offer draft revision with controlled category, localized content, canonical destination IDs, complete price tuples, schedules, provenance, and freshness metadata. It must reject arbitrary publication state, organization owner IDs, reviewer fields, or client-supplied approval. The server derives organization scope from membership. Exact route, payload, revision semantics, and category schemas require a later API design task.

### 11.4 Referral schema and API gate

No referral route is currently authorized. If the owner accepts referral scope and ADR-0007 is separately amended, a future request must bind a selected offer/recipient, purpose, policy version, exact data categories, consent timestamp, and an idempotency key. The response must not call the lead a booking and must not echo sensitive payload. Authentication, consent withdrawal, retention, delivery retries, and recipient access all require accepted policy before an endpoint is designed.

## 12. Existing identifiers, reuse, and new aggregates

### 12.1 Existing identifiers that may be referenced

- `knowledge.destinations.destination_id`: canonical place identity, only where the approved production catalogue permits use. Keep the existing resolver behavior; do not resolve partner content against pending, synthetic, or unverified rows.
- `identity.users.user_id`: current identity-related identifier, but it does not mean authentication/session is implemented or selected. Use only after ADR-0006 and role mapping are approved.
- `travel.trips.trip_id`, itinerary and stop identifiers: existing travel concepts; access remains blocked by authentication/privacy gates. They are not partner ownership keys.
- `recommendation.recommendation_request_id` / `recommendation_id`: existing destination recommendation concepts, potentially attributable only through a separately reviewed contract and authorized context.
- `integration.external_links.external_link_id` and `integration.outbound_clicks.outbound_click_id`: current allowlisted click concepts. Reuse only for the existing click meaning; do not overload them for referral payloads.
- `operations.audit_events`: current general audit concept. Its existence does not establish adequate partner-specific authorization, retention, or event policy.

No partner organization, membership, service, offer, price, schedule, availability, moderation case, consent receipt, or referral identifier exists in the current ERD. No identifier or relationship is created by this document.

### 12.2 Genuinely new logical aggregates (proposed)

At minimum, future domain design must separately reason about: organization and relationship; membership/invitation; verification case/evidence reference; service and revision; offer and revision; price assertion; schedule and availability observation; moderation decision; match evaluation; and (only if approved) consent/referral/delivery/status. Whether these share persistence boundaries is a later design decision. Do not force these concepts into destination, trip, click, or RAG entities for convenience.

## 13. Owner decisions and recommendation register

| Decision requiring owner approval | Viable options and trade-off | Recommended default (not accepted) | Consequence to resolve before implementation |
|---|---|---|---|
| Marketplace scope vs current MVP | Keep ADR-0007 link-only; approve non-transactional offers; approve offers plus leads | Decide a bounded non-transactional pilot separately; keep link-only behavior until accepted | Scope and any ADR-0007 amendment must be explicit |
| Authentication and identity | Select one identity/session design; defer all protected work | Keep ADR-0006 open until chosen; implement no protected feature meanwhile | No partner/admin/user-owned routes until approved and tested |
| Pilot categories/geography | One category, the two suggested categories, or broader set | Two bounded experience categories in a selected geography | Required fields, source/verification and operations depend on choice |
| Organization model and roles | Flat partners; explicit branch/brand relations; separate legal entities | Explicit relations, no permission inheritance; individual memberships | Needs tenant policy, invitations, recovery, suspension, audit |
| Verification and moderation | Platform review only; evidence tiers; third-party verification | Manual platform review with recorded evidence/policy and appeal | Evidence rules vary by geography; no legal assumptions may be encoded |
| Price contract | Exact-only; permit indicative assertions; support currency conversion | Explicit unit/currency/applicability and provenance; no conversion initially | Budget matching and display vary with the selected policy |
| Freshness | One TTL; category/field-specific TTL; live feed required | Category/field-specific manual freshness; fail closed on stale material facts | Owner must assign refresh responsibility and thresholds |
| Unknown/conflicting data | Exclude; show `needs_confirmation`; select source precedence | No positive claim; hard failure wins, otherwise material uncertainty needs confirmation | Candidate exposure and user wording need category policy |
| Consent-based referrals | Not in pilot; future lead with explicit consent; anonymous contact | Preserve current click-only scope until explicit approval; if added, named-recipient granular consent | Requires ADR-0007 amendment, privacy review, retention and operations |
| Retention | Short fixed window; purpose-specific schedule; minimal audit-only retention | Minimize and set explicit purpose-specific retention before collection | No referral collection until duration, deletion, withdrawal and audit policy exist |
| Commercial model/sponsorship | Neutral/free; subscription/affiliate; commission; labeled placement | Neutral pilot, no paid organic ranking; defer all settlement | Monetization and disclosure policy required before commercial use |
| Admin governance | Combined admin; separate partner/platform/provider capabilities | Separate marketplace governance from ADR-0008 provider control | Role matrix, bootstrap, separation of duties and audit are gates |
| Physical model/API | Model now; defer until domain decisions; reuse unrelated entities | Defer physical design until this contract is approved | Later design must prove tenant isolation, exact publication, and migration safety |

## 14. Implementation and release gates

Before any implementation task is authorized, the owner must review and decide:

1. Whether partner marketplace is in MVP and whether ADR-0007 scope is amended; outbound click remains the only currently accepted partner action.
2. ADR-0006 identity/session, user identity, partner membership, administrator bootstrap/recovery, and object-level authorization.
3. Pilot geography and service categories; verification evidence, taxonomy, localization, moderation, and appeals.
4. Price/provenance vocabulary, timezone/date semantics, freshness policies, conflict handling, and manual operations ownership.
5. Role matrix, separation of duties, referral-data classification, consent, withdrawal, retention, support, and audit policy.
6. Deterministic eligibility and score components, unknown-field behavior, reproducibility, and commercial neutrality.
7. API contract review and a separate physical-domain design; none of these examples are implemented endpoints or migration authorization.
8. Security/privacy review plus positive and negative authorization tests before protected surfaces or partner data are exposed.
9. Real partner data and publication workflow before recommendations; no synthetic or unreviewed records may be shown as production offers.
10. ADR-0008 gateway/admin gates before any AI/provider capability; partner/provider control planes remain separate.

Do not start Task 3 automatically. This document is a review artifact only.

## 15. Unresolved conflicts and explicit non-goals

The broad partner architecture proposes a non-transactional marketplace and possible consent-based referrals; current accepted ADR-0007 remains outbound-link/click-only. This is a scope conflict requiring owner decision, not permission to infer a referral capability. Any proposed amendment must explicitly say whether it adds public partner offer discovery, partner-submitted content, consented leads, and/or additional click attribution. It must continue excluding reservation confirmation, inventory holds, ticketing, payment, cancellations, refunds, commission settlement, and payouts unless separately approved.

This contract does not implement or authorize schema changes, migrations, ORM models, handlers, APIs, UI, authentication, provider controls, database access, external APIs, or shared infrastructure changes. It does not alter destination catalogue/resolver behavior or implement RAG/semantic retrieval.
