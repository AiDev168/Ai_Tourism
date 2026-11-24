# recommendation.recommendation_requests

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
| 'recommendation_request_id' | 'uuid' | خیر | 'gen_random_uuid()' | Identity of the recommendation request used to generate the result. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'trip_id' | 'uuid' | خیر | — | Stable trip identity connecting requirements, itinerary and company sharing. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'conversation_id' | 'uuid' | بله | — | Conversation containing the travel request/message context. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'algorithm_version' | 'text' | خیر | — | Version identifier for the deterministic recommendation algorithm. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'retrieval_version' | 'text' | بله | — | Version identifier for the evidence retrieval contract/configuration used by the request. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'input_snapshot' | 'jsonb' | خیر | '[redacted string default]' | Immutable requirements/input snapshot used for the associated recommendation request. | JSON object/array/scalar; exact shape is validated by the consuming contract. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype-json.html](https://www.postgresql.org/docs/17/datatype-json.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'request_status' | 'text' | خیر | '[redacted string default]' | Outcome/lifecycle state of the recommendation request. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((request_status = ANY (ARRAY['created'::text, 'processing'::text, 'completed'::text, 'failed'::text, 'cancelled'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'is_synthetic' | 'boolean' | خیر | 'false' | Synthetic/test fixture marker; these records must be excluded from production views. | PostgreSQL 'boolean'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'completed_at' | 'timestamp with time zone' | بله | — | Timestamp at which deterministic recommendation processing reached its completed state; null while pending or failed. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |

## محدودیت‌ها و ارتباط‌ها

- **recommendation_requests_request_status_check** (`c`): `CHECK ((request_status = ANY (ARRAY['created'::text, 'processing'::text, 'completed'::text, 'failed'::text, 'cancelled'::text])))`
- **recommendation_requests_conversation_id_fkey** (`f`): `FOREIGN KEY (conversation_id) REFERENCES conversation.conversations(conversation_id) ON DELETE SET NULL`
- **recommendation_requests_trip_id_fkey** (`f`): `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- **recommendation_requests_pkey** (`p`): `PRIMARY KEY (recommendation_request_id)`

## ایندکس‌ها

- `idx_recommendation_requests_trip_created`: `CREATE INDEX idx_recommendation_requests_trip_created ON recommendation.recommendation_requests USING btree (trip_id, created_at DESC)`
- `recommendation_requests_pkey`: `CREATE UNIQUE INDEX recommendation_requests_pkey ON recommendation.recommendation_requests USING btree (recommendation_request_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **10**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
