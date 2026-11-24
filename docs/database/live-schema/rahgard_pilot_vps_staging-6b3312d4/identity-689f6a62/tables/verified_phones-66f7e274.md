# identity.verified_phones

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
| 'phone_e164' | 'text' | خیر | — | Phone number in E.164 format; direct personal identifier and authentication contact data. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((phone_e164 ~ '^\+989[0-9]{9}$'::text)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/008_authentication_foundation.sql', 'engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_direct_identifier / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'user_id' | 'uuid' | خیر | — | User identity that owns or is associated with this record; foreign-key metadata identifies the referenced relation. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/008_authentication_foundation.sql', 'engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'verified_at' | 'timestamp with time zone' | خیر | — | Time when the associated identity, source, or organization was verified. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/008_authentication_foundation.sql', 'engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'challenge_id' | 'uuid' | بله | — | Nullable provenance link to the OTP challenge that verified this phone; it is not a reusable authentication credential. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/008_authentication_foundation.sql', 'engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |

## محدودیت‌ها و ارتباط‌ها

- **verified_phones_phone_e164_check** (`c`): `CHECK ((phone_e164 ~ '^\+989[0-9]{9}$'::text))`
- **verified_phones_challenge_id_fkey** (`f`): `FOREIGN KEY (challenge_id) REFERENCES identity.otp_challenges(challenge_id) ON DELETE SET NULL`
- **verified_phones_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **verified_phones_pkey** (`p`): `PRIMARY KEY (phone_e164)`
- **verified_phones_challenge_id_key** (`u`): `UNIQUE (challenge_id)`
- **verified_phones_user_id_key** (`u`): `UNIQUE (user_id)`

## ایندکس‌ها

- `verified_phones_challenge_id_key`: `CREATE UNIQUE INDEX verified_phones_challenge_id_key ON identity.verified_phones USING btree (challenge_id)`
- `verified_phones_pkey`: `CREATE UNIQUE INDEX verified_phones_pkey ON identity.verified_phones USING btree (phone_e164)`
- `verified_phones_user_id_key`: `CREATE UNIQUE INDEX verified_phones_user_id_key ON identity.verified_phones USING btree (user_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **4**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
