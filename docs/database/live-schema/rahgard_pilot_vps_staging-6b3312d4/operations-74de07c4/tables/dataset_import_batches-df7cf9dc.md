# operations.dataset_import_batches

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
| 'dataset_import_batch_id' | 'uuid' | خیر | 'gen_random_uuid()' | Identifier of the import batch associated with this candidate/proposal. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'batch_key' | 'text' | خیر | — | Stable identifier for an idempotent import batch. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'data_class' | 'text' | خیر | — | Classification of imported batch provenance; migration 0018 constrains it to verified_external, user_supplied_unverified, or synthetic_fixture. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((data_class = ANY (ARRAY['verified_external'::text, 'user_supplied_unverified'::text, 'synthetic_fixture'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'source_id' | 'bigint' | بله | — | Registered knowledge/source record associated with this evidence or destination. | PostgreSQL 'bigint'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'record_counts' | 'jsonb' | خیر | '[redacted string default]' | Per-record-type counts captured for the import batch; keys/schema are defined by the importer. | JSON object/array/scalar; exact shape is validated by the consuming contract. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype-json.html](https://www.postgresql.org/docs/17/datatype-json.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'source_checksum' | 'character(64)' | بله | — | Checksum of the imported source dataset; exact algorithm is identified by the contract or adjacent field. | PostgreSQL 'character(64)'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'imported_at' | 'timestamp with time zone' | خیر | 'now()' | Time when the import batch was committed to staging. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'notes' | 'text' | بله | — | Operator-entered note associated with the import or record. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |

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

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **8**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
