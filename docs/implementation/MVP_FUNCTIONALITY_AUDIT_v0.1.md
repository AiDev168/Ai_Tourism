# MVP functionality audit and dependency-ordered plan

> **Implementation update (2026-11-05):** The previous destination input and 1–3 day dropdown have been replaced with one natural-language request field and deterministic multilingual extraction. See [Natural-language trip intake V2 and retrieval readiness](NATURAL_LANGUAGE_TRIP_INTAKE_V2_AND_RETRIEVAL_READINESS.md) for parser behavior, regression coverage, verified publication counts, and retrieval blockers. Recommendations remain unavailable because production destination candidates are zero.

- **Status:** implementation audit for feature branch `fix/initialize-database-powershell-inspect-v1`
- **Baseline:** visual refresh `2646d19f0bb71bd1b8b6b3161c2cdd1695b2b0fd`
- **Scope:** distinguish working UI behavior from fixture presentation and sequence the next product capabilities within ADR-0006/0008 and the data-publication boundaries.

## What the refreshed UI actually does

| Surface/control | Actual behavior | Product status |
|---|---|---|
| Language selector | Switches the UI locale and document direction; saves only the locale preference in browser storage | Functional UI preference |
| Explore / itinerary navigation | Scrolls to page anchors | Functional navigation |
| Trip prompt (pre-slice) | Validated non-empty input and toggled a local “no API” notice; no parsing, network request, state model, or persistence | Decorative prototype; replaced by the local trip-intake slice |
| Destination inspiration cards | Show illustrative Kashan/Yazd/Qeshm copy and documentary photos; cards are not selectable and are not sourced from the publication view | UI fixture, not production destination data or recommendations |
| Conversation transcript | Displays fixed sample assistant text | UI fixture; no conversation API or LLM call |
| Conversation composer / send button | Looked interactive but had no handler or backend operation | Non-functional control; removed from the interface |
| Recommendation panel | Fixed empty-state copy; no catalogue retrieval or ranking | Static empty-state presentation |
| Itinerary edit button and fields | Toggle local component state and edit illustrative notes; changes disappear on reload | UI-only fixture editor, not a generated/persisted itinerary |
| “See all” link | Linked to the same discovery section | No-op control; removed |
| Offline banner | Reflects `navigator.onLine`; service worker caches same-origin resources after installation | Functional connectivity indicator and shell caching; not full offline trip planning |
| Photo credits | Link to each Commons source page and CC BY-SA 4.0 license | Functional attribution links |
| PWA install | Manifest/service worker exist; there is no custom install prompt | Browser-native install affordance only |

The home inspiration cards, sample dialogue, and itinerary remain visibly marked as UI-only material. They must never be returned as API catalogue content or presented as actual recommendations.

## First safe vertical slice

The current local trip-intake interaction has one natural-language field, preserves the original request, extracts destination(s), explicit duration (days/weeks, default technical cap 365 days), selected explicit optional fields and shows a localized summary or clarification. It supports Persian, English and Arabic text and digits. It stays in React memory only: no request text is persisted, sent to the backend, sent to a model, or treated as verified destination data. Clearing or reloading the page discards it. It performs no destination recommendation. The deterministic parser is heuristic with a limited destination alias list; see the V2 audit for tested behavior and limits.

## Dependency-ordered product plan

1. **Trip request and validation — started in this slice.** Define bounded input, explicit locale-independent API field semantics, deterministic duration parsing, localized validation, and a user-reviewable requirements object. Do not infer hard constraints or facts.
2. **Clarification questions — started locally; service behavior later.** Ask only for missing/ambiguous fields and let the traveler answer. Before durable conversation state, resolve ADR-0006 authentication/session and retention/privacy policy. Do not send these answers to a model before ADR-0008 gateway and processing decisions are implemented.
3. **Conversation state.** After approved authentication, persistence/retention, object authorization and API contract, add a conversation aggregate and turn lifecycle using existing schema only if it meets reviewed requirements; otherwise propose an additive migration. Do not add anonymous user-data endpoints.
4. **Verified destination retrieval.** Integrate only through the owner-controlled `RetrievalPort`/approved catalogue boundary. Production catalogue queries must read `knowledge.production_destinations` and related production provenance views, never raw tables or synthetic/review-required fixtures. Current production views are intentionally empty; editorial publication of sourced records is a prerequisite for recommendations.
5. **Requirement extraction.** Keep deterministic parsing for unambiguous fields. Any future LLM extraction is a replaceable gateway capability, server-side only, and may suggest values that the user reviews. It cannot set verification or override deterministic constraints.
6. **Clarification and state transitions.** Specify completion criteria, missing/contradictory values, idempotency, retries and locale behavior. Persist only after the identity and privacy decisions; audit the request ID while redacting trip content.
7. **Eligibility and ranking.** Approve a deterministic score, hard filters, tie-breaks, evidence requirements and explanation schema. Verify tests prove model/retrieval output cannot bypass constraints. Preserve the owner’s separate RAG implementation and semantic-quality evaluation boundary.
8. **Three justified recommendations.** Require at least three eligible, editorially active, source-backed destinations for the requested locale and trip constraints. Return fewer or none when evidence/candidates are insufficient; never fill slots from fixtures or fabricate reasons. Explain source, freshness, unknown facts and uncertainty.
9. **One-to-three-day itinerary generation.** Generate only from eligible destinations and verified facts, with explicit unknowns and no invented opening hours, prices, durations or access claims. Any model drafting is behind the Provider Gateway and deterministic validation.
10. **Itinerary editing and persistence.** First define editable fields, provenance for each stop, ownership/authorization, version conflict and deletion behavior. Persist under authenticated user ownership; add migration only if the reviewed existing schema is insufficient. Until then, label local edits as illustrative and non-persistent.
11. **Source and uncertainty presentation.** For every recommendation/itinerary fact, retain source URL/name, retrieval time, content/version hash and review status. Mark unknown/stale/unverified facts explicitly; do not describe a vector-storage smoke test as retrieval quality.
12. **Multilingual release gate.** Persian (`fa-IR`), English (`en-US`) and Arabic (`ar`) require user-facing destination text and assistant answers supported and native-quality reviewed in all three before the release may be called multilingual-ready.

## Architectural gates

- **ADR-0006 remains open:** no authenticated user-data route, durable conversation or itinerary ownership until the session, authorization and recovery design is approved.
- **ADR-0008 is accepted:** all future Chat, Vision, Embedding and optional Reranking use the server-side AI Provider Gateway. Admin/provider control-plane implementation waits for an approved administrator-authentication design. No user provider selection, provider detail, credential exposure, paid call, or implicit local-to-remote fallback.
- **Publication gate:** existing destination fixtures/records are not eligible for production recommendations. Only the curated production views and reviewed real data qualify.
- **Retrieval ownership:** do not replace or duplicate the owner’s RAG implementation. Integrate through a reviewed contract.
