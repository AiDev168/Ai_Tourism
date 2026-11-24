# knowledge.knowledge_sources

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** backend/app/api/catalogue_review.py:INSERT@424 | backend/app/api/catalogue_review.py:INSERT@533 | backend/app/api/catalogue_review.py:JOIN@260 | backend/app/api/catalogue_review.py:JOIN@607 | backend/app/api/catalogue_review.py:SELECT@401 | backend/app/api/catalogue_review.py:SELECT@412 | backend/app/api/catalogue_review.py:SELECT@490 | backend/app/api/catalogue_review.py:SELECT@526 | backend/app/api/catalogue_review.py:SELECT@663 | backend/app/api/catalogue_review.py:SELECT@706 | backend/app/modules/catalog/content_importer.py:SELECT@39 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/database-prep/legacy/tourism_points.sql:23
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-24T11:28:13Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'source_id' | 'bigint' | خیر | '[redacted string default]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bigint' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/legacy/tourism_points.sql:23 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py \| backend/app/modules/catalog/content_importer.py; column write path is not inferred |
| 'source_name' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/legacy/tourism_points.sql:23 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py \| backend/app/modules/catalog/content_importer.py; column write path is not inferred |
| 'source_type' | 'text' | خیر | '[redacted string default]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/legacy/tourism_points.sql:23 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py \| backend/app/modules/catalog/content_importer.py; column write path is not inferred |
| 'verification_status' | 'text' | خیر | '[redacted string default]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/legacy/tourism_points.sql:23 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py \| backend/app/modules/catalog/content_importer.py; column write path is not inferred |
| 'reliability_score' | 'numeric(5,4)' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'numeric(5,4)' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/legacy/tourism_points.sql:23 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py \| backend/app/modules/catalog/content_importer.py; column write path is not inferred |
| 'url' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/legacy/tourism_points.sql:23 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py \| backend/app/modules/catalog/content_importer.py; column write path is not inferred |
| 'notes' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/legacy/tourism_points.sql:23 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py \| backend/app/modules/catalog/content_importer.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/legacy/tourism_points.sql:23 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py \| backend/app/modules/catalog/content_importer.py; column write path is not inferred |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/legacy/tourism_points.sql:23 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py \| backend/app/modules/catalog/content_importer.py; column write path is not inferred |
| 'is_synthetic' | 'boolean' | خیر | 'false' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'boolean' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/legacy/tourism_points.sql:23 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py \| backend/app/modules/catalog/content_importer.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **chk_source_reliability** (`c`): `CHECK (((reliability_score IS NULL) OR ((reliability_score >= (0)::numeric) AND (reliability_score <= (1)::numeric))))`
- **chk_source_status** (`c`): `CHECK ((verification_status = ANY (ARRAY['pending'::text, 'verified'::text, 'rejected'::text, 'stale'::text])))`
- **knowledge_sources_pkey** (`p`): `PRIMARY KEY (source_id)`

## ایندکس‌ها

- `knowledge_sources_pkey`: `CREATE UNIQUE INDEX knowledge_sources_pkey ON knowledge.knowledge_sources USING btree (source_id)`
- `uq_knowledge_sources_source_name`: `CREATE UNIQUE INDEX uq_knowledge_sources_source_name ON knowledge.knowledge_sources USING btree (source_name)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **10** of **10**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
