# geo.admin_area_aliases

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
| 'alias_id' | 'bigint' | خیر | — | Surrogate key for one alternate spelling or name associated with a canonical administrative area. | PostgreSQL 'bigint'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'release_id' | 'uuid' | خیر | — | Administrative data release that defines this area or alias. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'admin_area_id' | 'bigint' | خیر | — | Reviewed administrative-area identity associated with the destination. | PostgreSQL 'bigint'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'alias' | 'text' | خیر | — | Alternate administrative place name retained for resolution and search. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((length(btrim(alias)) >= 1) AND (length(btrim(alias)) <= 320))) \| CHECK ((alias_type = ANY (ARRAY['official_variant'::text, 'transliteration'::text, 'historical'::text, 'source_spelling'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'normalized_key' | 'text' | خیر | — | Normalized comparison/search key derived from the original name/alias; it is not a replacement for the raw label. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((length(btrim(normalized_key)) >= 1) AND (length(btrim(normalized_key)) <= 320))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'locale' | 'text' | خیر | — | Locale of this localized value or evidence, using the application's supported locale contract. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text, 'und'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'alias_type' | 'text' | خیر | — | Classification of the alternate name (for example spelling, transliteration, or historical name). | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((alias_type = ANY (ARRAY['official_variant'::text, 'transliteration'::text, 'historical'::text, 'source_spelling'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'source_url' | 'text' | بله | — | Source URL supporting the associated identity, location, or operational claim. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'review_status' | 'text' | خیر | '[redacted string default]' | Review lifecycle state of this relation's entity; it is not synonymous with publication. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((review_status = ANY (ARRAY['needs_review'::text, 'approved'::text, 'rejected'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |

## محدودیت‌ها و ارتباط‌ها

- **admin_area_aliases_alias_check** (`c`): `CHECK (((length(btrim(alias)) >= 1) AND (length(btrim(alias)) <= 320)))`
- **admin_area_aliases_alias_type_check** (`c`): `CHECK ((alias_type = ANY (ARRAY['official_variant'::text, 'transliteration'::text, 'historical'::text, 'source_spelling'::text])))`
- **admin_area_aliases_locale_check** (`c`): `CHECK ((locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text, 'und'::text])))`
- **admin_area_aliases_normalized_key_check** (`c`): `CHECK (((length(btrim(normalized_key)) >= 1) AND (length(btrim(normalized_key)) <= 320)))`
- **admin_area_aliases_review_status_check** (`c`): `CHECK ((review_status = ANY (ARRAY['needs_review'::text, 'approved'::text, 'rejected'::text])))`
- **admin_area_aliases_release_id_admin_area_id_fkey** (`f`): `FOREIGN KEY (release_id, admin_area_id) REFERENCES geo.admin_areas(release_id, admin_area_id) ON DELETE RESTRICT`
- **admin_area_aliases_pkey** (`p`): `PRIMARY KEY (alias_id)`
- **admin_area_aliases_release_id_admin_area_id_normalized_key__key** (`u`): `UNIQUE (release_id, admin_area_id, normalized_key, locale)`

## ایندکس‌ها

- `admin_area_aliases_pkey`: `CREATE UNIQUE INDEX admin_area_aliases_pkey ON geo.admin_area_aliases USING btree (alias_id)`
- `admin_area_aliases_release_id_admin_area_id_normalized_key__key`: `CREATE UNIQUE INDEX admin_area_aliases_release_id_admin_area_id_normalized_key__key ON geo.admin_area_aliases USING btree (release_id, admin_area_id, normalized_key, locale)`
- `ix_admin_area_aliases_normalized`: `CREATE INDEX ix_admin_area_aliases_normalized ON geo.admin_area_aliases USING btree (release_id, normalized_key)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **10**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
