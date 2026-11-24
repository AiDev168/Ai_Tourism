# operations.audit_events

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
| 'audit_event_id' | 'uuid' | خیر | 'gen_random_uuid()' | Primary identifier for one security or business audit event; event payloads remain subject to minimization and access policy. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'actor_user_id' | 'uuid' | بله | — | Authenticated user identity that performed the associated action, when applicable. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'actor_type' | 'text' | خیر | '[redacted string default]' | Class of actor performing the audited action (for example user or system). | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((actor_type = ANY (ARRAY['user'::text, 'system'::text, 'administrator'::text, 'service'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'action' | 'text' | خیر | — | Audited operation/event name for the associated resource. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'resource_type' | 'text' | خیر | — | Type of audited/referenced resource associated with resource_id. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'resource_id' | 'text' | بله | — | Identifier of the audited/referenced resource; interpretation depends on resource_type. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'correlation_id' | 'uuid' | بله | — | Request/operation correlation identifier used to connect sanitized diagnostics. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'metadata' | 'jsonb' | خیر | '[redacted string default]' | Structured auxiliary metadata for the associated event/click; content schema is application-specific. | JSON object/array/scalar; exact shape is validated by the consuming contract. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype-json.html](https://www.postgresql.org/docs/17/datatype-json.html) | private_traveler_or_import_data / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |

## محدودیت‌ها و ارتباط‌ها

- **audit_events_actor_type_check** (`c`): `CHECK ((actor_type = ANY (ARRAY['user'::text, 'system'::text, 'administrator'::text, 'service'::text])))`
- **audit_events_actor_user_id_fkey** (`f`): `FOREIGN KEY (actor_user_id) REFERENCES identity.users(user_id) ON DELETE SET NULL`
- **audit_events_pkey** (`p`): `PRIMARY KEY (audit_event_id)`

## ایندکس‌ها

- `audit_events_pkey`: `CREATE UNIQUE INDEX audit_events_pkey ON operations.audit_events USING btree (audit_event_id)`
- `idx_audit_events_resource_time`: `CREATE INDEX idx_audit_events_resource_time ON operations.audit_events USING btree (resource_type, resource_id, created_at DESC)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **9**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
