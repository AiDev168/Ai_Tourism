# travel.provisional_itineraries

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** backend/app/modules/trip/provisional_itinerary.py:INSERT@122 | backend/app/modules/trip/provisional_itinerary.py:SELECT@132 | backend/app/modules/trip/provisional_itinerary.py:SELECT@164 | backend/app/modules/trip/provisional_itinerary.py:SELECT@89 | backend/app/modules/trip/provisional_itinerary.py:UPDATE@176 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/017_provisional_itineraries.sql:27
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'provisional_itinerary_id' | 'uuid' | خیر | 'gen_random_uuid()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/017_provisional_itineraries.sql:27 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/provisional_itinerary.py; column write path is not inferred |
| 'trip_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/017_provisional_itineraries.sql:27 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/provisional_itinerary.py; column write path is not inferred |
| 'user_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/017_provisional_itineraries.sql:27 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/provisional_itinerary.py; column write path is not inferred |
| 'revision' | 'integer' | خیر | '1' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'integer' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/017_provisional_itineraries.sql:27 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/provisional_itinerary.py; column write path is not inferred |
| 'day_count' | 'integer' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'integer' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/017_provisional_itineraries.sql:27 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/provisional_itinerary.py; column write path is not inferred |
| 'locale' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/017_provisional_itineraries.sql:27 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/provisional_itinerary.py; column write path is not inferred |
| 'title_by_locale' | 'jsonb' | خیر | '[redacted string default]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/017_provisional_itineraries.sql:27 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/provisional_itinerary.py; column write path is not inferred |
| 'days' | 'jsonb' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/017_provisional_itineraries.sql:27 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/provisional_itinerary.py; column write path is not inferred |
| 'status' | 'text' | خیر | '[redacted string default]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/017_provisional_itineraries.sql:27 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/provisional_itinerary.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/017_provisional_itineraries.sql:27 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/provisional_itinerary.py; column write path is not inferred |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/017_provisional_itineraries.sql:27 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/provisional_itinerary.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **provisional_itineraries_day_count_check** (`c`): `CHECK (((day_count >= 1) AND (day_count <= 365)))`
- **provisional_itineraries_days_check** (`c`): `CHECK ((jsonb_typeof(days) = 'array'::text))`
- **provisional_itineraries_locale_check** (`c`): `CHECK ((locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text])))`
- **provisional_itineraries_revision_check** (`c`): `CHECK ((revision > 0))`
- **provisional_itineraries_status_check** (`c`): `CHECK ((status = 'provisional_unverified'::text))`
- **provisional_itineraries_title_by_locale_check** (`c`): `CHECK ((jsonb_typeof(title_by_locale) = 'object'::text))`
- **provisional_itineraries_trip_id_user_id_fkey** (`f`): `FOREIGN KEY (trip_id, user_id) REFERENCES travel.trips(trip_id, user_id) ON DELETE CASCADE`
- **provisional_itineraries_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **provisional_itineraries_pkey** (`p`): `PRIMARY KEY (provisional_itinerary_id)`
- **provisional_itineraries_trip_id_key** (`u`): `UNIQUE (trip_id)`

## ایندکس‌ها

- `ix_provisional_itineraries_owner_updated`: `CREATE INDEX ix_provisional_itineraries_owner_updated ON travel.provisional_itineraries USING btree (user_id, updated_at DESC)`
- `provisional_itineraries_pkey`: `CREATE UNIQUE INDEX provisional_itineraries_pkey ON travel.provisional_itineraries USING btree (provisional_itinerary_id)`
- `provisional_itineraries_trip_id_key`: `CREATE UNIQUE INDEX provisional_itineraries_trip_id_key ON travel.provisional_itineraries USING btree (trip_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- `trg_trip_request_revision_provisional`: `CREATE TRIGGER trg_trip_request_revision_provisional AFTER INSERT OR DELETE OR UPDATE ON travel.provisional_itineraries FOR EACH ROW EXECUTE FUNCTION partner.capture_trip_request_revision_from_provisional()`

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **11** of **11**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
