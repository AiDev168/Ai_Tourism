# Rahgard national catalogue — owner architecture decisions and implementation contract

Status: **approved engineering direction for implementation**, except where explicitly labelled policy-dependent. Based on Stage 1 audit `9557d65a`, Stage 2A package `ac9f1c0f` and owner tourism archive. This document is not permission to publish third-party content, activate privileged company accounts, or deploy to VPS without the existing production release safeguards.

## Outcome, not a documentation milestone

Deliver a real nationwide catalogue ingestion → identity review → publication → searchable itinerary journey, plus company-owned data-entry workflows with access isolation. Do not split the outcome into repeated independent documentation assignments. Produce an implementation in a feature branch and validate end-to-end. Keep protected features disabled on live infrastructure until policy/security gates are met.

## Existing structures are authoritative

Reuse `knowledge.destinations`, destination/source links, categories and tags, knowledge documents/chunks/embedding spaces, claim-evidence and production-gated views, `operations.dataset_import_batches`, existing enrichment proposals, `identity.users`, `travel.*`, and outbound link/click tracking. A new candidate is **not** a published destination; companies and offers are **not** knowledge destinations. RAG is a separate owner-managed RetrievalPort and is not required for structured ingestion.

## Engineering decisions resolved here

1. **Identity review:** distinguish tentative matching from final accepted resolution. Rejection/defer/request-evidence require no destination target. Accepted same-entity requires an existing identity; accepted part-of/within preserves a distinct child and requires evidence before parent assignment; nearby-distinct never merges; unresolved stays unpublished. Imam Mosque, Sheikh Lotfollah Mosque and Naqsh-e Jahan Square are three separate entities.
2. **Duplicate handling:** distinguish delivery (archive + relative member path), content hash, row/source identity, and canonical real-world identity. Byte-identical Alborz Batch 001 delivered twice should create no second candidate-review item. Different bytes under an existing source identity trigger an immutable conflict/revision, not overwrite. Proximity alone cannot authorize merges.
3. **Administrative geography:** an additive, versioned hierarchy may be defined without loading an unapproved reference dataset. Enforce parent-child same-release consistency and prevent cycles at the database/service transaction boundary; keep the current province/city text fields. Do not invent official identifiers or redistribution rights.
4. **Coordinates:** keep raw unsupported roles in restricted staging and only map them after reviewed feature-level evidence. A property/representative point is not a visitor entrance. Withhold sensitive precise coordinates until publication policy is approved.
5. **Locale:** Persian is the primary launch locale. An approved Persian record need not wait for EN/AR. Unsupported translations are null/draft, not fabricated. Preserve reviewed file-based alias compatibility while migrating to database-backed aliases/localizations.
6. **Operational facts:** store separate, attributable, observation-time facts and mark missing/stale as unknown. Do not invent hours, price, availability or TTL. Structured SQL controls eligibility; RAG may only supply sourced narrative context.
7. **API:** keep existing `GET /api/v1/catalog/destinations` legacy envelope and `count` semantics until existing consumers are upgraded. Add a versioned cursor-paginated server-side filtered catalogue; update frontend and itinerary consumers together. Test thousands of records in disposable DB. Do not silently truncate a legacy response or reinterpret `count`.
8. **Partner linkage:** one organization owns service → offer → price/availability/schedule. Enforce same-tenant composite keys/FKs and bind availability to the correct offer and occurrence; no cross-offer capacity bleed. Authenticate membership on each write and test cross-tenant attacks. Partner service offers do not grant destination editing or publication rights.
9. **Staging retention:** minimize raw snapshots and restrict access. **Provisional 90-day post-decision retention is only a recommendation**, not an approved deletion rule; leave automatic deletion disabled pending policy. Never assume uploaded web text or URLs are licensed for public reuse.
10. **Protected platform limits:** ADR-0006 and partner ADR-0009–0013 remain proposed/unapproved in the existing governance record. Build/test the partner workspace in isolation with secure authentication and negative tenant tests, but keep live activation and privileged publication gated until explicit owner security/policy approval. No payment, booking, or personal-data referrals.

## Owner-facing policy defaults (require explicit approval before live use)

- Authoritative administrative-boundary dataset, code/geometry provenance and reuse license.
- Retention period of raw uploaded content and company private evidence.
- Reviewer/approver separation and access to sensitive raw coordinates.
- Per-fact freshness windows for operating hours, closures, permits, hazards, price, schedules and availability.
- Organization authentication, invitation, verification, moderation and document retention policy.

Missing policy decisions must block only the unsafe live action, **not** completion of code, isolated migrations, realistic dry-runs or browser acceptance.

## Existing verified baseline

At Stage 1: 66 destinations, **zero** production destinations, 58 source records, 52 documents, 81 chunks, zero embeddings, 16 migrations; partner tables absent. Owner ZIP: 167 unique destination keys, 10 duplicate delivery rows, 533 national discovery leads, 501 unique document keys; two proximity-based matches to Naqsh-e Jahan are **distinct nearby/component POIs**, not duplicates. The live database and GitHub release at Stage 1 were `5e2664fb51e18f52549aa37a8b5793e12ace09b2`. Refresh these baselines before any live release.

## Acceptance evidence

Provide actual SQL migration and publication view tests, raw archive inventory + duplicate report, candidate and reviewer UI, source-backed published POIs (or exact policy blocker), paginated national search beyond 1,000 rows, persisted real traveler itinerary, partner workspace negative authorization tests, and specific deployed/not-deployed SHA. No source publication without verification; no silent fallback to invented POIs. Preserve existing travelers, records, identities and secrets.
