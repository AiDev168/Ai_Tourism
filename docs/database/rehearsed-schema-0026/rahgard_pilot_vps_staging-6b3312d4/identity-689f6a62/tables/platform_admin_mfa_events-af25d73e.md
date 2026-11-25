# identity.platform_admin_mfa_events

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
| 'event_id' | 'uuid' | خیر | 'gen_random_uuid()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | not separately source-linked | not assessed / PostgreSQL owner 'unknown'; no column-level assessment | qualified backend relation refs: none found by static scan; column write path is not inferred |
| 'actor_user_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | not separately source-linked | not assessed / PostgreSQL owner 'unknown'; no column-level assessment | qualified backend relation refs: none found by static scan; column write path is not inferred |
| 'session_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | not separately source-linked | not assessed / PostgreSQL owner 'unknown'; no column-level assessment | qualified backend relation refs: none found by static scan; column write path is not inferred |
| 'action' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | not separately source-linked | not assessed / PostgreSQL owner 'unknown'; no column-level assessment | qualified backend relation refs: none found by static scan; column write path is not inferred |
| 'occurred_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | not separately source-linked | not assessed / PostgreSQL owner 'unknown'; no column-level assessment | qualified backend relation refs: none found by static scan; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **platform_admin_mfa_events_action_check** (`c`): `CHECK ((action = ANY (ARRAY['enrollment_started'::text, 'mfa_enrolled'::text, 'totp_step_up'::text, 'recovery_step_up'::text, 'recovery_reset'::text])))`
- **platform_admin_mfa_events_actor_user_id_fkey** (`f`): `FOREIGN KEY (actor_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **platform_admin_mfa_events_pkey** (`p`): `PRIMARY KEY (event_id)`

## ایندکس‌ها

- `ix_platform_admin_mfa_events_actor_time`: `CREATE INDEX ix_platform_admin_mfa_events_actor_time ON identity.platform_admin_mfa_events USING btree (actor_user_id, occurred_at DESC)`
- `platform_admin_mfa_events_pkey`: `CREATE UNIQUE INDEX platform_admin_mfa_events_pkey ON identity.platform_admin_mfa_events USING btree (event_id)`

## سیاست‌های RLS

- `platform_admin_mfa_events_self`: command=r, roles=[], using=`((actor_user_id = partner.current_actor_id()) AND identity.has_platform_admin_capability(actor_user_id))`, with_check=`—`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **5** of **5**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
