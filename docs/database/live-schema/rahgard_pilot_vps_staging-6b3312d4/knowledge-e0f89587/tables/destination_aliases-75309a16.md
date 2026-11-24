# knowledge.destination_aliases

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** no explicit qualified CRUD clause found; not proof of no read/write path (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `INVESTIGATE` — No qualified backend/frontend relation reference was found; dynamic queries, contracts, or compatibility use may exist. Preserve until confirmed.
- **DDL provenance:** engineering/pilot/sql/018_national_catalogue_ingestion.sql:258
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-24T11:28:13Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'alias_id' | 'uuid' | خیر | 'gen_random_uuid()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:258 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'destination_id' | 'bigint' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bigint' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:258 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'alias' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:258 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'normalized_key' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:258 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'locale' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:258 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'alias_type' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:258 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'source_id' | 'bigint' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bigint' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:258 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'source_url' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:258 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'review_status' | 'text' | خیر | '[redacted string default]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:258 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/018_national_catalogue_ingestion.sql:258 | editorial_private_or_public_after_publication / PostgreSQL owner 'ai_tourism_owner'; Knowledge/catalogue provenance and publication view govern exposure.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **destination_aliases_alias_check** (`c`): `CHECK (((length(btrim(alias)) >= 1) AND (length(btrim(alias)) <= 320)))`
- **destination_aliases_alias_type_check** (`c`): `CHECK ((alias_type = ANY (ARRAY['source_spelling'::text, 'local_name'::text, 'transliteration'::text, 'historical'::text, 'other'::text])))`
- **destination_aliases_check** (`c`): `CHECK (((source_id IS NOT NULL) OR (source_url IS NOT NULL)))`
- **destination_aliases_locale_check** (`c`): `CHECK (((locale IS NULL) OR (locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text, 'und'::text]))))`
- **destination_aliases_normalized_key_check** (`c`): `CHECK (((length(btrim(normalized_key)) >= 1) AND (length(btrim(normalized_key)) <= 400)))`
- **destination_aliases_review_status_check** (`c`): `CHECK ((review_status = ANY (ARRAY['needs_review'::text, 'approved'::text, 'rejected'::text])))`
- **destination_aliases_destination_id_fkey** (`f`): `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE`
- **destination_aliases_source_id_fkey** (`f`): `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- **destination_aliases_pkey** (`p`): `PRIMARY KEY (alias_id)`

## ایندکس‌ها

- `destination_aliases_pkey`: `CREATE UNIQUE INDEX destination_aliases_pkey ON knowledge.destination_aliases USING btree (alias_id)`
- `ix_destination_aliases_lookup`: `CREATE INDEX ix_destination_aliases_lookup ON knowledge.destination_aliases USING btree (normalized_key, locale) WHERE (review_status = 'approved'::text)`
- `uq_destination_alias_identity`: `CREATE UNIQUE INDEX uq_destination_alias_identity ON knowledge.destination_aliases USING btree (destination_id, normalized_key, COALESCE(locale, ''::text))`

## سیاست‌های RLS

- `aliases_select_reviewers`: command=r, roles=[], using=`(identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text) OR identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'catalogue_publish'::text))`, with_check=`—`
- `aliases_write_reviewers`: command=*, roles=[], using=`(identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text) OR identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'catalogue_publish'::text))`, with_check=`(((review_status <> 'approved'::text) AND identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text)) OR identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'catalogue_publish'::text))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **10** of **10**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
