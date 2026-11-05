# AI Tourism

AI Tourism / AI Travel Advisor — architecture baseline and design repository.

## Architecture and implementation documents

- [AI Travel Advisor Reference Architecture](docs/reference/AI_Travel_Advisor_Reference_Architecture.md) — supplied product and target-architecture reference.
- [Architecture Analysis](docs/reference/ARCHITECTURE_ANALYSIS.md) — architecture maturity, options and long-term evolutionary target.
- [Phase 0 Architecture Package](docs/architecture/README.md) — ADR index, ERD, API contract and security/privacy boundaries.
- [MVP Codex Handoff v0.4](docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.4.md) — current implementation boundary, database gate and owner decisions.
- [Codex Phase 1 Task Packet](docs/implementation/CODEX_PHASE_1_TASK_PACKET_v0.1.md) — bounded technical-skeleton instructions, gated on owner approval.

## MVP architecture decision

**The MVP uses a modular monolith with explicit internal module boundaries and a deterministic decision core.** The Hybrid / Hierarchical Agentic Swarm / Event-Driven architecture in the reference documents remains a longer-term evolution direction, not a Phase 1 requirement. See [ADR-0001](docs/architecture/decisions/ADR-0001-mvp-modular-monolith.md).

```text
MVP
  → mobile-first Persian client (technology selection pending owner approval)
  → modular-monolith backend
  → PostgreSQL + PostGIS + pgvector
  → replaceable LLM / Embedding / Retrieval adapters
  → deterministic eligibility, constraints, scoring and ranking

Later, only when justified and approved
  → selective service extraction / async side plane
  → event bus / agent orchestration
  → hierarchical agentic workflows
```

## Status — 2026-11-05

- Phase 0 architecture and design documents are prepared.
- The owner-run database suite passed: PostgreSQL 17, PostGIS 3.6.4, pgvector 0.8.7; 30 tables and 419 rows; SQL tests 000–008 all passed.
- No application runtime has been implemented yet.
- Phase 1 scaffold is gated on owner approval of ADR-0005 (client/backend stack). ADR-0006 (authentication/session strategy) must be accepted before Phase 2 introduces authenticated user-data endpoints.
