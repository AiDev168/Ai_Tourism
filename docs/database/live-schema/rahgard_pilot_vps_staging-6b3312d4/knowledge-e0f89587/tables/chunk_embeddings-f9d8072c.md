# knowledge.chunk_embeddings

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
| 'chunk_embedding_id' | 'uuid' | خیر | 'gen_random_uuid()' | Primary identifier for one stored embedding vector linked to a knowledge chunk and embedding space. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'chunk_id' | 'uuid' | خیر | — | Knowledge chunk associated with this record. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'embedding_space_id' | 'uuid' | خیر | — | Embedding-space configuration used to interpret this vector. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'embedding' | 'vector' | خیر | — | Embedding vector for one knowledge chunk in the linked embedding space; its dimension is validated against that space by the database trigger, and vector values are not source evidence. | pgvector vector value; dimension is stored in the linked embedding-space row and enforced by the database trigger. No fixed dimension is implied by this column type. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://github.com/pgvector/pgvector](https://github.com/pgvector/pgvector) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp at which this row or event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp of the last persisted update to this row. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |

## محدودیت‌ها و ارتباط‌ها

- **chunk_embeddings_chunk_id_fkey** (`f`): `FOREIGN KEY (chunk_id) REFERENCES knowledge.knowledge_chunks(chunk_id) ON DELETE CASCADE`
- **chunk_embeddings_embedding_space_id_fkey** (`f`): `FOREIGN KEY (embedding_space_id) REFERENCES knowledge.embedding_spaces(embedding_space_id) ON DELETE CASCADE`
- **chunk_embeddings_pkey** (`p`): `PRIMARY KEY (chunk_embedding_id)`
- **chunk_embeddings_chunk_id_embedding_space_id_key** (`u`): `UNIQUE (chunk_id, embedding_space_id)`

## ایندکس‌ها

- `chunk_embeddings_chunk_id_embedding_space_id_key`: `CREATE UNIQUE INDEX chunk_embeddings_chunk_id_embedding_space_id_key ON knowledge.chunk_embeddings USING btree (chunk_id, embedding_space_id)`
- `chunk_embeddings_pkey`: `CREATE UNIQUE INDEX chunk_embeddings_pkey ON knowledge.chunk_embeddings USING btree (chunk_embedding_id)`
- `idx_chunk_embeddings_space_chunk`: `CREATE INDEX idx_chunk_embeddings_space_chunk ON knowledge.chunk_embeddings USING btree (embedding_space_id, chunk_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- `trg_enforce_chunk_embedding_dimension`: `CREATE TRIGGER trg_enforce_chunk_embedding_dimension BEFORE INSERT OR UPDATE OF embedding, embedding_space_id ON knowledge.chunk_embeddings FOR EACH ROW EXECUTE FUNCTION knowledge.enforce_chunk_embedding_dimension()`

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **6**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
