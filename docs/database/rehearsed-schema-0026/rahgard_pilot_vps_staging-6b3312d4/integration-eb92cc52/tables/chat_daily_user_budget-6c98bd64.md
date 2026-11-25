# integration.chat_daily_user_budget

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** سقف روزانه مصرف نوبت‌های دستیار برای هر کاربر.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** backend/app/modules/trip/assistant_turns.py:INSERT@95 | backend/app/modules/trip/assistant_turns.py:JOIN@171 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/database-prep/sql/011_internal_chat_turns.sql:13
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'user_id' | 'uuid' | خیر | — | شناسه کاربر مشمول سقف. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:13; existing baseline glossary | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |
| 'budget_day' | 'date' | خیر | — | روز محاسبه سهمیه (در Backend از روز UTC استفاده شده است). | PostgreSQL storage type 'date' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:13; existing baseline glossary | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |
| 'hit_count' | 'integer' | خیر | — | تعداد سهمیه مصرف‌شده در روز. | PostgreSQL storage type 'integer' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:13; existing baseline glossary | restricted_operational_metadata / PostgreSQL owner 'ai_tourism_owner'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **chat_daily_user_budget_hit_count_check** (`c`): `CHECK (((hit_count >= 1) AND (hit_count <= 1000)))`
- **chat_daily_user_budget_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **chat_daily_user_budget_pkey** (`p`): `PRIMARY KEY (user_id, budget_day)`

## ایندکس‌ها

- `chat_daily_user_budget_pkey`: `CREATE UNIQUE INDEX chat_daily_user_budget_pkey ON integration.chat_daily_user_budget USING btree (user_id, budget_day)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **3**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
