# knowledge.destination_localizations

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نیازمند توضیح دامنه‌ای تأییدشده از کد و مالک محصول
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'destination_id' | 'bigint' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'locale' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'display_name' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'short_description' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'description' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'translation_status' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'content_status' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'content_version' | 'integer' | خیر | '1' | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'reviewed_at' | 'timestamp with time zone' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **destination_localizations_content_status_check** (`c`): `CHECK ((content_status = ANY (ARRAY['draft'::text, 'approved'::text, 'rejected'::text, 'withdrawn'::text])))`
- **destination_localizations_content_version_check** (`c`): `CHECK ((content_version > 0))`
- **destination_localizations_display_name_check** (`c`): `CHECK (((length(btrim(display_name)) >= 1) AND (length(btrim(display_name)) <= 240)))`
- **destination_localizations_locale_check** (`c`): `CHECK ((locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text])))`
- **destination_localizations_translation_status_check** (`c`): `CHECK ((translation_status = ANY (ARRAY['draft'::text, 'editor_reviewed'::text, 'native_review_required'::text, 'blocked'::text])))`
- **destination_localizations_destination_id_fkey** (`f`): `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE`
- **destination_localizations_pkey** (`p`): `PRIMARY KEY (destination_id, locale)`

## ایندکس‌ها

- `destination_localizations_pkey`: `CREATE UNIQUE INDEX destination_localizations_pkey ON knowledge.destination_localizations USING btree (destination_id, locale)`
- `ix_destination_localizations_locale_status`: `CREATE INDEX ix_destination_localizations_locale_status ON knowledge.destination_localizations USING btree (locale, content_status, destination_id)`

## سیاست‌های RLS

- `localizations_insert_reviewers`: command=a, roles=[], using=`—`, with_check=`(((content_status <> 'approved'::text) AND identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text)) OR identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'catalogue_publish'::text))`
- `localizations_select_reviewers`: command=r, roles=[], using=`(identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text) OR identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'catalogue_publish'::text))`, with_check=`—`
- `localizations_update_reviewers`: command=w, roles=[], using=`(identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text) OR identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'catalogue_publish'::text))`, with_check=`(((content_status <> 'approved'::text) AND identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text)) OR identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'catalogue_publish'::text))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **11** از **11**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
