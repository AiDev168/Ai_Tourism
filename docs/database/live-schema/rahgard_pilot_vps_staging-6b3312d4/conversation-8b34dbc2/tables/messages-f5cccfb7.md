# conversation.messages

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** پیام‌های کاربر، دستیار یا سیستم در یک مکالمه.
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
| 'message_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه یکتای پیام. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'conversation_id' | 'uuid' | خیر | — | شناسه مکالمه. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'role' | 'text' | خیر | — | نقش فرستنده: user/assistant/system/tool مطابق API. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'content' | 'text' | خیر | — | متن پیام که ممکن است داده خصوصی سفر باشد؛ مستندساز فقط متادیتا می‌خواند. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'message_type' | 'text' | خیر | '[redacted string default]' | نوع پیام. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'provider_name' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'model_name' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'input_tokens' | 'integer' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'output_tokens' | 'integer' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'latency_ms' | 'integer' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'metadata' | 'jsonb' | خیر | '[redacted string default]' | فراداده ساخت‌یافته پیام؛ قرارداد requirements_candidate و clarification و provisional_itinerary در کد Chat. | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'idempotency_key' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'is_synthetic' | 'boolean' | خیر | 'false' | تمایز رکورد آزمایشی از واقعی. | true / false |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | زمان ایجاد پیام. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'trip_id' | 'uuid' | بله | — | شناسه سفر مرتبط، در صورت تعیین. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |

## محدودیت‌ها و ارتباط‌ها

- **messages_input_tokens_check** (`c`): `CHECK (((input_tokens IS NULL) OR (input_tokens >= 0)))`
- **messages_latency_ms_check** (`c`): `CHECK (((latency_ms IS NULL) OR (latency_ms >= 0)))`
- **messages_message_type_check** (`c`): `CHECK ((message_type = ANY (ARRAY['text'::text, 'structured'::text, 'tool_call'::text, 'tool_result'::text, 'system_notice'::text])))`
- **messages_output_tokens_check** (`c`): `CHECK (((output_tokens IS NULL) OR (output_tokens >= 0)))`
- **messages_role_check** (`c`): `CHECK ((role = ANY (ARRAY['system'::text, 'user'::text, 'assistant'::text, 'tool'::text])))`
- **messages_conversation_id_fkey** (`f`): `FOREIGN KEY (conversation_id) REFERENCES conversation.conversations(conversation_id) ON DELETE CASCADE`
- **messages_trip_id_fkey** (`f`): `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- **messages_pkey** (`p`): `PRIMARY KEY (message_id)`
- **messages_conversation_id_idempotency_key_key** (`u`): `UNIQUE (conversation_id, idempotency_key)`

## ایندکس‌ها

- `idx_messages_conversation_created`: `CREATE INDEX idx_messages_conversation_created ON conversation.messages USING btree (conversation_id, created_at, message_id)`
- `idx_messages_trip_created`: `CREATE INDEX idx_messages_trip_created ON conversation.messages USING btree (trip_id, created_at, message_id) WHERE (trip_id IS NOT NULL)`
- `messages_conversation_id_idempotency_key_key`: `CREATE UNIQUE INDEX messages_conversation_id_idempotency_key_key ON conversation.messages USING btree (conversation_id, idempotency_key)`
- `messages_pkey`: `CREATE UNIQUE INDEX messages_pkey ON conversation.messages USING btree (message_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **6** از **15**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
