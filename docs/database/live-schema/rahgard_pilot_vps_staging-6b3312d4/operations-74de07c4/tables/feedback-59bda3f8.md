# operations.feedback

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
| 'feedback_id' | 'uuid' | خیر | 'gen_random_uuid()' | Identifier of a feedback record. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'engineering/database-prep/sql/009_traveler_core.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'user_id' | 'uuid' | بله | — | User identity that owns or is associated with this record; foreign-key metadata identifies the referenced relation. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((user_id IS NOT NULL) OR (conversation_id IS NOT NULL) OR (trip_id IS NOT NULL) OR (recommendation_id IS NOT NULL))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'engineering/database-prep/sql/009_traveler_core.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'conversation_id' | 'uuid' | بله | — | Conversation containing the travel request/message context. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((user_id IS NOT NULL) OR (conversation_id IS NOT NULL) OR (trip_id IS NOT NULL) OR (recommendation_id IS NOT NULL))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'engineering/database-prep/sql/009_traveler_core.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'trip_id' | 'uuid' | بله | — | Stable trip identity connecting requirements, itinerary and company sharing. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((user_id IS NOT NULL) OR (conversation_id IS NOT NULL) OR (trip_id IS NOT NULL) OR (recommendation_id IS NOT NULL))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'engineering/database-prep/sql/009_traveler_core.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'recommendation_id' | 'uuid' | بله | — | Recommendation associated with this record; foreign-key metadata identifies the recommendation relation. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((user_id IS NOT NULL) OR (conversation_id IS NOT NULL) OR (trip_id IS NOT NULL) OR (recommendation_id IS NOT NULL))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'engineering/database-prep/sql/009_traveler_core.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'feedback_type' | 'text' | خیر | — | Feedback category submitted for the associated trip/recommendation. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((feedback_type = ANY (ARRAY['recommendation_rating'::text, 'answer_quality'::text, 'itinerary_quality'::text, 'bug_report'::text, 'other'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'engineering/database-prep/sql/009_traveler_core.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'rating' | 'smallint' | بله | — | User-provided feedback rating; bounds are enforced by the feedback API/database constraints. | PostgreSQL 'smallint'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((feedback_type = ANY (ARRAY['recommendation_rating'::text, 'answer_quality'::text, 'itinerary_quality'::text, 'bug_report'::text, 'other'::text]))) \| CHECK (((rating IS NULL) OR ((rating >= 1) AND (rating <= 5)))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'engineering/database-prep/sql/009_traveler_core.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'comment' | 'text' | بله | — | User feedback text; may contain personal information and is not public by default. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'engineering/database-prep/sql/009_traveler_core.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | private_traveler_or_import_data / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'is_synthetic' | 'boolean' | خیر | 'false' | Synthetic/test fixture marker; these records must be excluded from production views. | PostgreSQL 'boolean'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'engineering/database-prep/sql/009_traveler_core.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'engineering/database-prep/sql/009_traveler_core.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_operational_or_audit_metadata / backend/system operator; no end-user generic write surface | خواندن: internal diagnostics/audit interfaces with minimization; نوشتن: backend operator/job only; no generic user CRUD |

## محدودیت‌ها و ارتباط‌ها

- **feedback_check** (`c`): `CHECK (((user_id IS NOT NULL) OR (conversation_id IS NOT NULL) OR (trip_id IS NOT NULL) OR (recommendation_id IS NOT NULL)))`
- **feedback_feedback_type_check** (`c`): `CHECK ((feedback_type = ANY (ARRAY['recommendation_rating'::text, 'answer_quality'::text, 'itinerary_quality'::text, 'bug_report'::text, 'other'::text])))`
- **feedback_rating_check** (`c`): `CHECK (((rating IS NULL) OR ((rating >= 1) AND (rating <= 5))))`
- **feedback_conversation_id_fkey** (`f`): `FOREIGN KEY (conversation_id) REFERENCES conversation.conversations(conversation_id) ON DELETE CASCADE`
- **feedback_recommendation_id_fkey** (`f`): `FOREIGN KEY (recommendation_id) REFERENCES recommendation.recommendations(recommendation_id) ON DELETE CASCADE`
- **feedback_trip_id_fkey** (`f`): `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- **feedback_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **feedback_pkey** (`p`): `PRIMARY KEY (feedback_id)`

## ایندکس‌ها

- `feedback_pkey`: `CREATE UNIQUE INDEX feedback_pkey ON operations.feedback USING btree (feedback_id)`
- `idx_feedback_type_created`: `CREATE INDEX idx_feedback_type_created ON operations.feedback USING btree (feedback_type, created_at DESC)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **10**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
