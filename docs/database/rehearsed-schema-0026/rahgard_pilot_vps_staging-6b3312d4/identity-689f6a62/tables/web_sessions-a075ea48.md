# identity.web_sessions

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** backend/app/modules/identity/auth_repository.py:INSERT@255 | backend/app/modules/identity/auth_repository.py:INSERT@360 | backend/app/modules/identity/auth_repository.py:SELECT@375 | backend/app/modules/identity/auth_repository.py:SELECT@394 | backend/app/modules/identity/auth_repository.py:SELECT@413 | backend/app/modules/identity/auth_repository.py:SELECT@428 | backend/app/modules/identity/auth_repository.py:SELECT@459 | backend/app/modules/identity/auth_repository.py:UPDATE@441 | backend/app/modules/identity/auth_repository.py:UPDATE@452 | backend/app/modules/identity/auth_repository.py:UPDATE@467 | backend/app/modules/identity/staging_auth.py:INSERT@136 | backend/app/modules/identity/staging_auth.py:INSERT@168 | backend/app/modules/identity/staging_auth.py:INSERT@96 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/database-prep/sql/008_authentication_foundation.sql:36
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'session_id' | 'uuid' | خیر | 'gen_random_uuid()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:36 | restricted_auth_or_secret_metadata / PostgreSQL owner 'ai_tourism_owner'; Column name and identity/provider contract; values must never be exposed in documentation.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'token_hash' | 'bytea' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bytea' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:36 | restricted_auth_or_secret_metadata / PostgreSQL owner 'ai_tourism_owner'; Column name and identity/provider contract; values must never be exposed in documentation.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'user_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:36 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'csrf_hash' | 'bytea' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bytea' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:36 | restricted_auth_or_secret_metadata / PostgreSQL owner 'ai_tourism_owner'; Column name and identity/provider contract; values must never be exposed in documentation.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:36 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'last_seen_at' | 'timestamp with time zone' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:36 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'idle_expires_at' | 'timestamp with time zone' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:36 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'absolute_expires_at' | 'timestamp with time zone' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:36 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'revoked_at' | 'timestamp with time zone' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:36 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'revoked_reason' | 'text' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/008_authentication_foundation.sql:36 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/auth_repository.py \| backend/app/modules/identity/staging_auth.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **web_sessions_check** (`c`): `CHECK ((idle_expires_at <= absolute_expires_at))`
- **web_sessions_check1** (`c`): `CHECK ((absolute_expires_at > created_at))`
- **web_sessions_csrf_hash_check** (`c`): `CHECK ((octet_length(csrf_hash) = 32))`
- **web_sessions_token_hash_check** (`c`): `CHECK ((octet_length(token_hash) = 32))`
- **web_sessions_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **web_sessions_pkey** (`p`): `PRIMARY KEY (session_id)`
- **web_sessions_token_hash_key** (`u`): `UNIQUE (token_hash)`

## ایندکس‌ها

- `idx_web_sessions_user_active`: `CREATE INDEX idx_web_sessions_user_active ON identity.web_sessions USING btree (user_id, absolute_expires_at) WHERE (revoked_at IS NULL)`
- `web_sessions_pkey`: `CREATE UNIQUE INDEX web_sessions_pkey ON identity.web_sessions USING btree (session_id)`
- `web_sessions_token_hash_key`: `CREATE UNIQUE INDEX web_sessions_token_hash_key ON identity.web_sessions USING btree (token_hash)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **10** of **10**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
