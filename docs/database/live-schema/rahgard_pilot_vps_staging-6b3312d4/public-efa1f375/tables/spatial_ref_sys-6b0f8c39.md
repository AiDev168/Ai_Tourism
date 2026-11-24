# public.spatial_ref_sys

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
- **Architecture disposition:** `EXTENSION-MANAGED` — PostGIS-owned technical catalog object; keep under extension lifecycle, not a Rahgard business form.
- **DDL provenance:** not found in scanned checked-in SQL
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-24T11:28:13Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'srid' | 'integer' | خیر | — | Extension-managed PostgreSQL/PostGIS metadata; not an independent Rahgard business field. See [official PostGIS database management documentation](https://postgis.net/docs/using_postgis_dbmanagement.html). | PostgreSQL storage type 'integer' only; business units, accepted values, and validation are not inferred from the SQL type. | https://postgis.net/docs/using_postgis_dbmanagement.html | technical_extension_metadata / PostgreSQL owner 'ai_tourism_owner'; PostGIS object classification; not traveler/company data.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'auth_name' | 'character varying(256)' | بله | — | Extension-managed PostgreSQL/PostGIS metadata; not an independent Rahgard business field. See [official PostGIS database management documentation](https://postgis.net/docs/using_postgis_dbmanagement.html). | PostgreSQL storage type 'character varying(256)' only; business units, accepted values, and validation are not inferred from the SQL type. | https://postgis.net/docs/using_postgis_dbmanagement.html | technical_extension_metadata / PostgreSQL owner 'ai_tourism_owner'; PostGIS object classification; not traveler/company data.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'auth_srid' | 'integer' | بله | — | Extension-managed PostgreSQL/PostGIS metadata; not an independent Rahgard business field. See [official PostGIS database management documentation](https://postgis.net/docs/using_postgis_dbmanagement.html). | PostgreSQL storage type 'integer' only; business units, accepted values, and validation are not inferred from the SQL type. | https://postgis.net/docs/using_postgis_dbmanagement.html | technical_extension_metadata / PostgreSQL owner 'ai_tourism_owner'; PostGIS object classification; not traveler/company data.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'srtext' | 'character varying(2048)' | بله | — | Extension-managed PostgreSQL/PostGIS metadata; not an independent Rahgard business field. See [official PostGIS database management documentation](https://postgis.net/docs/using_postgis_dbmanagement.html). | PostgreSQL storage type 'character varying(2048)' only; business units, accepted values, and validation are not inferred from the SQL type. | https://postgis.net/docs/using_postgis_dbmanagement.html | technical_extension_metadata / PostgreSQL owner 'ai_tourism_owner'; PostGIS object classification; not traveler/company data.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'proj4text' | 'character varying(2048)' | بله | — | Extension-managed PostgreSQL/PostGIS metadata; not an independent Rahgard business field. See [official PostGIS database management documentation](https://postgis.net/docs/using_postgis_dbmanagement.html). | PostgreSQL storage type 'character varying(2048)' only; business units, accepted values, and validation are not inferred from the SQL type. | https://postgis.net/docs/using_postgis_dbmanagement.html | technical_extension_metadata / PostgreSQL owner 'ai_tourism_owner'; PostGIS object classification; not traveler/company data.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **spatial_ref_sys_srid_check** (`c`): `CHECK (((srid > 0) AND (srid <= 998999)))`
- **spatial_ref_sys_pkey** (`p`): `PRIMARY KEY (srid)`

## ایندکس‌ها

- `spatial_ref_sys_pkey`: `CREATE UNIQUE INDEX spatial_ref_sys_pkey ON public.spatial_ref_sys USING btree (srid)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **5**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
