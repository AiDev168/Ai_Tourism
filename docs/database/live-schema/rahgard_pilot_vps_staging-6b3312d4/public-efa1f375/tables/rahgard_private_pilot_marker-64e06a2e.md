# public.rahgard_private_pilot_marker

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
| 'marker_value' | 'text' | خیر | — | Opaque deployment/test guard marker used to bind privileged pilot operations to the intended isolated database; not a user-facing value. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((marker_value ~ '^[a-fA-F0-9]{48}$'::text)) | 'docs/database/live-schema/catalog_snapshot.json', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html), [https://postgis.net/docs/using_postgis_dbmanagement.html](https://postgis.net/docs/using_postgis_dbmanagement.html), 'engineering/pilot/Run-National-Catalogue-Browser-E2E.ps1' | technical_or_administrative_metadata / PostgreSQL/PostGIS extension or platform metadata owner | خواندن: PostgreSQL/PostGIS metadata APIs only when needed; نوشتن: extension/platform managed |

## محدودیت‌ها و ارتباط‌ها

- **rahgard_private_pilot_marker_marker_value_check** (`c`): `CHECK ((marker_value ~ '^[a-fA-F0-9]{48}$'::text))`
- **rahgard_private_pilot_marker_pkey** (`p`): `PRIMARY KEY (marker_value)`

## ایندکس‌ها

- `rahgard_private_pilot_marker_pkey`: `CREATE UNIQUE INDEX rahgard_private_pilot_marker_pkey ON public.rahgard_private_pilot_marker USING btree (marker_value)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **1**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
