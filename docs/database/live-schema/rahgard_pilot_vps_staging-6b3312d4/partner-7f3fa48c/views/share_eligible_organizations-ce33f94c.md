# partner.share_eligible_organizations

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** View
- **شرح:** نمای فقط‌خواندنی سازمان‌های فعال و تأییدشده که می‌توانند درخواست مسافر دریافت کنند.
- **دسترسی خواندن:** Application can read the view; rows are not directly writable.
- **دسترسی نوشتن:** Read-only view.
- **نمایش عمومی:** Visible as recipient choices only through traveler share-options endpoint after authentication.
- **API مدل/مسیر:** GET /trips/{trip_id}/company-share-options reads this projection.
- **فیلد فرم UI:** TravelerWorkspace company-sharing selector; absent when there are no eligible organizations.
- **Static SQL operation hints:** backend/app/api/partners.py:JOIN@1312 | backend/app/api/partners.py:JOIN@425 | backend/app/api/partners.py:SELECT@1211 | backend/app/api/partners.py:SELECT@325 | backend/app/api/partners.py:SELECT@329 | backend/app/api/partners.py:SELECT@364 | backend/app/api/partners.py:SELECT@374 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Derived read boundary has an application source reference; retain publication/filter semantics and review changes additively.
- **DDL provenance:** engineering/pilot/sql/022_traveler_company_requests.sql:227; engineering/pilot/sql/023_partner_trip_responses.sql:44
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-24T11:28:13Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'organization_id' | 'uuid' | بله | — | Derived view output; not independently writable. SQL projection: 'organization_id [inputs: partner.organizations.organization_id]' (lineage: direct_unqualified_column_unique_source). | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=5ded23331c4ccd05f5a6e63af8a4661cfe865e5ee80bc8b5faaf2189a740fbc3; source expression in view_column_lineage.csv; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'display_name' | 'text' | بله | — | Derived view output; not independently writable. SQL projection: 'display_name [inputs: partner.organizations.display_name]' (lineage: direct_unqualified_column_unique_source). | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=5ded23331c4ccd05f5a6e63af8a4661cfe865e5ee80bc8b5faaf2189a740fbc3; source expression in view_column_lineage.csv; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'organization_type' | 'text' | بله | — | Derived view output; not independently writable. SQL projection: 'organization_type [inputs: partner.organizations.organization_type]' (lineage: direct_unqualified_column_unique_source). | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=5ded23331c4ccd05f5a6e63af8a4661cfe865e5ee80bc8b5faaf2189a740fbc3; source expression in view_column_lineage.csv; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- محدودیتی در `pg_constraint` برای این شیء مشاهده نشد.

## ایندکس‌ها

- ایندکسی مشاهده نشد / برای View قابل اعمال نیست.

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **3**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
