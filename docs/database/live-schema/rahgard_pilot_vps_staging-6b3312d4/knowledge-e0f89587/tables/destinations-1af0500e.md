# knowledge.destinations

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
| 'destination_id' | 'bigint' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'canonical_name' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'destination_type' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'province_name' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'city_name' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'description' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'difficulty' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'suitable_transport' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'local_language' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'local_food' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'local_souvenirs' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'best_travel_time' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'latitude' | 'double precision' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد ممیز شناور؛ دقت و واحد کاربردی نیازمند قرارداد دامنه است |
| 'longitude' | 'double precision' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد ممیز شناور؛ دقت و واحد کاربردی نیازمند قرارداد دامنه است |
| 'status' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'data_confidence' | 'numeric(5,4)' | خیر | '0' | **نیازمند تکمیل از API / منطق دامنه** | عدد ده‌دهی؛ precision و scale از PostgreSQL؛ واحد/ارز باید مستند شود |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'destination_key' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'country_code' | 'character(2)' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته با طول ثابت مشخص‌شده در PostgreSQL |
| 'aliases' | 'text[]' | خیر | 'ARRAY[]::text[]' | **نیازمند تکمیل از API / منطق دامنه** | آرایه‌ای از مقادیر؛ قالب عنصر مطابق نوع پایه |
| 'parent_destination_id' | 'bigint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'record_origin' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'verification_status' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'is_synthetic' | 'boolean' | خیر | 'false' | **نیازمند تکمیل از API / منطق دامنه** | true / false |
| 'coordinate_role' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'location' | 'geography(Point,4326)' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | نوع سفارشی یا قالب وابسته به دامنه؛ اعتبارسنجی API/enum را بررسی کنید |
| 'admin_area_id' | 'bigint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |

## محدودیت‌ها و ارتباط‌ها

- **chk_destination_confidence** (`c`): `CHECK (((data_confidence >= (0)::numeric) AND (data_confidence <= (1)::numeric)))`
- **chk_destination_coordinate_role** (`c`): `CHECK ((((latitude IS NULL) AND (longitude IS NULL) AND (coordinate_role = 'unknown'::text)) OR ((latitude IS NOT NULL) AND (longitude IS NOT NULL) AND (coordinate_role = ANY (ARRAY['property_reference'::text, 'representative_point'::text, 'visitor_entrance'::text, 'test_fixture'::text])))))`
- **chk_destination_coordinates_pair** (`c`): `CHECK (((latitude IS NULL) = (longitude IS NULL)))`
- **chk_destination_country_code** (`c`): `CHECK ((country_code ~ '^[A-Z]{2}$'::text))`
- **chk_destination_record_origin** (`c`): `CHECK ((record_origin = ANY (ARRAY['user_supplied_unverified'::text, 'verified_external'::text, 'synthetic_fixture'::text])))`
- **chk_destination_status** (`c`): `CHECK ((status = ANY (ARRAY['draft'::text, 'active'::text, 'inactive'::text, 'archived'::text, 'needs_review'::text, 'test_only'::text])))`
- **chk_destination_synthetic_origin** (`c`): `CHECK ((is_synthetic = (record_origin = 'synthetic_fixture'::text)))`
- **chk_destination_type_key** (`c`): `CHECK ((destination_type ~ '^[a-z][a-z0-9_]{1,63}$'::text))`
- **chk_destination_verification_status** (`c`): `CHECK ((verification_status = ANY (ARRAY['pending'::text, 'verified'::text, 'rejected'::text, 'stale'::text, 'not_applicable'::text])))`
- **chk_latitude** (`c`): `CHECK (((latitude IS NULL) OR ((latitude >= ('-90'::integer)::double precision) AND (latitude <= (90)::double precision))))`
- **chk_longitude** (`c`): `CHECK (((longitude IS NULL) OR ((longitude >= ('-180'::integer)::double precision) AND (longitude <= (180)::double precision))))`
- **destinations_admin_area_id_fkey** (`f`): `FOREIGN KEY (admin_area_id) REFERENCES geo.admin_areas(admin_area_id) ON DELETE RESTRICT`
- **fk_destination_parent** (`f`): `FOREIGN KEY (parent_destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE SET NULL`
- **destinations_pkey** (`p`): `PRIMARY KEY (destination_id)`
- **uq_destination_canonical** (`u`): `UNIQUE (canonical_name, province_name, city_name)`

## ایندکس‌ها

- `destinations_pkey`: `CREATE UNIQUE INDEX destinations_pkey ON knowledge.destinations USING btree (destination_id)`
- `idx_destinations_aliases_gin`: `CREATE INDEX idx_destinations_aliases_gin ON knowledge.destinations USING gin (aliases)`
- `idx_destinations_city`: `CREATE INDEX idx_destinations_city ON knowledge.destinations USING btree (city_name)`
- `idx_destinations_location_gist`: `CREATE INDEX idx_destinations_location_gist ON knowledge.destinations USING gist (location)`
- `idx_destinations_origin_status`: `CREATE INDEX idx_destinations_origin_status ON knowledge.destinations USING btree (record_origin, verification_status, status)`
- `idx_destinations_province`: `CREATE INDEX idx_destinations_province ON knowledge.destinations USING btree (province_name)`
- `idx_destinations_province_city`: `CREATE INDEX idx_destinations_province_city ON knowledge.destinations USING btree (province_name, city_name)`
- `idx_destinations_status`: `CREATE INDEX idx_destinations_status ON knowledge.destinations USING btree (status)`
- `ix_destinations_admin_area_id`: `CREATE INDEX ix_destinations_admin_area_id ON knowledge.destinations USING btree (admin_area_id) WHERE (admin_area_id IS NOT NULL)`
- `ix_destinations_city_prefix`: `CREATE INDEX ix_destinations_city_prefix ON knowledge.destinations USING btree (lower(city_name) text_pattern_ops, destination_id) WHERE (city_name IS NOT NULL)`
- `ix_destinations_name_prefix`: `CREATE INDEX ix_destinations_name_prefix ON knowledge.destinations USING btree (lower(canonical_name) text_pattern_ops, destination_id)`
- `ix_destinations_province_prefix`: `CREATE INDEX ix_destinations_province_prefix ON knowledge.destinations USING btree (lower(province_name) text_pattern_ops, destination_id)`
- `ix_destinations_type_id`: `CREATE INDEX ix_destinations_type_id ON knowledge.destinations USING btree (destination_type, destination_id)`
- `uq_destination_canonical`: `CREATE UNIQUE INDEX uq_destination_canonical ON knowledge.destinations USING btree (canonical_name, province_name, city_name)`
- `uq_destinations_canonical_identity`: `CREATE UNIQUE INDEX uq_destinations_canonical_identity ON knowledge.destinations USING btree (canonical_name, province_name, COALESCE(city_name, ''::text))`
- `uq_destinations_destination_key`: `CREATE UNIQUE INDEX uq_destinations_destination_key ON knowledge.destinations USING btree (destination_key)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- `trg_sync_destination_location`: `CREATE TRIGGER trg_sync_destination_location BEFORE INSERT OR UPDATE OF latitude, longitude ON knowledge.destinations FOR EACH ROW EXECUTE FUNCTION knowledge.sync_destination_location()`

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **28** از **28**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
