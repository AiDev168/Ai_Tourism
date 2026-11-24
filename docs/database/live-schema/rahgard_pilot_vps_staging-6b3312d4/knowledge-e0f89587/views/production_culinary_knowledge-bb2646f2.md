# knowledge.production_culinary_knowledge

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** View
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** backend/app/modules/catalog/repository.py:SELECT@83 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Derived read boundary has an application source reference; retain publication/filter semantics and review changes additively.
- **DDL provenance:** engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql:239
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-24T11:28:13Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'item_id' | 'uuid' | بله | — | Derived view output; not independently writable. SQL projection: 'i.item_id [inputs: knowledge.culinary_knowledge_items.item_id]' (lineage: direct_column_projection). | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=64b6d32de9f9c785f106ccabc356e19e468e194d73fd5fec37dd39937c2f0618; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/repository.py; column write path is not inferred |
| 'item_key' | 'text' | بله | — | Derived view output; not independently writable. SQL projection: 'i.item_key [inputs: knowledge.culinary_knowledge_items.item_key]' (lineage: direct_column_projection). | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=64b6d32de9f9c785f106ccabc356e19e468e194d73fd5fec37dd39937c2f0618; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/repository.py; column write path is not inferred |
| 'category' | 'text' | بله | — | Derived view output; not independently writable. SQL projection: 'i.category [inputs: knowledge.culinary_knowledge_items.category]' (lineage: direct_column_projection). | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=64b6d32de9f9c785f106ccabc356e19e468e194d73fd5fec37dd39937c2f0618; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/repository.py; column write path is not inferred |
| 'record_key' | 'text' | بله | — | Derived view output; not independently writable. SQL projection: 'i.record_key [inputs: knowledge.culinary_knowledge_items.record_key]' (lineage: direct_column_projection). | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=64b6d32de9f9c785f106ccabc356e19e468e194d73fd5fec37dd39937c2f0618; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/repository.py; column write path is not inferred |
| 'names_by_locale' | 'jsonb' | بله | — | Derived view output; not independently writable. SQL projection: 'i.names_by_locale [inputs: knowledge.culinary_knowledge_items.names_by_locale]' (lineage: direct_column_projection). | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=64b6d32de9f9c785f106ccabc356e19e468e194d73fd5fec37dd39937c2f0618; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/repository.py; column write path is not inferred |
| 'descriptions_by_locale' | 'jsonb' | بله | — | Derived view output; not independently writable. SQL projection: 'i.descriptions_by_locale [inputs: knowledge.culinary_knowledge_items.descriptions_by_locale]' (lineage: direct_column_projection). | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=64b6d32de9f9c785f106ccabc356e19e468e194d73fd5fec37dd39937c2f0618; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/repository.py; column write path is not inferred |
| 'claims' | 'jsonb' | بله | — | Derived view output; not independently writable. SQL projection: 'lc.claims [inputs: lc.claims]' (lineage: direct_column_projection). | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=64b6d32de9f9c785f106ccabc356e19e468e194d73fd5fec37dd39937c2f0618; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/repository.py; column write path is not inferred |
| 'provenance' | 'jsonb' | بله | — | Derived view output; not independently writable. SQL projection: 'cp.provenance [inputs: cp.provenance]' (lineage: direct_column_projection). | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=64b6d32de9f9c785f106ccabc356e19e468e194d73fd5fec37dd39937c2f0618; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/repository.py; column write path is not inferred |
| 'updated_at' | 'timestamp with time zone' | بله | — | Derived view output; not independently writable. SQL projection: 'i.updated_at [inputs: knowledge.culinary_knowledge_items.updated_at]' (lineage: direct_column_projection). | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | live read-only pg_get_viewdef sha256=64b6d32de9f9c785f106ccabc356e19e468e194d73fd5fec37dd39937c2f0618; source expression in view_column_lineage.csv | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/repository.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- محدودیتی در `pg_constraint` برای این شیء مشاهده نشد.

## ایندکس‌ها

- ایندکسی مشاهده نشد / برای View قابل اعمال نیست.

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **9**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
