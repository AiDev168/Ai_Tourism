# travel.itinerary_stops

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** backend/app/modules/trip/repository.py:DELETE@1088 | backend/app/modules/trip/repository.py:INSERT@1021 | backend/app/modules/trip/repository.py:SELECT@1046 | backend/app/modules/trip/repository.py:SELECT@1088 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/database-prep/sql/001_core_schema.sql:516
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'itinerary_stop_id' | 'uuid' | خیر | 'gen_random_uuid()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:516 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'itinerary_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:516 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'destination_id' | 'bigint' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bigint' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:516 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'day_number' | 'smallint' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'smallint' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:516 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'stop_order' | 'smallint' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'smallint' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:516 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'planned_start_time' | 'time without time zone' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'time without time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:516 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'duration_minutes' | 'smallint' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'smallint' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:516 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'travel_to_next_estimate_minutes' | 'smallint' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'smallint' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:516 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'notes_fa' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:516 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'is_synthetic' | 'boolean' | خیر | 'false' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'boolean' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:516 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:516 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'notes_by_locale' | 'jsonb' | خیر | '[redacted string default]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:516 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |
| 'recommendation_id' | 'uuid' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/001_core_schema.sql:516 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/repository.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **itinerary_stops_day_number_365_check** (`c`): `CHECK (((day_number >= 1) AND (day_number <= 365)))`
- **itinerary_stops_duration_minutes_check** (`c`): `CHECK (((duration_minutes IS NULL) OR ((duration_minutes >= 1) AND (duration_minutes <= 1440))))`
- **itinerary_stops_notes_by_locale_check** (`c`): `CHECK ((jsonb_typeof(notes_by_locale) = 'object'::text))`
- **itinerary_stops_stop_order_50_check** (`c`): `CHECK (((stop_order >= 1) AND (stop_order <= 50)))`
- **itinerary_stops_travel_to_next_estimate_minutes_check** (`c`): `CHECK (((travel_to_next_estimate_minutes IS NULL) OR (travel_to_next_estimate_minutes >= 0)))`
- **itinerary_stops_destination_id_fkey** (`f`): `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- **itinerary_stops_itinerary_id_fkey** (`f`): `FOREIGN KEY (itinerary_id) REFERENCES travel.itineraries(itinerary_id) ON DELETE CASCADE`
- **itinerary_stops_recommendation_id_fkey** (`f`): `FOREIGN KEY (recommendation_id) REFERENCES recommendation.recommendations(recommendation_id) ON DELETE CASCADE`
- **itinerary_stops_pkey** (`p`): `PRIMARY KEY (itinerary_stop_id)`
- **itinerary_stops_itinerary_id_day_number_stop_order_key** (`u`): `UNIQUE (itinerary_id, day_number, stop_order)`

## ایندکس‌ها

- `idx_itinerary_stops_itinerary_day`: `CREATE INDEX idx_itinerary_stops_itinerary_day ON travel.itinerary_stops USING btree (itinerary_id, day_number, stop_order)`
- `itinerary_stops_itinerary_id_day_number_stop_order_key`: `CREATE UNIQUE INDEX itinerary_stops_itinerary_id_day_number_stop_order_key ON travel.itinerary_stops USING btree (itinerary_id, day_number, stop_order)`
- `itinerary_stops_pkey`: `CREATE UNIQUE INDEX itinerary_stops_pkey ON travel.itinerary_stops USING btree (itinerary_stop_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- `trg_enforce_itinerary_stop_bounds`: `CREATE TRIGGER trg_enforce_itinerary_stop_bounds BEFORE INSERT OR UPDATE OF itinerary_id, day_number ON travel.itinerary_stops FOR EACH ROW EXECUTE FUNCTION travel.enforce_itinerary_stop_bounds()`

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **13** of **13**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
