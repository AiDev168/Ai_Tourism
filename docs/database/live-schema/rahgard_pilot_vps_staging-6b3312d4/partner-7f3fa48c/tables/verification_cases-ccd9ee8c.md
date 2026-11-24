# partner.verification_cases

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** Organization evidence submission and reviewer decision lifecycle.
- **دسترسی خواندن:** Submitting organization owner/manager; separate reviewer capability for decisions.
- **دسترسی نوشتن:** POST submission; verification decision only through reviewer capability; self-review is forbidden.
- **نمایش عمومی:** Private. Evidence references must be reviewed independently.
- **API مدل/مسیر:** POST /organizations/{organization_id}/verification-cases; GET /platform/organization-review; POST /platform/verification-cases/{case_id}/decision.
- **فیلد فرم UI:** PartnerWorkspace evidence submission and reviewer queue.
- **Static SQL operation hints:** backend/app/api/partners.py:INSERT@636 | backend/app/api/partners.py:SELECT@671 | backend/app/api/partners.py:SELECT@709 | backend/app/api/partners.py:UPDATE@721 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/019_partner_workspace.sql:93
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-24T11:28:13Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'case_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier for one organization verification submission. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:93; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'organization_id' | 'uuid' | خیر | — | Organization under review. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:93; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'status' | 'text' | خیر | '[redacted string default]' | Verification case lifecycle: draft, submitted, needs_information, verified, rejected, or withdrawn. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:93; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'evidence_refs' | 'jsonb' | خیر | '[redacted string default]' | JSON array of evidence references submitted for independent review; values are untrusted until checked. | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:93; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'submitted_by' | 'uuid' | بله | — | User account that submitted the evidence. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:93; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'reviewer_user_id' | 'uuid' | بله | — | Independent reviewer account; must differ from submitter for a final decision. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:93; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'policy_version' | 'text' | خیر | — | Identifier of the review policy used. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:93; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'decision_reason' | 'text' | بله | — | Reviewer rationale, if a decision has been made. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:93; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'submitted_at' | 'timestamp with time zone' | بله | — | Submission timestamp. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:93; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'decided_at' | 'timestamp with time zone' | بله | — | Final decision timestamp. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:93; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:93; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **verification_cases_check** (`c`): `CHECK (((status <> ALL (ARRAY['verified'::text, 'rejected'::text])) OR ((reviewer_user_id IS NOT NULL) AND (reviewer_user_id <> submitted_by) AND (decided_at IS NOT NULL))))`
- **verification_cases_evidence_refs_check** (`c`): `CHECK ((jsonb_typeof(evidence_refs) = 'array'::text))`
- **verification_cases_status_check** (`c`): `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'needs_information'::text, 'verified'::text, 'rejected'::text, 'withdrawn'::text])))`
- **verification_cases_organization_id_fkey** (`f`): `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- **verification_cases_reviewer_user_id_fkey** (`f`): `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **verification_cases_submitted_by_fkey** (`f`): `FOREIGN KEY (submitted_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **verification_cases_pkey** (`p`): `PRIMARY KEY (case_id)`

## ایندکس‌ها

- `ix_partner_verification_org_time`: `CREATE INDEX ix_partner_verification_org_time ON partner.verification_cases USING btree (organization_id, created_at DESC)`
- `verification_cases_pkey`: `CREATE UNIQUE INDEX verification_cases_pkey ON partner.verification_cases USING btree (case_id)`

## سیاست‌های RLS

- `verification_case_platform_review`: command=w, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'organization_review'::text)`, with_check=`(partner.has_platform_capability(partner.current_actor_id(), 'organization_review'::text) AND (reviewer_user_id = partner.current_actor_id()) AND (reviewer_user_id <> submitted_by) AND (status = ANY (ARRAY['needs_information'::text, 'verified'::text, 'rejected'::text, 'withdrawn'::text])))`
- `verification_case_select`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'organization_review'::text))`, with_check=`—`
- `verification_case_submit`: command=a, roles=[], using=`—`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text]) AND (submitted_by = partner.current_actor_id()) AND (reviewer_user_id IS NULL) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text, 'withdrawn'::text])))`
- `verification_case_update_self`: command=w, roles=[], using=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text]) AND (reviewer_user_id IS NULL))`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text]) AND (reviewer_user_id IS NULL) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text, 'needs_information'::text, 'withdrawn'::text])))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **11**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
