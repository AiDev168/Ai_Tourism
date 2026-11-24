# travel.trip_interests

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
| 'trip_interest_id' | 'uuid' | خیر | 'gen_random_uuid()' | Primary identifier for one weighted traveler interest attached to a trip. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |
| 'trip_id' | 'uuid' | خیر | — | Stable trip identity connecting requirements, itinerary and company sharing. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |
| 'interest_key' | 'text' | خیر | — | Stable identifier for a traveler interest used by the recommendation pipeline. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |
| 'weight' | 'numeric(5,4)' | خیر | '0.5' | Relative preference/constraint weight used by recommendation logic; scale and normalization are defined by the application contract. | PostgreSQL 'numeric(5,4)'; unit/currency comes from the paired domain fields, never from the numeric type. DB CHECK: CHECK (((weight >= (0)::numeric) AND (weight <= (1)::numeric))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |
| 'is_required' | 'boolean' | خیر | 'false' | Whether the associated interest/constraint is mandatory rather than a preference. | PostgreSQL 'boolean'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |
| 'is_synthetic' | 'boolean' | خیر | 'false' | Synthetic/test fixture marker; these records must be excluded from production views. | PostgreSQL 'boolean'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |

## محدودیت‌ها و ارتباط‌ها

- **trip_interests_weight_check** (`c`): `CHECK (((weight >= (0)::numeric) AND (weight <= (1)::numeric)))`
- **trip_interests_trip_id_fkey** (`f`): `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- **trip_interests_pkey** (`p`): `PRIMARY KEY (trip_interest_id)`
- **trip_interests_trip_id_interest_key_key** (`u`): `UNIQUE (trip_id, interest_key)`

## ایندکس‌ها

- `idx_trip_interests_trip`: `CREATE INDEX idx_trip_interests_trip ON travel.trip_interests USING btree (trip_id, is_required DESC, weight DESC)`
- `trip_interests_pkey`: `CREATE UNIQUE INDEX trip_interests_pkey ON travel.trip_interests USING btree (trip_interest_id)`
- `trip_interests_trip_id_interest_key_key`: `CREATE UNIQUE INDEX trip_interests_trip_id_interest_key_key ON travel.trip_interests USING btree (trip_id, interest_key)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **7**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
