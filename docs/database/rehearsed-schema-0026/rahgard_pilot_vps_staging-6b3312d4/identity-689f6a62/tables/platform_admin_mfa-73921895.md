# identity.platform_admin_mfa

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** not identified; static absence does not prove no read/write path (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `not captured` (technical ownership only; not product approval)
- **Architecture disposition:** `not assessed` — see architecture usage audit
- **DDL provenance:** not linked; see architecture usage audit
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'user_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | not separately source-linked | not assessed / PostgreSQL owner 'unknown'; no column-level assessment | qualified backend relation refs: none found by static scan; column write path is not inferred |
| 'secret_ciphertext' | 'bytea' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bytea' only; business units, accepted values, and validation are not inferred from the SQL type. | not separately source-linked | not assessed / PostgreSQL owner 'unknown'; no column-level assessment | qualified backend relation refs: none found by static scan; column write path is not inferred |
| 'pending_secret_ciphertext' | 'bytea' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bytea' only; business units, accepted values, and validation are not inferred from the SQL type. | not separately source-linked | not assessed / PostgreSQL owner 'unknown'; no column-level assessment | qualified backend relation refs: none found by static scan; column write path is not inferred |
| 'enabled_at' | 'timestamp with time zone' | بله | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | not separately source-linked | not assessed / PostgreSQL owner 'unknown'; no column-level assessment | qualified backend relation refs: none found by static scan; column write path is not inferred |
| 'last_totp_counter' | 'bigint' | خیر | '[redacted string default]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bigint' only; business units, accepted values, and validation are not inferred from the SQL type. | not separately source-linked | not assessed / PostgreSQL owner 'unknown'; no column-level assessment | qualified backend relation refs: none found by static scan; column write path is not inferred |
| 'recovery_hashes' | 'bytea[]' | خیر | 'ARRAY[]::bytea[]' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'bytea[]' only; business units, accepted values, and validation are not inferred from the SQL type. | not separately source-linked | not assessed / PostgreSQL owner 'unknown'; no column-level assessment | qualified backend relation refs: none found by static scan; column write path is not inferred |
| 'version' | 'integer' | خیر | '1' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'integer' only; business units, accepted values, and validation are not inferred from the SQL type. | not separately source-linked | not assessed / PostgreSQL owner 'unknown'; no column-level assessment | qualified backend relation refs: none found by static scan; column write path is not inferred |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | not separately source-linked | not assessed / PostgreSQL owner 'unknown'; no column-level assessment | qualified backend relation refs: none found by static scan; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **platform_admin_mfa_check** (`c`): `CHECK (((enabled_at IS NULL) = (secret_ciphertext IS NULL)))`
- **platform_admin_mfa_last_totp_counter_check** (`c`): `CHECK ((last_totp_counter >= '-1'::integer))`
- **platform_admin_mfa_pending_secret_ciphertext_check** (`c`): `CHECK (((pending_secret_ciphertext IS NULL) OR (octet_length(pending_secret_ciphertext) = 49)))`
- **platform_admin_mfa_recovery_hashes_check** (`c`): `CHECK ((cardinality(recovery_hashes) <= 20))`
- **platform_admin_mfa_secret_ciphertext_check** (`c`): `CHECK (((secret_ciphertext IS NULL) OR (octet_length(secret_ciphertext) = 49)))`
- **platform_admin_mfa_version_check** (`c`): `CHECK ((version > 0))`
- **platform_admin_mfa_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **platform_admin_mfa_pkey** (`p`): `PRIMARY KEY (user_id)`

## ایندکس‌ها

- `platform_admin_mfa_pkey`: `CREATE UNIQUE INDEX platform_admin_mfa_pkey ON identity.platform_admin_mfa USING btree (user_id)`

## سیاست‌های RLS

- `platform_admin_mfa_self`: command=*, roles=[], using=`((user_id = partner.current_actor_id()) AND identity.has_platform_admin_capability(user_id))`, with_check=`((user_id = partner.current_actor_id()) AND identity.has_platform_admin_capability(user_id))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **8** of **8**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
