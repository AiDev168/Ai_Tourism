# Architecture Decision Records

| ADR | Subject | Status | Implementation effect |
|---|---|---|---|
| [0001](ADR-0001-mvp-modular-monolith.md) | MVP architecture boundary | Accepted | Modular monolith; future hybrid/agentic architecture remains evolutionary |
| [0002](ADR-0002-postgresql-postgis-pgvector.md) | Database platform | Accepted for the prepared development baseline | PostgreSQL 17 + PostGIS + pgvector; no production hosting choice |
| [0003](ADR-0003-ai-and-rag-provider-boundaries.md) | LLM, embedding and retrieval boundaries | Accepted | Replaceable adapters; owner-controlled RAG; deterministic decision core |
| [0004](ADR-0004-hierarchical-destination-catalog.md) | Destination/catalog model and provenance | Accepted | One hierarchical destination catalogue with explicit provenance/review gates |
| [0005](ADR-0005-client-and-backend-stack.md) | Client and backend technology + visual quality | Accepted — owner approved 2026-11-05 | PWA + React/TypeScript + FastAPI/Python 3.13; native Windows development; premium Persian RTL design brief |
| [0006](ADR-0006-authentication-and-session.md) | Authentication and session strategy | Accepted for initial domestic MVP; production/security gates remain | Traveler OTP/session foundation is implemented; production SMS, operational/recovery policy, and privileged administrator controls remain gated |
| [0007](ADR-0007-mvp-external-integrations.md) | Booking, maps and weather boundary | Accepted for MVP scope | Allowlisted redirects; no in-app booking/payment; provider choices remain open |
| [0008](ADR-0008-centralized-ai-provider-management.md) | Centralized AI Provider Gateway and admin control plane | Accepted owner requirement; admin auth gate remains | All AI calls server-side; admin-only configuration; no provider/model/infra detail in ordinary-user surfaces |

## Change process

Create a new numbered ADR when an owner-approved decision materially changes a boundary, public interface, persistence model, provider contract, privacy behavior or deployment topology. Do not silently rewrite an Accepted decision. Update the index and affected handoff/API/security documents in the same reviewable change.
