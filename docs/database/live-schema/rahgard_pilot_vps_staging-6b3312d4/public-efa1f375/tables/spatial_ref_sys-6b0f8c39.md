# public.spatial_ref_sys

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
| 'srid' | 'integer' | خیر | — | PostGIS spatial reference system identifier used by spatial values to identify their coordinate reference system. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((srid > 0) AND (srid <= 998999))) | 'docs/database/live-schema/catalog_snapshot.json', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html), [https://postgis.net/docs/using_postgis_dbmanagement.html](https://postgis.net/docs/using_postgis_dbmanagement.html) | technical_or_administrative_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'auth_name' | 'character varying(256)' | بله | — | Name of the standards authority that assigned the corresponding auth_srid, when available. | PostgreSQL 'character varying(256)'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html), [https://postgis.net/docs/using_postgis_dbmanagement.html](https://postgis.net/docs/using_postgis_dbmanagement.html) | technical_or_administrative_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'auth_srid' | 'integer' | بله | — | Authority-assigned SRID corresponding to this PostGIS spatial reference definition, when known. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html), [https://postgis.net/docs/using_postgis_dbmanagement.html](https://postgis.net/docs/using_postgis_dbmanagement.html) | technical_or_administrative_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'srtext' | 'character varying(2048)' | بله | — | Well-Known Text definition of the coordinate reference system represented by this PostGIS SRID. | PostgreSQL 'character varying(2048)'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html), [https://postgis.net/docs/using_postgis_dbmanagement.html](https://postgis.net/docs/using_postgis_dbmanagement.html) | technical_or_administrative_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'proj4text' | 'character varying(2048)' | بله | — | PROJ parameter-string representation of the coordinate reference system; retained for compatibility with PostGIS/PROJ transformations. | PostgreSQL 'character varying(2048)'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html), [https://postgis.net/docs/using_postgis_dbmanagement.html](https://postgis.net/docs/using_postgis_dbmanagement.html) | technical_or_administrative_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |

## محدودیت‌ها و ارتباط‌ها

- **spatial_ref_sys_srid_check** (`c`): `CHECK (((srid > 0) AND (srid <= 998999)))`
- **spatial_ref_sys_pkey** (`p`): `PRIMARY KEY (srid)`

## ایندکس‌ها

- `spatial_ref_sys_pkey`: `CREATE UNIQUE INDEX spatial_ref_sys_pkey ON public.spatial_ref_sys USING btree (srid)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **5**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
