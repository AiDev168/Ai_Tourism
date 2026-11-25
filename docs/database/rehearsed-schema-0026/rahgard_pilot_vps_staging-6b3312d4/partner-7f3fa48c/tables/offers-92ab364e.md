# partner.offers

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** پیشنهاد تجاری/بسته خدمت که ممکن است زمان‌بندی و ظرفیت داشته باشد.
- **دسترسی خواندن:** Organization owner/manager/editor under RLS.
- **دسترسی نوشتن:** Create/edit unpublished offer; capacity is non-negative and published state is reviewer-controlled.
- **نمایش عمومی:** Private until separate publication.
- **API مدل/مسیر:** POST/PUT /organizations/{organization_id}/offers[/{offer_id}]; workspace GET.
- **فیلد فرم UI:** PartnerWorkspace optional offer form and edit list.
- **Static SQL operation hints:** backend/app/api/partners.py:INSERT@1068 | backend/app/api/partners.py:SELECT@1003 | backend/app/api/partners.py:UPDATE@1099 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/019_partner_workspace.sql:198
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'offer_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه یکتای پیشنهاد. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:198; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'organization_id' | 'uuid' | خیر | — | سازمان مالک پیشنهاد. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:198; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'service_id' | 'uuid' | خیر | — | خدمت پایه پیشنهاد. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:198; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'schedule_id' | 'uuid' | بله | — | زمان‌بندی مرتبط، در صورت وجود. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:198; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'offer_type' | 'text' | خیر | — | نوع پیشنهاد با قرارداد ثابت. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:198; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'status' | 'text' | خیر | '[redacted string default]' | وضعیت پیشنهاد. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:198; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'valid_from' | 'timestamp with time zone' | بله | — | آغاز دوره اعتبار پیشنهاد. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:198; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'valid_until' | 'timestamp with time zone' | بله | — | پایان دوره اعتبار پیشنهاد. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:198; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'capacity_limit' | 'integer' | بله | — | حداکثر ظرفیت قابل ارائه؛ واحد از قرارداد API. | PostgreSQL storage type 'integer' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:198; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_by' | 'uuid' | خیر | — | User account that created the offer. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:198; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:198; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp of the latest editable offer change. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:198; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'published_at' | 'timestamp with time zone' | بله | — | Publication timestamp; a published offer must have this value and publication is reviewer-controlled. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:198; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **offers_capacity_limit_check** (`c`): `CHECK (((capacity_limit IS NULL) OR (capacity_limit >= 0)))`
- **offers_check** (`c`): `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- **offers_check1** (`c`): `CHECK (((status <> 'published'::text) OR (published_at IS NOT NULL)))`
- **offers_offer_type_check** (`c`): `CHECK (((length(btrim(offer_type)) >= 1) AND (length(btrim(offer_type)) <= 80)))`
- **offers_status_check** (`c`): `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'published'::text, 'suspended'::text, 'withdrawn'::text, 'rejected'::text])))`
- **offers_created_by_fkey** (`f`): `FOREIGN KEY (created_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **offers_organization_id_service_id_fkey** (`f`): `FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT`
- **offers_organization_id_service_id_schedule_id_fkey** (`f`): `FOREIGN KEY (organization_id, service_id, schedule_id) REFERENCES partner.schedules(organization_id, service_id, schedule_id) ON DELETE RESTRICT`
- **offers_pkey** (`p`): `PRIMARY KEY (offer_id)`
- **offers_organization_id_offer_id_key** (`u`): `UNIQUE (organization_id, offer_id)`
- **offers_organization_id_offer_id_schedule_id_key** (`u`): `UNIQUE (organization_id, offer_id, schedule_id)`

## ایندکس‌ها

- `ix_partner_offers_service_state`: `CREATE INDEX ix_partner_offers_service_state ON partner.offers USING btree (organization_id, service_id, status, valid_from, valid_until)`
- `offers_organization_id_offer_id_key`: `CREATE UNIQUE INDEX offers_organization_id_offer_id_key ON partner.offers USING btree (organization_id, offer_id)`
- `offers_organization_id_offer_id_schedule_id_key`: `CREATE UNIQUE INDEX offers_organization_id_offer_id_schedule_id_key ON partner.offers USING btree (organization_id, offer_id, schedule_id)`
- `offers_pkey`: `CREATE UNIQUE INDEX offers_pkey ON partner.offers USING btree (offer_id)`

## سیاست‌های RLS

- `offers_platform`: command=w, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text)`, with_check=`partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text)`
- `offers_select`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text))`, with_check=`—`
- `offers_write`: command=*, roles=[], using=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text])`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text]) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text, 'withdrawn'::text, 'rejected'::text])) AND (published_at IS NULL))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **13**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
