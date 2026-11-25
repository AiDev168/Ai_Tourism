# partner.review_events

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** Append-only audit of reviewer decisions.
- **دسترسی خواندن:** Reviewer/authorized backend paths; no general table access.
- **دسترسی نوشتن:** Written within audited decision routes only; no generic CRUD.
- **نمایش عمومی:** Never public.
- **API مدل/مسیر:** Inserted by organization verification/application/participation decision endpoints.
- **فیلد فرم UI:** Reviewer decision controls; no audit editor.
- **Static SQL operation hints:** backend/app/api/partners.py:INSERT@745 | backend/app/api/partners.py:INSERT@793 | backend/app/api/partners.py:INSERT@839 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/019_partner_workspace.sql:269
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'review_event_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier for an immutable review audit event. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:269; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'organization_id' | 'uuid' | خیر | — | Organization whose record was reviewed. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:269; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'entity_type' | 'text' | خیر | — | Reviewed object type: organization, verification_case, branch, service, offer, price, schedule, or availability. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:269; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'entity_id' | 'uuid' | خیر | — | Identifier of the reviewed object within the declared entity type. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:269; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'decision' | 'text' | خیر | — | Audited action: approve, reject, request_changes, suspend, reinstate, activate, or deactivate. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:269; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'reviewer_user_id' | 'uuid' | خیر | — | User account that performed the review action. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:269; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'reason' | 'text' | خیر | — | Required decision rationale, 10?2000 characters. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:269; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'policy_version' | 'text' | خیر | — | Version of the decision policy applied. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:269; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'occurred_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp when the review action occurred. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:269; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **review_events_decision_check** (`c`): `CHECK ((decision = ANY (ARRAY['approve'::text, 'reject'::text, 'request_changes'::text, 'suspend'::text, 'reinstate'::text, 'activate'::text, 'deactivate'::text])))`
- **review_events_entity_type_check** (`c`): `CHECK ((entity_type = ANY (ARRAY['organization'::text, 'verification_case'::text, 'branch'::text, 'service'::text, 'offer'::text, 'price'::text, 'schedule'::text, 'availability'::text])))`
- **review_events_reason_check** (`c`): `CHECK (((length(btrim(reason)) >= 10) AND (length(btrim(reason)) <= 2000)))`
- **review_events_organization_id_fkey** (`f`): `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- **review_events_reviewer_user_id_fkey** (`f`): `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **review_events_pkey** (`p`): `PRIMARY KEY (review_event_id)`

## ایندکس‌ها

- `ix_partner_review_events_org_time`: `CREATE INDEX ix_partner_review_events_org_time ON partner.review_events USING btree (organization_id, occurred_at DESC)`
- `review_events_pkey`: `CREATE UNIQUE INDEX review_events_pkey ON partner.review_events USING btree (review_event_id)`

## سیاست‌های RLS

- `review_events_member_read`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'organization_review'::text) OR partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text) OR partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text))`, with_check=`—`
- `review_events_platform_insert`: command=a, roles=[], using=`—`, with_check=`((reviewer_user_id = partner.current_actor_id()) AND (((entity_type = ANY (ARRAY['organization'::text, 'verification_case'::text])) AND partner.has_platform_capability(partner.current_actor_id(), 'organization_review'::text)) OR ((entity_type = ANY (ARRAY['service'::text, 'branch'::text])) AND partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)) OR ((entity_type = ANY (ARRAY['offer'::text, 'price'::text, 'schedule'::text, 'availability'::text])) AND partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text))))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **9**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
