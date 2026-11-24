# knowledge.source_candidate_reviews

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نیازمند توضیح دامنه‌ای تأییدشده از کد و مالک محصول
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T11:28:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | معنی کسب‌وکاری | قالب/واحد/enum | منبع شواهد | حساسیت/مالک | سطح خواندن/نوشتن |
|---|---|---|---|---|---|---|---|---|
| 'source_review_id' | 'uuid' | خیر | 'gen_random_uuid()' | Identifier of the source-candidate review decision. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'source_candidate_id' | 'uuid' | خیر | — | Imported source-candidate row associated with this review. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'decision' | 'text' | خیر | — | Decision for the linked review; the exact enum values are shown in the constraints/API contract. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((decision = 'register_pending'::text) = (source_id IS NOT NULL))) \| CHECK ((decision = ANY (ARRAY['register_pending'::text, 'reject'::text, 'defer'::text, 'request_evidence'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'source_id' | 'bigint' | بله | — | Registered knowledge/source record associated with this evidence or destination. | PostgreSQL 'bigint'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((decision = 'register_pending'::text) = (source_id IS NOT NULL))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'reason' | 'text' | خیر | — | Reviewer explanation for accepting, rejecting, or returning the associated record. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((length(btrim(reason)) >= 1) AND (length(btrim(reason)) <= 2000))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'evidence_refs' | 'jsonb' | خیر | '[redacted string default]' | Evidence reference list submitted for independent verification. | JSON object/array/scalar; exact shape is validated by the consuming contract. DB CHECK: CHECK ((jsonb_typeof(evidence_refs) = 'array'::text)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype-json.html](https://www.postgresql.org/docs/17/datatype-json.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'reviewer_user_id' | 'uuid' | خیر | — | Identifier of the authenticated reviewer who made the decision. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'policy_version' | 'text' | خیر | — | Consent or review policy identifier acknowledged at the time. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((length(btrim(policy_version)) >= 1) AND (length(btrim(policy_version)) <= 80))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'decided_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp when the review decision was made. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/018_national_catalogue_ingestion.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |

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

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **9**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
