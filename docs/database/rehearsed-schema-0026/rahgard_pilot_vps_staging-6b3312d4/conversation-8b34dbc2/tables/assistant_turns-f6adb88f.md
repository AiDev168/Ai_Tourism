# conversation.assistant_turns

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** ثبت شناسه یکتا، وضعیت و چرخه اجرای هر نوبت مدل در مکالمه.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** backend/app/modules/trip/assistant_turns.py:INSERT@146 | backend/app/modules/trip/assistant_turns.py:SELECT@129 | backend/app/modules/trip/assistant_turns.py:SELECT@229 | backend/app/modules/trip/assistant_turns.py:SELECT@268 | backend/app/modules/trip/assistant_turns.py:SELECT@66 | backend/app/modules/trip/assistant_turns.py:UPDATE@244 | backend/app/modules/trip/assistant_turns.py:UPDATE@257 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/database-prep/sql/011_internal_chat_turns.sql:23
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'turn_id' | 'uuid' | خیر | — | شناسه یکتای نوبت دستیار. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:23; existing baseline glossary | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |
| 'user_id' | 'uuid' | خیر | — | مالک مجاز نوبت. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:23; existing baseline glossary | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |
| 'conversation_id' | 'uuid' | خیر | — | مکالمه مربوطه. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:23; existing baseline glossary | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |
| 'trip_id' | 'uuid' | خیر | — | سفر مربوطه. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:23; existing baseline glossary | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |
| 'idempotency_key' | 'text' | خیر | — | کلید جلوگیری از اجرای تکراری یک درخواست. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:23; existing baseline glossary | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |
| 'content_sha256' | 'bytea' | خیر | — | هش متن درخواست؛ مقدار واقعی نباید در سند منتشر شود. | PostgreSQL storage type 'bytea' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:23; existing baseline glossary | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |
| 'status' | 'text' | خیر | — | وضعیت چرخه اجرا مثل reserved/completed/failed. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:23; existing baseline glossary | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |
| 'user_message_id' | 'uuid' | خیر | — | ارجاع به پیام درخواست کاربر. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:23; existing baseline glossary | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |
| 'assistant_message_id' | 'uuid' | بله | — | ارجاع به پیام خروجی دستیار پس از تکمیل. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:23; existing baseline glossary | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |
| 'consented_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:23 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:23 | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | زمان آخرین تغییر وضعیت. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/database-prep/sql/011_internal_chat_turns.sql:23; existing baseline glossary | traveler_private / PostgreSQL owner 'ai_tourism_owner'; Owning domain contains identity, trip, conversation, or personalized recommendation state.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/modules/trip/assistant_turns.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **assistant_turns_check** (`c`): `CHECK (((status = 'completed'::text) = (assistant_message_id IS NOT NULL)))`
- **assistant_turns_content_sha256_check** (`c`): `CHECK ((octet_length(content_sha256) = 32))`
- **assistant_turns_idempotency_key_check** (`c`): `CHECK (((length(idempotency_key) >= 8) AND (length(idempotency_key) <= 128)))`
- **assistant_turns_status_check** (`c`): `CHECK ((status = ANY (ARRAY['reserved'::text, 'completed'::text, 'failed'::text])))`
- **assistant_turns_assistant_message_id_fkey** (`f`): `FOREIGN KEY (assistant_message_id) REFERENCES conversation.messages(message_id) ON DELETE CASCADE`
- **assistant_turns_conversation_id_fkey** (`f`): `FOREIGN KEY (conversation_id) REFERENCES conversation.conversations(conversation_id) ON DELETE CASCADE`
- **assistant_turns_trip_id_fkey** (`f`): `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- **assistant_turns_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **assistant_turns_user_message_id_fkey** (`f`): `FOREIGN KEY (user_message_id) REFERENCES conversation.messages(message_id) ON DELETE CASCADE`
- **assistant_turns_pkey** (`p`): `PRIMARY KEY (turn_id)`
- **assistant_turns_conversation_id_idempotency_key_key** (`u`): `UNIQUE (conversation_id, idempotency_key)`

## ایندکس‌ها

- `assistant_turns_conversation_id_idempotency_key_key`: `CREATE UNIQUE INDEX assistant_turns_conversation_id_idempotency_key_key ON conversation.assistant_turns USING btree (conversation_id, idempotency_key)`
- `assistant_turns_pkey`: `CREATE UNIQUE INDEX assistant_turns_pkey ON conversation.assistant_turns USING btree (turn_id)`
- `idx_assistant_turns_owner_trip`: `CREATE INDEX idx_assistant_turns_owner_trip ON conversation.assistant_turns USING btree (user_id, trip_id, created_at DESC)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **2** of **12**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
