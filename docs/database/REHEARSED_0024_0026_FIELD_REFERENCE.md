# Rehearsed schema additions: migrations 0024–0026

**Status:** Rehearsed only on a network-isolated restore of the observed live PG17/0023 backup. This document is not evidence that the live database has these relations. The live snapshot remains separately documented through 0023.

## Source and ownership boundary

All columns below come directly from `engineering/pilot/sql/024_partner_review_audit_actions.sql`, `025_owner_control_center.sql`, and `026_platform_reviewer_mfa.sql`. Types, nullability, defaults, checks, and foreign keys are DDL-derived. The API consumers are `backend/app/api/partners.py`, `backend/app/api/admin.py`, and `backend/app/api/platform_admin_mfa.py`; the owner-facing forms are `frontend/src/admin/AdminControlCenter.tsx` and `PlatformAdminMfaPanel.tsx`. These are not ordinary company or traveler forms.

Abbreviations: **P** = platform reviewer/operator; **A** = authenticated application process; **user-secret** = sensitive MFA configuration; **audit** = append-only operational evidence. Application-role access remains constrained by RLS and grants; users cannot self-provision capabilities.

## `partner.platform_grant_events` — migration 0025

| Column | PostgreSQL type | Null/default | Constraint/meaning | Sensitivity/owner/write path |
|---|---|---|---|---|
| `event_id` | `uuid` | NOT NULL; `gen_random_uuid()` | Primary key for one capability grant/revocation event. | Audit; P-only provisioning tool. |
| `grant_domain` | `text` | NOT NULL | `partner` or `catalogue`; scopes the capability namespace. | Authorization metadata; P. |
| `target_user_id` | `uuid` | NOT NULL | FK to `identity.users(user_id)`, `ON DELETE RESTRICT`; subject receiving/revoking a grant. | Account linkage; P. |
| `capability` | `text` | NOT NULL | One of organization/service/offer/admin-overview/candidate/source/catalogue-publish capabilities; domain pairing is constrained. | Privileged metadata; P. |
| `action` | `text` | NOT NULL | `granted` or `revoked`. | Audit; P. |
| `actor_user_id` | `uuid` | NOT NULL | FK to `identity.users(user_id)`, `ON DELETE RESTRICT`; initiating operator. | Account linkage; P. |
| `reason` | `text` | NOT NULL | Trimmed length 10–1000 characters; operator justification. | Internal audit text; P, not public. |
| `occurred_at` | `timestamptz` | NOT NULL; `now()` | Time the action was recorded. | Audit timestamp; system. |

Table check constraints prohibit self-grant and enforce `grant_domain`/`capability` pairing. Index `ix_platform_grant_events_target` supports target-user history. The application role has no direct table privileges; provisioning is operator-controlled. No grants are created by the migration.

## `identity.platform_admin_mfa` — migration 0026

| Column | PostgreSQL type | Null/default | Constraint/meaning | Sensitivity/owner/write path |
|---|---|---|---|---|
| `user_id` | `uuid` | NOT NULL | PK/FK to `identity.users(user_id)`, `ON DELETE CASCADE`; reviewer identity. | Account linkage; A after prior operator grant. |
| `secret_ciphertext` | `bytea` | NULL | AES-GCM encrypted active TOTP seed; stored envelope is 49 bytes when present. | Highly sensitive secret ciphertext; A via MFA API only. |
| `pending_secret_ciphertext` | `bytea` | NULL | Encrypted unconfirmed seed during enrollment; 49 bytes when present. | Highly sensitive; A via enrollment API. |
| `enabled_at` | `timestamptz` | NULL | Enrollment activation time; null exactly when active ciphertext is null. | Security state; A. |
| `last_totp_counter` | `bigint` | NOT NULL; `-1` | Last accepted counter, cannot be less than `-1`; prevents code replay. | Security state; A. |
| `recovery_hashes` | `bytea[]` | NOT NULL; empty array | One-time recovery-code verifiers; maximum cardinality 20. | Credential verifier; A. |
| `version` | `integer` | NOT NULL; `1` | Positive row version for state changes. | Concurrency/security metadata; A. |
| `updated_at` | `timestamptz` | NOT NULL; `now()` | Last MFA-row update. | Security timestamp; A. |

RLS policy `platform_admin_mfa_self` binds reads/writes to the authenticated actor who has platform-administrator capability. This table is not exposed by a generic admin form or database explorer.

## `identity.platform_admin_step_up` — migration 0026

| Column | PostgreSQL type | Null/default | Constraint/meaning | Sensitivity/owner/write path |
|---|---|---|---|---|
| `user_id` | `uuid` | NOT NULL | FK to MFA row, `ON DELETE CASCADE`; reviewer identity. | Session security; A. |
| `session_id` | `uuid` | NOT NULL | FK to `identity.web_sessions(session_id)`, `ON DELETE CASCADE`; exact authenticated session. | Session linkage; A. |
| `verified_at` | `timestamptz` | NOT NULL | Time of successful TOTP/recovery step-up. | Security timestamp; A. |
| `expires_at` | `timestamptz` | NOT NULL | Must be after `verified_at` and no more than five minutes later. | Security expiry; A. |
| `revoked_at` | `timestamptz` | NULL | Optional revocation; if set, cannot precede verification. | Security state; A. |

Composite PK: `(user_id, session_id)`. Partial index `ix_platform_admin_step_up_expiry` covers non-revoked rows. RLS binds access to the same capable actor. This is an exact-session, short-lived authorization record—not a user-wide admin flag.

## `identity.platform_admin_mfa_events` — migration 0026

| Column | PostgreSQL type | Null/default | Constraint/meaning | Sensitivity/owner/write path |
|---|---|---|---|---|
| `event_id` | `uuid` | NOT NULL; `gen_random_uuid()` | Primary key for an MFA audit event. | Audit; A through security-definer function. |
| `actor_user_id` | `uuid` | NOT NULL | FK to `identity.users(user_id)`, `ON DELETE RESTRICT`. | Account linkage; A. |
| `session_id` | `uuid` | NOT NULL | Session identifier retained even after the session row is deleted; deliberately no FK. | Security linkage; A. |
| `action` | `text` | NOT NULL | `enrollment_started`, `mfa_enrolled`, `totp_step_up`, `recovery_step_up`, or `recovery_reset`. | Audit; A via `identity.record_platform_admin_mfa_event`. |
| `occurred_at` | `timestamptz` | NOT NULL; `now()` | Event timestamp. | Audit timestamp; system. |

Index `ix_platform_admin_mfa_events_actor_time` supports actor history. RLS permits actor-bound reads. The application role has no direct `SELECT`/`INSERT`; the security-definer audit function validates actor, capability, action, and session before insertion.

## Classification and unresolved limits

- These tables represent security/audit state and are not company-editable form fields. MFA setup is exposed only in the privileged UI after operator-issued capability; secret contents and recovery codes are never shown in the database reference.
- Migration 0024 updates a review-event decision check and the reviewer insert RLS policy; it creates no table or new UI form. Migration 0025 adds one audit table/function and extends the capability check; it does not grant a reviewer. Migration 0026 adds MFA persistence/functions/policies but creates no user grant or MFA enrollment.
- The isolated rehearsal created no reviewer grant and no MFA secret rows. Public production AI-provider administration remains disabled by Compose.
- The production deployment must use a protected secret manager/files, an explicit operator provisioning ceremony, and separately authorized live DDL. Those steps were not performed in this task.
