# ADR-0005: Client and Backend Technology Selection

- **Status:** Proposed — explicit owner approval required before Phase 1 implementation
- **Proposed date:** 2026-11-05
- **Sources:** `README.md`; `docs/reference/AI_Travel_Advisor_Reference_Architecture.md`; `docs/reference/ARCHITECTURE_ANALYSIS.md`; `docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.3.md` sections 9, 13 and 17.

## Context

The product is Persian-first and mobile-first. The handoff recommends an installable PWA and lists React + TypeScript for the frontend and Python + FastAPI for the backend, but explicitly says those are recommendations pending owner confirmation. The local environment has Python 3.13.15 and `uv`; that does not by itself select the backend framework or frontend toolchain.

## Proposed decision

Approve the following as the default Phase 1 stack:

- **Client:** installable PWA, responsive RTL experience, React + TypeScript.
- **Backend:** Python 3.13 + FastAPI, structured as a modular monolith.
- **Python environment/dependencies:** project-local `uv` workflow; no global package installation.
- **Local runtime:** run app processes natively on Windows initially; keep the already prepared PostgreSQL service isolated in Docker Compose.
- **Package manager/build tooling:** select only after compatibility review; do not assume npm/pnpm/Vite without a separate explicit selection.

## Alternatives considered

- Native or cross-platform mobile application: defer unless device capabilities or distribution requirements make a PWA insufficient.
- Other frontend frameworks: possible, but React + TypeScript is the current documented recommendation.
- Other Python backend frameworks: possible, but FastAPI is the documented recommendation and aligns with the API-first MVP.
- Containerizing the application from day one: defer; the prepared database is already isolated in Docker and early native app processes reduce local complexity.

## Consequences if approved

- Phase 1 can create the PWA shell, API application, configuration, health/readiness endpoints and local developer commands.
- The UI must support Persian RTL and narrow Android Chrome/iOS Safari viewports from the start.
- The backend owns authentication, persistence and provider credentials; the browser never connects directly to PostgreSQL or sees secrets.
- Exact framework/package versions must be checked and pinned at implementation time; this ADR does not authorize large dependency upgrades or model downloads.

## Approval required

The owner must explicitly confirm or replace:
1. PWA rather than native/cross-platform app;
2. React + TypeScript;
3. FastAPI + Python 3.13;
4. native Windows app processes for the first local development slice.

Until confirmed, Codex may inspect and propose an implementation plan but must not scaffold against these choices.
