# system.schema_migrations

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
| 'migration_id' | 'text' | خیر | — | Stable migration identifier recorded in the applied-schema ledger; it is the logical migration name, not the source checksum. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/000_bootstrap.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'sha256' | 'text' | خیر | — | SHA-256 checksum of the exact migration source applied for this migration_id; used to detect schema-history drift. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((length(sha256) = 64)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/000_bootstrap.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'applied_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp when this migration ledger entry was committed by the migration runner. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/000_bootstrap.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_catalogue_or_recommendation_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |

## محدودیت‌ها و ارتباط‌ها

- **schema_migrations_sha256_check** (`c`): `CHECK ((length(sha256) = 64))`
- **schema_migrations_pkey** (`p`): `PRIMARY KEY (migration_id)`

## ایندکس‌ها

- `schema_migrations_pkey`: `CREATE UNIQUE INDEX schema_migrations_pkey ON system.schema_migrations USING btree (migration_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **3**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
