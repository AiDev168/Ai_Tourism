# public.geometry_columns

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** View
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
| 'f_table_catalog' | 'character varying(256)' | بله | — | PostGIS compatibility-view catalog name for the database containing a geometry-typed column. | PostgreSQL 'character varying(256)'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html), [https://postgis.net/docs/using_postgis_dbmanagement.html](https://postgis.net/docs/using_postgis_dbmanagement.html) | technical_or_administrative_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'f_table_schema' | 'name' | بله | — | PostGIS compatibility-view schema name containing a geometry-typed column. | PostgreSQL identifier-name type; maximum length is the PostgreSQL NAMEDATALEN limit (63 bytes in standard builds). This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html), [https://postgis.net/docs/using_postgis_dbmanagement.html](https://postgis.net/docs/using_postgis_dbmanagement.html) | technical_or_administrative_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'f_table_name' | 'name' | بله | — | PostGIS compatibility-view name of the table containing the geometry column. | PostgreSQL identifier-name type; maximum length is the PostgreSQL NAMEDATALEN limit (63 bytes in standard builds). This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html), [https://postgis.net/docs/using_postgis_dbmanagement.html](https://postgis.net/docs/using_postgis_dbmanagement.html) | technical_or_administrative_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'f_geometry_column' | 'name' | بله | — | PostGIS compatibility-view column name whose type is geometry. | PostgreSQL identifier-name type; maximum length is the PostgreSQL NAMEDATALEN limit (63 bytes in standard builds). This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html), [https://postgis.net/docs/using_postgis_dbmanagement.html](https://postgis.net/docs/using_postgis_dbmanagement.html) | technical_or_administrative_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'coord_dimension' | 'integer' | بله | — | Coordinate dimension reported for the geometry column (for example 2D or 3D), as exposed by the PostGIS compatibility view. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html), [https://postgis.net/docs/using_postgis_dbmanagement.html](https://postgis.net/docs/using_postgis_dbmanagement.html) | technical_or_administrative_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'srid' | 'integer' | بله | — | Spatial Reference System Identifier associated with the geometry column, as exposed by PostGIS metadata. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html), [https://postgis.net/docs/using_postgis_dbmanagement.html](https://postgis.net/docs/using_postgis_dbmanagement.html) | technical_or_administrative_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |
| 'type' | 'character varying(30)' | بله | — | PostGIS geometry subtype reported by the compatibility view, such as Point or MultiPolygon. | PostgreSQL 'character varying(30)'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html), [https://postgis.net/docs/using_postgis_dbmanagement.html](https://postgis.net/docs/using_postgis_dbmanagement.html) | technical_or_administrative_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |

## محدودیت‌ها و ارتباط‌ها

- محدودیتی در `pg_constraint` برای این شیء مشاهده نشد.

## ایندکس‌ها

- ایندکسی مشاهده نشد / برای View قابل اعمال نیست.

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **7**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
