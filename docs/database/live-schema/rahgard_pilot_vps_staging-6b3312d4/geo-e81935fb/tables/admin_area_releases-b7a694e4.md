# geo.admin_area_releases

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
| 'release_id' | 'uuid' | خیر | 'gen_random_uuid()' | Administrative data release that defines this area or alias. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'authority' | 'text' | خیر | — | Publisher/authority responsible for the administrative dataset release. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((length(btrim(authority)) >= 1) AND (length(btrim(authority)) <= 240))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'dataset_title' | 'text' | خیر | — | Title of the administrative dataset release. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((length(btrim(dataset_title)) >= 1) AND (length(btrim(dataset_title)) <= 240))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'source_url' | 'text' | خیر | — | Source URL supporting the associated identity, location, or operational claim. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((source_url ~ '^https://'::text)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'release_key' | 'text' | خیر | — | Stable identifier for the administrative dataset release. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((length(btrim(release_key)) >= 1) AND (length(btrim(release_key)) <= 120))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'published_at' | 'timestamp with time zone' | بله | — | Publication time reported for the administrative dataset or content. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'retrieved_at' | 'timestamp with time zone' | خیر | 'now()' | Time when the associated source/document/evidence was retrieved. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'effective_from' | 'date' | بله | — | Start date when the administrative release or fact applies. | Gregorian ISO date YYYY-MM-DD in storage; localized calendars are presentation only. DB CHECK: CHECK (((effective_until IS NULL) OR (effective_from IS NULL) OR (effective_until >= effective_from))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'effective_until' | 'date' | بله | — | End date when the administrative release or fact applies, if bounded. | Gregorian ISO date YYYY-MM-DD in storage; localized calendars are presentation only. DB CHECK: CHECK (((effective_until IS NULL) OR (effective_from IS NULL) OR (effective_until >= effective_from))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'content_sha256' | 'character(64)' | خیر | — | SHA-256 digest of the associated content version, used for integrity/version identity. | PostgreSQL 'character(64)'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((content_sha256 ~ '^[a-f0-9]{64}$'::text)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |

## محدودیت‌ها و ارتباط‌ها

- **admin_area_releases_authority_check** (`c`): `CHECK (((length(btrim(authority)) >= 1) AND (length(btrim(authority)) <= 240)))`
- **admin_area_releases_check** (`c`): `CHECK (((effective_until IS NULL) OR (effective_from IS NULL) OR (effective_until >= effective_from)))`
- **admin_area_releases_content_sha256_check** (`c`): `CHECK ((content_sha256 ~ '^[a-f0-9]{64}$'::text))`
- **admin_area_releases_dataset_title_check** (`c`): `CHECK (((length(btrim(dataset_title)) >= 1) AND (length(btrim(dataset_title)) <= 240)))`
- **admin_area_releases_release_key_check** (`c`): `CHECK (((length(btrim(release_key)) >= 1) AND (length(btrim(release_key)) <= 120)))`
- **admin_area_releases_source_url_check** (`c`): `CHECK ((source_url ~ '^https://'::text))`
- **admin_area_releases_pkey** (`p`): `PRIMARY KEY (release_id)`
- **admin_area_releases_authority_release_key_key** (`u`): `UNIQUE (authority, release_key)`

## ایندکس‌ها

- `admin_area_releases_authority_release_key_key`: `CREATE UNIQUE INDEX admin_area_releases_authority_release_key_key ON geo.admin_area_releases USING btree (authority, release_key)`
- `admin_area_releases_pkey`: `CREATE UNIQUE INDEX admin_area_releases_pkey ON geo.admin_area_releases USING btree (release_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **11**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
