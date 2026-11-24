# recommendation.recommendations

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
| 'recommendation_id' | 'uuid' | خیر | 'gen_random_uuid()' | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'recommendation_request_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'destination_id' | 'bigint' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'rank' | 'smallint' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'final_score' | 'numeric(7,6)' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد ده‌دهی؛ precision و scale از PostgreSQL؛ واحد/ارز باید مستند شود |
| 'confidence' | 'numeric(5,4)' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد ده‌دهی؛ precision و scale از PostgreSQL؛ واحد/ارز باید مستند شود |
| 'explanation_fa' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'warnings' | 'jsonb' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'is_synthetic' | 'boolean' | خیر | 'false' | **نیازمند تکمیل از API / منطق دامنه** | true / false |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'evidence' | 'jsonb' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'explanation_by_locale' | 'jsonb' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |

## محدودیت‌ها و ارتباط‌ها

- **recommendations_confidence_check** (`c`): `CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))))`
- **recommendations_evidence_check** (`c`): `CHECK ((jsonb_typeof(evidence) = 'array'::text))`
- **recommendations_explanation_by_locale_check** (`c`): `CHECK ((jsonb_typeof(explanation_by_locale) = 'object'::text))`
- **recommendations_final_score_check** (`c`): `CHECK (((final_score >= (0)::numeric) AND (final_score <= (1)::numeric)))`
- **recommendations_rank_check** (`c`): `CHECK ((rank > 0))`
- **recommendations_destination_id_fkey** (`f`): `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- **recommendations_recommendation_request_id_fkey** (`f`): `FOREIGN KEY (recommendation_request_id) REFERENCES recommendation.recommendation_requests(recommendation_request_id) ON DELETE CASCADE`
- **recommendations_pkey** (`p`): `PRIMARY KEY (recommendation_id)`
- **recommendations_recommendation_request_id_destination_id_key** (`u`): `UNIQUE (recommendation_request_id, destination_id)`
- **recommendations_recommendation_request_id_rank_key** (`u`): `UNIQUE (recommendation_request_id, rank)`

## ایندکس‌ها

- `idx_recommendations_request_rank`: `CREATE INDEX idx_recommendations_request_rank ON recommendation.recommendations USING btree (recommendation_request_id, rank)`
- `recommendations_pkey`: `CREATE UNIQUE INDEX recommendations_pkey ON recommendation.recommendations USING btree (recommendation_id)`
- `recommendations_recommendation_request_id_destination_id_key`: `CREATE UNIQUE INDEX recommendations_recommendation_request_id_destination_id_key ON recommendation.recommendations USING btree (recommendation_request_id, destination_id)`
- `recommendations_recommendation_request_id_rank_key`: `CREATE UNIQUE INDEX recommendations_recommendation_request_id_rank_key ON recommendation.recommendations USING btree (recommendation_request_id, rank)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **12** از **12**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
