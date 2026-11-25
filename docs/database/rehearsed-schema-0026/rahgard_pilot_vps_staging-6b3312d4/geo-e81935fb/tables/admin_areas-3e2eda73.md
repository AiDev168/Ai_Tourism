# geo.admin_areas

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** no explicit qualified CRUD clause found; not proof of no read/write path (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `INVESTIGATE` — No qualified backend/frontend relation reference was found; dynamic queries, contracts, or compatibility use may exist. Preserve until confirmed.
- **DDL provenance:** engineering/pilot/sql/018_national_catalogue_ingestion.sql:50
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'admin_area_id' | 'bigint' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bigint' only; business units, accepted values, and validation are not inferred from the SQL type.; identity-generated database key | engineering/pilot/sql/018_national_catalogue_ingestion.sql:50 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'release_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:50 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'area_type' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:50 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'official_code' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:50 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'parent_admin_area_id' | 'bigint' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bigint' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:50 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'canonical_name_fa' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:50 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'canonical_name_en' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:50 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'canonical_name_ar' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:50 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'normalized_key' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:50 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'geometry' | 'geometry(Geometry,4326)' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'geometry(Geometry,4326)' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:50 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'geometry_source_url' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:50 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'geometry_feature_key' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:50 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:50 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |

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

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **13** of **13**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
