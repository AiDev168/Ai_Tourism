# Data Dictionary — Rahgard National Catalogue v1

**Scope:** the audited existing objects referenced below plus proposed additive objects. Types use PostgreSQL 17 syntax; PostGIS geometry uses SRID 4326. This is a contract, not an executed migration. “Existing” columns are not altered. Proposed object owner defaults to the database schema owner for migrations and a least-privilege application role for runtime grants; no end-user receives direct database access.

## 1. Existing objects reused without duplication

The Stage 1 live manifest is the physical baseline. Counts are a 2026-11-14 snapshot, not design constants: 66 `knowledge.destinations`, 58 `knowledge.knowledge_sources`, 116 destination-source links, 52 knowledge documents, 81 chunks, 0 embeddings, 6 import batches, 0 claim-evidence rows, 0 enrichment proposals, and 0 rows in the production destination view.

| Existing relation | Existing contract relevant to this design | Owner/privacy | Reuse and constraints |
|---|---|---|---|
| `knowledge.destinations` | `destination_id bigint PK`; `destination_key text unique`; canonical name/type; free-text province/city; description; optional attributes; lat/long and PostGIS `location`; `parent_destination_id`; aliases; record origin, verification, status, synthetic flag, coordinate role | Catalogue operator; internal until view eligible | Unified hierarchy per accepted ADR-0004. Preserve all current columns and values. Existing coordinate-role check requires `unknown` if no coordinate and one allowed role if coordinates exist. No inferred entrance. |
| `knowledge.destination_categories`, `knowledge.destination_category_map`, `knowledge.destination_tags` | Existing category catalogue, destination relation and tags | Catalogue operator; public projection only | Reuse. Do not create a competing category taxonomy table in this task. Category additions require taxonomy review. |
| `knowledge.knowledge_sources`, `knowledge.destination_sources` | Existing source identity/review and source-to-destination evidence link, role, retrieval and validity timestamps | Source governance; internal metadata/public citations are field allowlisted | Reuse. Do not create a second source registry. Candidate URLs are not source rows until inspected/approved under existing rules. |
| `operations.dataset_import_batches` | Existing UUID batch identity and unique `batch_key` | Ingestion operators | Reuse as outer import/run identity; proposed `dataset_import_files` adds per-file identity only. |
| `knowledge.destination_enrichment_proposals`, `knowledge.destination_enrichment_proposal_sources` | Existing proposed changes targeting an existing canonical destination, with payload digest and review state | Editors/reviewers | Reuse for enrichment of a known identity. Do not misuse for unresolved/new-identity rows. Candidate resolution precedes any enrichment proposal. |
| `knowledge.knowledge_documents`, `knowledge.knowledge_chunks`, embedding spaces/embeddings | Existing evidence document, chunk and replaceable vector contracts | Content/RAG pipeline; documents may contain licensed text | Reuse, no new RAG store. Embeddings are optional downstream artifacts; not a destination-ingestion prerequisite. |
| `knowledge.destination_claim_evidence` | Existing claim-to-destination/document/chunk/source evidence, locale, hashes, validity, review/publication state | Editorial/source governance | Reuse for factual claims; no parallel claim ledger. Stage 1 had zero records. |
| `knowledge.production_destinations`, `production_destination_sources`, `production_destination_categories`, `production_destination_category_map`, `production_destination_tags`, production retrieval/evidence views | Existing allowlisted read projections | Read-only application role | Sole consumer boundary for public destination/catalogue facts unless a reviewed migration explicitly versions these views. Existing safeguards include active + verified + non-synthetic + geolocated identity and verified/current source provenance. |
| `operations.audit_events` | Existing append-only operational audit relation; resource type/id and timestamp index | Restricted operators | Reuse for batch/review/publication actions if actor, action, result and reason fields fit; inspect exact column contract in migration before writing. Do not create a parallel generic audit log. If immutable review history needs relational FK semantics, use proposed candidate review rows plus the audit event. |
| `identity.users` and existing travel entities | Existing traveler identity and data | Private user data | Reuse identity references only for future membership. Do not copy traveler accounts or create partner copies. |

The manifest documents that RLS is currently disabled on the inspected tables and has zero policies. Stage 2A does not change that fact. Proposed partner tables require a new, isolated authorization/RLS design before runtime routes are enabled.

## 2. Proposed additive data dictionary

All proposed objects below are **not present in the live database**. The key constraints/indexes listed are normative for the first migration unless an owner decision changes the underlying contract. Common audit columns (`created_at timestamptz NOT NULL DEFAULT now()`, `created_by uuid NULL`, `updated_at timestamptz NOT NULL DEFAULT now()`) are included only where mutable records are described; append-only evidence/review records have creation time only. Actor FK should target the audited `identity.users` key only after confirmed in migration code. Every JSONB field has a versioned application schema; arbitrary unvalidated JSON is prohibited.

### 2.1 Administrative geography — proposed `geo` schema

| Object / column | Type / nullability | Validation / index | Owner, privacy, publication |
|---|---|---|---|
| `geo.admin_area_releases.release_id` | `uuid PK NOT NULL DEFAULT gen_random_uuid()` | PK | Platform data steward; internal |
| `.authority`, `.dataset_title` | `text NOT NULL` | trimmed non-empty, bounded 240 chars | Steward; internal |
| `.source_url` | `text NOT NULL` | HTTPS where available; actual exact dataset URL | Steward; internal citation |
| `.release_key` | `text NOT NULL` | source release/version, UNIQUE with authority | Steward; internal |
| `.published_at`, `.retrieved_at` | `timestamptz NULL`, `timestamptz NOT NULL` | retrieved time recorded | Steward; internal |
| `.effective_from`, `.effective_until` | `date NULL` | end >= start if both set | Steward; internal |
| `.content_sha256` | `char(64) NOT NULL` | lowercase SHA-256 check | Steward; integrity metadata |
| `.created_at` | `timestamptz NOT NULL DEFAULT now()` | — | System |
| `geo.admin_areas.admin_area_id` | `bigint GENERATED BY DEFAULT AS IDENTITY PK` | PK | Platform steward; internal/public normalized identity |
| `.release_id` | `uuid NOT NULL FK admin_area_releases` | index `(release_id, area_type)` | Steward |
| `.area_type` | `text NOT NULL` | controlled initial values: `country`, `province`, `county`, `district`, `city`, `rural_district`, `locality`, `other`; versioned taxonomy | Steward; public only where approved |
| `.official_code` | `text NULL` | not assumed numeric; unique `(release_id, area_type, official_code)` where non-null | Steward |
| `.parent_admin_area_id` | `bigint NULL FK admin_areas` | self-reference; no cycles enforced by service/validation; index | Steward |
| `.canonical_name_fa` | `text NOT NULL` | NFC + Persian character normalization is a search key, never a replacement for raw official spelling | Steward; public label after review |
| `.canonical_name_en`, `.canonical_name_ar` | `text NULL` | meaningful scripts; translation status in alias/locale extension or approved editor process | Steward |
| `.normalized_key` | `text NOT NULL` | deterministic normalized search key; index `(area_type, normalized_key)` | Steward; internal |
| `.geometry` | `geometry(Geometry,4326) NULL` | GiST; geometry type depends on authoritative source and may be generalized | Steward; public policy gated for sensitive boundaries |
| `.geometry_source_url`, `.geometry_feature_key` | `text NULL` | both null or both present | Steward; internal provenance |
| `.created_at` | `timestamptz NOT NULL DEFAULT now()` | — | System |
| `geo.admin_area_aliases.alias_id` | `bigint identity PK` | PK | Steward; internal/public labels |
| `.admin_area_id` | `bigint NOT NULL FK` | index | Steward |
| `.release_id` | `uuid NOT NULL FK` | release-scoped evidence | Steward |
| `.alias`, `.normalized_key` | `text NOT NULL` each | unique `(release_id, normalized_key, admin_area_id)` | Steward |
| `.locale`, `.alias_type` | `text NOT NULL` each | locale `fa-IR`, `en-US`, `ar`, or source tag; type `official_variant`, `transliteration`, `historical`, `source_spelling` | Steward |
| `.source_url`, `.review_status` | `text NULL`, controlled text NOT NULL | `needs_review`, `approved`, `rejected`; index on normalized key | Steward; aliases not auto-published |

`knowledge.destinations.admin_area_id bigint NULL FK geo.admin_areas` is the only proposed canonical geography column. Keep existing `province_name` and `city_name` untouched and readable. Backfill only exact, reviewed mappings; ambiguous and unmatched values remain null and are listed in a mapping queue. Do not force village or point records into a county centroid.

### 2.2 File-level import identity and candidate review — proposed

| Object / column | Type / nullability | Validation / index | Owner, privacy, publication |
|---|---|---|---|
| `operations.dataset_import_files.file_id` | `uuid PK DEFAULT gen_random_uuid()` | PK | Ingestion service; internal |
| `.dataset_import_batch_id` | `uuid NOT NULL FK operations.dataset_import_batches` | index | Ingestion operator |
| `.relative_path` | `text NOT NULL` | normalized archive-relative path; reject traversal/absolute paths | Ingestion service; internal |
| `.file_sha256` | `char(64) NOT NULL` | lowercase SHA-256 | Ingestion service; integrity |
| `.byte_size` | `bigint NOT NULL` | `>=0` and configured maximum | Ingestion service |
| `.format`, `.schema_signature` | `text NOT NULL`, `char(64) NULL` | allowlisted parser; signature hashes normalized header/schema | Ingestion service |
| `.source_locale`, `.source_dataset_key` | `text NULL`, `text NULL` | locale validation | Ingestion service |
| `.row_count`, `.accepted_count`, `.rejected_count` | `bigint NULL` each | nonnegative; populate only after parse | Ingestion service |
| `.import_status` | `text NOT NULL DEFAULT 'received'` | `received`, `parsed`, `review_ready`, `failed`, `quarantined` | Ingestion service |
| `.created_at`, `.parsed_at` | `timestamptz NOT NULL`, `timestamptz NULL` | — | System |
| unique index | — | `(dataset_import_batch_id, relative_path, file_sha256)`; second unique `(dataset_import_batch_id, relative_path)` to detect changed bytes as conflict | — |
| `knowledge.destination_candidates.candidate_id` | `uuid PK DEFAULT gen_random_uuid()` | PK | Review queue; internal |
| `.file_id` | `uuid NOT NULL FK dataset_import_files` | index | Ingestion service |
| `.source_record_key` | `text NOT NULL` | Provided stable external key, otherwise deterministic source row locator; unique `(file_id, source_record_key)` | Ingestion service |
| `.row_sha256` | `char(64) NOT NULL` | hash of canonicalized raw row serialization | Ingestion service |
| `.raw_record` | `jsonb NOT NULL` | versioned parser mapping; field/size limits; no secrets or unnecessary personal data | Restricted ingestion; never public |
| `.raw_name`, `.raw_province`, `.raw_city`, `.raw_coordinate_role` | `text NULL` | exact original strings; preserve unknown role tokens | Restricted/internal |
| `.proposed_destination_key`, `.proposed_name_fa`, `.proposed_type` | `text NULL` | suggestions only; normalized lookup indexes, no uniqueness as canonical identity | Review queue |
| `.proposed_latitude`, `.proposed_longitude` | `double precision NULL` each | both null or valid WGS84 ranges; source role remains raw | Restricted review; never presumed entrance |
| `.canonical_destination_id` | `bigint NULL FK knowledge.destinations` | indexed; populated only after reviewed identity decision | Steward; no effect on publication by itself |
| `.candidate_status` | `text NOT NULL DEFAULT 'needs_review'` | `needs_review`, `in_review`, `resolved_existing`, `approved_new_identity`, `rejected`, `conflict`; check constraint | Steward |
| `.created_at`, `.updated_at` | `timestamptz` | — | System |
| unique/indexes | — | unique `(file_id, source_record_key)`; `(candidate_status, created_at, candidate_id)`; partial `(canonical_destination_id)` | — |
| `knowledge.destination_candidate_reviews.review_id` | `uuid PK DEFAULT gen_random_uuid()` | append-only | Reviewer; restricted |
| `.candidate_id` | `uuid NOT NULL FK candidate` | index `(candidate_id, decided_at DESC)` | Reviewer |
| `.identity_relation` | `text NOT NULL` | exact enum/check: `same_entity`, `part_of_or_within`, `nearby_distinct`, `unresolved` | Reviewer |
| `.target_destination_id` | `bigint NULL FK destinations` | required except unresolved; forbidden for unresolved | Reviewer |
| `.decision` | `text NOT NULL` | `accept_relation`, `reject_candidate`, `defer`, `request_evidence` | Reviewer |
| `.reason`, `.evidence_refs` | `text NOT NULL`, `jsonb NOT NULL DEFAULT '[]'` | evidence refs point to inspected source/file locator; bounded | Reviewer |
| `.reviewer_user_id` | `uuid NOT NULL FK identity.users` | reviewer cannot equal submitting author for privileged publication | Restricted |
| `.policy_version`, `.decided_at` | `text NOT NULL`, `timestamptz NOT NULL DEFAULT now()` | policy version recorded | Restricted |

No transition out of `needs_review` creates or activates rows in `knowledge.destinations` automatically. An `approved_new_identity` is an authorization to a separate canonical creation command; the command writes a normal destination with provenance and ordinary publication status (initially not published).

### 2.3 Destination presentation and visit facts — proposed

| Object / column | Type / nullability | Validation / index | Owner, privacy, publication |
|---|---|---|---|
| `knowledge.destination_localizations.destination_id` | `bigint NOT NULL FK destinations` | composite PK with locale | Content editor |
| `.locale` | `text NOT NULL` | `fa-IR`, `en-US`, `ar`; composite PK `(destination_id, locale)` | Editor |
| `.display_name` | `text NOT NULL` | trimmed, max 240 | Editor; public only reviewed |
| `.short_description`, `.description` | `text NULL` | bounded; factual claims independently source-backed | Editor |
| `.translation_status` | `text NOT NULL` | `draft`, `editor_reviewed`, `native_review_required`, `blocked` | Editor; only approved state can project |
| `.content_status` | `text NOT NULL` | `draft`, `approved`, `rejected`, `withdrawn` | Editorial gate |
| `.content_version`, `.updated_at`, `.reviewed_at` | `integer NOT NULL`, `timestamptz NOT NULL`, `timestamptz NULL` | version increments; audit fields | Editorial |
| indexes | — | `(locale, content_status, destination_id)` | — |
| `knowledge.destination_aliases.alias_id` | `uuid PK` | UUID | Catalogue steward |
| `.destination_id` | `bigint NOT NULL FK destinations` | index | Steward |
| `.alias`, `.normalized_key` | `text NOT NULL` each | normalized but raw alias preserved; no auto-merge | Steward |
| `.locale`, `.alias_type` | `text NULL`, controlled text NOT NULL | `source_spelling`, `local_name`, `transliteration`, `historical`, `other` | Steward |
| `.source_id`, `.source_url` | `bigint NULL FK knowledge_sources`, `text NULL` | at least one provenance reference for claimed local/source spelling | Steward |
| `.review_status`, `.created_at` | controlled text NOT NULL, timestamptz NOT NULL | `needs_review`, `approved`, `rejected` | Steward |
| indexes | — | unique `(destination_id, normalized_key, COALESCE(locale,''))` via unique index; GIN/trigram only after extension review | — |
| `knowledge.destination_access_points.access_point_id` | `uuid PK` | UUID | Catalogue steward |
| `.destination_id` | `bigint NOT NULL FK destinations` | index `(destination_id, status)` | Steward |
| `.point` | `geometry(Point,4326) NULL` | GiST; coordinate required for point if active | Steward; may be restricted/generalized |
| `.point_role` | `text NOT NULL` | `visitor_entrance`, `visitor_access`, `trailhead`, `boat_landing`, `parking_access`, `other`; role-specific evidence required | Steward |
| `.label`, `.accessibility_state` | `text NULL`, `text NOT NULL DEFAULT 'unknown'` | accessibility: `known`, `unknown`, `not_applicable`, `conflicting`; claims require evidence | Steward; public only reviewed |
| `.source_id`, `.source_url`, `.evidence_note` | `bigint NULL FK`, `text NULL`, `text NULL` | approved point requires attributable feature-level evidence; precise protected points can be restricted | Steward |
| `.coordinate_precision_m` | `numeric(8,2) NULL` | positive, records source precision, not survey guarantee | Steward |
| `.status`, `.observed_at`, `.reviewed_at` | controlled text, `timestamptz NULL`, `timestamptz NULL` | `needs_review`, `approved`, `withdrawn` | Steward |
| `knowledge.destination_visit_duration_evidence.duration_id` | `uuid PK` | UUID | Evidence editor |
| `.destination_id`, `.source_id` | `bigint NOT NULL FK` each | indexes `(destination_id, observed_at DESC)` | Editor |
| `.minimum_minutes`, `.maximum_minutes` | `integer NULL` each | at least one; positive; max >= min | Editor |
| `.visit_context`, `.evidence_note`, `.source_url` | `text NOT NULL`, `text NOT NULL`, `text NULL` | no inferred duration; source claim locator | Editor |
| `.observed_at`, `.valid_from`, `.valid_until` | timestamptz NULL each | end >= start | Editor |
| `.review_status`, `.created_at` | controlled text, timestamptz | reviewed state independent of destination publication | Editor |
| `knowledge.destination_operational_assertions.assertion_id` | `uuid PK` | UUID | Operations/editorial steward |
| `.destination_id`, `.access_point_id` | `bigint NOT NULL FK`, `uuid NULL FK` | index by destination/type/currentness | Steward |
| `.fact_type` | `text NOT NULL` | initial allowlist: `opening_hours`, `access_status`, `access_restriction`, `fee`, `permit`, `hazard`, `seasonality`; new types require versioned schema review | Steward |
| `.value_state` | `text NOT NULL` | `known`, `unknown`, `not_applicable`, `conflicting`, `temporarily_unavailable` | Steward |
| `.value` | `jsonb NULL` | required only for known; schema validates against fact type/version | Steward |
| `.value_schema_version`, `.freshness_policy_key` | `text NOT NULL` each | policy registry maintained in app/config | Steward |
| `.source_id`, `.source_url`, `.evidence_note` | `bigint NULL FK`, `text NULL`, `text NULL` | known operational claims require source or reviewed first-party observation; operator source identified | Steward |
| `.observed_at` | `timestamptz NULL` | mandatory for known; captures observation time | Steward |
| `.valid_from`, `.valid_until` | `timestamptz NULL` | end >= start | Steward |
| `.review_status`, `.recorded_by`, `.created_at` | controlled text, `uuid NULL FK`, timestamptz | immutable revisions; supersede rather than overwrite | Restricted internal reviewer |
| indexes | — | `(destination_id, fact_type, observed_at DESC)`, partial current-state index not interpreted as freshness without policy | — |

`unknown` is a first-class state and is not equivalent to unavailable, open, closed or zero-cost. A fact may be returned as current only when its policy allows it at request time. No stored fact is current indefinitely by default.

### 2.4 Partner logical/physical proposal — tables gated by approval

All tables in schema `partner`; all have `created_at timestamptz NOT NULL DEFAULT now()`, `updated_at timestamptz NOT NULL DEFAULT now()` only if mutable, and an organization scope. Tenant-owned children carry `organization_id` even where derivable; composite unique/FKs enforce same-tenant links. Common deletion policy is soft lifecycle state and FK `RESTRICT`, not cascade. Public fields are projected through explicit views; never serialize a row wholesale.

| Table and columns | Types/nullability and constraints | Field owner / privacy / publication |
|---|---|---|
| `organizations`: `organization_id uuid PK`; `legal_name text NOT NULL`; `display_name text NOT NULL`; `organization_type text NOT NULL`; `registration_country char(2) NOT NULL`; `registration_number text NULL`; `primary_admin_area_id bigint NULL FK`; `verification_status text NOT NULL`; `participation_status text NOT NULL`; `application_status text NOT NULL`; `created_at`, `updated_at timestamptz NOT NULL`; `closed_at timestamptz NULL` | `organization_type` controlled taxonomy; registration tuple unique only where lawful/verified; statuses independently constrained; no public registry number by default | Legal name, numbers tenant-confidential/restricted; reviewed display name public only after organization and profile approval. Platform verification separate from participation/publication. |
| `memberships`: `membership_id uuid PK`; `organization_id uuid NOT NULL FK`; `user_id uuid NOT NULL FK identity.users`; `role text NOT NULL`; `status text NOT NULL`; `invited_by uuid NULL FK`; `accepted_at`, `revoked_at timestamptz NULL`; `created_at timestamptz NOT NULL` | unique `(organization_id,user_id)`; state check; role allowlist proposal `owner`,`manager`,`editor`,`availability_operator`,`viewer`; action permissions must be matrix-based | Private; organization manager nominates, platform policy controls; never public. Roles remain owner decision. |
| `invitations`: `invitation_id uuid PK`; `organization_id uuid NOT NULL`; `email_digest bytea NOT NULL`; `token_hash bytea NOT NULL`; `proposed_role text NOT NULL`; `invited_by uuid NOT NULL FK`; `expires_at timestamptz NOT NULL`; `accepted_at`, `revoked_at timestamptz NULL`; `created_at timestamptz NOT NULL` | single-use; unique token hash; expiry > creation; token itself never persisted | Restricted identity data. Invitee/organization authority subject to approved policy. No public fields. |
| `verification_cases`: `case_id uuid PK`; `organization_id uuid NOT NULL`; `status text NOT NULL`; `evidence_refs jsonb NOT NULL`; `submitted_by uuid NULL FK`; `reviewer_user_id uuid NULL FK`; `policy_version text NOT NULL`; `decision_reason text NULL`; `submitted_at`, `decided_at timestamptz NULL`; `created_at timestamptz NOT NULL` | status controlled `draft`,`submitted`,`needs_information`,`verified`,`rejected`,`withdrawn`; reviewer cannot be submitter for approval; JSON refs only to restricted evidence storage, not raw ID documents | Restricted. Organization may see its status; only authorized reviewers see evidence; public gets verified badge/status only if explicitly approved. |
| `branches`: `branch_id uuid PK`; `organization_id uuid NOT NULL`; `display_name text NOT NULL`; `address_text text NULL`; `admin_area_id bigint NULL FK`; `location geometry(Point,4326) NULL`; `location_role text NOT NULL`; `coordinate_source text NULL`; `contact_public text NULL`; `status text NOT NULL`; `created_at`, `updated_at timestamptz NOT NULL` | `location_role` `service_location`,`entrance`,`approximate_reference`,`unknown`; point validity; GiST; unique `(organization_id,branch_id)` | Address/contact confidential by default; public only field-level opt-in/review. No entrance claim from approximate point. |
| `services`: `service_id uuid PK`; `organization_id uuid NOT NULL`; `branch_id uuid NULL`; `service_type text NOT NULL`; `service_key text NOT NULL`; `status text NOT NULL`; `submission_status text NOT NULL`; `public_fields jsonb NOT NULL DEFAULT '{}'`; `internal_notes text NULL`; `created_by uuid NOT NULL FK`; `created_at`, `updated_at timestamptz NOT NULL`; `published_at timestamptz NULL` | unique `(organization_id,service_key)`; composite FK `(organization_id,branch_id)`; public_fields allowlist by schema version; statuses distinct draft/submitted/approved/published/suspended/withdrawn | Partner owns draft. Internal notes restricted. Public view allowlists reviewed service data. Service never creates destination facts. |
| `service_localizations`: `service_id uuid NOT NULL`; `organization_id uuid NOT NULL`; `locale text NOT NULL`; `display_name text NOT NULL`; `description text NULL`; `content_status text NOT NULL`; `reviewed_at timestamptz NULL`; PK `(service_id,locale)` plus composite FK to service | locales `fa-IR`,`en-US`,`ar`; lengths; service status gate | Partner-authored, editorially reviewed before public projection. |
| `service_destinations`: `organization_id uuid NOT NULL`; `service_id uuid NOT NULL`; `destination_id bigint NOT NULL FK knowledge.destinations`; `relation_type text NOT NULL`; `evidence_note text NULL`; `status text NOT NULL`; PK `(service_id,destination_id)` and composite FK to service | relation `at`,`serves`,`near`,`route_endpoint`; geographic relation does not imply identity | Partner may propose; platform review before public use; destination canonical ownership remains catalogue. |
| `offers`: `offer_id uuid PK`; `organization_id uuid NOT NULL`; `service_id uuid NOT NULL`; `offer_type text NOT NULL`; `status text NOT NULL`; `submission_status text NOT NULL`; `valid_from`, `valid_until timestamptz NULL`; `capacity_limit integer NULL`; `created_by uuid NOT NULL FK`; `created_at`, `updated_at timestamptz NOT NULL`; `published_at timestamptz NULL` | composite FK `(organization_id,service_id)`; end >= start; capacity >=0; `unknown` never means available | Partner-owned draft, review then public allowlisted state; no booking/transaction. |
| `prices`: `price_id uuid PK`; `organization_id uuid NOT NULL`; `offer_id uuid NOT NULL`; `price_state text NOT NULL`; `amount numeric(14,2) NULL`; `currency char(3) NULL`; `unit text NULL`; `tax_included boolean NULL`; `valid_from`, `valid_until timestamptz NULL`; `observed_at timestamptz NULL`; `source_kind text NOT NULL`; `created_at timestamptz NOT NULL` | composite FK to offer; known price requires amount >=0, currency, unit, observed_at; unknown has null amount/currency; no implicit IRR/Toman conversion | Partner confidential until offer approved; display exactly denomination, tax treatment and unit approved. Currency/denomination decision required for Iran market. |
| `schedules`: `schedule_id uuid PK`; `organization_id uuid NOT NULL`; `service_id uuid NOT NULL`; `schedule_type text NOT NULL`; `timezone text NULL`; `starts_at`, `ends_at timestamptz NULL`; `recurrence jsonb NULL`; `status text NOT NULL`; `observed_at timestamptz NULL`; `valid_until timestamptz NULL`; `created_at timestamptz NOT NULL` | composite FK; IANA timezone for local-time schedules; end >= start; recurrence JSON versioned and bounded | Partner owns submitted schedules; only approved current schedule public. |
| `availability_snapshots`: `snapshot_id uuid PK`; `organization_id uuid NOT NULL`; `offer_id uuid NOT NULL`; `availability_state text NOT NULL`; `available_count integer NULL`; `observed_at timestamptz NULL`; `valid_from`, `valid_until timestamptz NULL`; `source_kind text NOT NULL`; `created_by uuid NULL FK`; `created_at timestamptz NOT NULL` | `available`,`unavailable`,`limited`,`unknown`,`conflicting`; unknown count null; observed_at required except unknown; immutable snapshots; composite FK | Partner/operator input; public only if current and policy permits. No reservation semantics. |

Partner ownership and publication columns are separated: tenant author creates/edits drafts; platform reviewer approves and publishes; no partner role approves its own content. Field-level public exposure is an explicit allowlist. The exact action/role matrix, identity enrollment, verification evidence handling, price denomination and retention require owner decisions before partner migrations or routes.

## 3. Index and integrity conventions

- Every FK has a supporting index unless the referencing side is covered by a unique index.
- UUID primary keys for review/batch/candidate records, bigint for existing canonical catalogue compatibility.
- Natural external codes remain text and are scoped to source release; never assume globally stable national codes.
- Geometry uses GiST only where spatial filtering exists. Geography-sensitive content may be generalized or excluded.
- High-volume text search may add `pg_trgm` only after checking installed extension and query measurements; no unreviewed extension requirement in the first migration. Use normalized key B-tree as baseline.
- All candidate, observation, review and availability histories are retained as append-only revisions; correction supersedes a row or appends a decision, not silent overwrite.
