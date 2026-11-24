# knowledge.catalogue_publication_events

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
| 'publication_id' | 'uuid' | خیر | 'gen_random_uuid()' | Identity of the destination publication event. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/020_archive_candidate_publication.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'candidate_id' | 'uuid' | خیر | — | Imported destination-candidate row associated with this review/evidence. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/020_archive_candidate_publication.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'destination_id' | 'bigint' | خیر | — | Canonical destination identity associated with this row. | PostgreSQL 'bigint'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/020_archive_candidate_publication.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'evidence_ids' | 'jsonb' | خیر | — | Identifiers of the reviewed evidence claims supporting publication. | JSON object/array/scalar; exact shape is validated by the consuming contract. DB CHECK: CHECK (((jsonb_typeof(evidence_ids) = 'array'::text) AND (jsonb_array_length(evidence_ids) >= 4))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/020_archive_candidate_publication.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype-json.html](https://www.postgresql.org/docs/17/datatype-json.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'reviewer_user_id' | 'uuid' | خیر | — | Identifier of the authenticated reviewer who made the decision. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/020_archive_candidate_publication.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'policy_version' | 'text' | خیر | — | Consent or review policy identifier acknowledged at the time. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((length(btrim(policy_version)) >= 1) AND (length(btrim(policy_version)) <= 80))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/020_archive_candidate_publication.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |
| 'published_at' | 'timestamp with time zone' | خیر | 'now()' | Publication time reported for the administrative dataset or content. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/020_archive_candidate_publication.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: operator review API or controlled published projection; نوشتن: authorized catalogue/import/review service; candidate data is not public |

## محدودیت‌ها و ارتباط‌ها

- **catalogue_publication_events_evidence_ids_check** (`c`): `CHECK (((jsonb_typeof(evidence_ids) = 'array'::text) AND (jsonb_array_length(evidence_ids) >= 4)))`
- **catalogue_publication_events_policy_version_check** (`c`): `CHECK (((length(btrim(policy_version)) >= 1) AND (length(btrim(policy_version)) <= 80)))`
- **catalogue_publication_events_candidate_id_fkey** (`f`): `FOREIGN KEY (candidate_id) REFERENCES knowledge.destination_candidates(candidate_id) ON DELETE RESTRICT`
- **catalogue_publication_events_destination_id_fkey** (`f`): `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- **catalogue_publication_events_reviewer_user_id_fkey** (`f`): `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **catalogue_publication_events_pkey** (`p`): `PRIMARY KEY (publication_id)`
- **catalogue_publication_events_candidate_id_key** (`u`): `UNIQUE (candidate_id)`
- **catalogue_publication_events_destination_id_key** (`u`): `UNIQUE (destination_id)`

## ایندکس‌ها

- `catalogue_publication_events_candidate_id_key`: `CREATE UNIQUE INDEX catalogue_publication_events_candidate_id_key ON knowledge.catalogue_publication_events USING btree (candidate_id)`
- `catalogue_publication_events_destination_id_key`: `CREATE UNIQUE INDEX catalogue_publication_events_destination_id_key ON knowledge.catalogue_publication_events USING btree (destination_id)`
- `catalogue_publication_events_pkey`: `CREATE UNIQUE INDEX catalogue_publication_events_pkey ON knowledge.catalogue_publication_events USING btree (publication_id)`

## سیاست‌های RLS

- `publication_insert`: command=a, roles=[], using=`—`, with_check=`((reviewer_user_id = identity.current_app_actor_id()) AND identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'catalogue_publish'::text))`
- `publication_reviewers`: command=r, roles=[], using=`identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'catalogue_publish'::text)`, with_check=`—`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **7**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
