# Rehearsed schema 0027 — AI provider administration fields

**Scope.** This is a source-derived field reference for `engineering/pilot/sql/027_server_ai_provider_admin.sql`, exercised on the isolated Windows acceptance PostgreSQL 17 database at `Issue27OwnerAcceptance`. It is not a live VPS snapshot. The migration was applied only to a local disposable project volume; no live schema or settings were changed. The migration is additive and intentionally does not replay historical migration 0015 or create a second MFA store.

**Evidence paths.** Column types, nullability, defaults and CHECK/FK constraints below come from the migration SQL named above. Application readers/writers are `backend/app/modules/provider_admin/registry.py`, `backend/app/api/provider_admin.py`, `backend/app/modules/provider_admin/runtime.py`, `backend/app/modules/provider_admin/server_vault.py`, and `frontend/src/admin/aiProviders/{AiProviderAdminPanel.tsx,api.ts}`. Authorization comes from the migration's RLS policies, `identity.has_ai_provider_admin_capability`, `identity.has_ai_provider_admin_step_up`, existing platform MFA in migration 0026, and the operator-only `backend/scripts/provision_platform_capability.py`. Roles and write surfaces are specified per relation; no raw row data or secret values are included here.

## Field conventions

- `PK`, `FK`, `UNIQUE`, and `CHECK` refer to constraints in migration 0027; UUID keys default to `gen_random_uuid()` unless stated otherwise.
- Text fields and JSON configuration are sensitive operational metadata. User-entered profile names are editable; provider secrets are never stored in these tables. `secret_ref` points to an authenticated-encryption vault object and is not a credential.
- Actors can read provider registry data only with the separate provider-administration grant, except the trusted application runtime's route/usage path. Writes require that capability plus an unexpired session-bound platform TOTP step-up. The runtime can read routing configuration and insert bounded usage telemetry; it cannot administer profiles or routes.
- AI calls are not enabled by this migration. Empty routes and disabled fallbacks are defaults. A provider/model becomes operational only after authorized configuration, validation, and route activation.

## `ai_provider.profiles` — operator-managed profile identity

| Column | PostgreSQL contract | Business meaning / ownership / surface |
|---|---|---|
| `profile_id` | uuid, PK, not null, `gen_random_uuid()` | Stable provider-profile identity; system-managed; API returns it for profile lifecycle operations. |
| `name` | text, not null, unique; trimmed length 1–100 | Human-readable administration label; Owner/provider administrator enters through the profile form. |
| `provider_kind` | text, not null; `lm_studio` or `openai_compatible` | Adapter family selected by administrator; endpoint capability checks are enforced in API validation. |
| `enabled` | boolean, not null, default true | Whether the profile may be selected; administrator-controlled, but it does not itself activate a route. |
| `archived_at` | timestamptz, nullable | When a profile was archived; automatic audit/lifecycle value; archived profiles must be disabled. |
| `version` | integer, not null, default 1, `>0` | Optimistic profile edit version used to reject stale updates; system incremented. |
| `created_by` | uuid, not null, FK `identity.users.user_id` | Authenticated creator; set by server, never client-supplied as authority. |
| `created_at` | timestamptz, not null, default `now()` | Creation time; database-managed. |
| `updated_at` | timestamptz, not null, default `now()` | Latest profile edit time; server-managed. |

## `ai_provider.revisions` — immutable configuration snapshots

| Column | PostgreSQL contract | Business meaning / ownership / surface |
|---|---|---|
| `revision_id` | uuid, PK, not null, generated | Immutable configuration revision identity; system-managed. |
| `profile_id` | uuid, not null, FK profiles | Parent provider profile; server links revision to the selected profile. |
| `revision_no` | integer, not null, `>0`, unique with profile | Monotonic revision number; server-managed. |
| `config` | jsonb, not null, JSON object | Validated non-secret endpoint, timeout, concurrency and capability/model configuration; administrator supplies supported values, API validates contract and safe endpoint policy. |
| `secret_ref` | text, nullable, length 8–512 if present | Opaque reference to the server-side AES-GCM vault; API accepts a secret transiently then stores only this reference. Never a key or secret value. |
| `created_by` | uuid, not null, FK users | Authenticated revision author; server-managed. |
| `created_at` | timestamptz, not null, default `now()` | Revision creation time; database-managed. |

## `ai_provider.revision_validations` — connection/inference validation outcomes

| Column | PostgreSQL contract | Business meaning / ownership / surface |
|---|---|---|
| `validation_id` | uuid, PK, generated | Validation record identity; system-managed. |
| `revision_id` | uuid, not null, FK revisions | Exact configuration tested; server-managed. |
| `outcome` | text, not null; `valid`, `invalid`, `unavailable` | Result category from an administrator-triggered bounded validation; not proof of traveler inference by itself. |
| `details` | jsonb, not null, default `{}`, JSON object | Sanitized model/capability and diagnostic metadata; never contains API keys, prompts or raw provider envelopes. |
| `validated_by` | uuid, nullable, FK users | Authenticated administrator for interactive tests; null is reserved for system initiated validation. |
| `validated_at` | timestamptz, not null, default `now()` | Test time; database-managed. |

## `ai_provider.active_routes` — capability to active revision

| Column | PostgreSQL contract | Business meaning / ownership / surface |
|---|---|---|
| `capability` | text, PK; `chat`, `vision`, `embedding`, `reranking` | One independent routing slot per supported model capability; fixed migration bootstrap rows. |
| `revision_id` | uuid, nullable, FK revisions | Active validated revision for this capability; administrator-selected; initially null. |
| `generation` | bigint, not null, default 0, `>=0` | Monotonic route switch generation for conflict/staleness detection; server-managed. |
| `updated_by` | uuid, nullable, FK users | Authenticated actor changing the route; server-managed. |
| `updated_at` | timestamptz, not null, default `now()` | Route change time; database-managed. |

## `ai_provider.fallback_policy` — explicit, disabled-by-default fallback

| Column | PostgreSQL contract | Business meaning / ownership / surface |
|---|---|---|
| `capability` | text, PK, FK active_routes | Capability whose fallback applies; one row per supported capability. |
| `enabled` | boolean, not null, default false | Whether fallback is allowed; disabled by default and explicitly administrator-controlled. |
| `ordered_revision_ids` | uuid[], not null, default empty | Ordered validated revision candidates; when disabled this must be empty. |
| `updated_by` | uuid, nullable, FK users | Authenticated policy editor; server-managed. |
| `updated_at` | timestamptz, not null, default `now()` | Policy edit time; database-managed. |

## `ai_provider.audit_events` — administration audit

| Column | PostgreSQL contract | Business meaning / ownership / surface |
|---|---|---|
| `event_id` | uuid, PK, generated | Audit event identity. |
| `actor_id` | uuid, nullable, FK users | Authenticated actor; null only for system event. |
| `action` | text, not null, length 1–80 | Sanitized action identifier such as profile update, validation, activation or rollback. |
| `target_type` | text, not null, length 1–40 | Type of affected provider object. |
| `target_id` | text, nullable | Opaque target identifier; not provider configuration or secret. |
| `outcome` | text, not null; `success`, `denied`, `failure` | Result category; server-managed. |
| `metadata` | jsonb, not null, default `{}`, JSON object | Minimal redacted audit metadata; must not hold prompts, API keys, TOTP or recovery material. |
| `occurred_at` | timestamptz, not null, default `now()` | Audit event time. |

## `ai_provider.usage_events` — bounded provider runtime telemetry

| Column | PostgreSQL contract | Business meaning / ownership / surface |
|---|---|---|
| `usage_id` | uuid, PK, generated | Usage record identity. |
| `capability` | text, not null; chat/vision/embedding/reranking | Runtime capability invoked. |
| `revision_id` | uuid, nullable, FK revisions | Configuration revision used; nullable when unavailable before route resolution. |
| `outcome` | text, not null; `success`, `unavailable`, `rejected` | Sanitized invocation result. |
| `latency_ms` | integer, nullable, `>=0` | Measured elapsed milliseconds; no request content. |
| `input_units` | integer, nullable, `>=0` | Provider-reported or safely estimated input units; null when unavailable. |
| `output_units` | integer, nullable, `>=0` | Provider-reported or safely estimated output units; null when unavailable. |
| `occurred_at` | timestamptz, not null, default `now()` | Invocation time. Runtime can insert telemetry; administrator can read. |

## `identity.ai_provider_admin_grants` — separate privileged capability

| Column | PostgreSQL contract | Business meaning / ownership / surface |
|---|---|---|
| `user_id` | uuid, PK, FK users, cascade on user deletion | Provider-admin principal; requires existing platform-admin capability; grant is never automatic for company/reviewer membership. |
| `granted_at` | timestamptz, not null, default `now()` | Grant time. |
| `granted_by` | uuid, nullable, FK users, delete restricted | Independent operator who provisioned grant; audit identity. |
| `grant_reason` | text, not null, trimmed length 10–1000 | Required operator rationale; not a secret. |
| `revoked_at` | timestamptz, nullable | Revocation time; must not predate grant. |
| `revoked_by` | uuid, nullable, FK users, delete restricted | Independent revoking operator. |
| `revoke_reason` | text, nullable; required with revocation, trimmed length 10–1000 | Required revocation rationale; no grant exists in migration bootstrap. |

## `identity.ai_provider_admin_grant_events` — append-only grant audit

| Column | PostgreSQL contract | Business meaning / ownership / surface |
|---|---|---|
| `event_id` | uuid, PK, generated | Grant event identity. |
| `actor_user_id` | uuid, not null, FK users, delete restricted | Independent authorized operator performing the action. |
| `target_user_id` | uuid, not null, FK users, delete restricted | User receiving/revoking provider capability; cannot equal actor. |
| `action` | text, not null; `granted` or `revoked` | Lifecycle event. |
| `reason` | text, not null, trimmed length 10–1000 | Auditable rationale supplied by operator. |
| `occurred_at` | timestamptz, not null, default `now()` | Event time. |

## Migration and acceptance state

Migration 0027 SHA-256 is derived from the checked-in SQL at validation time and stored in `system.schema_migrations`; it is intentionally not duplicated here as a mutable constant. Local fresh-chain initialization and the existing volume upgrade both verified 26 ledger rows, exact checksums and aggregate count preservation. The RLS suite passed in disposable PG17. The OwnerAcceptance instance is fresh local seed data, not a restored production clone. No provider profile or active route has been created and no real model invocation has been tested. Do not interpret this field reference as approval to apply migration 0027 to the VPS.
