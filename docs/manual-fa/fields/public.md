# فرهنگ فیلدهای افزونه و نشانگر (public)

[فهرست اصلی](../README.md). مبنا cab603a7d40cfa35dd20de2ffb12a336d84f56ff؛ metadata پایلوت 0026 + DDL 0027، نه snapshot زنده. NULL قید SQL است نه الزام فرم. پیش‌فرض redacted پالایش شده؛ مقدار را حدس نزنید. توضیح خوانش نام/نوع اثبات معنای تجاری نیست. اطلاعات شخصی، رمز، توکن و ممیزی را مستقیم تغییر ندهید.

[metadata](../../database/rehearsed-schema-0026/catalog_metadata_snapshot.json) | [glossary](../../database/field_descriptions.json) | [DDL 0027](../../../engineering/pilot/sql/027_server_ai_provider_admin.sql) | [مرجع 0027](../../database/rehearsed-schema-0027/PROVIDER_ADMIN_FIELD_REFERENCE.md)

## public.geography_columns

دامنه: افزونه و نشانگر؛ geography_columns (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: PostGIS یا اپراتور.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `f_table_catalog` | `name` | بله | ندارد | نام پایگاه جدول مکانی | نمای مشتق؛ بدون ورود | PostGIS |
| `f_table_schema` | `name` | بله | ندارد | نام شمای جدول مکانی | نمای مشتق؛ بدون ورود | PostGIS |
| `f_table_name` | `name` | بله | ندارد | نام جدول مکانی | نمای مشتق؛ بدون ورود | PostGIS |
| `f_geography_column` | `name` | بله | ندارد | نام ستون geography | نمای مشتق؛ بدون ورود | PostGIS |
| `coord_dimension` | `integer` | بله | ندارد | تعداد ابعاد مختصات | نمای مشتق؛ بدون ورود | PostGIS |
| `srid` | `integer` | بله | ندارد | شناسه دستگاه مختصات | نمای مشتق؛ بدون ورود | PostGIS |
| `type` | `text` | بله | ندارد | نوع هندسه | نمای مشتق؛ بدون ورود | PostGIS |

## public.geometry_columns

دامنه: افزونه و نشانگر؛ geometry_columns (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: PostGIS یا اپراتور.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `f_table_catalog` | `character varying(256)` | بله | ندارد | نام پایگاه جدول مکانی | نمای مشتق؛ بدون ورود | PostGIS |
| `f_table_schema` | `name` | بله | ندارد | نام شمای جدول مکانی | نمای مشتق؛ بدون ورود | PostGIS |
| `f_table_name` | `name` | بله | ندارد | نام جدول مکانی | نمای مشتق؛ بدون ورود | PostGIS |
| `f_geometry_column` | `name` | بله | ندارد | نام ستون geometry | نمای مشتق؛ بدون ورود | PostGIS |
| `coord_dimension` | `integer` | بله | ندارد | تعداد ابعاد مختصات | نمای مشتق؛ بدون ورود | PostGIS |
| `srid` | `integer` | بله | ندارد | شناسه دستگاه مختصات | نمای مشتق؛ بدون ورود | PostGIS |
| `type` | `character varying(30)` | بله | ندارد | نوع هندسه | نمای مشتق؛ بدون ورود | PostGIS |

## public.rahgard_private_pilot_marker

دامنه: افزونه و نشانگر؛ rahgard_private_pilot_marker (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: PostGIS یا اپراتور.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `marker_value` | `text` | خیر | ندارد | مقدار ـ نشانگر محیط؛ کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |

قیود جدول:
- `CHECK ((marker_value ~ '^[a-fA-F0-9]{48}$'::text))`
- `PRIMARY KEY (marker_value)`

## public.spatial_ref_sys

دامنه: افزونه و نشانگر؛ spatial_ref_sys (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: PostGIS یا اپراتور.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `srid` | `integer` | خیر | ندارد | شناسه دستگاه مختصات | افزونه؛ بدون ورود | PostGIS |
| `auth_name` | `character varying(256)` | بله | ندارد | نام مرجع سیستم مختصات | افزونه؛ بدون ورود | PostGIS |
| `auth_srid` | `integer` | بله | ندارد | شناسه نزد مرجع | افزونه؛ بدون ورود | PostGIS |
| `srtext` | `character varying(2048)` | بله | ندارد | تعریف متنی دستگاه مختصات | افزونه؛ بدون ورود | PostGIS |
| `proj4text` | `character varying(2048)` | بله | ندارد | پارامتر تصویرسازی | افزونه؛ بدون ورود | PostGIS |

قیود جدول:
- `CHECK (((srid > 0) AND (srid <= 998999)))`
- `PRIMARY KEY (srid)`
