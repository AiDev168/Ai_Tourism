# identity.staging_auth_limits

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
| 'dimension' | 'text' | خیر | — | Staging-auth rate-limit bucket dimension; accepted values are defined by the CHECK constraint in migration 0016. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((dimension = ANY (ARRAY['login_name'::text, 'global'::text, 'invite'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'subject_digest' | 'bytea' | خیر | — | Pseudonymous digest used to scope a rate-limit subject without storing its raw identifier. | PostgreSQL 'bytea'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((octet_length(subject_digest) = 32)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'window_started_at' | 'timestamp with time zone' | خیر | — | Timestamp marking the beginning of a staging authentication rate-limit window. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'hit_count' | 'integer' | خیر | — | Number of requests counted in the associated rate-limit window. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((hit_count > 0)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |

## محدودیت‌ها و ارتباط‌ها

- **staging_auth_limits_dimension_check** (`c`): `CHECK ((dimension = ANY (ARRAY['login_name'::text, 'global'::text, 'invite'::text])))`
- **staging_auth_limits_hit_count_check** (`c`): `CHECK ((hit_count > 0))`
- **staging_auth_limits_subject_digest_check** (`c`): `CHECK ((octet_length(subject_digest) = 32))`
- **staging_auth_limits_pkey** (`p`): `PRIMARY KEY (dimension, subject_digest, window_started_at)`

## ایندکس‌ها

- `ix_staging_auth_limits_window`: `CREATE INDEX ix_staging_auth_limits_window ON identity.staging_auth_limits USING btree (window_started_at)`
- `staging_auth_limits_pkey`: `CREATE UNIQUE INDEX staging_auth_limits_pkey ON identity.staging_auth_limits USING btree (dimension, subject_digest, window_started_at)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **4**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
