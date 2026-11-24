# identity.staging_password_credentials

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
| 'user_id' | 'uuid' | خیر | — | User identity that owns or is associated with this record; foreign-key metadata identifies the referenced relation. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'login_name' | 'text' | خیر | — | Normalized login identifier used by the staging/local password authentication contract. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((login_name = lower(login_name)) AND ((length(login_name) >= 5) AND (length(login_name) <= 254)) AND (login_name ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'::text))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'salt' | 'bytea' | خیر | — | Per-credential random salt used by password derivation; security metadata, never a client field. | PostgreSQL 'bytea'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((octet_length(salt) = 32)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'verifier' | 'bytea' | خیر | — | Reviewer identity or system label that performed source verification; public exposure is restricted. | PostgreSQL 'bytea'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((octet_length(verifier) = 32)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'iterations' | 'integer' | خیر | — | Password-derivation iteration count used for this credential record; the derived verifier and salt are sensitive authentication data. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((iterations = 600000)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |

## محدودیت‌ها و ارتباط‌ها

- **staging_password_credentials_iterations_check** (`c`): `CHECK ((iterations = 600000))`
- **staging_password_credentials_login_name_check** (`c`): `CHECK (((login_name = lower(login_name)) AND ((length(login_name) >= 5) AND (length(login_name) <= 254)) AND (login_name ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'::text)))`
- **staging_password_credentials_salt_check** (`c`): `CHECK ((octet_length(salt) = 32))`
- **staging_password_credentials_verifier_check** (`c`): `CHECK ((octet_length(verifier) = 32))`
- **staging_password_credentials_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **staging_password_credentials_pkey** (`p`): `PRIMARY KEY (user_id)`
- **staging_password_credentials_login_name_key** (`u`): `UNIQUE (login_name)`

## ایندکس‌ها

- `staging_password_credentials_login_name_key`: `CREATE UNIQUE INDEX staging_password_credentials_login_name_key ON identity.staging_password_credentials USING btree (login_name)`
- `staging_password_credentials_pkey`: `CREATE UNIQUE INDEX staging_password_credentials_pkey ON identity.staging_password_credentials USING btree (user_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **6**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
