# geo.admin_areas

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
| 'admin_area_id' | 'bigint' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود; ستون Identity |
| 'release_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'area_type' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'official_code' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'parent_admin_area_id' | 'bigint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'canonical_name_fa' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'canonical_name_en' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'canonical_name_ar' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'normalized_key' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'geometry' | 'geometry(Geometry,4326)' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | نوع سفارشی یا قالب وابسته به دامنه؛ اعتبارسنجی API/enum را بررسی کنید |
| 'geometry_source_url' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'geometry_feature_key' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

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

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **13** از **13**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
