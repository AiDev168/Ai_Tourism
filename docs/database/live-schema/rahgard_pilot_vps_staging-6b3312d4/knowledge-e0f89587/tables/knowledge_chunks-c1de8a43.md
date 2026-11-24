# knowledge.knowledge_chunks

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نیازمند توضیح دامنه‌ای تأییدشده از کد و مالک محصول
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T11:28:13Z`
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | معنی کسب‌وکاری | قالب/واحد/enum | منبع شواهد | حساسیت/مالک | سطح خواندن/نوشتن |
|---|---|---|---|---|---|---|---|---|
| 'chunk_id' | 'uuid' | خیر | 'gen_random_uuid()' | Knowledge chunk associated with this record. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'document_id' | 'uuid' | خیر | — | Knowledge document associated with this record. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'chunk_index' | 'integer' | خیر | — | Zero-based or one-based chunk sequence position as defined by the document splitter contract. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((chunk_index >= 0)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'content' | 'text' | خیر | — | Text content of the associated knowledge chunk; use only through publication and provenance safeguards. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'char_count' | 'integer' | خیر | — | Character count stored for the associated chunk/content. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((char_count >= 0)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'token_count' | 'integer' | بله | — | Token count measured by the configured tokenizer; it is not interchangeable with Unicode character count. | PostgreSQL 'integer'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((token_count IS NULL) OR (token_count >= 0))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_direct_identifier / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'content_sha256' | 'character(64)' | خیر | — | SHA-256 digest of the associated content version, used for integrity/version identity. | PostgreSQL 'character(64)'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'metadata' | 'jsonb' | خیر | '[redacted string default]' | Structured auxiliary metadata for the associated event/click; content schema is application-specific. | JSON object/array/scalar; exact shape is validated by the consuming contract. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype-json.html](https://www.postgresql.org/docs/17/datatype-json.html) | private_traveler_or_import_data / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'is_synthetic' | 'boolean' | خیر | 'false' | Synthetic/test fixture marker; these records must be excluded from production views. | PostgreSQL 'boolean'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |

## محدودیت‌ها و ارتباط‌ها

- **knowledge_chunks_char_count_check** (`c`): `CHECK ((char_count >= 0))`
- **knowledge_chunks_chunk_index_check** (`c`): `CHECK ((chunk_index >= 0))`
- **knowledge_chunks_token_count_check** (`c`): `CHECK (((token_count IS NULL) OR (token_count >= 0)))`
- **knowledge_chunks_document_id_fkey** (`f`): `FOREIGN KEY (document_id) REFERENCES knowledge.knowledge_documents(document_id) ON DELETE CASCADE`
- **knowledge_chunks_pkey** (`p`): `PRIMARY KEY (chunk_id)`
- **knowledge_chunks_document_id_chunk_index_key** (`u`): `UNIQUE (document_id, chunk_index)`

## ایندکس‌ها

- `idx_knowledge_chunks_document`: `CREATE INDEX idx_knowledge_chunks_document ON knowledge.knowledge_chunks USING btree (document_id, chunk_index)`
- `knowledge_chunks_document_id_chunk_index_key`: `CREATE UNIQUE INDEX knowledge_chunks_document_id_chunk_index_key ON knowledge.knowledge_chunks USING btree (document_id, chunk_index)`
- `knowledge_chunks_pkey`: `CREATE UNIQUE INDEX knowledge_chunks_pkey ON knowledge.knowledge_chunks USING btree (chunk_id)`
- `uq_knowledge_chunks_chunk_document`: `CREATE UNIQUE INDEX uq_knowledge_chunks_chunk_document ON knowledge.knowledge_chunks USING btree (chunk_id, document_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **10**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
