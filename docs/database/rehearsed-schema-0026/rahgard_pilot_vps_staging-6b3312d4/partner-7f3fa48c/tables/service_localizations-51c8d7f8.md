# partner.service_localizations

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نام و توضیح ترجمه‌شده خدمت در زبان‌های قابل پشتیبانی.
- **دسترسی خواندن:** Same organization membership and service-review policy.
- **دسترسی نوشتن:** Written as part of service create/update API; no independent SQL form.
- **نمایش عمومی:** Only approved published content can be public.
- **API مدل/مسیر:** POST/PUT service routes accept locale, display_name and description.
- **فیلد فرم UI:** PartnerWorkspace service name/description fields.
- **Static SQL operation hints:** backend/app/api/partners.py:INSERT@875 | backend/app/api/partners.py:INSERT@912 | backend/app/api/partners.py:JOIN@1001 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/019_partner_workspace.sql:149
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'organization_id' | 'uuid' | خیر | — | مالک سازمانی ترجمه. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:149; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'service_id' | 'uuid' | خیر | — | ارجاع به خدمت. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:149; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'locale' | 'text' | خیر | — | زبان/محل نمایشی، مانند fa-IR یا en-US بر اساس قرارداد API. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:149; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'display_name' | 'text' | خیر | — | نام نمایشی خدمت در آن زبان. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:149; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'description' | 'text' | بله | — | توضیحات خدمت در همان زبان. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:149; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'content_status' | 'text' | خیر | '[redacted string default]' | Locale content lifecycle: draft, submitted, approved, rejected, or withdrawn. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:149; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'reviewed_at' | 'timestamp with time zone' | بله | — | Timestamp of editorial review when present. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:149; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:149; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp of the latest localization update. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:149; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **service_localizations_content_status_check** (`c`): `CHECK ((content_status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'rejected'::text, 'withdrawn'::text])))`
- **service_localizations_display_name_check** (`c`): `CHECK (((length(btrim(display_name)) >= 1) AND (length(btrim(display_name)) <= 240)))`
- **service_localizations_locale_check** (`c`): `CHECK ((locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text])))`
- **service_localizations_organization_id_service_id_fkey** (`f`): `FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT`
- **service_localizations_pkey** (`p`): `PRIMARY KEY (service_id, locale)`

## ایندکس‌ها

- `service_localizations_pkey`: `CREATE UNIQUE INDEX service_localizations_pkey ON partner.service_localizations USING btree (service_id, locale)`

## سیاست‌های RLS

- `service_localizations_platform`: command=w, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`, with_check=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`
- `service_localizations_select`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text))`, with_check=`—`
- `service_localizations_write`: command=*, roles=[], using=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text])`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text]) AND (content_status = ANY (ARRAY['draft'::text, 'submitted'::text, 'withdrawn'::text])))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **9**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
