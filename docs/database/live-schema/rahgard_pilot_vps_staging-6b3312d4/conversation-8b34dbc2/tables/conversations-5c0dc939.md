# conversation.conversations

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** ظرف مکالمه مسافر با دستیار پیرامون سفرهای ثبت‌شده.
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
| 'conversation_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه یکتای مکالمه. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'user_id' | 'uuid' | بله | — | مالک مکالمه و مبنای محدودسازی دسترسی. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'channel' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'language_code' | 'text' | خیر | '[redacted string default]' | زبان مکالمه. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'conversation_status' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'structured_context' | 'jsonb' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'is_synthetic' | 'boolean' | خیر | 'false' | **نیازمند تکمیل از API / منطق دامنه** | true / false |
| 'started_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'last_message_at' | 'timestamp with time zone' | بله | — | زمان آخرین پیام مکالمه. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'ended_at' | 'timestamp with time zone' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'version' | 'integer' | خیر | '1' | شماره نسخه برای کنترل تعارض به‌روزرسانی. | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | زمان آخرین تغییر. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'create_idempotency_key' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |

## محدودیت‌ها و ارتباط‌ها

- **conversations_channel_check** (`c`): `CHECK ((channel = ANY (ARRAY['pwa'::text, 'web'::text, 'mobile_web'::text, 'admin_test'::text])))`
- **conversations_conversation_status_check** (`c`): `CHECK ((conversation_status = ANY (ARRAY['active'::text, 'completed'::text, 'archived'::text, 'deleted'::text])))`
- **conversations_version_check** (`c`): `CHECK ((version > 0))`
- **conversations_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **conversations_pkey** (`p`): `PRIMARY KEY (conversation_id)`

## ایندکس‌ها

- `conversations_pkey`: `CREATE UNIQUE INDEX conversations_pkey ON conversation.conversations USING btree (conversation_id)`
- `idx_conversations_user_started`: `CREATE INDEX idx_conversations_user_started ON conversation.conversations USING btree (user_id, started_at DESC)`
- `uq_conversations_owner_create_key`: `CREATE UNIQUE INDEX uq_conversations_owner_create_key ON conversation.conversations USING btree (user_id, create_idempotency_key) WHERE ((user_id IS NOT NULL) AND (create_idempotency_key IS NOT NULL))`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **7** از **13**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
