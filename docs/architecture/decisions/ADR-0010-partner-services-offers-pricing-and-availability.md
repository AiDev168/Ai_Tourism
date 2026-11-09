# ADR-0010: Partner Services, Offers, Pricing, and Availability

- **Status:** Proposed — Owner Decision Required
- **Decision date:** Not accepted
- **Scope:** Logical commercial catalogue and freshness contract for a future partner marketplace
- **Related:** [Marketplace decision package](../PARTNER_MARKETPLACE_ARCHITECTURE_DECISION_PACKAGE_v1.0.md), [marketplace architecture proposal](../PARTNER_MARKETPLACE_AND_ADMIN_PLATFORM_ARCHITECTURE_v1.0.md), [ADR-0004](ADR-0004-hierarchical-destination-catalog.md), [ADR-0007](ADR-0007-mvp-external-integrations.md), [current ERD](../ERD_MVP_v0.1.md)

## Context

The current database has a unified place catalogue and knowledge records, but no partner-owned commercial services, offers, schedules, or availability. Company/service facts and dynamic commercial terms have different ownership, review, and freshness from destination knowledge. This proposal is logical only and does not prescribe physical tables.

## Decision drivers

- Keep durable destination identity and source-backed editorial knowledge separate from partner commercial data.
- Make price units, currency, time windows, and freshness explicit.
- Prevent unknown or stale availability from appearing current or guaranteed.
- Start with operationally manageable data collection and review.
- Preserve replaceable integration boundaries without introducing unapproved feeds or infrastructure.

## Options considered

| Option | Benefits | Costs and risks |
|---|---|---|
| Put partner services and prices into destination/RAG content | Reuses existing catalogue and retrieval concepts | Mixes ownership and volatility, weakens publication semantics, and makes stale commercial claims likely |
| Structured partner services and time-bound offers, manually maintained initially | Explicit validation, moderation, and freshness; suitable for a bounded pilot | Requires a new domain contract and partner operations |
| Launch immediately with live partner feeds | Potentially fresher availability at scale | Requires partner-specific contracts, credentials, retries, reconciliation, monitoring, and failure policy before pilot learning |

## Proposed decision

Recommend structured commercial data, manually entered and reviewed for the initial pilot, subject to owner approval:

1. A **service** describes the reusable thing a partner provides, its controlled category, localized presentation, delivery mode, supported destination associations, and explicitly known constraints.
2. An **offer** describes time- and condition-bound commercial terms for a service. A service may have multiple offers, dates, branches, or price bases.
3. Use a controlled service taxonomy. Required fields and constraints are category-specific and versioned. Do not use an unrestricted JSON object as the sole contract.
4. Represent schedules as explicit dates or validity windows, departures/time slots, and timezone where applicable. Capacity and availability must identify their source and observation time. `unknown` is never treated as `available`.
5. Each price states amount, ISO currency, basis/unit, applicable period, known taxes/fees, inclusions and exclusions. Unknown components remain explicitly unknown. Do not silently convert currencies or multiply incomparable units into a trip total.
6. Separate organization verification, service moderation, offer moderation, publication, pause/withdrawal, expiry, and suspension. Approval of an organization does not publish its content.
7. Track source/entry method, last-verified time, freshness expiry, responsible partner or approved feed, and review/policy version. Freshness thresholds are set by category and field; stale data is labeled and excluded from claims that require currentness.
8. Begin with manual partner entry and platform moderation. Future feeds/API adapters require explicit partner/provider approval, field mapping, authentication/secret handling, update cadence, conflict precedence, bounded retries, failure behavior, and auditability.
9. Keep commercial services, offers, prices, schedules, and availability outside `knowledge.destinations` and destination RAG documents. The catalogue remains the canonical place identity boundary under ADR-0004; RAG does not establish current commercial eligibility.
10. Do not claim a reservation, guaranteed capacity, final payable price, or real-time availability unless a separately approved capability supports that statement.

## Consequences

- **Security/privacy:** Partner writes require organization-scoped authorization under ADR-0009. Public reads expose only published fields and must not leak internal moderation notes or partner evidence.
- **Operations:** Manual freshness review is a real workload. A pilot must choose categories whose update burden can be sustained.
- **Migration:** No tables, columns, or migration are authorized. The current ERD does not contain these commercial entities.
- **RAG/catalogue:** Existing place identifiers may link a service to a destination, but a place record does not imply a partner service and a RAG document is not an offer source.
- **Scope:** Partner offer discovery and management exceed the current ADR-0007 link-only booking boundary and require explicit scope approval.

## Open owner decisions

- Initial categories and category-specific required fields.
- Localization requirements for partner-entered content and minimum locale coverage.
- Price provenance types accepted (partner-entered, provider-confirmed, or other) and display wording.
- Currency policy and whether conversion is allowed; if so, approved rate source and disclosure.
- Freshness/expiry thresholds for service profile, price, schedule, and capacity per category.
- How stale offers are displayed, excluded, or routed to a confirmation request.
- Moderation and appeal workflow, media rules, and partner evidence policy.
- Which manual update tools and operational staff are available for the proposed pilot geography.
- Whether and when partner APIs/feeds may be considered, with data and contract requirements.

## Implementation gate

No commercial schema, partner editing endpoint, offer API, public offer UI, or data import until the owner approves marketplace scope, ADR-0009 identity/tenancy gates, the initial taxonomy, moderation policy, privacy and freshness rules, and the ADR-0007 relationship. Any physical design and migration require separate review and isolated validation.

## Revisit conditions

Revisit after the pilot identifies measurable manual update failures, new service categories that cannot fit the approved contract, or a specific partner feed with an approved data and operational agreement.
