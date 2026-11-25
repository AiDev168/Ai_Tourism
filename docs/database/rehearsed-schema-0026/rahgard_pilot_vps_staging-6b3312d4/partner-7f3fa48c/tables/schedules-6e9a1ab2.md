# partner.schedules

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** زمان‌بندی خدمت و بازه اعتبار اطلاعات زمانی.
- **دسترسی خواندن:** Organization owner/manager/editor/availability operator under RLS.
- **دسترسی نوشتن:** Create/edit draft schedule; all instants use ISO timestamp and explicit time zone when times exist.
- **نمایش عمومی:** Private unless independently reviewed. Freshness is controlled by observed_at/valid_until.
- **API مدل/مسیر:** POST/PUT /organizations/{organization_id}/schedules[/{schedule_id}]; workspace GET.
- **فیلد فرم UI:** PartnerWorkspace optional schedule form and edit list.
- **Static SQL operation hints:** backend/app/api/partners.py:INSERT@938 | backend/app/api/partners.py:SELECT@1002 | backend/app/api/partners.py:UPDATE@970 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/019_partner_workspace.sql:176
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'schedule_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه یکتای زمان‌بندی. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:176; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'organization_id' | 'uuid' | خیر | — | سازمان مالک زمان‌بندی. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:176; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'service_id' | 'uuid' | خیر | — | خدمت مربوط به زمان‌بندی. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:176; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'schedule_type' | 'text' | خیر | — | دسته زمان‌بندی و الگوی اجرای آن. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:176; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'timezone' | 'text' | بله | — | شناسه منطقه زمانی معتبر IANA، در صورت انطباق با قرارداد. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:176; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'starts_at' | 'timestamp with time zone' | بله | — | لحظه یا زمان شروع. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:176; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'ends_at' | 'timestamp with time zone' | بله | — | لحظه یا زمان پایان. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:176; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'recurrence' | 'jsonb' | بله | — | قاعده تکرار؛ فرمت دقیق از API/SQL. | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:176; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'status' | 'text' | خیر | '[redacted string default]' | وضعیت زمان‌بندی. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:176; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'observed_at' | 'timestamp with time zone' | بله | — | زمان آخرین مشاهده/تأیید این داده زمانی. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:176; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'valid_until' | 'timestamp with time zone' | بله | — | انقضای اعتبار اطلاع زمان‌بندی. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:176; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:176; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **schedules_check** (`c`): `CHECK (((ends_at IS NULL) OR (starts_at IS NULL) OR (ends_at >= starts_at)))`
- **schedules_check1** (`c`): `CHECK (((valid_until IS NULL) OR (observed_at IS NULL) OR (valid_until >= observed_at)))`
- **schedules_check2** (`c`): `CHECK ((((starts_at IS NULL) AND (ends_at IS NULL)) OR (timezone IS NOT NULL)))`
- **schedules_recurrence_check** (`c`): `CHECK (((recurrence IS NULL) OR (jsonb_typeof(recurrence) = 'object'::text)))`
- **schedules_schedule_type_check** (`c`): `CHECK ((schedule_type = ANY (ARRAY['opening_window'::text, 'departure'::text, 'appointment'::text, 'event'::text, 'other'::text])))`
- **schedules_status_check** (`c`): `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'withdrawn'::text, 'expired'::text])))`
- **schedules_organization_id_service_id_fkey** (`f`): `FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT`
- **schedules_pkey** (`p`): `PRIMARY KEY (schedule_id)`
- **schedules_organization_id_schedule_id_key** (`u`): `UNIQUE (organization_id, schedule_id)`
- **schedules_organization_id_service_id_schedule_id_key** (`u`): `UNIQUE (organization_id, service_id, schedule_id)`

## ایندکس‌ها

- `ix_partner_schedules_service_state`: `CREATE INDEX ix_partner_schedules_service_state ON partner.schedules USING btree (organization_id, service_id, status, starts_at)`
- `schedules_organization_id_schedule_id_key`: `CREATE UNIQUE INDEX schedules_organization_id_schedule_id_key ON partner.schedules USING btree (organization_id, schedule_id)`
- `schedules_organization_id_service_id_schedule_id_key`: `CREATE UNIQUE INDEX schedules_organization_id_service_id_schedule_id_key ON partner.schedules USING btree (organization_id, service_id, schedule_id)`
- `schedules_pkey`: `CREATE UNIQUE INDEX schedules_pkey ON partner.schedules USING btree (schedule_id)`

## سیاست‌های RLS

- `schedules_platform`: command=w, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text)`, with_check=`partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text)`
- `schedules_select`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text))`, with_check=`—`
- `schedules_write`: command=*, roles=[], using=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text, 'availability_operator'::text])`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text, 'availability_operator'::text]) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text, 'withdrawn'::text, 'expired'::text])))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **12**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
