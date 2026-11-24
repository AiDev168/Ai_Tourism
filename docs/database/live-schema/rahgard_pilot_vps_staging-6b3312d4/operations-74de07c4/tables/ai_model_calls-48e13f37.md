# operations.ai_model_calls

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نیازمند توضیح دامنه‌ای تأییدشده از کد و مالک محصول
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T11:28:13Z`
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | معنی کسب‌وکاری | قالب/واحد/enum | منبع شواهد | حساسیت/مالک | سطح خواندن/نوشتن |
|---|---|---|---|---|---|---|---|---|
| 'ai_model_call_id' | 'uuid' | خیر | 'gen_random_uuid()' | Identifier of the recorded model invocation telemetry row. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'correlation_id' | 'uuid' | بله | — | Request/operation correlation identifier used to connect sanitized diagnostics. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'provider_name' | 'text' | خیر | — | Provider identifier used for the recorded call or space; API keys are stored elsewhere and never documented here. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'model_name' | 'text' | خیر | — | Model identifier used for the call/space; not a model credential. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'task_type' | 'text' | خیر | — | Application task class for the associated model invocation. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'call_status' | 'text' | خیر | — | Outcome state of the recorded AI provider invocation. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((call_status = ANY (ARRAY['success'::text, 'timeout'::text, 'rate_limited'::text, 'provider_error'::text, 'validation_error'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'input_tokens' | 'integer' | بله | — | Provider-reported or estimated prompt token count. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((input_tokens IS NULL) OR (input_tokens >= 0))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_direct_identifier / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'output_tokens' | 'integer' | بله | — | Provider-reported or estimated completion token count. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((output_tokens IS NULL) OR (output_tokens >= 0))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_direct_identifier / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'latency_ms' | 'integer' | بله | — | Duration between request start and completion, in milliseconds. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((latency_ms IS NULL) OR (latency_ms >= 0))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'estimated_cost' | 'numeric(14,8)' | بله | — | Estimated provider cost for the call; estimation basis is provider/configuration specific. | PostgreSQL 'numeric(14,8)'; unit/currency comes from the paired domain fields, never from the numeric type. DB CHECK: CHECK (((estimated_cost IS NULL) OR (estimated_cost >= (0)::numeric))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'cost_currency' | 'character(3)' | بله | — | Currency used for the estimated model call cost. | PostgreSQL 'character(3)'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |

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

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **12**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
