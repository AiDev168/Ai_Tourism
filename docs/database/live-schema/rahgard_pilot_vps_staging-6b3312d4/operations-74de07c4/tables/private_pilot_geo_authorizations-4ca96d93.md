# operations.private_pilot_geo_authorizations

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
| 'authorization_id' | 'uuid' | خیر | 'gen_random_uuid()' | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'destination_key' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'decision_sha256' | 'character(64)' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته با طول ثابت مشخص‌شده در PostgreSQL |
| 'marker_sha256' | 'character(64)' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته با طول ثابت مشخص‌شده در PostgreSQL |
| 'canonical_name' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'destination_type' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'province_name' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'city_name' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'latitude' | 'double precision' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد ممیز شناور؛ دقت و واحد کاربردی نیازمند قرارداد دامنه است |
| 'longitude' | 'double precision' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد ممیز شناور؛ دقت و واحد کاربردی نیازمند قرارداد دامنه است |
| 'coordinate_role' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'source_url' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'reviewer' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'approval_reference' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'reviewed_at' | 'timestamp with time zone' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'expires_at' | 'timestamp with time zone' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **private_pilot_geo_authorizations_approval_reference_check** (`c`): `CHECK (((length(btrim(approval_reference)) >= 1) AND (length(btrim(approval_reference)) <= 240)))`
- **private_pilot_geo_authorizations_check** (`c`): `CHECK (((reviewed_at <= created_at) AND (expires_at > created_at) AND (expires_at <= (created_at + '01:00:00'::interval))))`
- **private_pilot_geo_authorizations_check1** (`c`): `CHECK ((((destination_key = 'shiraz-hafezieh-v1'::text) AND (coordinate_role = 'representative_point'::text) AND (source_url = 'https://en.wikipedia.org/wiki/Tomb_of_Hafez'::text)) OR ((destination_key = 'shiraz-eram-garden-v1'::text) AND (coordinate_role = 'representative_point'::text) AND (source_url = 'https://en.wikipedia.org/wiki/Eram_Garden'::text)) OR ((destination_key = 'shiraz-vakil-bazaar-v1'::text) AND (coordinate_role = 'representative_point'::text) AND (source_url = 'https://en.wikipedia.org/wiki/Vakil_Bazaar'::text)) OR ((destination_key = 'unesco-persepolis-v1'::text) AND (coordinate_role = 'property_reference'::text) AND (source_url = 'https://whc.unesco.org/en/list/114/maps/'::text))))`
- **private_pilot_geo_authorizations_decision_sha256_check** (`c`): `CHECK ((decision_sha256 ~ '^[a-f0-9]{64}$'::text))`
- **private_pilot_geo_authorizations_latitude_check** (`c`): `CHECK (((latitude >= ('-90'::integer)::double precision) AND (latitude <= (90)::double precision)))`
- **private_pilot_geo_authorizations_longitude_check** (`c`): `CHECK (((longitude >= ('-180'::integer)::double precision) AND (longitude <= (180)::double precision)))`
- **private_pilot_geo_authorizations_marker_sha256_check** (`c`): `CHECK ((marker_sha256 ~ '^[a-f0-9]{64}$'::text))`
- **private_pilot_geo_authorizations_reviewer_check** (`c`): `CHECK (((length(btrim(reviewer)) >= 1) AND (length(btrim(reviewer)) <= 240)))`
- **private_pilot_geo_authorizations_destination_key_fkey** (`f`): `FOREIGN KEY (destination_key) REFERENCES knowledge.destinations(destination_key)`
- **private_pilot_geo_authorizations_pkey** (`p`): `PRIMARY KEY (authorization_id)`
- **private_pilot_geo_authorizati_destination_key_decision_sha2_key** (`u`): `UNIQUE (destination_key, decision_sha256, marker_sha256)`

## ایندکس‌ها

- `private_pilot_geo_authorizati_destination_key_decision_sha2_key`: `CREATE UNIQUE INDEX private_pilot_geo_authorizati_destination_key_decision_sha2_key ON operations.private_pilot_geo_authorizations USING btree (destination_key, decision_sha256, marker_sha256)`
- `private_pilot_geo_authorizations_pkey`: `CREATE UNIQUE INDEX private_pilot_geo_authorizations_pkey ON operations.private_pilot_geo_authorizations USING btree (authorization_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **17** از **17**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
