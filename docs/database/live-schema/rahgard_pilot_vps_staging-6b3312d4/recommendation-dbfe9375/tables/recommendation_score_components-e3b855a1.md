# recommendation.recommendation_score_components

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
| 'score_component_id' | 'uuid' | خیر | 'gen_random_uuid()' | Identifier of a deterministic recommendation score component. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'recommendation_id' | 'uuid' | خیر | — | Recommendation associated with this record; foreign-key metadata identifies the recommendation relation. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'component_key' | 'text' | خیر | — | Stable name of a recommendation scoring component. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'raw_score' | 'numeric(12,6)' | بله | — | Unnormalized score for one recommendation component. | PostgreSQL 'numeric(12,6)'; unit/currency comes from the paired domain fields, never from the numeric type. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'normalized_score' | 'numeric(7,6)' | بله | — | Score transformed to the recommendation component's normalized scale. | PostgreSQL 'numeric(7,6)'; unit/currency comes from the paired domain fields, never from the numeric type. DB CHECK: CHECK (((normalized_score IS NULL) OR ((normalized_score >= (0)::numeric) AND (normalized_score <= (1)::numeric)))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'weight' | 'numeric(7,6)' | خیر | — | Relative preference/constraint weight used by recommendation logic; scale and normalization are defined by the application contract. | PostgreSQL 'numeric(7,6)'; unit/currency comes from the paired domain fields, never from the numeric type. DB CHECK: CHECK (((weight >= (0)::numeric) AND (weight <= (1)::numeric))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'weighted_score' | 'numeric(12,6)' | خیر | — | Component score after applying its configured weight. | PostgreSQL 'numeric(12,6)'; unit/currency comes from the paired domain fields, never from the numeric type. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'component_reason' | 'text' | بله | — | Explanation for the score contribution from the associated component. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'is_synthetic' | 'boolean' | خیر | 'false' | Synthetic/test fixture marker; these records must be excluded from production views. | PostgreSQL 'boolean'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/modules/recommendation/service.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_catalogue_or_recommendation_metadata / recommendation service; input snapshots may contain traveler data | خواندن: authenticated recommendation response; private input snapshot is not exposed wholesale; نوشتن: deterministic recommendation service |

## محدودیت‌ها و ارتباط‌ها

- **recommendation_score_components_normalized_score_check** (`c`): `CHECK (((normalized_score IS NULL) OR ((normalized_score >= (0)::numeric) AND (normalized_score <= (1)::numeric))))`
- **recommendation_score_components_weight_check** (`c`): `CHECK (((weight >= (0)::numeric) AND (weight <= (1)::numeric)))`
- **recommendation_score_components_recommendation_id_fkey** (`f`): `FOREIGN KEY (recommendation_id) REFERENCES recommendation.recommendations(recommendation_id) ON DELETE CASCADE`
- **recommendation_score_components_pkey** (`p`): `PRIMARY KEY (score_component_id)`
- **recommendation_score_componen_recommendation_id_component_k_key** (`u`): `UNIQUE (recommendation_id, component_key)`

## ایندکس‌ها

- `idx_score_components_recommendation`: `CREATE INDEX idx_score_components_recommendation ON recommendation.recommendation_score_components USING btree (recommendation_id)`
- `recommendation_score_componen_recommendation_id_component_k_key`: `CREATE UNIQUE INDEX recommendation_score_componen_recommendation_id_component_k_key ON recommendation.recommendation_score_components USING btree (recommendation_id, component_key)`
- `recommendation_score_components_pkey`: `CREATE UNIQUE INDEX recommendation_score_components_pkey ON recommendation.recommendation_score_components USING btree (score_component_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **10**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
