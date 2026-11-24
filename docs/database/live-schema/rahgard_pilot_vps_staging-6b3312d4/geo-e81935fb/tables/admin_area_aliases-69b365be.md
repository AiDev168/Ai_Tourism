# geo.admin_area_aliases

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
- **DDL provenance:** engineering/pilot/sql/018_national_catalogue_ingestion.sql:74
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-24T11:28:13Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'alias_id' | 'bigint' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bigint' only; business units, accepted values, and validation are not inferred from the SQL type.; identity-generated database key | engineering/pilot/sql/018_national_catalogue_ingestion.sql:74 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'release_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:74 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'admin_area_id' | 'bigint' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bigint' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:74 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'alias' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:74 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'normalized_key' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:74 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'locale' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:74 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'alias_type' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:74 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'source_url' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:74 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'review_status' | 'text' | خیر | '[redacted string default]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:74 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:74 | administrative_geography_metadata / PostgreSQL owner 'ai_tourism_owner'; Administrative reference data; source release and publication context still apply.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |

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

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **10** of **10**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
