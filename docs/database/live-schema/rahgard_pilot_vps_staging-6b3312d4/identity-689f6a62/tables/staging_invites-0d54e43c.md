# identity.staging_invites

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
| 'invite_id' | 'uuid' | خیر | 'gen_random_uuid()' | Primary identifier for one operator-issued, single-use staging invitation; the invitation secret is stored as a verifier, not in this identifier. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'token_digest' | 'bytea' | خیر | — | One-way digest of an invitation token; never expose or log the raw token. | PostgreSQL 'bytea'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((octet_length(token_digest) = 32)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. DB CHECK: CHECK (((expires_at > created_at) AND (expires_at <= (created_at + '14 days'::interval)))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'expires_at' | 'timestamp with time zone' | خیر | — | Expiry instant after which the associated credential, invitation, session, or record is no longer valid; see table context. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. DB CHECK: CHECK (((expires_at > created_at) AND (expires_at <= (created_at + '14 days'::interval)))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'consumed_at' | 'timestamp with time zone' | بله | — | Time when the one-time challenge or invitation was consumed; null means it has not been consumed. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. DB CHECK: CHECK (((consumed_at IS NULL) = (consumed_by IS NULL))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'consumed_by' | 'uuid' | بله | — | User identity that redeemed this one-time staging invitation; null until successful redemption. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((consumed_at IS NULL) = (consumed_by IS NULL))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/016_staging_invitation_auth.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |

## محدودیت‌ها و ارتباط‌ها

- **staging_invites_check** (`c`): `CHECK (((expires_at > created_at) AND (expires_at <= (created_at + '14 days'::interval))))`
- **staging_invites_check1** (`c`): `CHECK (((consumed_at IS NULL) = (consumed_by IS NULL)))`
- **staging_invites_token_digest_check** (`c`): `CHECK ((octet_length(token_digest) = 32))`
- **staging_invites_consumed_by_fkey** (`f`): `FOREIGN KEY (consumed_by) REFERENCES identity.users(user_id) ON DELETE SET NULL`
- **staging_invites_pkey** (`p`): `PRIMARY KEY (invite_id)`
- **staging_invites_token_digest_key** (`u`): `UNIQUE (token_digest)`

## ایندکس‌ها

- `staging_invites_pkey`: `CREATE UNIQUE INDEX staging_invites_pkey ON identity.staging_invites USING btree (invite_id)`
- `staging_invites_token_digest_key`: `CREATE UNIQUE INDEX staging_invites_token_digest_key ON identity.staging_invites USING btree (token_digest)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **6**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
