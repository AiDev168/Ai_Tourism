# ADR-0012: Partner Referrals, Consent, Attribution, and Commercial Model

- **Status:** Proposed — Owner Decision Required
- **Decision date:** Not accepted
- **Scope:** Non-transactional partner contact/referral and commercial measurement concepts
- **Related:** [Marketplace decision package](../PARTNER_MARKETPLACE_ARCHITECTURE_DECISION_PACKAGE_v1.0.md), [marketplace architecture proposal](../PARTNER_MARKETPLACE_AND_ADMIN_PLATFORM_ARCHITECTURE_v1.0.md), [ADR-0006](ADR-0006-authentication-and-session.md), [ADR-0007](ADR-0007-mvp-external-integrations.md), [ADR-0010](ADR-0010-partner-services-offers-pricing-and-availability.md)

## Context

ADR-0007 currently permits allowlisted outbound links and click tracking only for MVP booking actions. A partner referral/contact lead is a distinct event: it may transfer personal or trip information and creates operational obligations. The current ERD includes `integration.external_links` and `integration.outbound_clicks`, but no referral lead or booking-confirmation domain.

## Decision drivers

- Obtain specific, informed traveler consent before disclosing any personal or trip data.
- Minimize the data and recipients; record purpose and consent policy version.
- Distinguish a click, a lead, a partner response, and a confirmed booking.
- Avoid implying booking or revenue from referral status.
- Permit future commercial models without treating accounting or settlement as part of a pilot.

## Options considered

| Option | Benefits | Costs and risks |
|---|---|---|
| Outbound click only, as in current ADR-0007 | Lowest personal-data exposure; existing conceptual boundary | Does not create a platform-mediated contact lead |
| Traveler-consented contact/referral lead | Enables measurable introduction while remaining non-transactional | Requires authenticated or otherwise approved identity, consent capture, delivery, retention, support, and partner response operations |
| In-app reservation and transaction | Complete conversion workflow | Requires inventory, booking, payment, cancellation/refund, consumer-protection, and financial controls; outside current MVP authorization |

## Proposed decision

Recommend treating referral/contact as an optional, separately approved non-transactional capability:

1. A referral is created only after the traveler selects a named partner/action, sees the exact data categories and recipient, purpose, retention summary, and privacy notice, and affirmatively consents. No consent is inferred from a click, recommendation impression, account creation, or prior trip entry.
2. Default to the minimum contact channel and trip details needed for the selected request. Do not disclose full conversation history, unrelated interests, precise location, or the complete trip unless separately justified and explicitly consented.
3. Model distinct event concepts: **outbound click** (allowlisted link opened), **referral/contact lead** (consented request delivered or queued), **partner response** (acknowledgment/contact outcome), and **confirmed booking** (external claim or future integrated transaction). One must never be reported as another.
4. Referral lifecycle may cover requested, consent-recorded, queued, delivered, acknowledged, responded, closed, withdrawn, and delivery-failed states. Exact states and transitions need product approval. It is not a reservation or payment state machine.
5. Attribute an interaction to an offer/recommendation version using a bounded, non-secret identifier and timestamp. Deduplicate retries with an idempotency mechanism. Do not use attribution identifiers as cross-site tracking tokens or expose personal identity in URLs.
6. Partner responses update only the referral they are authorized to access. Travelers can see status and available withdrawal/correction behavior. Disputes and suspected misuse have an operator path.
7. Separate possible business concepts—commission, subscription, affiliate/referral fee, or neutral/free pilot—from actual financial obligations. A calculation record, if later authorized, is not settlement, invoice, payment, or ledger. No rate, tax treatment, payout, or financial settlement is chosen here.
8. Retention is purpose-limited and selected with the privacy policy. Keep consent and minimal audit evidence as required while deleting or de-identifying excess personal payloads. Partner reporting is aggregated and scoped; it must not reveal another partner's data or unnecessary traveler details.
9. The current allowlisted outbound click mechanism can coexist with referrals as a separate event path: preserve the safe link identifier/redirect model, and do not overload click rows with lead payloads. Any reuse of attribution infrastructure requires a reviewed contract.
10. This proposal does not amend ADR-0007. Adding referral submission or lead tracking to the MVP requires an explicit owner decision and a separately accepted ADR-0007 amendment/addendum. Booking, payment, ticketing, cancellation, refunds, commission settlement, and payouts remain out of scope.

## Consequences

- **Security/privacy:** Lead endpoints contain sensitive data and require ADR-0006 authentication, object-level authorization, consent evidence, abuse controls, and restricted partner access.
- **Operations:** Delivery failures, partner response expectations, support, deletion, consent withdrawal, and disputes require accountable ownership.
- **Migration:** No referral or financial tables are authorized. Existing outbound click records do not imply that lead storage is available or appropriate.
- **Commercial:** Business-model exploration does not grant permission to collect commissions or share user data.

## Open owner decisions

- Whether a referral/contact lead is included in the pilot or only outbound links are allowed.
- Whether the traveler must authenticate, and approved fallback behavior for an anonymous traveler.
- Exact data categories, consent wording/version, withdrawal/correction options, recipient disclosure, and retention/deletion schedule.
- Contact methods, delivery channel, partner response SLA, status vocabulary, disputes, and abuse process.
- Attribution window, deduplication scope, reporting granularity, and privacy thresholds.
- Pilot commercial model: neutral/free, subscription, affiliate, commission, or clearly labeled sponsorship.
- Whether any future calculation record is needed and who may review it; settlement remains separately gated.

## Implementation gate

Do not implement referral, lead submission, personal-data transfer, partner inbox, or commercial reporting until ADR-0006 is accepted; privacy notice, consent, retention, recipient, and operational policies are approved; ADR-0007's scope is explicitly amended if needed; and organization authorization under ADR-0009 is approved. No booking or financial settlement implementation is authorized.

## Revisit conditions

Revisit after owner approval of a bounded referral pilot, after privacy/legal review for its target geography, or before any commercial attribution or financial obligation is introduced.
