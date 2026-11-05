# ADR-0002: PostgreSQL, PostGIS and pgvector as the Prepared Database Baseline

- **Status:** Accepted for the isolated development/test baseline; production topology remains open
- **Decision date:** 2026-11-05
- **Sources:** `engineering/database-prep/README_FA.md`; SQL bootstrap/migrations `000_bootstrap.sql`, `001_core_schema.sql`; database test output supplied by the owner on 2026-11-05.

## Context

The project needs relational integrity for users, conversations, trips, recommendations and provenance, geospatial support for verified destination coordinates, and a replaceable vector-persistence boundary. The repository now contains a separately configured local database package.

## Decision

1. The prepared local development/test database is PostgreSQL 17 with PostGIS 3.6.4 and pgvector 0.8.7.
2. PostGIS stores destination points as `geography(Point, 4326)`; coordinate semantics are separately represented by `coordinate_role`.
3. pgvector is available for vector persistence, but no production embedding provider, model, revision, dimension or retrieval algorithm is selected by this ADR.
4. The application connects using the least-privilege `ai_tourism_app` role. The owner/migration role is reserved for schema administration and migration execution.
5. The local service remains isolated to loopback port `127.0.0.1:55433` with the project-specific Compose/volume configuration already documented in the database-prep package.
6. Do not interpret the local Compose package as a production deployment design. Production hosting, managed database, region, backup service and network topology remain open.

## Verified baseline

The owner ran `Test-Database.ps1` and supplied the complete successful output on 2026-11-05:

- PostgreSQL 17, PostGIS 3.6.4, pgvector 0.8.7;
- all nine SQL test files (000 through 008) passed;
- exact per-table row checks passed for all 30 project-owned tables;
- total actual and expected rows: 419;
- migration checksums and idempotent seed re-runs passed;
- application-role least-privilege checks passed;
- production destination and retrieval views remained empty.

The prepared baseline intentionally has zero persistent embedding spaces, zero chunk embeddings, zero outbound clicks, zero real AI model calls and zero audit events. The pgvector contract test uses temporary synthetic vectors inside a rollback transaction.

## Consequences and limits

- The database contract is ready for application-skeleton integration; this does not prove the application is implemented or that semantic RAG quality is adequate.
- Schema changes must be additive/versioned through migrations and accompanied by invariant and relationship tests.
- Do not reset, delete or recreate the owner's volume to repeat this successful baseline.
- Keep test, development, staging and production credentials/data isolated.

## Revisit when

Production hosting is selected, measured query volume justifies indexing/caching changes, semantic retrieval has an approved implementation, or a database migration/managed-service decision is required.
