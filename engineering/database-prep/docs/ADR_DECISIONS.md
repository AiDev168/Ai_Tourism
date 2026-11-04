# AI Tourism — Architecture Decision Records (Draft for approval)

Status: Proposed baseline. These decisions become binding only after owner review.

## ADR-001 — MVP application topology

**Decision:** Use a modular monolith with internal domain boundaries.  
**Why:** The current repository is an architecture baseline, not an operational multi-service platform. One deployable backend reduces operational and data-consistency complexity while preserving boundaries for future extraction.  
**MVP modules:** Identity/Consent, Conversation, Trip Requirements, Knowledge/RAG Adapter, Recommendation/Decision, Itinerary, External Integrations, Feedback/Operations.  
**Deferred:** microservices, event broker, dynamic agent swarm, data warehouse.

## ADR-002 — Mobile-first client

**Decision:** Build the initial client as a responsive Persian-first PWA.  
**Why:** One client surface supports mobile browser and home-screen installation on Android/iOS while the backend stays independently deployable.  
**Boundary:** PWA is not claimed to be a full native offline application.

## ADR-003 — Backend and trust boundary

**Decision:** Backend owns authentication, authorization, secrets, domain rules, database access and all provider calls.  
**Boundary:** The PWA never connects directly to PostgreSQL and never contains an LLM API key.

## ADR-004 — Remote LLM provider abstraction

**Decision:** Use Remote LLM API through a provider-neutral backend interface.  
**Required controls:** server-side secrets, explicit provider/model configuration, timeouts, bounded retries, rate/cost limits, token/cost telemetry, privacy minimization and fallback behavior.  
**Deferred:** selecting the actual vendor/model until provider, latency, legal, availability and cost constraints are reviewed.

## ADR-005 — Replaceable Embedding/RAG provider

**Decision:** Store embedding provider, model, revision, dimension, metric and preprocessing version as data in `knowledge.embedding_spaces`. Do not encode one selected model or dimension into the domain schema.  
**MVP retrieval baseline:** exact search as correctness reference; add ANN indexes only after profiling and recall verification.  
**Owner boundary:** the owner's independent RAG algorithm work remains authoritative; the application integrates through an adapter and does not replace that algorithm without approval.

## ADR-006 — Development database

**Decision:** Use an isolated Docker database container for development: PostgreSQL 17, PostGIS 3.6 and pgvector 0.8.7. Backend/frontend remain host-run initially.  
**Network:** publish only on `127.0.0.1:55433`.  
**Persistence:** independent named volume `ai_tourism_pgdata`.  
**Safety:** do not stop, inspect by mutation, delete or reuse other project containers/volumes or the host PostgreSQL service.

## ADR-007 — MVP database size and boundaries

**Decision:** Start with the 30 tables enumerated in `DATA_MODEL.md`; schemas reflect modular-monolith ownership.  
**Deferred tables:** booking, payment, notification delivery, ticket/refund/cancellation, loyalty and analytics warehouse. Add these only in a later approved phase.

## ADR-008 — Data classification

**Decision:** Preserve the current 15 supplied destinations as unverified/pending, and use explicitly marked synthetic QA data for development and deterministic tests.  
**Release gate:** synthetic/test-only data must not be eligible for production recommendations. No location or dynamic fact may be invented for factual records.

## ADR-009 — Booking MVP boundary

**Decision:** MVP stores external provider URLs and outbound-click telemetry only. There are no internal booking or payment transactions in the MVP database.

## ADR-010 — Asynchronous work

**Decision:** Keep the primary conversation/recommendation response synchronous. Add asynchronous workers only for concrete needs such as import jobs, notifications or analytics; do not add a broker pre-emptively.


## ADR-011 — Coordinate semantics and editorial publication gate

**Decision:** Every coordinate has an explicit role. UNESCO property/map points are stored as `property_reference`, not visitor entrances. Synthetic test points use `test_fixture`; unknown coordinates remain NULL with `unknown`. Production destination views require a non-null point and a non-unknown role.

**Rationale:** A point on a heritage-property map is not proof of a public entrance or routable access. Separating geometry semantics prevents false navigation claims.

## ADR-012 — Source verification is separate from editorial/product approval

**Decision:** The first 10 official UNESCO-sourced records are marked `record_origin=verified_external` and `verification_status=verified`, but keep `status=needs_review`. Production destination and retrieval views require explicit `status=active`, so verified factual data is ingested and testable without being published automatically.

**Rationale:** Trusted source provenance does not automatically establish operational access, current visitor conditions, product taxonomy decisions, or readiness for user-facing recommendations.
