# travel.itinerary_stops

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
| 'itinerary_stop_id' | 'uuid' | خیر | 'gen_random_uuid()' | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'itinerary_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'destination_id' | 'bigint' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'day_number' | 'smallint' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'stop_order' | 'smallint' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'planned_start_time' | 'time without time zone' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | زمان روز؛ قالب HH:MM:SS و منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'duration_minutes' | 'smallint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'travel_to_next_estimate_minutes' | 'smallint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'notes_fa' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'is_synthetic' | 'boolean' | خیر | 'false' | **نیازمند تکمیل از API / منطق دامنه** | true / false |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'notes_by_locale' | 'jsonb' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'recommendation_id' | 'uuid' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |

## محدودیت‌ها و ارتباط‌ها

- **itinerary_stops_day_number_365_check** (`c`): `CHECK (((day_number >= 1) AND (day_number <= 365)))`
- **itinerary_stops_duration_minutes_check** (`c`): `CHECK (((duration_minutes IS NULL) OR ((duration_minutes >= 1) AND (duration_minutes <= 1440))))`
- **itinerary_stops_notes_by_locale_check** (`c`): `CHECK ((jsonb_typeof(notes_by_locale) = 'object'::text))`
- **itinerary_stops_stop_order_50_check** (`c`): `CHECK (((stop_order >= 1) AND (stop_order <= 50)))`
- **itinerary_stops_travel_to_next_estimate_minutes_check** (`c`): `CHECK (((travel_to_next_estimate_minutes IS NULL) OR (travel_to_next_estimate_minutes >= 0)))`
- **itinerary_stops_destination_id_fkey** (`f`): `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- **itinerary_stops_itinerary_id_fkey** (`f`): `FOREIGN KEY (itinerary_id) REFERENCES travel.itineraries(itinerary_id) ON DELETE CASCADE`
- **itinerary_stops_recommendation_id_fkey** (`f`): `FOREIGN KEY (recommendation_id) REFERENCES recommendation.recommendations(recommendation_id) ON DELETE CASCADE`
- **itinerary_stops_pkey** (`p`): `PRIMARY KEY (itinerary_stop_id)`
- **itinerary_stops_itinerary_id_day_number_stop_order_key** (`u`): `UNIQUE (itinerary_id, day_number, stop_order)`

## ایندکس‌ها

- `idx_itinerary_stops_itinerary_day`: `CREATE INDEX idx_itinerary_stops_itinerary_day ON travel.itinerary_stops USING btree (itinerary_id, day_number, stop_order)`
- `itinerary_stops_itinerary_id_day_number_stop_order_key`: `CREATE UNIQUE INDEX itinerary_stops_itinerary_id_day_number_stop_order_key ON travel.itinerary_stops USING btree (itinerary_id, day_number, stop_order)`
- `itinerary_stops_pkey`: `CREATE UNIQUE INDEX itinerary_stops_pkey ON travel.itinerary_stops USING btree (itinerary_stop_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- `trg_enforce_itinerary_stop_bounds`: `CREATE TRIGGER trg_enforce_itinerary_stop_bounds BEFORE INSERT OR UPDATE OF itinerary_id, day_number ON travel.itinerary_stops FOR EACH ROW EXECUTE FUNCTION travel.enforce_itinerary_stop_bounds()`

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **13** از **13**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
