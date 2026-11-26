# فرهنگ فیلدهای جغرافیا (geo)

[فهرست اصلی](../README.md). مبنا cab603a7d40cfa35dd20de2ffb12a336d84f56ff؛ metadata پایلوت 0026 + DDL 0027، نه snapshot زنده. NULL قید SQL است نه الزام فرم. پیش‌فرض redacted پالایش شده؛ مقدار را حدس نزنید. توضیح خوانش نام/نوع اثبات معنای تجاری نیست. اطلاعات شخصی، رمز، توکن و ممیزی را مستقیم تغییر ندهید.

[metadata](../../database/rehearsed-schema-0026/catalog_metadata_snapshot.json) | [glossary](../../database/field_descriptions.json) | [DDL 0027](../../../engineering/pilot/sql/027_server_ai_provider_admin.sql) | [مرجع 0027](../../database/rehearsed-schema-0027/PROVIDER_ADMIN_FIELD_REFERENCE.md)

## geo.admin_area_aliases

دامنه: جغرافیا؛ نام‌های جایگزین ـ محدوده ـ اداری/مدیریتی (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود داده مرجع؛ فرم مستقل احراز نشده.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `alias_id` | `bigint` | خیر | ندارد | شناسه ـ نام جایگزین؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `release_id` | `uuid` | خیر | ندارد | شناسه نسخه مجموعه داده محدوده | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `admin_area_id` | `bigint` | خیر | ندارد | شناسه محدوده اداری | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `alias` | `text` | خیر | ندارد | نام جایگزین که ممکن است در جستجو به کار رود | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `normalized_key` | `text` | خیر | ندارد | کلید نرمال‌شده برای تطبیق نام‌ها | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `locale` | `text` | خیر | ندارد | کد زبان و منطقه متن | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `alias_type` | `text` | خیر | ندارد | نوع نام جایگزین | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_url` | `text` | بله | ندارد | نشانی منبع این داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `review_status` | `text` | خیر | `[redacted string default]` | وضعیت بازبینی رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((length(btrim(alias)) >= 1) AND (length(btrim(alias)) <= 320)))`
- `CHECK ((alias_type = ANY (ARRAY['official_variant'::text, 'transliteration'::text, 'historical'::text, 'source_spelling'::text])))`
- `CHECK ((locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text, 'und'::text])))`
- `CHECK (((length(btrim(normalized_key)) >= 1) AND (length(btrim(normalized_key)) <= 320)))`
- `CHECK ((review_status = ANY (ARRAY['needs_review'::text, 'approved'::text, 'rejected'::text])))`
- `FOREIGN KEY (release_id, admin_area_id) REFERENCES geo.admin_areas(release_id, admin_area_id) ON DELETE RESTRICT`
- `PRIMARY KEY (alias_id)`
- `UNIQUE (release_id, admin_area_id, normalized_key, locale)`

## geo.admin_area_releases

دامنه: جغرافیا؛ admin_area_releases (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود داده مرجع؛ فرم مستقل احراز نشده.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `release_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ انتشار؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `authority` | `text` | خیر | ندارد | مرجع منتشرکننده داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `dataset_title` | `text` | خیر | ندارد | عنوان مجموعه داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_url` | `text` | خیر | ندارد | نشانی منبع این داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `release_key` | `text` | خیر | ندارد | کلید نسخه داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `published_at` | `timestamp with time zone` | بله | ندارد | زمان انتشار رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `retrieved_at` | `timestamp with time zone` | خیر | `now()` | زمان دریافت اطلاعات منبع | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `effective_from` | `date` | بله | ندارد | زمان شروع اعتبار نسخه | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `effective_until` | `date` | بله | ندارد | زمان پایان اعتبار نسخه | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `content_sha256` | `character(64)` | خیر | ندارد | اثر انگشت SHA-256 محتوا برای مقایسه و تشخیص تغییر | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((length(btrim(authority)) >= 1) AND (length(btrim(authority)) <= 240)))`
- `CHECK (((effective_until IS NULL) OR (effective_from IS NULL) OR (effective_until >= effective_from)))`
- `CHECK ((content_sha256 ~ '^[a-f0-9]{64}$'::text))`
- `CHECK (((length(btrim(dataset_title)) >= 1) AND (length(btrim(dataset_title)) <= 240)))`
- `CHECK (((length(btrim(release_key)) >= 1) AND (length(btrim(release_key)) <= 120)))`
- `CHECK ((source_url ~ '^https://'::text))`
- `PRIMARY KEY (release_id)`
- `UNIQUE (authority, release_key)`

## geo.admin_areas

دامنه: جغرافیا؛ admin_areas (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود داده مرجع؛ فرم مستقل احراز نشده.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `admin_area_id` | `bigint` | خیر | ندارد | شناسه ـ محدوده ـ اداری/مدیریتی؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `release_id` | `uuid` | خیر | ندارد | شناسه ـ انتشار؛ ارجاع به geo.admin_area_releases(release_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `area_type` | `text` | خیر | ندارد | نوع محدوده اداری | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `official_code` | `text` | بله | ندارد | کد رسمی محدوده نزد مرجع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `parent_admin_area_id` | `bigint` | بله | ندارد | شناسه محدوده والد در سلسله مراتب | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `canonical_name_fa` | `text` | خیر | ندارد | نام معیار فارسی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `canonical_name_en` | `text` | بله | ندارد | نام معیار انگلیسی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `canonical_name_ar` | `text` | بله | ندارد | نام معیار عربی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `normalized_key` | `text` | خیر | ندارد | کلید نرمال‌شده برای تطبیق نام‌ها | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `geometry` | `geometry(Geometry,4326)` | بله | ندارد | هندسه محدوده جغرافیایی در نوع مکانی SQL | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `geometry_source_url` | `text` | بله | ندارد | نشانی منبع هندسه | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `geometry_feature_key` | `text` | بله | ندارد | کلید عارضه جغرافیایی در منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((area_type = ANY (ARRAY['country'::text, 'province'::text, 'county'::text, 'district'::text, 'city'::text, 'rural_district'::text, 'locality'::text, 'other'::text])))`
- `CHECK (((length(btrim(canonical_name_fa)) >= 1) AND (length(btrim(canonical_name_fa)) <= 240)))`
- `CHECK (((geometry_source_url IS NULL) = (geometry_feature_key IS NULL)))`
- `CHECK (((length(btrim(normalized_key)) >= 1) AND (length(btrim(normalized_key)) <= 320)))`
- `FOREIGN KEY (release_id) REFERENCES geo.admin_area_releases(release_id) ON DELETE RESTRICT`
- `FOREIGN KEY (release_id, parent_admin_area_id) REFERENCES geo.admin_areas(release_id, admin_area_id) ON DELETE RESTRICT`
- `PRIMARY KEY (admin_area_id)`
- `UNIQUE (release_id, admin_area_id)`
- `UNIQUE (release_id, area_type, official_code)`
