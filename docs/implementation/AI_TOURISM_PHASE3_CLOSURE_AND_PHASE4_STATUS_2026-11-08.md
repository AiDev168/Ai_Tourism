# AI Tourism — Phase 3 Closure and Phase 4 Readiness

**Status date:** 2026-11-08  
**Verified branch:** `fix/initialize-database-powershell-inspect-v1`  
**Verified HEAD:** `a921277cd8488b6b5959429c7cb74ff5a05be462`  
**Milestone:** Pilot Readiness & Owner-RAG Integration

## Phase 3 decision

Phase 3's final budget-contract and preference-semantics correction is accepted. The independent Phase 3 status review records the integrated result as **GO**. The Phase 4 verification run also exercised the consent/history/empty-catalogue path through a real browser and isolated PostgreSQL. This decision is not a public-pilot or production approval.

Accepted behavior remains:

- Budget amount, denomination, currency and original expression are retained without silent conversion; legacy columns remain null where they cannot represent a value losslessly.
- Explicit soft preferences are distinct from hard requirements. Ambiguous constraints remain mandatory. Accessibility and safety-critical constraints are non-waivable. Advisory consent is explicit, profile-bound and reported as `not_evaluated`.

## Phase 4 implementation status

The following facts were checked against the repository at the verified HEAD and, where stated, exercised in this Phase 4 run:

| Area | Current evidence | Status |
|---|---|---|
| Traveler authentication | PostgreSQL-backed OTP/session, CSRF, principal and owner-scoped trip flows are present. `AUTH_ENABLED` defaults false; production authentication remains prevented by configuration. | Implemented locally; production gated |
| Structured catalogue | The public adapter reads approved production views only. The three-locale browser run received the honest empty production-catalogue state. | Safe empty path verified; no approved pilot corpus |
| Semantic retrieval | `backend/app/modules/retrieval` is a placeholder. `backend/app/modules/recommendation/retrieval.py` is exact structured catalogue retrieval, not semantic RAG. No owner interface or versioned callable contract is in this repository. | Blocked on owner contract |
| AI Provider Gateway | A small generic, injected capability boundary and deterministic test adapter exist. There is no provider routing/configuration, live provider adapter, fallback, admin route or control plane. | Internal seam only; provider activation gated |
| Editorial content | Candidate and review records remain outside traveler production views. The typed non-spatial culinary contract and approved-view endpoint exist separately from spatial destinations, but no approved culinary items or editorial source publication were established by this work. | Blocked on owner/editorial decisions |
| Authentication operations | Production SMS, carrier testing, account recovery, session operations, administrator MFA/bootstrap/recovery and incident ownership remain open. | Production gated |
| PWA staging/mobile | The service worker excludes API paths from cache and Vite has local development/preview proxying. No approved HTTPS staging origin or physical Android/iOS acceptance environment was supplied. | Local browser verified; staging/device gate open |

The isolated SQL validation reported an immutable seed/migration manifest of 698 rows. That is test-fixture evidence, not a production catalogue count. Production spatial recommendations remained empty during the browser journey; the page's separately labelled inspiration content is not endpoint-backed recommendation output. The existing culinary API reads a separate approved non-spatial publication view, but this run did not publish or return candidate culinary content.

## Content coverage audit before geography approval

No pilot geography or user promise was approved, so there is no honest region-specific coverage numerator/denominator or minimum threshold to report. The current repository contracts and evidence show these readiness states:

| Content class | Contract/evidence available | Coverage or publication state | Missing before pilot |
|---|---|---|---|
| Spatial places/areas | Production view requires eligible publication and provenance; typed adapter exposes canonical identity, locale-reviewed names/aliases, type and province/city. Source projection carries source URL/role and retrieved/validity timestamps. | Browser API returned zero approved spatial candidates; runtime alias manifest is empty. | Owner-selected geography; exact locale coverage inventory; coordinate roles and sourced facts; rights/source registry policy; named editorial reviewer and freshness cadence. |
| Culinary knowledge | Separate typed `/api/v1/catalog/culinary` read path projects only `knowledge.production_culinary_knowledge`; localized records contain claim-level provenance. It is not a spatial destination or itinerary stop. | This run published no addendum candidates and demonstrated no approved production culinary content. | Approved source/right-to-use review, locale-native editorial review, reviewer/publication authority and per-claim freshness policy. |
| Volatile or safety-sensitive facts | Existing contract preserves unknown values and does not infer operational data. | Prices, opening hours, schedules, transport, routing, weather, venue availability, accessibility and difficulty were not established as current sourced facts here. | Select each fact only if pilot scope requires it; identify an approved source, freshness interval and reviewer before display. |

For an owner-approved region, the first coverage matrix should count exact canonical identities, per-locale names and descriptions, independently sourced claims, coordinate role for spatial entities, validity/freshness state, review state, and each requested volatile/access field as evidenced or unknown. The launch threshold must be chosen only after the region and user promise are approved.

## Phase 4 owner decisions still required

- Supply the actual owner-RAG request/response and provenance contract, its version/error/deployment boundaries, and an approved evaluation set.
- Select pilot geography and user promise; approve source classes/rights, source registry policy, editorial reviewer, locale review and freshness process, plus a measurable coverage matrix.
- Decide provider/data-processing region, secret storage, usage/cost limits, consent and live-call authorization before any external AI processing.
- Approve production SMS vendor/route after representative MCI, Irancell and Rightel tests; approve session/OTP operations, phone recovery, administrator MFA, first-admin bootstrap, recovery and break-glass controls.
- Resolve privacy notice, conversation and backup retention, support/incident ownership, hosting region, public origin, TLS/trusted proxy and backup/restore operations.
- Supply approved staging hosting and real Android/iOS devices for physical installation acceptance.

## Verification record

Fresh Phase 4 commands, exit codes, skips, browser evidence and the final decision are recorded in [the Phase 4 pilot-readiness report](PHASE4_PILOT_READINESS_REPORT_2026-11-08.md). Phase 3's earlier integrated counts are owner-reported evidence retained in the supplied readiness handoff; they are not represented as newly rerun by this status document.
