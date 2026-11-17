# Decision Log — Stage 2A

**Document status:** Proposed architecture package; no implementation or owner acceptance is implied. This log distinguishes already accepted repository decisions from new recommendations and genuinely open decisions.

## 1. Accepted decisions reused

| Decision | Existing authority | Reuse in this package |
|---|---|---|
| Modular monolith with explicit module boundaries | ADR-0001 accepted | New catalogue, ingestion and any future partner code remain modules/schemas in the existing application; no microservices/event broker. |
| PostgreSQL + PostGIS + replaceable vector capability | ADR-0002 accepted | Admin hierarchy and visitor points use PostGIS where needed; destination facts remain relational; no hard-coded vector provider or dimensions. |
| Owner-controlled replaceable retrieval boundary | ADR-0003 accepted | Existing knowledge docs/chunks/claim evidence and retrieval boundary reused; no second RAG engine or embedding prerequisite for ingestion. |
| Unified hierarchical destination entity | ADR-0004 accepted | Keep `knowledge.destinations` for city/region/attraction hierarchy and existing `parent_destination_id`; no duplicate attractions table. |
| Current client/backend stack | ADR-0005 accepted | No replacement stack or public DB access. |
| Current external booking boundary | ADR-0007 accepted | Allowlisted external links/clicks remain; no booking/transaction/referral leads unless separately approved. |
| Existing provider admin boundary | ADR-0008 accepted | Partner/platform roles do not inherit AI provider administration. |

The live manifest captured in Stage 1 supersedes older ERD row counts for current physical state. It records PostgreSQL 17.11; 62 relations; 11 views; 16 migrations; 66 canonical destination rows but zero in `knowledge.production_destinations`; 58 source rows, 52 documents, 81 chunks, zero embeddings, six batches and zero claim-evidence rows. None of these counts is a migration target or expected future count.

## 2. New recommendations in this package — require review/acceptance

1. Add `geo.admin_area_releases`, `geo.admin_areas`, and `geo.admin_area_aliases`; add only a nullable `admin_area_id` FK to existing destinations. Keep legacy province/city text.
2. Add per-file import identity and a destination candidate/review queue; retain raw row snapshots, hashes and append-only decisions. Do not auto-create canonical destinations.
3. Use exactly four identity relation terms: `same_entity`, `part_of_or_within`, `nearby_distinct`, `unresolved`. Proximity is not identity. Keep Imam Mosque, Sheikh Lotfollah Mosque and Naqsh-e Jahan Square as distinct entities.
4. Add normalized destination localizations and aliases while preserving existing name/alias columns as compatibility data.
5. Add separate visitor access points, visit-duration evidence and typed operational assertion history with observation time and fact-specific freshness rules.
6. Replace catalogue-wide loading with indexed filters and stable signed keyset cursors while preserving the current API envelope and publication view safeguards during transition.
7. For a future partner model, use organization-scoped tables in a separate `partner` schema, composite tenant FKs, server-derived actor context, application object authorization and RLS as defense-in-depth. Do not implement until owner decisions are made.
8. Use field-level public projections and separate organization verification, partner participation, service approval, offer publication and availability states.

These recommendations are not accepted ADR decisions. No owner has approved new migrations or partner scope by accepting this architecture task alone.

## 3. Existing proposed ADRs that remain open

- ADR-0006 authentication/session design remains a prerequisite for partner identity and privileged authorization.
- ADR-0009 partner organization, invitation, roles, tenant boundary and membership lifecycle: proposed only.
- ADR-0010 partner service/offer/pricing/schedule/availability fields and freshness: proposed only.
- ADR-0011 eligibility/ranking, unknown/stale handling, commercial placement separation and tie-break: proposed only.
- ADR-0012 consented lead/referral and commercial model; referral requires ADR-0007 amendment if added. This package adds no referral tables.
- ADR-0013 platform governance, reviewer separation, admin provisioning/recovery, appeals and audit: proposed only; ADR-0008 AI provider admin remains separate.

## 4. Owner decisions required before next implementation

### Catalogue / ingestion

1. Which exact current official Ministry of Interior/Statistical Center release is authoritative for national administrative areas, and may its codes/geometry be stored and redistributed? Record source URL, release, license/terms and effective date.
2. Which existing uploaded archive/datasets are approved for ingestion, and under what retention/license policy for raw files and extracted fields? This architecture does not import them.
3. Approve initial candidate queue retention/access policy, reviewer roles and whether submitter/author separation is mandatory for every new place.
4. Approve supported locale fallback and publication threshold for English/Arabic name/description completeness.
5. Approve sensitive coordinate generalization rules and category-specific freshness policy owners/values. Per-fact freshness mechanisms are designed, but numeric time-to-live values remain deliberately open.
6. Confirm whether route/area geometries need a separate first-release collection; this design prevents forcing a line/polygon into a point destination but does not implement a route schema.

### Partner platform

7. Accept/revise relevant ADR-0006 and ADR-0009–0013 decisions before any partner DDL or routes.
8. Select initial service categories, launch geography, legal/business identity evidence, branch location precision, approved public fields and verification-document retention/storage.
9. Decide roles/action matrix, who invites staff, organization suspension/closure and appeal/review process.
10. Decide Iran pricing denomination (`IRR` vs `Toman` display/storage semantics), taxes, price units and currency allowlist; never infer or convert.
11. Decide schedules/time zones, operational freshness windows and whether availability values may ever be used in eligibility.
12. Decide whether pilot includes only external links or later consented referrals; no referral/booking/payment flow is authorized here.
13. Decide if/when sponsored placement exists, with explicit separation from organic relevance.

## 5. Decisions intentionally not made

- No source registry rows, destination rows, uploaded records, canonical mappings, publication, embedding or RAG indexing.
- No exact administrative dataset release is asserted from a secondary source; authoritative source selection is a migration prerequisite.
- No unresolved point coordinate is repaired or promoted to visitor entrance.
- No numeric freshness TTL, pricing conversion, service-category taxonomy, ranking weight, partner role permission, admin bootstrap/recovery protocol, or retention period is invented.
- No partner tables or routes are authorized; no live schema is claimed for partner entities.
- No schema redesign or change to current live tables/views is performed by Stage 2A.

## 6. Source artifacts read

- All five files in `engineering/database-reconciliation/stage-1/`.
- `ADR-0001` through `ADR-0013`, with particular attention to accepted ADR-0004 and proposed ADR-0009–0013.
- `docs/architecture/PARTNER_MARKETPLACE_DOMAIN_CONTRACT_v1.0.md` and `PARTNER_MARKETPLACE_ARCHITECTURE_DECISION_PACKAGE_v1.0.md`.
- `docs/architecture/ERD_MVP_v0.1.md` as historical context only; the Stage 1 live manifest is the current physical baseline.
- Current `backend/app/api/catalogue.py`, `backend/app/modules/catalog/repository.py` and catalogue schemas for route/response compatibility.
