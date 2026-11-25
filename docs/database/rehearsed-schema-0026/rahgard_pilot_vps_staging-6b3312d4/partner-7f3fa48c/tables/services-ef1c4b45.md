# partner.services

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** خدمات قابل ارائه توسط سازمان؛ اطلاعات عمومی خدمت از قرارداد انتشار جداست.
- **دسترسی خواندن:** Active organization owner/manager/editor through membership RLS.
- **دسترسی نوشتن:** Create/update private draft or submitted values; service key is generated server-side.
- **نمایش عمومی:** Private until separately reviewed and published.
- **API مدل/مسیر:** POST/PUT /organizations/{organization_id}/services[/{service_id}]; GET /organizations/{organization_id}/workspace.
- **فیلد فرم UI:** PartnerWorkspace first-service form and editable service list.
- **Static SQL operation hints:** backend/app/api/partners.py:INSERT@863 | backend/app/api/partners.py:SELECT@1001 | backend/app/api/partners.py:UPDATE@903 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/019_partner_workspace.sql:129
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'service_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه یکتای خدمت. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:129; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'organization_id' | 'uuid' | خیر | — | سازمان مالک خدمت. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:129; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'branch_id' | 'uuid' | بله | — | شعبه مرتبط، اگر خدمت شعبه‌محور باشد. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:129; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'service_type' | 'text' | خیر | — | نوع خدمت با مقادیر مجاز تعریف‌شده در API/دیتابیس. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:129; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'service_key' | 'text' | خیر | — | شناسه/کلید کسب‌وکاری خدمت نزد سازمان. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:129; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'status' | 'text' | خیر | '[redacted string default]' | وضعیت چرخه عمر خدمت. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:129; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'public_fields' | 'jsonb' | خیر | '[redacted string default]' | فراداده/فیلدهای عمومی‌شدنی خدمت؛ کلیدهای JSON باید جداگانه مستند شوند. | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:129; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'internal_notes' | 'text' | بله | — | Private organization-side notes; never part of public service output. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:129; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_by' | 'uuid' | خیر | — | کاربر ثبت‌کننده خدمت. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:129; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | زمان ایجاد خدمت. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:129; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp of the latest service change. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:129; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'published_at' | 'timestamp with time zone' | بله | — | Publication timestamp; required only for published state and set by an authorized review path. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:129; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **services_check** (`c`): `CHECK (((status <> 'published'::text) OR (published_at IS NOT NULL)))`
- **services_public_fields_check** (`c`): `CHECK ((jsonb_typeof(public_fields) = 'object'::text))`
- **services_service_key_check** (`c`): `CHECK (((length(btrim(service_key)) >= 1) AND (length(btrim(service_key)) <= 160)))`
- **services_service_type_check** (`c`): `CHECK (((length(btrim(service_type)) >= 1) AND (length(btrim(service_type)) <= 80)))`
- **services_status_check** (`c`): `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'published'::text, 'suspended'::text, 'withdrawn'::text, 'rejected'::text])))`
- **services_created_by_fkey** (`f`): `FOREIGN KEY (created_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **services_organization_id_branch_id_fkey** (`f`): `FOREIGN KEY (organization_id, branch_id) REFERENCES partner.branches(organization_id, branch_id) ON DELETE RESTRICT`
- **services_organization_id_fkey** (`f`): `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- **services_pkey** (`p`): `PRIMARY KEY (service_id)`
- **services_organization_id_service_id_key** (`u`): `UNIQUE (organization_id, service_id)`
- **services_organization_id_service_key_key** (`u`): `UNIQUE (organization_id, service_key)`

## ایندکس‌ها

- `ix_partner_services_org_status`: `CREATE INDEX ix_partner_services_org_status ON partner.services USING btree (organization_id, status, updated_at DESC)`
- `services_organization_id_service_id_key`: `CREATE UNIQUE INDEX services_organization_id_service_id_key ON partner.services USING btree (organization_id, service_id)`
- `services_organization_id_service_key_key`: `CREATE UNIQUE INDEX services_organization_id_service_key_key ON partner.services USING btree (organization_id, service_key)`
- `services_pkey`: `CREATE UNIQUE INDEX services_pkey ON partner.services USING btree (service_id)`

## سیاست‌های RLS

- `services_insert_editor`: command=a, roles=[], using=`—`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text]) AND (created_by = partner.current_actor_id()) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text])) AND (published_at IS NULL))`
- `services_platform_review`: command=w, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`, with_check=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`
- `services_select_member`: command=r, roles=[], using=`partner.has_active_membership(organization_id, partner.current_actor_id())`, with_check=`—`
- `services_select_reviewer`: command=r, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`, with_check=`—`
- `services_update_editor`: command=w, roles=[], using=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text]) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text])))`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text]) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text])) AND (published_at IS NULL))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **12**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
