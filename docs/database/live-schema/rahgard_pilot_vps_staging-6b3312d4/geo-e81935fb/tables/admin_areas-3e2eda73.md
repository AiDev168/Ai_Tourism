# geo.admin_areas

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
| 'admin_area_id' | 'bigint' | خیر | — | Reviewed administrative-area identity associated with the destination. | PostgreSQL 'bigint'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'release_id' | 'uuid' | خیر | — | Administrative data release that defines this area or alias. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'area_type' | 'text' | خیر | — | Hierarchy level/type for the administrative area (for example province, county, district, or city). | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((area_type = ANY (ARRAY['country'::text, 'province'::text, 'county'::text, 'district'::text, 'city'::text, 'rural_district'::text, 'locality'::text, 'other'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'official_code' | 'text' | بله | — | Official administrative-area code from the identified source release. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'parent_admin_area_id' | 'bigint' | بله | — | Parent administrative area in the hierarchy from the referenced release. | PostgreSQL 'bigint'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'canonical_name_fa' | 'text' | خیر | — | Official/local Persian canonical name for the administrative area. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((length(btrim(canonical_name_fa)) >= 1) AND (length(btrim(canonical_name_fa)) <= 240))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'canonical_name_en' | 'text' | بله | — | English canonical name for the administrative area. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'canonical_name_ar' | 'text' | بله | — | Arabic canonical name for the administrative area. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'normalized_key' | 'text' | خیر | — | Normalized comparison/search key derived from the original name/alias; it is not a replacement for the raw label. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((length(btrim(normalized_key)) >= 1) AND (length(btrim(normalized_key)) <= 320))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'geometry' | 'geometry(Geometry,4326)' | بله | — | PostGIS geometry for the administrative area; geometry source, feature identity and SRID are recorded separately. | PostGIS 'geometry(Geometry,4326)'; interpret SRID and coordinate role from relation constraints/companion fields. DB CHECK: CHECK (((geometry_source_url IS NULL) = (geometry_feature_key IS NULL))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'geometry_source_url' | 'text' | بله | — | URL associated with the 'geometry source' relationship; exact rights and publication eligibility depend on the associated source record. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((geometry_source_url IS NULL) = (geometry_feature_key IS NULL))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'geometry_feature_key' | 'text' | بله | — | Stable machine-readable key for the associated 'geometry feature' identity or vocabulary. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((geometry_source_url IS NULL) = (geometry_feature_key IS NULL))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | technical_or_administrative_metadata / administrative data steward/import process | خواندن: resolved administrative metadata/map filters where explicitly exposed; نوشتن: administrative import/review tooling only |

## محدودیت‌ها و ارتباط‌ها

- **admin_areas_area_type_check** (`c`): `CHECK ((area_type = ANY (ARRAY['country'::text, 'province'::text, 'county'::text, 'district'::text, 'city'::text, 'rural_district'::text, 'locality'::text, 'other'::text])))`
- **admin_areas_canonical_name_fa_check** (`c`): `CHECK (((length(btrim(canonical_name_fa)) >= 1) AND (length(btrim(canonical_name_fa)) <= 240)))`
- **admin_areas_check** (`c`): `CHECK (((geometry_source_url IS NULL) = (geometry_feature_key IS NULL)))`
- **admin_areas_normalized_key_check** (`c`): `CHECK (((length(btrim(normalized_key)) >= 1) AND (length(btrim(normalized_key)) <= 320)))`
- **admin_areas_release_id_fkey** (`f`): `FOREIGN KEY (release_id) REFERENCES geo.admin_area_releases(release_id) ON DELETE RESTRICT`
- **admin_areas_release_id_parent_admin_area_id_fkey** (`f`): `FOREIGN KEY (release_id, parent_admin_area_id) REFERENCES geo.admin_areas(release_id, admin_area_id) ON DELETE RESTRICT`
- **admin_areas_pkey** (`p`): `PRIMARY KEY (admin_area_id)`
- **admin_areas_release_id_admin_area_id_key** (`u`): `UNIQUE (release_id, admin_area_id)`
- **admin_areas_release_id_area_type_official_code_key** (`u`): `UNIQUE (release_id, area_type, official_code)`

## ایندکس‌ها

- `admin_areas_pkey`: `CREATE UNIQUE INDEX admin_areas_pkey ON geo.admin_areas USING btree (admin_area_id)`
- `admin_areas_release_id_admin_area_id_key`: `CREATE UNIQUE INDEX admin_areas_release_id_admin_area_id_key ON geo.admin_areas USING btree (release_id, admin_area_id)`
- `admin_areas_release_id_area_type_official_code_key`: `CREATE UNIQUE INDEX admin_areas_release_id_area_type_official_code_key ON geo.admin_areas USING btree (release_id, area_type, official_code)`
- `ix_admin_areas_geometry`: `CREATE INDEX ix_admin_areas_geometry ON geo.admin_areas USING gist (geometry) WHERE (geometry IS NOT NULL)`
- `ix_admin_areas_release_parent`: `CREATE INDEX ix_admin_areas_release_parent ON geo.admin_areas USING btree (release_id, parent_admin_area_id, area_type)`
- `ix_admin_areas_type_normalized`: `CREATE INDEX ix_admin_areas_type_normalized ON geo.admin_areas USING btree (area_type, normalized_key)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **13**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
