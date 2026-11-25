# operations.ai_model_calls

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
- **DDL provenance:** engineering/database-prep/sql/001_core_schema.sql:589
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'ai_model_call_id' | 'uuid' | خیر | 'gen_random_uuid()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:589 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'correlation_id' | 'uuid' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:589 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'provider_name' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:589 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'model_name' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:589 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'task_type' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:589 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'call_status' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:589 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'input_tokens' | 'integer' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'integer' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:589 | restricted_auth_or_secret_metadata / PostgreSQL owner 'ai_tourism_owner'; Column name and identity/provider contract; values must never be exposed in documentation.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'output_tokens' | 'integer' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'integer' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:589 | restricted_auth_or_secret_metadata / PostgreSQL owner 'ai_tourism_owner'; Column name and identity/provider contract; values must never be exposed in documentation.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'latency_ms' | 'integer' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'integer' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:589 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'estimated_cost' | 'numeric(14,8)' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'numeric(14,8)' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:589 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'cost_currency' | 'character(3)' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'character(3)' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:589 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:589 | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **ai_model_calls_call_status_check** (`c`): `CHECK ((call_status = ANY (ARRAY['success'::text, 'timeout'::text, 'rate_limited'::text, 'provider_error'::text, 'validation_error'::text])))`
- **ai_model_calls_estimated_cost_check** (`c`): `CHECK (((estimated_cost IS NULL) OR (estimated_cost >= (0)::numeric)))`
- **ai_model_calls_input_tokens_check** (`c`): `CHECK (((input_tokens IS NULL) OR (input_tokens >= 0)))`
- **ai_model_calls_latency_ms_check** (`c`): `CHECK (((latency_ms IS NULL) OR (latency_ms >= 0)))`
- **ai_model_calls_output_tokens_check** (`c`): `CHECK (((output_tokens IS NULL) OR (output_tokens >= 0)))`
- **ai_model_calls_pkey** (`p`): `PRIMARY KEY (ai_model_call_id)`

## ایندکس‌ها

- `ai_model_calls_pkey`: `CREATE UNIQUE INDEX ai_model_calls_pkey ON operations.ai_model_calls USING btree (ai_model_call_id)`
- `idx_ai_model_calls_provider_created`: `CREATE INDEX idx_ai_model_calls_provider_created ON operations.ai_model_calls USING btree (provider_name, created_at DESC)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **12**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
