# conversation.assistant_turns

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** ثبت شناسه یکتا، وضعیت و چرخه اجرای هر نوبت مدل در مکالمه.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'turn_id' | 'uuid' | خیر | — | شناسه یکتای نوبت دستیار. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'user_id' | 'uuid' | خیر | — | مالک مجاز نوبت. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'conversation_id' | 'uuid' | خیر | — | مکالمه مربوطه. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'trip_id' | 'uuid' | خیر | — | سفر مربوطه. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'idempotency_key' | 'text' | خیر | — | کلید جلوگیری از اجرای تکراری یک درخواست. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'content_sha256' | 'bytea' | خیر | — | هش متن درخواست؛ مقدار واقعی نباید در سند منتشر شود. | دادهٔ دودویی؛ مقدار خام نباید در این مستندات نمایش داده شود |
| 'status' | 'text' | خیر | — | وضعیت چرخه اجرا مثل reserved/completed/failed. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'user_message_id' | 'uuid' | خیر | — | ارجاع به پیام درخواست کاربر. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'assistant_message_id' | 'uuid' | بله | — | ارجاع به پیام خروجی دستیار پس از تکمیل. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'consented_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | زمان آخرین تغییر وضعیت. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

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

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **2** از **12**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
