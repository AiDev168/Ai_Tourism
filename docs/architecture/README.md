# AI Tourism — Phase 0 Architecture Artifacts

**Status:** Phase 0 design package, version 0.2; Phase 1 stack owner-approved  
**Baseline branch:** `fix/initialize-database-powershell-inspect-v1`  
**Database gate:** Owner-run Pre-Codex v0.3 checks passed on 2026-11-05; 30 tables / 419 rows.

This folder turns the repository's reference architecture, architecture analysis, current database schema and MVP handoff into implementation-facing design artifacts. It does not authorize deployment, paid provider use, model downloads, schema changes, or changes to `main`.

## Reading order

1. [Architecture decision records](decisions/README.md) — what is decided, proposed, or explicitly open.
2. [MVP ERD v0.1](ERD_MVP_v0.1.md) — relationship view of the current 30-table database schema.
3. [OpenAPI MVP v1 draft](../api/openapi-mvp-v1.yaml) — initial API boundary; authentication and streaming details remain gated decisions.
4. [PWA design package](../design/README.md) — owner-approved art direction and visual brief, page layouts, responsive behavior, performance and accessibility acceptance criteria.
5. [Security and privacy boundaries](../security/SECURITY_PRIVACY_BOUNDARIES_v0.1.md) — trust boundaries, abuse cases, data handling and unresolved policy choices.
6. [Codex Phase 1 task packet](../implementation/CODEX_PHASE_1_TASK_PACKET_v0.2.md) — bounded implementation instructions for the approved technical skeleton.

## Source precedence

Use these materials in this order when they differ:

1. Root `AGENTS.md` and explicit owner decisions in the conversation.
2. Approved ADRs and this MVP implementation handoff.
3. The current database DDL/migrations and their tests for the schema that actually exists.
4. `docs/reference/AI_Travel_Advisor_Reference_Architecture.md` and `docs/reference/ARCHITECTURE_ANALYSIS.md` for product vision and long-term architecture context.

The reference architecture includes future capabilities such as agent orchestration, booking, payment, event-driven processing and service extraction. Their presence in the reference does not place them in the MVP scope. ADR-0001 preserves the MVP-first modular-monolith boundary while keeping the longer-term direction evolutionary.

## Status vocabulary

- **Accepted:** a project guardrail or database contract already established by the owner/repository.
- **Proposed:** a recommended choice that still requires explicit owner approval.
- **Open:** no implementation choice has been made; alternatives and decision criteria are documented.
- **Superseded:** retained for history but replaced by a later ADR.

No ADR marked Proposed or Open should be treated as permission to implement the choice. ADR-0005 is accepted by the owner; ADR-0006 remains Open and gates authenticated user-data APIs in Phase 2. ADR-0008 records the accepted centralized AI Provider Gateway requirement; implementation of its protected admin control plane also requires an approved administrator authentication/authorization design.
