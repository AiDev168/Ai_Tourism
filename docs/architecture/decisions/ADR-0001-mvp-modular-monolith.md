# ADR-0001: Modular Monolith for the MVP

- **Status:** Accepted
- **Decision date:** 2026-11-05
- **Scope:** MVP / first implementation phases
- **Sources:** root `AGENTS.md`; `docs/reference/ARCHITECTURE_ANALYSIS.md` sections 5, 12 and 14; `docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.3.md`.

## Context

The reference architecture describes a long-term Hybrid Architecture with a central orchestrator, hierarchical agentic workers and an event-driven side plane. The architecture analysis also evaluates Modular Monolith, Microservices, Event-Driven and AI-Centric Agentic alternatives. It explicitly identifies the Modular Monolith as the best MVP starting point and the other patterns as evolutionary/later-phase capabilities.

The current MVP requires a reliable Persian conversational journey, deterministic eligibility/ranking, source-grounded recommendations and a simple editable itinerary. There is no demonstrated MVP need for independently deployed services, a message broker or autonomous agent workers.

## Decision

1. Implement the MVP as one deployable backend application with explicit internal module boundaries and a separate mobile-first client.
2. Keep the request/decision path synchronous and inspectable. The deterministic decision core owns hard constraints, eligibility, scoring, ranking and warning/reason facts.
3. Define module interfaces so selected components can later be extracted without changing domain semantics.
4. Do not introduce microservices, Kubernetes, Redis, an event broker, a multi-agent swarm, autonomous tool loops or a DAG orchestrator in the MVP without measured need and explicit owner approval.
5. Treat the Hybrid / Hierarchical Agentic Swarm architecture in the reference materials as a later evolution target, not as a Phase 1 implementation requirement.

## Consequences

- Lower operational and debugging complexity for the initial release.
- Module boundaries must be enforced in code review; a monolith is not permission for unrestricted cross-module access.
- Cross-cutting concerns such as request IDs, provider adapters, data provenance and authorization must have explicit interfaces.
- Future asynchronous analytics, notification and audit processing can be introduced when real workload and reliability requirements justify it.

## Revisit when

A module has independently measurable scaling, deployment, ownership or isolation needs; synchronous processing has a demonstrated bottleneck; or approved product scope requires durable asynchronous workflows. Any change requires an ADR and an explicit migration path.
