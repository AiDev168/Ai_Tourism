# ADR-0011: Partner Offer Matching and Ranking

- **Status:** Proposed — Owner Decision Required
- **Decision date:** Not accepted
- **Scope:** Eligibility, explanation, and ranking contract for future partner offers
- **Related:** [Marketplace decision package](../PARTNER_MARKETPLACE_ARCHITECTURE_DECISION_PACKAGE_v1.0.md), [marketplace architecture proposal](../PARTNER_MARKETPLACE_AND_ADMIN_PLATFORM_ARCHITECTURE_v1.0.md), [ADR-0003](ADR-0003-ai-and-rag-provider-boundaries.md), [ADR-0004](ADR-0004-hierarchical-destination-catalog.md), [ADR-0010](ADR-0010-partner-services-offers-pricing-and-availability.md)

## Context

The product architecture requires deterministic hard constraints and explainable recommendations. The existing recommendation boundary concerns destinations; it does not currently implement partner-offer matching. This proposal defines a future commercial decision contract without claiming runtime behavior or choosing a scoring algorithm.

## Decision drivers

- Eligibility constraints must not be overridden by a high score or model output.
- Results must reflect the traveler’s explicit needs and the actual commercial data state.
- Missing, stale, conflicting, or incomparable data must be visible and handled conservatively.
- Commercial incentives must not silently alter organic results.
- Decisions must be reproducible and explainable after the fact.

## Options considered

| Option | Benefits | Costs and risks |
|---|---|---|
| LLM selects and ranks offers from text | Flexible language interface | Non-deterministic; can invent facts, miss hard constraints, or conceal commercial influence |
| Deterministic eligibility then versioned, explainable ranking | Auditable hard constraints and repeatable outcomes | Requires explicit field semantics, policies, and score calibration |
| Paid placement blended into organic score | Commercially flexible | Misleads users and makes organic ranking non-transparent |

## Proposed decision

Recommend a two-stage deterministic process, subject to owner approval:

1. **Resolve input evidence.** Use approved canonical destination identities, explicit trip dates/date flexibility, time windows, party size, budget amount/currency/basis, service requirements, and constraints. Unknown values remain unknown; parsed destination text is not verified identity.
2. **Apply hard eligibility first.** Candidate organization and offer must be active, approved, published, in scope for the destination and applicable dates, and not expired, withdrawn, suspended, or blocked. Apply explicit service requirements, party-size limits, time compatibility, and other accepted hard constraints. Apply capacity only where a sufficiently fresh explicit capacity statement supports it.
3. **Treat incomplete commercial terms conservatively.** Unknown availability is not available. Unknown/stale price cannot be represented as within budget. Cross-currency or incompatible price-basis comparisons are not silently made. Depending on the future policy, such offers are excluded or returned in a separate `needs_confirmation` state; this policy remains open.
4. **Rank only eligible candidates.** Use a versioned deterministic score with declared components such as fit to requested service/interests, destination/itinerary fit, schedule convenience, comparable price fit, data completeness/freshness, and sufficiently supported quality signals. No unapproved component or weight is implied by this ADR.
5. **Return reasons and uncertainty.** Explain the factors actually used, hard constraints satisfied, unknown/stale fields, and data timestamp. Do not fabricate quality, value, schedule, availability, distance, route, or price claims.
6. **Separate sponsorship.** Organic ranking excludes commission, subscription status, or payment. If sponsored placement is later accepted, it is a separately identified, clearly labeled placement with an explicit policy and cannot bypass eligibility or safety constraints.
7. **Reproducibility.** Record or make reproducible the input snapshot/version, candidate-data version/freshness, eligibility policy, ranking algorithm/version and component values, tie-break rule, and result timestamp. Audit records must minimize traveler data.
8. **Provider boundaries.** Any future LLM may phrase explanations from supplied evidence only. It cannot establish eligibility, change scores, infer missing data, or override the deterministic result. Any AI calls remain behind the server-side gateway under ADR-0008.

## Consequences

- **Security/privacy:** Matching a saved trip requires authenticated ownership checks. Anonymous requests must not expose or persist user trip data before ADR-0006 is resolved.
- **Operations:** Scores require versioning, review, test fixtures, and drift/quality evaluation; weights are not selected here.
- **Migration:** No recommendation tables or schema changes are authorized. The current ERD has destination recommendations, not partner-offer matching records.
- **Commercial neutrality:** A future business model cannot silently rewrite relevance ranking.
- **Scope:** Offer matching is beyond the current destination-only functionality and needs explicit marketplace scope approval.

## Open owner decisions

- Required fields and policy for exclusion versus `needs_confirmation` when commercial data is incomplete.
- Which trip constraints are hard by service category and how conflicts are surfaced.
- Whether dates may be flexible and what schedule buffer policy is justified.
- Acceptable budget comparison and tax/fee treatment.
- Score components, weights, quality evidence, tie-breaking, minimum evidence, and ranking version policy.
- Whether sponsored placements are allowed at all; labeling, placement limits, and user controls if allowed.
- Audit retention, explainability detail, and traveler appeal/correction mechanisms.
- Evaluation criteria and minimum evidence before public pilot.

## Implementation gate

Do not implement offer retrieval, matching, ranking, or recommendation UI until ADR-0009 and ADR-0010 contracts, destination identity integration, eligible published data, privacy/session design under ADR-0006, and commercial neutrality policy are accepted. Require deterministic contract tests for hard filters, stale/unknown values, ranking reproducibility, and sponsored separation before release.

## Revisit conditions

Revisit when the pilot supplies real published offer data, when user evaluation exposes a ranking defect, or before introducing paid placement, new hard constraints, or model-assisted ranking explanations.
