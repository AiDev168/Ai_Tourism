# operations.dataset_import_files

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
| 'file_id' | 'uuid' | خیر | 'gen_random_uuid()' | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'dataset_import_batch_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'relative_path' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'file_sha256' | 'character(64)' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته با طول ثابت مشخص‌شده در PostgreSQL |
| 'byte_size' | 'bigint' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'format' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'schema_signature' | 'character(64)' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته با طول ثابت مشخص‌شده در PostgreSQL |
| 'source_locale' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'source_dataset_key' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'row_count' | 'bigint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'accepted_count' | 'bigint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'rejected_count' | 'bigint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'import_status' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'parsed_at' | 'timestamp with time zone' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **dataset_import_files_accepted_count_check** (`c`): `CHECK (((accepted_count IS NULL) OR (accepted_count >= 0)))`
- **dataset_import_files_byte_size_check** (`c`): `CHECK ((byte_size >= 0))`
- **dataset_import_files_check** (`c`): `CHECK (((accepted_count IS NULL) OR (row_count IS NULL) OR (accepted_count <= row_count)))`
- **dataset_import_files_check1** (`c`): `CHECK (((rejected_count IS NULL) OR (row_count IS NULL) OR (rejected_count <= row_count)))`
- **dataset_import_files_file_sha256_check** (`c`): `CHECK ((file_sha256 ~ '^[a-f0-9]{64}$'::text))`
- **dataset_import_files_format_check** (`c`): `CHECK ((format = ANY (ARRAY['csv'::text, 'json'::text, 'geojson'::text, 'xlsx'::text, 'other'::text])))`
- **dataset_import_files_import_status_check** (`c`): `CHECK ((import_status = ANY (ARRAY['received'::text, 'parsed'::text, 'review_ready'::text, 'failed'::text, 'quarantined'::text, 'conflict'::text])))`
- **dataset_import_files_rejected_count_check** (`c`): `CHECK (((rejected_count IS NULL) OR (rejected_count >= 0)))`
- **dataset_import_files_relative_path_check** (`c`): `CHECK ((((length(btrim(relative_path)) >= 1) AND (length(btrim(relative_path)) <= 1024)) AND (relative_path !~ '(^/\|(^\|/)\.\.(/\|$))'::text)))`
- **dataset_import_files_row_count_check** (`c`): `CHECK (((row_count IS NULL) OR (row_count >= 0)))`
- **dataset_import_files_schema_signature_check** (`c`): `CHECK (((schema_signature IS NULL) OR (schema_signature ~ '^[a-f0-9]{64}$'::text)))`
- **dataset_import_files_source_locale_check** (`c`): `CHECK (((source_locale IS NULL) OR (source_locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text, 'und'::text]))))`
- **dataset_import_files_dataset_import_batch_id_fkey** (`f`): `FOREIGN KEY (dataset_import_batch_id) REFERENCES operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT`
- **dataset_import_files_pkey** (`p`): `PRIMARY KEY (file_id)`
- **dataset_import_files_dataset_import_batch_id_relative_path__key** (`u`): `UNIQUE (dataset_import_batch_id, relative_path, file_sha256)`

## ایندکس‌ها

- `dataset_import_files_dataset_import_batch_id_relative_path__key`: `CREATE UNIQUE INDEX dataset_import_files_dataset_import_batch_id_relative_path__key ON operations.dataset_import_files USING btree (dataset_import_batch_id, relative_path, file_sha256)`
- `dataset_import_files_pkey`: `CREATE UNIQUE INDEX dataset_import_files_pkey ON operations.dataset_import_files USING btree (file_id)`
- `ix_dataset_import_files_batch`: `CREATE INDEX ix_dataset_import_files_batch ON operations.dataset_import_files USING btree (dataset_import_batch_id, created_at)`

## سیاست‌های RLS

- `dataset_files_reviewer`: command=*, roles=[], using=`identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text)`, with_check=`identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text)`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **15** از **15**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
