# AI Tourism

AI Tourism / AI Travel Advisor — architecture baseline and design repository.

## Architecture documents

- [AI Travel Advisor Reference Architecture](docs/reference/AI_Travel_Advisor_Reference_Architecture.md) — complete Markdown transcription of the supplied reference architecture document.
- [Architecture Analysis & Proposed Target Architecture](docs/reference/ARCHITECTURE_ANALYSIS.md) — database/data model proposal, alternative architecture options, recommended hybrid architecture, hierarchical agentic swarm/orchestration design, and assessment of the current architecture maturity.

## Recommended architecture direction

The current recommendation is:

**Hybrid Architecture + Hierarchical Agentic Swarm + Central Orchestrator + Deterministic Decision Core + Event-Driven Side Plane**

The implementation path should remain evolutionary:

```text
MVP
  → Modular Monolith
  → PostgreSQL + pgvector
  → Redis
  → Object Storage
  → synchronous decision core
  → asynchronous analytics / notification / audit

Scale-up
  → selective service extraction
  → event bus
  → independent AI/agent workers
  → data warehouse

Advanced Agentic phase
  → hierarchical dynamic swarm
  → DAG orchestration
  → explicit agent contracts
  → deterministic safety / constraint / scoring core
  → traceable XAI
```

## Status

The repository is currently an architecture/documentation baseline. Detailed domain models, database schemas, API/event contracts, agent contracts, state machines, security boundaries, deployment topology and implementation architecture are the next design artifacts.
