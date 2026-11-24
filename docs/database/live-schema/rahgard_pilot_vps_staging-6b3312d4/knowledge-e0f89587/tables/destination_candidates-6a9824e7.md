# knowledge.destination_candidates

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
| 'candidate_id' | 'uuid' | خیر | 'gen_random_uuid()' | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'candidate_kind' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'dataset_import_batch_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'file_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'source_file_sha256' | 'character(64)' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته با طول ثابت مشخص‌شده در PostgreSQL |
| 'source_record_key' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'row_sha256' | 'character(64)' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته با طول ثابت مشخص‌شده در PostgreSQL |
| 'raw_record' | 'jsonb' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'raw_name' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'raw_province' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'raw_city' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'raw_coordinate_role' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'proposed_destination_key' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'proposed_name_fa' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'proposed_destination_type' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'proposed_latitude' | 'double precision' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد ممیز شناور؛ دقت و واحد کاربردی نیازمند قرارداد دامنه است |
| 'proposed_longitude' | 'double precision' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد ممیز شناور؛ دقت و واحد کاربردی نیازمند قرارداد دامنه است |
| 'canonical_destination_id' | 'bigint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'candidate_status' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **destination_candidates_candidate_kind_check** (`c`): `CHECK ((candidate_kind = ANY (ARRAY['destination_identity'::text, 'discovery_lead'::text])))`
- **destination_candidates_candidate_status_check** (`c`): `CHECK ((candidate_status = ANY (ARRAY['needs_review'::text, 'in_review'::text, 'resolved_existing'::text, 'approved_new_identity'::text, 'rejected'::text, 'conflict'::text])))`
- **destination_candidates_check** (`c`): `CHECK (((proposed_latitude IS NULL) = (proposed_longitude IS NULL)))`
- **destination_candidates_proposed_latitude_check** (`c`): `CHECK (((proposed_latitude IS NULL) OR ((proposed_latitude >= ('-90'::integer)::double precision) AND (proposed_latitude <= (90)::double precision))))`
- **destination_candidates_proposed_longitude_check** (`c`): `CHECK (((proposed_longitude IS NULL) OR ((proposed_longitude >= ('-180'::integer)::double precision) AND (proposed_longitude <= (180)::double precision))))`
- **destination_candidates_raw_record_check** (`c`): `CHECK ((jsonb_typeof(raw_record) = 'object'::text))`
- **destination_candidates_row_sha256_check** (`c`): `CHECK ((row_sha256 ~ '^[a-f0-9]{64}$'::text))`
- **destination_candidates_source_file_sha256_check** (`c`): `CHECK ((source_file_sha256 ~ '^[a-f0-9]{64}$'::text))`
- **destination_candidates_source_record_key_check** (`c`): `CHECK (((length(btrim(source_record_key)) >= 1) AND (length(btrim(source_record_key)) <= 512)))`
- **destination_candidates_canonical_destination_id_fkey** (`f`): `FOREIGN KEY (canonical_destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- **destination_candidates_dataset_import_batch_id_fkey** (`f`): `FOREIGN KEY (dataset_import_batch_id) REFERENCES operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT`
- **destination_candidates_file_id_fkey** (`f`): `FOREIGN KEY (file_id) REFERENCES operations.dataset_import_files(file_id) ON DELETE RESTRICT`
- **destination_candidates_pkey** (`p`): `PRIMARY KEY (candidate_id)`
- **destination_candidates_dataset_import_batch_id_source_file__key** (`u`): `UNIQUE (dataset_import_batch_id, source_file_sha256, source_record_key)`

## ایندکس‌ها

- `destination_candidates_dataset_import_batch_id_source_file__key`: `CREATE UNIQUE INDEX destination_candidates_dataset_import_batch_id_source_file__key ON knowledge.destination_candidates USING btree (dataset_import_batch_id, source_file_sha256, source_record_key)`
- `destination_candidates_pkey`: `CREATE UNIQUE INDEX destination_candidates_pkey ON knowledge.destination_candidates USING btree (candidate_id)`
- `ix_destination_candidates_canonical`: `CREATE INDEX ix_destination_candidates_canonical ON knowledge.destination_candidates USING btree (canonical_destination_id) WHERE (canonical_destination_id IS NOT NULL)`
- `ix_destination_candidates_name`: `CREATE INDEX ix_destination_candidates_name ON knowledge.destination_candidates USING btree (proposed_name_fa)`
- `ix_destination_candidates_queue`: `CREATE INDEX ix_destination_candidates_queue ON knowledge.destination_candidates USING btree (candidate_status, created_at, candidate_id)`
- `uq_destination_candidate_source_row`: `CREATE UNIQUE INDEX uq_destination_candidate_source_row ON knowledge.destination_candidates USING btree (source_file_sha256, source_record_key)`

## سیاست‌های RLS

- `candidate_insert_reviewers`: command=a, roles=[], using=`—`, with_check=`identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text)`
- `candidate_select_reviewers`: command=r, roles=[], using=`identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text)`, with_check=`—`
- `candidate_update_reviewers`: command=w, roles=[], using=`identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text)`, with_check=`identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text)`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **21** از **21**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
