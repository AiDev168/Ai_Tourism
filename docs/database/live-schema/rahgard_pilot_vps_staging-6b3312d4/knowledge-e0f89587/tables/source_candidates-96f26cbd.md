# knowledge.source_candidates

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
| 'source_candidate_id' | 'uuid' | خیر | 'gen_random_uuid()' | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'dataset_import_batch_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'file_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'source_file_sha256' | 'character(64)' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته با طول ثابت مشخص‌شده در PostgreSQL |
| 'source_record_key' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'row_sha256' | 'character(64)' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته با طول ثابت مشخص‌شده در PostgreSQL |
| 'raw_record' | 'jsonb' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'proposed_source_key' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'proposed_source_name' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'proposed_publisher' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'proposed_source_type' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'proposed_url' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'proposed_license' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'candidate_status' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'registered_source_id' | 'bigint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **source_candidates_candidate_status_check** (`c`): `CHECK ((candidate_status = ANY (ARRAY['needs_review'::text, 'registered_pending'::text, 'rejected'::text, 'conflict'::text])))`
- **source_candidates_check** (`c`): `CHECK (((candidate_status = 'registered_pending'::text) = (registered_source_id IS NOT NULL)))`
- **source_candidates_raw_record_check** (`c`): `CHECK ((jsonb_typeof(raw_record) = 'object'::text))`
- **source_candidates_row_sha256_check** (`c`): `CHECK ((row_sha256 ~ '^[a-f0-9]{64}$'::text))`
- **source_candidates_source_file_sha256_check** (`c`): `CHECK ((source_file_sha256 ~ '^[a-f0-9]{64}$'::text))`
- **source_candidates_source_record_key_check** (`c`): `CHECK (((length(btrim(source_record_key)) >= 1) AND (length(btrim(source_record_key)) <= 512)))`
- **source_candidates_dataset_import_batch_id_fkey** (`f`): `FOREIGN KEY (dataset_import_batch_id) REFERENCES operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT`
- **source_candidates_file_id_fkey** (`f`): `FOREIGN KEY (file_id) REFERENCES operations.dataset_import_files(file_id) ON DELETE RESTRICT`
- **source_candidates_registered_source_id_fkey** (`f`): `FOREIGN KEY (registered_source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- **source_candidates_pkey** (`p`): `PRIMARY KEY (source_candidate_id)`
- **source_candidates_dataset_import_batch_id_source_file_sha25_key** (`u`): `UNIQUE (dataset_import_batch_id, source_file_sha256, source_record_key)`

## ایندکس‌ها

- `ix_source_candidates_queue`: `CREATE INDEX ix_source_candidates_queue ON knowledge.source_candidates USING btree (candidate_status, created_at, source_candidate_id)`
- `source_candidates_dataset_import_batch_id_source_file_sha25_key`: `CREATE UNIQUE INDEX source_candidates_dataset_import_batch_id_source_file_sha25_key ON knowledge.source_candidates USING btree (dataset_import_batch_id, source_file_sha256, source_record_key)`
- `source_candidates_pkey`: `CREATE UNIQUE INDEX source_candidates_pkey ON knowledge.source_candidates USING btree (source_candidate_id)`
- `uq_source_candidate_file_identity`: `CREATE UNIQUE INDEX uq_source_candidate_file_identity ON knowledge.source_candidates USING btree (source_file_sha256, source_record_key)`

## سیاست‌های RLS

- `source_candidates_reviewer`: command=*, roles=[], using=`(identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'source_review'::text) OR identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text))`, with_check=`(identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'source_review'::text) OR identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **17** از **17**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
