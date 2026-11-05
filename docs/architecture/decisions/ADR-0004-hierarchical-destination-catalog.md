# ADR-0004: One Hierarchical Destination Catalogue with Explicit Provenance

- **Status:** Accepted
- **Decision date:** 2026-11-05
- **Sources:** current database migrations and tests; `docs/implementation/AI_TOURISM_MVP_CODEX_HANDOFF_v0.3.md` sections 5.3 and 6; `docs/reference/ARCHITECTURE_ANALYSIS.md` sections 3.6–3.8.

## Context

The architecture analysis contains a broader conceptual model with separate destinations, attractions, accommodations, activities and transport options. The prepared MVP schema uses a single `knowledge.destinations` catalogue and a flexible `destination_type`, with `parent_destination_id` for hierarchy. Provenance, categories, tags, documents, chunks and embedding spaces are separate related tables.

## Decision

1. The MVP uses the existing `knowledge.destinations` table for cities, regions, destinations, attractions/POIs and other approved place entities.
2. Entity kind is represented by `destination_type`; containment or composition is represented by `parent_destination_id`. Do not create a separate attractions table unless a reviewed ADR demonstrates independent lifecycle or attributes that cannot be represented safely in the catalogue.
3. Sources and place/source relationships remain explicit through `knowledge_sources` and `destination_sources`. Documents link to their source and optionally to a destination; chunks belong to documents.
4. A coordinate is not self-describing. Preserve `coordinate_role` semantics such as `property_reference`, `representative_point` and `visitor_entrance`; never treat a UNESCO property point as a visitor gate or a routable entrance.
5. Source verification is separate from editorial/product publication. Verified external records can remain `needs_review`; production-facing views must enforce publication gates.
6. Synthetic fixtures remain explicitly synthetic/test-only and must never leak into production queries.
7. The 15 supplied legacy destinations remain pending/unverified and coordinate-free unless independently sourced and reviewed.

## Verified data baseline (2026-11-05)

- 30 project-owned tables and 419 rows passed the owner-run database suite.
- 44 destination rows comprise 15 legacy pending rows, 12 synthetic QA fixtures and 17 UNESCO-sourced records.
- The 17 UNESCO records have 38 combined source/provenance records across the two batches, 17 Persian paraphrased documents and 34 non-synthetic chunks.
- All 17 UNESCO destinations remain `needs_review`; production destination and retrieval views were empty at test time.
- The 12 taxonomy categories are active. The exact table-by-table manifest is `engineering/database-prep/docs/EXPECTED_ROW_COUNTS.md`.

## Consequences

- A unified catalogue avoids duplicating place identity across separate destination/attraction tables.
- Query and API layers must filter on source verification, editorial status and synthetic classification; a valid foreign key alone does not make a fact safe to show.
- Complex multi-component heritage sites may need parent/component records and richer geometry later; do not collapse a complex site to an arbitrary coordinate.

## Revisit when

Pilot geography, editorial workflow or new place types demonstrate a genuine need for a separate lifecycle or geometry model. Add a reviewed ADR and migration instead of silently changing the entity boundary.
