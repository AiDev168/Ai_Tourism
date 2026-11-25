# integration.external_links

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** no explicit qualified CRUD clause found; not proof of no read/write path (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `INVESTIGATE` — No qualified backend/frontend relation reference was found; dynamic queries, contracts, or compatibility use may exist. Preserve until confirmed.
- **DDL provenance:** engineering/database-prep/sql/001_core_schema.sql:538
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'external_link_id' | 'uuid' | خیر | 'gen_random_uuid()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:538 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'destination_id' | 'bigint' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bigint' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:538 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'provider_name' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:538 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'service_type' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:538 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'label_fa' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:538 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'target_url' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:538 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'is_active' | 'boolean' | خیر | 'true' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'boolean' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:538 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'is_synthetic' | 'boolean' | خیر | 'false' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'boolean' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:538 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:538 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **external_links_service_type_check** (`c`): `CHECK ((service_type = ANY (ARRAY['hotel'::text, 'flight'::text, 'train'::text, 'tour'::text, 'car_rental'::text, 'official_info'::text, 'other'::text])))`
- **external_links_target_url_check** (`c`): `CHECK ((target_url ~ '^https?://'::text))`
- **external_links_destination_id_fkey** (`f`): `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE SET NULL`
- **external_links_pkey** (`p`): `PRIMARY KEY (external_link_id)`

## ایندکس‌ها

- `external_links_pkey`: `CREATE UNIQUE INDEX external_links_pkey ON integration.external_links USING btree (external_link_id)`
- `idx_external_links_destination_service`: `CREATE INDEX idx_external_links_destination_service ON integration.external_links USING btree (destination_id, service_type, is_active)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **9**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
