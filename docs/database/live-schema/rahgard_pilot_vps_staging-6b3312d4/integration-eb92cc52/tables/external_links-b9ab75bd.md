# integration.external_links

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
| 'external_link_id' | 'uuid' | خیر | 'gen_random_uuid()' | Identifier of the destination's external booking/information link. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'destination_id' | 'bigint' | بله | — | Canonical destination identity associated with this row. | PostgreSQL 'bigint'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'provider_name' | 'text' | خیر | — | Provider identifier used for the recorded call or space; API keys are stored elsewhere and never documented here. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'service_type' | 'text' | خیر | — | Company service classification; allowed types follow the partner API vocabulary. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((service_type = ANY (ARRAY['hotel'::text, 'flight'::text, 'train'::text, 'tour'::text, 'car_rental'::text, 'official_info'::text, 'other'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'label_fa' | 'text' | خیر | — | Persian human-readable label for the associated external link. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'target_url' | 'text' | خیر | — | URL opened by an authorized external-link action. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((target_url ~ '^https?://'::text)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'is_active' | 'boolean' | خیر | 'true' | Activation flag for the associated record; review and publication status remain separate. | PostgreSQL 'boolean'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'is_synthetic' | 'boolean' | خیر | 'false' | Synthetic/test fixture marker; these records must be excluded from production views. | PostgreSQL 'boolean'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_catalogue_or_recommendation_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |

## محدودیت‌ها و ارتباط‌ها

- **external_links_service_type_check** (`c`): `CHECK ((service_type = ANY (ARRAY['hotel'::text, 'flight'::text, 'train'::text, 'tour'::text, 'car_rental'::text, 'official_info'::text, 'other'::text])))`
- **external_links_target_url_check** (`c`): `CHECK ((target_url ~ '^https?://'::text))`
- **external_links_destination_id_fkey** (`f`): `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE SET NULL`
- **external_links_pkey** (`p`): `PRIMARY KEY (external_link_id)`

## ایندکس‌ها

- `external_links_pkey`: `CREATE UNIQUE INDEX external_links_pkey ON integration.external_links USING btree (external_link_id)`
- `idx_external_links_destination_service`: `CREATE INDEX idx_external_links_destination_service ON integration.external_links USING btree (destination_id, service_type, is_active)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **9**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
