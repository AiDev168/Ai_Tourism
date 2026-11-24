# knowledge.culinary_knowledge_items

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
| 'item_id' | 'uuid' | خیر | 'gen_random_uuid()' | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'item_key' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'record_key' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'dataset_import_batch_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'record_action' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'legacy_destination_id' | 'bigint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'category' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'names_by_locale' | 'jsonb' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'descriptions_by_locale' | 'jsonb' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'claims' | 'jsonb' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'payload' | 'jsonb' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'payload_sha256' | 'character(64)' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته با طول ثابت مشخص‌شده در PostgreSQL |
| 'review_status' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'record_origin' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'verification_status' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'is_synthetic' | 'boolean' | خیر | 'false' | **نیازمند تکمیل از API / منطق دامنه** | true / false |
| 'approval_confidence' | 'numeric(5,4)' | خیر | '0' | **نیازمند تکمیل از API / منطق دامنه** | عدد ده‌دهی؛ precision و scale از PostgreSQL؛ واحد/ارز باید مستند شود |
| 'publishable' | 'boolean' | خیر | 'false' | **نیازمند تکمیل از API / منطق دامنه** | true / false |
| 'published_at' | 'timestamp with time zone' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **culinary_knowledge_items_approval_confidence_check** (`c`): `CHECK (((approval_confidence >= (0)::numeric) AND (approval_confidence <= (1)::numeric)))`
- **culinary_knowledge_items_category_check** (`c`): `CHECK ((category ~ '^[a-z][a-z0-9_]{1,63}$'::text))`
- **culinary_knowledge_items_check** (`c`): `CHECK (((length(btrim(item_key)) > 0) AND (length(btrim(record_key)) > 0)))`
- **culinary_knowledge_items_check1** (`c`): `CHECK ((((record_action = 'stage_existing_record_enrichment_review'::text) AND (legacy_destination_id IS NOT NULL)) OR ((record_action = 'stage_new_non_spatial_candidate_review'::text) AND (legacy_destination_id IS NULL))))`
- **culinary_knowledge_items_check2** (`c`): `CHECK ((((review_status = 'approved'::text) AND (publishable = true) AND (verification_status = 'verified'::text) AND (approval_confidence > (0)::numeric) AND (published_at IS NOT NULL)) OR ((review_status <> 'approved'::text) AND (publishable = false) AND (published_at IS NULL) AND (approval_confidence = (0)::numeric))))`
- **culinary_knowledge_items_claims_check** (`c`): `CHECK (((jsonb_typeof(claims) = 'array'::text) AND (jsonb_array_length(claims) > 0)))`
- **culinary_knowledge_items_descriptions_by_locale_check** (`c`): `CHECK (((jsonb_typeof(descriptions_by_locale) = 'object'::text) AND (descriptions_by_locale ?& ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text]) AND (jsonb_typeof((descriptions_by_locale -> 'fa-IR'::text)) = 'string'::text) AND (jsonb_typeof((descriptions_by_locale -> 'en-US'::text)) = 'string'::text) AND (jsonb_typeof((descriptions_by_locale -> 'ar'::text)) = 'string'::text) AND (length(btrim((descriptions_by_locale ->> 'fa-IR'::text))) > 0) AND (length(btrim((descriptions_by_locale ->> 'en-US'::text))) > 0) AND (length(btrim((descriptions_by_locale ->> 'ar'::text))) > 0)))`
- **culinary_knowledge_items_is_synthetic_check** (`c`): `CHECK ((is_synthetic = false))`
- **culinary_knowledge_items_names_by_locale_check** (`c`): `CHECK (((jsonb_typeof(names_by_locale) = 'object'::text) AND (names_by_locale ?& ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text]) AND (jsonb_typeof((names_by_locale -> 'fa-IR'::text)) = 'string'::text) AND (jsonb_typeof((names_by_locale -> 'en-US'::text)) = 'string'::text) AND (jsonb_typeof((names_by_locale -> 'ar'::text)) = 'string'::text) AND (length(btrim((names_by_locale ->> 'fa-IR'::text))) > 0) AND (length(btrim((names_by_locale ->> 'en-US'::text))) > 0) AND (length(btrim((names_by_locale ->> 'ar'::text))) > 0)))`
- **culinary_knowledge_items_payload_check** (`c`): `CHECK ((jsonb_typeof(payload) = 'object'::text))`
- **culinary_knowledge_items_payload_sha256_check** (`c`): `CHECK ((payload_sha256 ~ '^[0-9a-f]{64}$'::text))`
- **culinary_knowledge_items_record_action_check** (`c`): `CHECK ((record_action = ANY (ARRAY['stage_existing_record_enrichment_review'::text, 'stage_new_non_spatial_candidate_review'::text])))`
- **culinary_knowledge_items_record_origin_check** (`c`): `CHECK ((record_origin = 'verified_external'::text))`
- **culinary_knowledge_items_review_status_check** (`c`): `CHECK ((review_status = ANY (ARRAY['pending_review'::text, 'approved'::text, 'rejected'::text, 'withdrawn'::text])))`
- **culinary_knowledge_items_verification_status_check** (`c`): `CHECK ((verification_status = ANY (ARRAY['pending'::text, 'verified'::text, 'rejected'::text, 'stale'::text])))`
- **culinary_knowledge_items_dataset_import_batch_id_fkey** (`f`): `FOREIGN KEY (dataset_import_batch_id) REFERENCES operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT`
- **culinary_knowledge_items_legacy_destination_id_fkey** (`f`): `FOREIGN KEY (legacy_destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- **culinary_knowledge_items_pkey** (`p`): `PRIMARY KEY (item_id)`
- **culinary_knowledge_items_item_key_key** (`u`): `UNIQUE (item_key)`

## ایندکس‌ها

- `culinary_knowledge_items_item_key_key`: `CREATE UNIQUE INDEX culinary_knowledge_items_item_key_key ON knowledge.culinary_knowledge_items USING btree (item_key)`
- `culinary_knowledge_items_pkey`: `CREATE UNIQUE INDEX culinary_knowledge_items_pkey ON knowledge.culinary_knowledge_items USING btree (item_id)`
- `idx_culinary_knowledge_review`: `CREATE INDEX idx_culinary_knowledge_review ON knowledge.culinary_knowledge_items USING btree (review_status, updated_at DESC)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **21** از **21**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
