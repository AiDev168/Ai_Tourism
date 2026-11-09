# AI Tourism

AI Tourism / AI Travel Advisor — architecture baseline and design repository.

## Architecture and implementation documents

- [AI Travel Advisor Reference Architecture](docs/reference/AI_Travel_Advisor_Reference_Architecture.md) — supplied product and target-architecture reference.
- [Architecture Analysis](docs/reference/ARCHITECTURE_ANALYSIS.md) — architecture maturity, options and long-term evolutionary target.
- [Phase 0 Architecture Package](docs/architecture/README.md) — ADR index, ERD, API contract and security/privacy boundaries.
- [MVP Codex Handoff v0.5](docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.5.md) — current implementation boundary, approved stack and verified database gate.
- [Phase 3 closure and Phase 4 status](docs/implementation/AI_TOURISM_PHASE3_CLOSURE_AND_PHASE4_STATUS_2026-11-08.md) — accepted Phase 3 correction and current Phase 4 readiness.
- [Phase 4 pilot readiness report](docs/implementation/PHASE4_PILOT_READINESS_REPORT_2026-11-08.md) — integrated milestone findings, evidence and release decision.
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

## Current status — 2026-11-08

- Phase 3 traveler foundation and its final budget/preference correction are accepted based on the integrated verification reported by the owner. The current branch includes authenticated, owner-scoped trip/conversation persistence, field-specific consent, multilingual browser coverage, and deterministic recommendations over approved catalogue views.
- ADR-0006's high-level domestic authentication/session decisions are accepted and the traveler OTP/session foundation is implemented. Authentication remains disabled by default; production SMS, production activation, account recovery, and operational security settings remain gated.
- The production catalogue was reported empty in the Phase 3 isolated environment. Research/candidate content is not approved for publication, so an honest empty recommendation state is expected until editorially approved data exists.
- Structured catalogue retrieval is not semantic RAG. The owner-RAG interface/contract has not been supplied in this repository, and the production AI Provider Gateway/control plane is not implemented.
- ADR-0008 remains authoritative for centralized server-side AI provider management. Protected administration requires separately approved MFA, bootstrap, authorization, recovery, secret-management, and deployment controls.
- Phase 4 is a readiness and integration milestone, not a pilot approval. Real content/editorial policy, owner-RAG integration, production authentication, hosting/security operations, and physical mobile-device acceptance remain release gates.
- Historical baseline: on 2026-11-05, Phase 0/1 architecture and the local PostgreSQL 17/PostGIS/pgvector preparation were documented. That dated snapshot is retained here as history; it does not describe the current implementation state.

## Phase 1 local development

The PWA UI supports Persian (`fa-IR`, default), English (`en-US`) and Arabic (`ar`). The backend locale contract uses the same identifiers; Phase 1 makes no assistant or other provider calls.

1. From the repository root, create `.env` from `.env.example` and set `DATABASE_PASSWORD` to the local `ai_tourism_app` password already provisioned in `engineering/database-prep/.env`. Keep both local files untracked.
2. Run `uv sync`, then `uv run uvicorn app.main:app --app-dir backend --reload`.
3. In `frontend/`, run `npm ci` then `npm run dev`.
4. Run `uv run pytest`, `uv run ruff check backend`, and from `frontend/`: `npm test`, `npm run build`, and `npm run visual-qa`.

The app uses the existing local database at `127.0.0.1:55433`, database `ai_tourism_dev`, and app role only. Do not rerun database initialization. Production destination text and assistant responses require reviewed three-language coverage before the MVP can be described as multilingual-ready.

The local screenshot pack and automated viewport/locale/accessibility findings are recorded under [`artifacts/visual-qa`](artifacts/visual-qa/report.json). The hero artwork is an imagined generated composite, not evidence of a real destination.
