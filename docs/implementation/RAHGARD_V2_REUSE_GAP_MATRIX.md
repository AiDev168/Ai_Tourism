# Rahgard V2 reuse and gap matrix

This matrix records the implementation boundary for `feat/rahgard-unified-travel-v2`.
The V2 work is additive. It does not change the live VPS, live PostgreSQL, DNS,
provider configuration, or publication status of any destination.

| Capability | Existing contract reused | V2 gap addressed | Remaining validation |
|---|---|---|---|
| Natural-language intake | `TripRequirementsV1`, backend interpretation and authenticated assistant-turn endpoint; deterministic parsing remains fallback | One authenticated workspace presents the initial request and conversation together; LLM and fallback field provenance is retained when the reviewed profile is saved | Real vLLM validation requires an authorized development endpoint; no paid call is made here |
| Requirements | Existing typed destination, origin, duration, date, travelers, budget, interests, preferences, hard-constraint and accessibility fields | Difficulty, weather preferences and local cuisine are carried through typed extraction, form state and persisted requirements | Existing records without these optional fields remain readable |
| Profile state | `travel.trips.confirmed_requirements`, trip versioning, profile confirmation and the existing consent assessment | Confirmation writes an immutable requirements revision and synchronizes the confirmed snapshot into conversation context without rewriting the original user message | Exercised with migration 0022 and authenticated Chromium against disposable PostgreSQL 17; live provider behavior remains separate |
| Itineraries | Published-catalogue itinerary and existing provisional itinerary contracts | Requirement/profile revisions are captured after itinerary edits; the same stable trip identity is used for authorized company revisions | Catalogue remains publication-gated; test publication existed only in disposable PostgreSQL and was not promoted |
| Companies | Existing `partner.organizations`, memberships, service, offer, schedule, price and availability entities; existing RLS/tenant checks | Explicit, selected-organization sharing, consent, revocation, immutable request/plan revisions and an authenticated in-app inbox | No email/SMS delivery or unauthenticated public request links |
| Sharing discovery | Existing partner organization RLS and approval lifecycle | A narrow eligible-organization view exposes only verified/active/approved recipients and only display fields | View access, explicit recipient selection, revocation and cross-tenant denial passed in isolated PG17 browser acceptance |
| AI privacy | Existing authenticated backend adapter; provider credentials stay server-side | No AI opt-in checkbox is introduced; the UI retains a non-blocking processing notice. Company disclosure has a separate explicit opt-in | Existing requirement consent and hard-constraint protections remain in force |
| Locale and intake controls | Existing locale-aware PWA, localized date handling and browser timezone derivation | Timezone selector and explicit location-as-origin button are removed from the intake controls without altering stored ISO date behavior | Verify Persian RTL, Arabic RTL and English LTR at mobile and desktop sizes |

## Precedence and identity

The original request remains immutable conversation content. The reviewed
`confirmed_requirements` object is the authoritative planning and sharing
snapshot. Trip `version` plus `requirements_revision` identify the accepted
profile revision. Per-field provenance distinguishes traveler text, LLM
interpretation, fallback interpretation, and a direct correction. A direct
traveler edit wins over later model suggestions. A company share is attached to
the stable trip UUID, names one or more eligible organization UUIDs, and can be
revoked. No share is created without the explicit share consent payload.

## Publication and test-data boundary

The existing production destination view remains the sole destination source
for evidence-backed recommendations. This work adds no destination rows and
does not weaken publication checks. Synthetic/test trips are not shareable and
request inbox queries exclude synthetic revisions. Company-entered content
continues to use existing review and publication rules; this migration does
not grant a tenant the ability to approve or publish its own content.

## Proposed additive migration

`engineering/pilot/sql/022_traveler_company_requests.sql` adds requirement
revision history and opt-in company request sharing/inbox records. The guarded
isolated PG17 browser workflow applied it through migration 0022. It has not
been applied to any persistent or live database. Its SHA-256 is recorded in
`RAHGARD_V2_LOCAL_ACCEPTANCE.md`.
