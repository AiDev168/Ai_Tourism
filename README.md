# AI Tourism

AI Tourism / AI Travel Advisor — architecture baseline and design repository.

## Architecture and implementation documents

- [AI Travel Advisor Reference Architecture](docs/reference/AI_Travel_Advisor_Reference_Architecture.md) — supplied product and target-architecture reference.
- [Architecture Analysis](docs/reference/ARCHITECTURE_ANALYSIS.md) — architecture maturity, options and long-term evolutionary target.
- [Phase 0 Architecture Package](docs/architecture/README.md) — ADR index, ERD, API contract and security/privacy boundaries.
- [MVP Codex Handoff v0.5](docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.5.md) — current implementation boundary, approved stack and verified database gate.
- [PWA Design Package](docs/design/README.md) — owner-approved design direction, visual quality, performance and accessibility bar.
- [Codex Phase 1 Task Packet v0.2](docs/implementation/CODEX_PHASE_1_TASK_PACKET_v0.2.md) — approved Phase 1 implementation and visual QA requirements.

## MVP architecture decision

**The MVP uses a modular monolith with explicit internal module boundaries and a deterministic decision core.** The Hybrid / Hierarchical Agentic Swarm / Event-Driven architecture in the reference documents remains a longer-term evolution direction, not a Phase 1 requirement. See [ADR-0001](docs/architecture/decisions/ADR-0001-mvp-modular-monolith.md).

```text
MVP
  → mobile-first Persian PWA (React + TypeScript)
  → FastAPI/Python 3.13 modular-monolith backend
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
- The owner approved PWA + React + TypeScript + FastAPI + Python 3.13 on 2026-11-05.
- The PWA must meet the high visual-quality requirements in the visual design brief as well as the performance/accessibility targets.
- ADR-0006 (authentication/session strategy) must be accepted before Phase 2 introduces authenticated user-data endpoints.
