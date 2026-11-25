# knowledge.production_destination_categories

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** View
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** no explicit qualified CRUD clause found; not proof of no read/write path (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `INVESTIGATE` — Derived view has no literal application reference in the scanned source; static search is incomplete evidence, so do not remove.
- **DDL provenance:** engineering/database-prep/sql/001_core_schema.sql:677
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'category_id' | 'bigint' | بله | — | Derived view output; not independently writable. SQL projection: 'category_id [inputs: knowledge.destination_categories.category_id]' (lineage: direct_unqualified_column_unique_source). | PostgreSQL storage type 'bigint' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=a441b22f1c36c74b5efa2f99f25ae6751a7f343e52c26acbf535e8e423fe7005; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'category_key' | 'text' | بله | — | Derived view output; not independently writable. SQL projection: 'category_key [inputs: knowledge.destination_categories.category_key]' (lineage: direct_unqualified_column_unique_source). | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=a441b22f1c36c74b5efa2f99f25ae6751a7f343e52c26acbf535e8e423fe7005; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'name_fa' | 'text' | بله | — | Derived view output; not independently writable. SQL projection: 'name_fa [inputs: knowledge.destination_categories.name_fa]' (lineage: direct_unqualified_column_unique_source). | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=a441b22f1c36c74b5efa2f99f25ae6751a7f343e52c26acbf535e8e423fe7005; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'description' | 'text' | بله | — | Derived view output; not independently writable. SQL projection: 'description [inputs: knowledge.destination_categories.description]' (lineage: direct_unqualified_column_unique_source). | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=a441b22f1c36c74b5efa2f99f25ae6751a7f343e52c26acbf535e8e423fe7005; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'sort_order' | 'smallint' | بله | — | Derived view output; not independently writable. SQL projection: 'sort_order [inputs: knowledge.destination_categories.sort_order]' (lineage: direct_unqualified_column_unique_source). | PostgreSQL storage type 'smallint' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=a441b22f1c36c74b5efa2f99f25ae6751a7f343e52c26acbf535e8e423fe7005; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- محدودیتی در `pg_constraint` برای این شیء مشاهده نشد.

## ایندکس‌ها

- ایندکسی مشاهده نشد / برای View قابل اعمال نیست.

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **5**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
