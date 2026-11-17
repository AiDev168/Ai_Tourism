# Publication and Provenance Contract

## 1. Separate statuses

No single `status` means “good.” Keep separate state dimensions for:

| Dimension | Suggested controlled values | Meaning |
|---|---|---|
| Discovery | `discovered`, `researched`, `not_a_valid_entity`, `duplicate_candidate` | Whether an entity candidate was found and classified. |
| Identity | `unresolved`, `resolved`, `same_entity`, `part_of_or_within`, `nearby_distinct` | Identity/relationship resolution, independent of quality. |
| Evidence | `insufficient`, `single_source`, `corroborated`, `conflicting` | Support quality for specific claims, not a blanket promotion. |
| Canonical review | existing destination review/verification fields | Whether canonical data passed the existing catalogue controls. |
| Translation | per locale `draft`, `editor_reviewed`, `native_review_required`, `blocked` | Language quality and review. |
| Operational fact | `known`, `unknown`, `not_applicable`, `conflicting`, `temporarily_unavailable` | Current fact state with observation and expiry. |
| Publication | not published / published / withdrawn by existing publication view/fields | Whether the ordinary API may return it. |

Candidate review never changes source verification, destination verification, or publication by implication. Organization verification never publishes a destination or partner service. A verified identity is not proof that a place is open, accessible, safe, or visitor-ready.

## 2. Destination publication eligibility

The existing `knowledge.production_destinations` view is the baseline authority and must not be weakened. It currently requires active, verified, non-synthetic destinations, valid coordinates with a non-unknown role, `verified_external` origin, and at least one verified/non-synthetic/current source link. Existing production source views independently exclude unverified, synthetic, future/expired links. New views must preserve or strengthen these conditions.

For localized publication, require a canonical destination already eligible through the established view, plus one locale row with `content_status='approved'`, a translation status meeting the locale policy, factual claim links where factual description is material, and explicit field allowlisting. Missing locale content returns a documented fallback only if product approves that locale fallback; it must not silently translate at request time as factual verification.

For a newly ingested candidate, publication eligibility is a sequence, not one flag:

1. Candidate is reconciled to an exact canonical identity (or approved new identity) by an authorized reviewer.
2. Canonical destination is created/updated through the existing canonical/enrichment path and remains unpublished while incomplete.
3. Every material factual assertion has claim-level provenance to an inspected source, appropriate evidence class, retrieval time and validity. The verified source is registered using existing source tables and review lifecycle.
4. Coordinate feature identity and role are reviewed. A representative/property-reference coordinate is not an entrance. Spatial production API requires coordinate role semantics accepted by its current projection; an unverified point stays out.
5. Required category assignments reference existing reviewed categories. Taxonomy additions are an explicit steward action.
6. Localized label/description passes language review; missing languages remain missing/draft.
7. The normal destination verification/status fields meet the pre-existing production view requirements. No upload flag, candidate state, partner submission or model response can set these automatically.
8. Final publication is performed by an operator distinct from the content author where the governance policy requires it; append audit event with actor, target, action, reason and content/source versions.

There is no auto-publication on import. This contract neither creates new source-register rows nor changes any source's verification.

## 3. Claim and source provenance

Reuse `knowledge.knowledge_sources`, `knowledge.destination_sources`, `knowledge.knowledge_documents`, `knowledge.knowledge_chunks`, and `knowledge.destination_claim_evidence`. A source URL is not a claim. Evidence must identify:

- exact source row and canonical URL, publisher/title/source type and language;
- retrieval timestamp, publication/update timestamp if provided, and validity interval;
- relevant claim key/field and concise evidence note or locator;
- exact destination identity supported (not just a city or province mention);
- content hash/version and synthetic/review/publication state;
- whether the source supports identity, geography, history, access, opening, price, accessibility, safety or another claim.

Contradictory evidence stays visible; a conflict is not resolved by choosing the newest or most authoritative source silently. Revocation, source invalidation or content correction must remove dependent claim/source rows from publication projections promptly. The existing production evidence view already exposes destination/document/synthetic/revocation predicates; preserve its fail-closed behavior.

## 4. Freshness and time-dependent facts

The proposed operational assertion row stores `observed_at`, `valid_from`, `valid_until`, fact type and policy key/version. The policy registry defines maximum age per fact type and, where relevant, geography/source class. Freshness is evaluated at read time:

`current = reviewed && valid_from <= now (or null) && valid_until >= now (or null) && now - observed_at <= max_age(policy_key)`.

If observation time or policy is unavailable, the fact is stale/unknown for decisions that require currentness. Do not use a universal expiry value. At minimum, opening hours, closures/access status, fees, permits, availability, schedules and hazards have separate policies. A stale fact may remain visible as a dated historical note only with its age labeled; it cannot satisfy hard eligibility. For unknown or conflicting data, return that exact state and an explanation, never infer open/available/free/safe.

Proposed duration-of-visit evidence is contextual and not a guarantee: store min/max where supported, source, observed date, audience/activity context and review status. It does not prove transit time or daily feasibility.

## 5. Geographic truth

- Existing `destinations.location` and `coordinate_role` retain audited semantics.
- Admin-area geometry describes administrative boundaries, not attractions.
- `visitor_access_points` stores an entrance/access feature only with evidence that identifies that exact feature.
- A site reference point, property pin, village center, route endpoint or area representative point cannot be promoted to entrance by proximity.
- Routes/areas remain separately represented when the actual geometry is line/polygon; never convert to a misleading precise point. Stage 2A does not add a general route table because the audited task baseline focuses on destination catalogue and partner design; route records require a separate bounded data contract if the existing destination type/geometry cannot express them safely.
- Sensitive ecological/cultural locations may be withheld or generalized by explicit policy.

## 6. RAG integration boundary

The structured destination and operational projection is authoritative for identity, coordinate, hierarchy, categories, current access, schedule, price and eligibility. Existing knowledge documents/chunks/claim evidence and owner-controlled retrieval remain the narrative evidence path. RAG may retrieve only from existing approved publication views; it may not invent or establish canonical identity, publish content, override deterministic eligibility, or populate coordinate/access facts. No embeddings, indexing jobs, vector table or owner RAG engine are required for catalogue ingestion.

The application verifies any returned canonical key/document/claim/source identities against the current published projection. If that mapping cannot be verified or a source is revoked/stale, the evidence is not presented as traveler-facing fact. Keep `no_evidence`, `unavailable` and malformed response distinct.

## 7. Audit and revocation

Every review, approval, reject, canonical link, publication, withdrawal, source revocation and operational correction records actor, authority scope, resource key, action, result, reason, time and policy/content version through the existing `operations.audit_events` contract where suitable plus append-only domain review records. Never place raw credentials, private verification documents, or traveler PII in these audit events. View security is read-only least privilege; candidate/raw and editorial tables are not granted to public/API roles.
