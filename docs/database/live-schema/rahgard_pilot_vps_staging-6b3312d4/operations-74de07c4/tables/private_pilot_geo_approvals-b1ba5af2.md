# operations.private_pilot_geo_approvals

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
| 'authorization_id' | 'uuid' | خیر | — | Foreign-key identity of the one-use geographic authorization consumed by this approval event. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/013_private_pilot_geo_audit.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'destination_key' | 'text' | خیر | — | Stable canonical destination identity key; not a localized display name. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/013_private_pilot_geo_audit.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'decision_sha256' | 'character(64)' | خیر | — | Digest binding a review authorization to its exact serialized decision payload. | PostgreSQL 'character(64)'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((decision_sha256 ~ '^[a-f0-9]{64}$'::text)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/013_private_pilot_geo_audit.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'marker_sha256' | 'character(64)' | خیر | — | Digest of the isolated pilot/deployment marker used to bind an approval to a specific environment. | PostgreSQL 'character(64)'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((marker_sha256 ~ '^[a-f0-9]{64}$'::text)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/013_private_pilot_geo_audit.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'reviewer' | 'text' | خیر | — | Reviewer label recorded for the approval; not a public contact field. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/013_private_pilot_geo_audit.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'approval_reference' | 'text' | خیر | — | Non-secret reference identifying the owner approval associated with this consumed geographic visibility authorization. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/013_private_pilot_geo_audit.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'reviewed_at' | 'timestamp with time zone' | خیر | — | Timestamp when a reviewer last inspected or reviewed this record. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/013_private_pilot_geo_audit.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'coordinate_role' | 'text' | خیر | — | Meaning of the stored coordinate (such as representative point or access point); never infer an entrance from another role. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((coordinate_role = ANY (ARRAY['representative_point'::text, 'property_reference'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/013_private_pilot_geo_audit.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/013_private_pilot_geo_audit.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |

## محدودیت‌ها و ارتباط‌ها

- **private_pilot_geo_approvals_coordinate_role_check** (`c`): `CHECK ((coordinate_role = ANY (ARRAY['representative_point'::text, 'property_reference'::text])))`
- **private_pilot_geo_approvals_decision_sha256_check** (`c`): `CHECK ((decision_sha256 ~ '^[a-f0-9]{64}$'::text))`
- **private_pilot_geo_approvals_marker_sha256_check** (`c`): `CHECK ((marker_sha256 ~ '^[a-f0-9]{64}$'::text))`
- **private_pilot_geo_approvals_authorization_id_fkey** (`f`): `FOREIGN KEY (authorization_id) REFERENCES operations.private_pilot_geo_authorizations(authorization_id)`
- **private_pilot_geo_approvals_destination_key_fkey** (`f`): `FOREIGN KEY (destination_key) REFERENCES knowledge.destinations(destination_key)`
- **private_pilot_geo_approvals_pkey** (`p`): `PRIMARY KEY (authorization_id)`
- **private_pilot_geo_approvals_destination_key_decision_sha256_key** (`u`): `UNIQUE (destination_key, decision_sha256, marker_sha256)`

## ایندکس‌ها

- `private_pilot_geo_approvals_destination_key_decision_sha256_key`: `CREATE UNIQUE INDEX private_pilot_geo_approvals_destination_key_decision_sha256_key ON operations.private_pilot_geo_approvals USING btree (destination_key, decision_sha256, marker_sha256)`
- `private_pilot_geo_approvals_pkey`: `CREATE UNIQUE INDEX private_pilot_geo_approvals_pkey ON operations.private_pilot_geo_approvals USING btree (authorization_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **9**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
