# recommendation.recommendation_requests

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** backend/app/modules/trip/repository.py:INSERT@859 | backend/app/modules/trip/repository.py:JOIN@1079 | backend/app/modules/trip/repository.py:JOIN@786 | backend/app/modules/trip/repository.py:JOIN@798 | backend/app/modules/trip/repository.py:SELECT@694 | backend/app/modules/trip/repository.py:SELECT@912 | backend/app/modules/trip/repository.py:SELECT@973 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/database-prep/sql/001_core_schema.sql:446
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'recommendation_request_id' | 'uuid' | خیر | 'gen_random_uuid()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:446 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'trip_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:446 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'conversation_id' | 'uuid' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:446 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'algorithm_version' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:446 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'retrieval_version' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:446 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'input_snapshot' | 'jsonb' | خیر | '[redacted string default]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:446 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'request_status' | 'text' | خیر | '[redacted string default]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:446 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'is_synthetic' | 'boolean' | خیر | 'false' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'boolean' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:446 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:446 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'completed_at' | 'timestamp with time zone' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:446 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **recommendation_requests_request_status_check** (`c`): `CHECK ((request_status = ANY (ARRAY['created'::text, 'processing'::text, 'completed'::text, 'failed'::text, 'cancelled'::text])))`
- **recommendation_requests_conversation_id_fkey** (`f`): `FOREIGN KEY (conversation_id) REFERENCES conversation.conversations(conversation_id) ON DELETE SET NULL`
- **recommendation_requests_trip_id_fkey** (`f`): `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- **recommendation_requests_pkey** (`p`): `PRIMARY KEY (recommendation_request_id)`

## ایندکس‌ها

- `idx_recommendation_requests_trip_created`: `CREATE INDEX idx_recommendation_requests_trip_created ON recommendation.recommendation_requests USING btree (trip_id, created_at DESC)`
- `recommendation_requests_pkey`: `CREATE UNIQUE INDEX recommendation_requests_pkey ON recommendation.recommendation_requests USING btree (recommendation_request_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **10** of **10**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
