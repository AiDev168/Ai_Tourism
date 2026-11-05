# ADR-0003: Replaceable LLM, Embedding and Retrieval Boundaries

- **Status:** Accepted
- **Decision date:** 2026-11-05
- **Sources:** root `AGENTS.md`; `docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.3.md` section 7; `docs/reference/ARCHITECTURE_ANALYSIS.md` sections 6–8 and 10.

## Context

The owner maintains separate RAG engineering work and has explicitly required that the tourism project not duplicate, benchmark or replace that work. The architecture reference describes several knowledge/agent components, but the MVP handoff requires a provider-neutral boundary and a deterministic decision core.

## Decision

1. The backend depends on application-owned interfaces, not vendor SDK calls embedded in domain modules.
2. LLM calls occur only through a server-side provider adapter. Provider/model configuration and credentials remain outside the client and domain logic.
3. Embedding generation and vector persistence are separate from retrieval policy. The embedding interface may be local or remote; no provider, model, revision or dimension is selected here.
4. The owner's RAG implementation plugs into a stable `RetrievalPort` after its interface and integration behavior are approved. Until then, application tests use a deterministic fake adapter.
5. Codex must not create another embedding benchmark, select a replacement retrieval algorithm, download models, run paid API calls, or refactor the owner's external RAG implementation without explicit approval.
6. Retrieved text, web content and user messages are untrusted data. They cannot grant authority, change system policy or bypass application validation.
7. The deterministic decision core alone enforces hard constraints, eligibility, scores, ranking, tie-breaks and warning/reason facts. The LLM may interpret Persian text, extract candidate structured fields, ask clarifying questions and phrase explanations from supplied evidence; it cannot invent factual data or override a hard rule.
8. Persist provider/model aliases, version metadata, prompt version, latency, token usage, estimated cost and outcome where applicable, while minimizing personal content in telemetry.
9. The accepted centralized AI Provider Gateway and administrator control-plane requirements in [ADR-0008](ADR-0008-centralized-ai-provider-management.md) apply to all provider calls and supersede any interpretation that provider/model configuration is an ordinary-user or per-user choice.

## Consequences

- The MVP can progress with a fake retrieval/LLM adapter before real provider selection.
- Adapter contracts require explicit schemas, timeouts, bounded retries, safe error mapping and tests.
- Semantic Persian retrieval recall/quality remains a separate owner-approved evaluation gate; the current vector storage test is not evidence of semantic quality.
- Changing an embedding model requires explicit versioned embedding-space/re-indexing work and must not silently mix vector spaces.
- No model/provider metadata or infrastructure health is part of the ordinary-user API; user-facing provider errors are provider-neutral.

## Revisit when

The owner supplies the approved RAG contract, selects an LLM/embedding provider, or requests a separately scoped retrieval evaluation/integration.
