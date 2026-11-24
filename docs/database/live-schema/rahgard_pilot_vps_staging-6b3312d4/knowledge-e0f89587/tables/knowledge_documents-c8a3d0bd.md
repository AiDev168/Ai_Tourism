# knowledge.knowledge_documents

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
| 'document_id' | 'uuid' | خیر | 'gen_random_uuid()' | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'document_key' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'source_id' | 'bigint' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'destination_id' | 'bigint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'title' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'language_code' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'document_type' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'canonical_url' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'raw_content' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'content_sha256' | 'character(64)' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته با طول ثابت مشخص‌شده در PostgreSQL |
| 'ingestion_status' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'record_origin' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'is_synthetic' | 'boolean' | خیر | 'false' | **نیازمند تکمیل از API / منطق دامنه** | true / false |
| 'retrieved_at' | 'timestamp with time zone' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'valid_from' | 'timestamp with time zone' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'valid_until' | 'timestamp with time zone' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **knowledge_documents_check** (`c`): `CHECK ((is_synthetic = (record_origin = 'synthetic_fixture'::text)))`
- **knowledge_documents_check1** (`c`): `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- **knowledge_documents_ingestion_status_check** (`c`): `CHECK ((ingestion_status = ANY (ARRAY['pending'::text, 'processed'::text, 'failed'::text, 'stale'::text, 'test_only'::text])))`
- **knowledge_documents_record_origin_check** (`c`): `CHECK ((record_origin = ANY (ARRAY['user_supplied_unverified'::text, 'verified_external'::text, 'synthetic_fixture'::text])))`
- **knowledge_documents_destination_id_fkey** (`f`): `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE SET NULL`
- **knowledge_documents_source_id_fkey** (`f`): `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- **knowledge_documents_pkey** (`p`): `PRIMARY KEY (document_id)`
- **knowledge_documents_document_key_key** (`u`): `UNIQUE (document_key)`

## ایندکس‌ها

- `idx_knowledge_documents_destination`: `CREATE INDEX idx_knowledge_documents_destination ON knowledge.knowledge_documents USING btree (destination_id)`
- `idx_knowledge_documents_source_status`: `CREATE INDEX idx_knowledge_documents_source_status ON knowledge.knowledge_documents USING btree (source_id, ingestion_status)`
- `knowledge_documents_document_key_key`: `CREATE UNIQUE INDEX knowledge_documents_document_key_key ON knowledge.knowledge_documents USING btree (document_key)`
- `knowledge_documents_pkey`: `CREATE UNIQUE INDEX knowledge_documents_pkey ON knowledge.knowledge_documents USING btree (document_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **18** از **18**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
