# identity.verified_phones

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** backend/app/modules/identity/auth_repository.py:INSERT@226 | backend/app/modules/identity/auth_repository.py:JOIN@377 | backend/app/modules/identity/auth_repository.py:JOIN@396 | backend/app/modules/identity/auth_repository.py:JOIN@415 | backend/app/modules/identity/auth_repository.py:JOIN@430 | backend/app/modules/identity/auth_repository.py:SELECT@210 | backend/app/modules/identity/auth_repository.py:SELECT@235 | backend/app/modules/trip/repository.py:SELECT@775 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/database-prep/sql/008_authentication_foundation.sql:29
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-24T11:28:13Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'phone_e164' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:29 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/trip/repository.py; column write path is not inferred |
| 'user_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:29 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/trip/repository.py; column write path is not inferred |
| 'verified_at' | 'timestamp with time zone' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:29 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/trip/repository.py; column write path is not inferred |
| 'challenge_id' | 'uuid' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:29 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/trip/repository.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **verified_phones_phone_e164_check** (`c`): `CHECK ((phone_e164 ~ '^\+989[0-9]{9}$'::text))`
- **verified_phones_challenge_id_fkey** (`f`): `FOREIGN KEY (challenge_id) REFERENCES identity.otp_challenges(challenge_id) ON DELETE SET NULL`
- **verified_phones_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **verified_phones_pkey** (`p`): `PRIMARY KEY (phone_e164)`
- **verified_phones_challenge_id_key** (`u`): `UNIQUE (challenge_id)`
- **verified_phones_user_id_key** (`u`): `UNIQUE (user_id)`

## ایندکس‌ها

- `verified_phones_challenge_id_key`: `CREATE UNIQUE INDEX verified_phones_challenge_id_key ON identity.verified_phones USING btree (challenge_id)`
- `verified_phones_pkey`: `CREATE UNIQUE INDEX verified_phones_pkey ON identity.verified_phones USING btree (phone_e164)`
- `verified_phones_user_id_key`: `CREATE UNIQUE INDEX verified_phones_user_id_key ON identity.verified_phones USING btree (user_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **4** of **4**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
