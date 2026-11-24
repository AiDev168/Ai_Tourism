# geo.admin_area_aliases

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نیازمند توضیح دامنه‌ای تأییدشده از کد و مالک محصول
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'alias_id' | 'bigint' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود; ستون Identity |
| 'release_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'admin_area_id' | 'bigint' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'alias' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'normalized_key' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'locale' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'alias_type' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'source_url' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'review_status' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

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

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **10** از **10**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
