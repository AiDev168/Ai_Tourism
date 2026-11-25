# operations.dataset_import_batches

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** backend/app/modules/catalog/archive_ingest.py:INSERT@156 | backend/app/modules/catalog/archive_ingest.py:SELECT@166 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/database-prep/sql/001_core_schema.sql:622
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'dataset_import_batch_id' | 'uuid' | خیر | 'gen_random_uuid()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:622 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/archive_ingest.py; column write path is not inferred |
| 'batch_key' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:622 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/archive_ingest.py; column write path is not inferred |
| 'data_class' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:622 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/archive_ingest.py; column write path is not inferred |
| 'source_id' | 'bigint' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bigint' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:622 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/archive_ingest.py; column write path is not inferred |
| 'record_counts' | 'jsonb' | خیر | '[redacted string default]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:622 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/archive_ingest.py; column write path is not inferred |
| 'source_checksum' | 'character(64)' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'character(64)' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:622 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/archive_ingest.py; column write path is not inferred |
| 'imported_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:622 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/archive_ingest.py; column write path is not inferred |
| 'notes' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:622 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/catalog/archive_ingest.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **dataset_import_batches_data_class_check** (`c`): `CHECK ((data_class = ANY (ARRAY['verified_external'::text, 'user_supplied_unverified'::text, 'synthetic_fixture'::text])))`
- **dataset_import_batches_source_id_fkey** (`f`): `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE SET NULL`
- **dataset_import_batches_pkey** (`p`): `PRIMARY KEY (dataset_import_batch_id)`
- **dataset_import_batches_batch_key_key** (`u`): `UNIQUE (batch_key)`

## ایندکس‌ها

- `dataset_import_batches_batch_key_key`: `CREATE UNIQUE INDEX dataset_import_batches_batch_key_key ON operations.dataset_import_batches USING btree (batch_key)`
- `dataset_import_batches_pkey`: `CREATE UNIQUE INDEX dataset_import_batches_pkey ON operations.dataset_import_batches USING btree (dataset_import_batch_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **8**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
