# identity.staging_invites

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** backend/app/modules/identity/staging_auth.py:INSERT@70 | backend/app/modules/identity/staging_auth.py:SELECT@149 | backend/app/modules/identity/staging_auth.py:UPDATE@165 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/016_staging_invitation_auth.sql:24
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'invite_id' | 'uuid' | خیر | 'gen_random_uuid()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/016_staging_invitation_auth.sql:24 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'token_digest' | 'bytea' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bytea' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/016_staging_invitation_auth.sql:24 | restricted_auth_or_secret_metadata / PostgreSQL owner 'ai_tourism_owner'; Column name and identity/provider contract; values must never be exposed in documentation.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/016_staging_invitation_auth.sql:24 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'expires_at' | 'timestamp with time zone' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/016_staging_invitation_auth.sql:24 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'consumed_at' | 'timestamp with time zone' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/016_staging_invitation_auth.sql:24 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/staging_auth.py; column write path is not inferred |
| 'consumed_by' | 'uuid' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/016_staging_invitation_auth.sql:24 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/identity/staging_auth.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **staging_invites_check** (`c`): `CHECK (((expires_at > created_at) AND (expires_at <= (created_at + '14 days'::interval))))`
- **staging_invites_check1** (`c`): `CHECK (((consumed_at IS NULL) = (consumed_by IS NULL)))`
- **staging_invites_token_digest_check** (`c`): `CHECK ((octet_length(token_digest) = 32))`
- **staging_invites_consumed_by_fkey** (`f`): `FOREIGN KEY (consumed_by) REFERENCES identity.users(user_id) ON DELETE SET NULL`
- **staging_invites_pkey** (`p`): `PRIMARY KEY (invite_id)`
- **staging_invites_token_digest_key** (`u`): `UNIQUE (token_digest)`

## ایندکس‌ها

- `staging_invites_pkey`: `CREATE UNIQUE INDEX staging_invites_pkey ON identity.staging_invites USING btree (invite_id)`
- `staging_invites_token_digest_key`: `CREATE UNIQUE INDEX staging_invites_token_digest_key ON identity.staging_invites USING btree (token_digest)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **6** of **6**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
