# travel.trip_requirement_revisions

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نیازمند توضیح دامنه‌ای تأییدشده از کد و مالک محصول
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T11:28:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | معنی کسب‌وکاری | قالب/واحد/enum | منبع شواهد | حساسیت/مالک | سطح خواندن/نوشتن |
|---|---|---|---|---|---|---|---|---|
| 'trip_id' | 'uuid' | خیر | — | Stable trip identity connecting requirements, itinerary and company sharing. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |
| 'user_id' | 'uuid' | خیر | — | User identity that owns or is associated with this record; foreign-key metadata identifies the referenced relation. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |
| 'revision_number' | 'integer' | خیر | — | Sequential revision number of the trip requirements snapshot. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((revision_number > 0)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |
| 'trip_version' | 'integer' | خیر | — | Revision/version number used for optimistic concurrency and stale-update detection. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((trip_version > 0)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |
| 'requirement_snapshot' | 'jsonb' | خیر | — | Versioned traveler-requirements snapshot recorded for the trip revision. | JSON object/array/scalar; exact shape is validated by the consuming contract. DB CHECK: CHECK ((jsonb_typeof(requirement_snapshot) = 'object'::text)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype-json.html](https://www.postgresql.org/docs/17/datatype-json.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |
| 'is_synthetic' | 'boolean' | خیر | 'false' | Synthetic/test fixture marker; these records must be excluded from production views. | PostgreSQL 'boolean'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'backend/app/api/traveler.py', 'backend/app/modules/trip/repository.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / traveler/account owner, with authentication/system-managed fields writable only by backend services | خواندن: authenticated traveler conversation/trip endpoints, owner-scoped; نوشتن: authenticated traveler endpoints with CSRF, ownership, and revision checks |

## محدودیت‌ها و ارتباط‌ها

- **trip_requirement_revisions_requirement_snapshot_check** (`c`): `CHECK ((jsonb_typeof(requirement_snapshot) = 'object'::text))`
- **trip_requirement_revisions_revision_number_check** (`c`): `CHECK ((revision_number > 0))`
- **trip_requirement_revisions_trip_version_check** (`c`): `CHECK ((trip_version > 0))`
- **trip_requirement_revisions_trip_id_user_id_fkey** (`f`): `FOREIGN KEY (trip_id, user_id) REFERENCES travel.trips(trip_id, user_id) ON DELETE CASCADE`
- **trip_requirement_revisions_pkey** (`p`): `PRIMARY KEY (trip_id, revision_number)`

## ایندکس‌ها

- `trip_requirement_revisions_pkey`: `CREATE UNIQUE INDEX trip_requirement_revisions_pkey ON travel.trip_requirement_revisions USING btree (trip_id, revision_number)`

## سیاست‌های RLS

- `trip_requirement_revision_owner_insert`: command=a, roles=[], using=`—`, with_check=`(user_id = partner.current_actor_id())`
- `trip_requirement_revision_owner_read`: command=r, roles=[], using=`(user_id = partner.current_actor_id())`, with_check=`—`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **7**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
