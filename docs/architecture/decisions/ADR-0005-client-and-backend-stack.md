# ADR-0005: Client and Backend Technology Selection

- **Status:** Accepted — owner approval recorded 2026-11-05
- **Decision date:** 2026-11-05
- **Sources:** `README.md`; `docs/reference/AI_Travel_Advisor_Reference_Architecture.md`; `docs/reference/ARCHITECTURE_ANALYSIS.md`; `docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.5.md` sections 9, 13 and 17.

## Context

The product is Persian-first and mobile-first. The owner explicitly approved an installable PWA, React + TypeScript, FastAPI + Python 3.13, and native Windows app processes for the initial local development workflow on 2026-11-05. The owner also explicitly requires a highly polished, visually distinctive PWA in addition to high performance. The detailed approved visual-quality brief is `docs/design/PWA_VISUAL_DESIGN_BRIEF_v0.1.md`.

## Decision

The owner approved the following Phase 1 stack on 2026-11-05:

- **Client:** installable PWA, responsive RTL experience, React + TypeScript.
- **Backend:** Python 3.13 + FastAPI, structured as a modular monolith.
- **Python environment/dependencies:** project-local `uv` workflow; no global package installation.
- **Local runtime:** run app processes natively on Windows initially; keep the already prepared PostgreSQL service isolated in Docker Compose.
- **Frontend build tooling/package manager:** not separately selected by the owner. Codex must inspect compatibility and propose a small, maintainable choice (including version pinning) in its preflight plan before adding a lockfile or installing dependencies.

## Alternatives considered

- Native or cross-platform mobile application: defer unless device capabilities or distribution requirements make a PWA insufficient.
- Other frontend frameworks: possible, but React + TypeScript is the current documented recommendation.
- Other Python backend frameworks: possible, but FastAPI is the documented recommendation and aligns with the API-first MVP.
- Containerizing the application from day one: defer; the prepared database is already isolated in Docker and early native app processes reduce local complexity.

## Consequences

- Phase 1 can create the PWA shell, API application, configuration, health/readiness endpoints and local developer commands.
- The UI must support Persian RTL and narrow Android Chrome/iOS Safari viewports from the start.
- The backend owns authentication, persistence and provider credentials; the browser never connects directly to PostgreSQL or sees secrets.
- Exact framework/package versions must be checked and pinned at implementation time; this ADR does not authorize large dependency upgrades or model downloads.

## Owner-approved decisions

The owner explicitly confirmed on 2026-11-05:
1. Installable mobile-first PWA rather than native/cross-platform app for the first client;
2. React + TypeScript;
3. FastAPI + Python 3.13;
4. Native Windows backend/frontend processes for the initial local workflow;
5. High-end visual quality as a first-class product requirement, not a post-MVP polish task.

The visual direction starts with Contemporary Iranian Travel Editorial: photo-led compositions, warm paper/earth neutrals, deep botanical/ink tones, restrained turquoise/saffron accents, excellent Persian typography, intentional RTL layouts and subtle motion. See the visual brief for complete tokens, page requirements, accessibility and performance acceptance criteria.

Codex may proceed with Phase 1 implementation after its required repository preflight and proposed frontend build-tool/package-manager compatibility review. It must not silently add a large component library or an unapproved dependency stack.
