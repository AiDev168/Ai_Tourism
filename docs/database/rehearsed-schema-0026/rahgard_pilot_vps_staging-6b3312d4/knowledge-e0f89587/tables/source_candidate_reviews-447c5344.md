# knowledge.source_candidate_reviews

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** backend/app/api/catalogue_review.py:INSERT@431 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/018_national_catalogue_ingestion.sql:173
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'source_review_id' | 'uuid' | خیر | 'gen_random_uuid()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:173 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py; column write path is not inferred |
| 'source_candidate_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:173 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py; column write path is not inferred |
| 'decision' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:173 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py; column write path is not inferred |
| 'source_id' | 'bigint' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bigint' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:173 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py; column write path is not inferred |
| 'reason' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:173 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py; column write path is not inferred |
| 'evidence_refs' | 'jsonb' | خیر | '[redacted string default]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:173 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py; column write path is not inferred |
| 'reviewer_user_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:173 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py; column write path is not inferred |
| 'policy_version' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:173 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py; column write path is not inferred |
| 'decided_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:173 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/catalogue_review.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **source_candidate_reviews_check** (`c`): `CHECK (((decision = 'register_pending'::text) = (source_id IS NOT NULL)))`
- **source_candidate_reviews_decision_check** (`c`): `CHECK ((decision = ANY (ARRAY['register_pending'::text, 'reject'::text, 'defer'::text, 'request_evidence'::text])))`
- **source_candidate_reviews_evidence_refs_check** (`c`): `CHECK ((jsonb_typeof(evidence_refs) = 'array'::text))`
- **source_candidate_reviews_policy_version_check** (`c`): `CHECK (((length(btrim(policy_version)) >= 1) AND (length(btrim(policy_version)) <= 80)))`
- **source_candidate_reviews_reason_check** (`c`): `CHECK (((length(btrim(reason)) >= 1) AND (length(btrim(reason)) <= 2000)))`
- **source_candidate_reviews_reviewer_user_id_fkey** (`f`): `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **source_candidate_reviews_source_candidate_id_fkey** (`f`): `FOREIGN KEY (source_candidate_id) REFERENCES knowledge.source_candidates(source_candidate_id) ON DELETE RESTRICT`
- **source_candidate_reviews_source_id_fkey** (`f`): `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- **source_candidate_reviews_pkey** (`p`): `PRIMARY KEY (source_review_id)`

## ایندکس‌ها

- `ix_source_candidate_reviews_candidate_time`: `CREATE INDEX ix_source_candidate_reviews_candidate_time ON knowledge.source_candidate_reviews USING btree (source_candidate_id, decided_at DESC)`
- `source_candidate_reviews_pkey`: `CREATE UNIQUE INDEX source_candidate_reviews_pkey ON knowledge.source_candidate_reviews USING btree (source_review_id)`

## سیاست‌های RLS

- `source_reviews_insert`: command=a, roles=[], using=`—`, with_check=`((reviewer_user_id = identity.current_app_actor_id()) AND identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'source_review'::text))`
- `source_reviews_select`: command=r, roles=[], using=`identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'source_review'::text)`, with_check=`—`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **9** of **9**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
