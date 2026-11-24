# identity.catalogue_review_grants

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
| 'user_id' | 'uuid' | خیر | — | User identity that owns or is associated with this record; foreign-key metadata identifies the referenced relation. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'capability' | 'text' | خیر | — | Catalogue capability granted to a reviewer; allowed capabilities are candidate_review, source_review, and catalogue_publish. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((capability = ANY (ARRAY['candidate_review'::text, 'source_review'::text, 'catalogue_publish'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'granted_by' | 'uuid' | خیر | — | User identity of the operator who issued this catalogue capability grant; it is audit provenance, not the grantee. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'reason' | 'text' | خیر | — | Reviewer explanation for accepting, rejecting, or returning the associated record. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((length(btrim(reason)) >= 10) AND (length(btrim(reason)) <= 1000))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'granted_at' | 'timestamp with time zone' | خیر | 'now()' | Time at which the associated permission or consent was granted. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. DB CHECK: CHECK (((revoked_at IS NULL) OR (revoked_at >= granted_at))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |
| 'revoked_at' | 'timestamp with time zone' | بله | — | Time at which the associated permission or consent was revoked. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. DB CHECK: CHECK (((revoked_at IS NULL) OR (revoked_at >= granted_at))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/auth.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | restricted_authentication_or_authorization_metadata / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authentication/session endpoints only; secrets/digests never returned; نوشتن: backend auth service only; no direct client table writes |

## محدودیت‌ها و ارتباط‌ها

- **catalogue_review_grants_capability_check** (`c`): `CHECK ((capability = ANY (ARRAY['candidate_review'::text, 'source_review'::text, 'catalogue_publish'::text])))`
- **catalogue_review_grants_check** (`c`): `CHECK (((revoked_at IS NULL) OR (revoked_at >= granted_at)))`
- **catalogue_review_grants_reason_check** (`c`): `CHECK (((length(btrim(reason)) >= 10) AND (length(btrim(reason)) <= 1000)))`
- **catalogue_review_grants_granted_by_fkey** (`f`): `FOREIGN KEY (granted_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **catalogue_review_grants_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **catalogue_review_grants_pkey** (`p`): `PRIMARY KEY (user_id, capability, granted_at)`

## ایندکس‌ها

- `catalogue_review_grants_pkey`: `CREATE UNIQUE INDEX catalogue_review_grants_pkey ON identity.catalogue_review_grants USING btree (user_id, capability, granted_at)`
- `ix_catalogue_review_grants_active`: `CREATE INDEX ix_catalogue_review_grants_active ON identity.catalogue_review_grants USING btree (user_id, capability) WHERE (revoked_at IS NULL)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **6**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
