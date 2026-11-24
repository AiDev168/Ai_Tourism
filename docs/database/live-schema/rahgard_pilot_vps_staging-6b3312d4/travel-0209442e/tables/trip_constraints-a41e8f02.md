# travel.trip_constraints

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
| 'constraint_id' | 'uuid' | خیر | 'gen_random_uuid()' | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'trip_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'constraint_key' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'operator' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'constraint_value' | 'jsonb' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'constraint_strength' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'weight' | 'numeric(5,4)' | خیر | '1.0' | **نیازمند تکمیل از API / منطق دامنه** | عدد ده‌دهی؛ precision و scale از PostgreSQL؛ واحد/ارز باید مستند شود |
| 'confidence' | 'numeric(5,4)' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد ده‌دهی؛ precision و scale از PostgreSQL؛ واحد/ارز باید مستند شود |
| 'source_message_id' | 'uuid' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'is_synthetic' | 'boolean' | خیر | 'false' | **نیازمند تکمیل از API / منطق دامنه** | true / false |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **trip_constraints_confidence_check** (`c`): `CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))))`
- **trip_constraints_constraint_strength_check** (`c`): `CHECK ((constraint_strength = ANY (ARRAY['hard'::text, 'soft'::text])))`
- **trip_constraints_weight_check** (`c`): `CHECK (((weight >= (0)::numeric) AND (weight <= (1)::numeric)))`
- **trip_constraints_source_message_id_fkey** (`f`): `FOREIGN KEY (source_message_id) REFERENCES conversation.messages(message_id) ON DELETE SET NULL`
- **trip_constraints_trip_id_fkey** (`f`): `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- **trip_constraints_pkey** (`p`): `PRIMARY KEY (constraint_id)`
- **trip_constraints_trip_id_constraint_key_key** (`u`): `UNIQUE (trip_id, constraint_key)`

## ایندکس‌ها

- `idx_trip_constraints_trip_strength`: `CREATE INDEX idx_trip_constraints_trip_strength ON travel.trip_constraints USING btree (trip_id, constraint_strength)`
- `trip_constraints_pkey`: `CREATE UNIQUE INDEX trip_constraints_pkey ON travel.trip_constraints USING btree (constraint_id)`
- `trip_constraints_trip_id_constraint_key_key`: `CREATE UNIQUE INDEX trip_constraints_trip_id_constraint_key_key ON travel.trip_constraints USING btree (trip_id, constraint_key)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **11** از **11**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
