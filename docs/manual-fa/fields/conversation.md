# فرهنگ فیلدهای گفتگو (conversation)

[فهرست اصلی](../README.md). مبنا cab603a7d40cfa35dd20de2ffb12a336d84f56ff؛ metadata پایلوت 0026 + DDL 0027، نه snapshot زنده. NULL قید SQL است نه الزام فرم. پیش‌فرض redacted پالایش شده؛ مقدار را حدس نزنید. توضیح خوانش نام/نوع اثبات معنای تجاری نیست. اطلاعات شخصی، رمز، توکن و ممیزی را مستقیم تغییر ندهید.

[metadata](../../database/rehearsed-schema-0026/catalog_metadata_snapshot.json) | [glossary](../../database/field_descriptions.json) | [DDL 0027](../../../engineering/pilot/sql/027_server_ai_provider_admin.sql) | [مرجع 0027](../../database/rehearsed-schema-0027/PROVIDER_ADMIN_FIELD_REFERENCE.md)

## conversation.assistant_turns

ثبت شناسه یکتا، وضعیت و چرخه اجرای هر نوبت مدل در مکالمه.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: گفتگوی مسافر؛ assistant.py/traveler.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `turn_id` | `uuid` | خیر | ندارد | شناسه یکتای نوبت دستیار. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ مالک مجاز نوبت. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `conversation_id` | `uuid` | خیر | ندارد | شناسه ـ گفتگو؛ مکالمه مربوطه. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `trip_id` | `uuid` | خیر | ندارد | شناسه ـ سفر؛ سفر مربوطه. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `idempotency_key` | `text` | خیر | ندارد | کلید جلوگیری از اجرای دوباره درخواست؛ کلید جلوگیری از اجرای تکراری یک درخواست. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `content_sha256` | `bytea` | خیر | ندارد | اثر انگشت SHA-256 محتوا؛ هش متن درخواست؛ مقدار واقعی نباید در سند منتشر شود. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `status` | `text` | خیر | ندارد | وضعیت؛ وضعیت چرخه اجرا مثل reserved/completed/failed. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `user_message_id` | `uuid` | خیر | ندارد | شناسه ـ پیام ـ کاربر؛ ارجاع به پیام درخواست کاربر. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `assistant_message_id` | `uuid` | بله | ندارد | ارجاع به پیام خروجی دستیار پس از تکمیل. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `consented_at` | `timestamp with time zone` | خیر | `now()` | زمان ـ رضایت ثبت‌شده | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر؛ زمان آخرین تغییر وضعیت. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK (((status = 'completed'::text) = (assistant_message_id IS NOT NULL)))`
- `CHECK ((octet_length(content_sha256) = 32))`
- `CHECK (((length(idempotency_key) >= 8) AND (length(idempotency_key) <= 128)))`
- `CHECK ((status = ANY (ARRAY['reserved'::text, 'completed'::text, 'failed'::text])))`
- `FOREIGN KEY (assistant_message_id) REFERENCES conversation.messages(message_id) ON DELETE CASCADE`
- `FOREIGN KEY (conversation_id) REFERENCES conversation.conversations(conversation_id) ON DELETE CASCADE`
- `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `FOREIGN KEY (user_message_id) REFERENCES conversation.messages(message_id) ON DELETE CASCADE`
- `PRIMARY KEY (turn_id)`
- `UNIQUE (conversation_id, idempotency_key)`

## conversation.conversations

ظرف مکالمه مسافر با دستیار پیرامون سفرهای ثبت‌شده.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: گفتگوی مسافر؛ assistant.py/traveler.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `conversation_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ گفتگو؛ شناسه یکتای مکالمه. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `user_id` | `uuid` | بله | ندارد | شناسه ـ کاربر؛ مالک مکالمه و مبنای محدودسازی دسترسی. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `channel` | `text` | خیر | `[redacted string default]` | کانال | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `language_code` | `text` | خیر | `[redacted string default]` | کد ـ زبان؛ زبان مکالمه. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `conversation_status` | `text` | خیر | `[redacted string default]` | وضعیت ـ گفتگو | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `structured_context` | `jsonb` | خیر | `[redacted string default]` | زمینه ـ ساخت‌یافته | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی، نه واقعی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `started_at` | `timestamp with time zone` | خیر | `now()` | زمان ـ شروع | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `last_message_at` | `timestamp with time zone` | بله | ندارد | زمان ـ پیام ـ آخرین؛ زمان آخرین پیام مکالمه. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `ended_at` | `timestamp with time zone` | بله | ندارد | زمان ـ پایان | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `version` | `integer` | خیر | `1` | نسخه؛ شماره نسخه برای کنترل تعارض به‌روزرسانی. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر؛ زمان آخرین تغییر. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `create_idempotency_key` | `text` | بله | ندارد | کلید جلوگیری از ایجاد دوباره | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((channel = ANY (ARRAY['pwa'::text, 'web'::text, 'mobile_web'::text, 'admin_test'::text])))`
- `CHECK ((conversation_status = ANY (ARRAY['active'::text, 'completed'::text, 'archived'::text, 'deleted'::text])))`
- `CHECK ((version > 0))`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `PRIMARY KEY (conversation_id)`

## conversation.messages

پیام‌های کاربر، دستیار یا سیستم در یک مکالمه.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: گفتگوی مسافر؛ assistant.py/traveler.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `message_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ پیام؛ شناسه یکتای پیام. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `conversation_id` | `uuid` | خیر | ندارد | شناسه ـ گفتگو؛ شناسه مکالمه. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `role` | `text` | خیر | ندارد | نقش؛ نقش فرستنده: user/assistant/system/tool مطابق API. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `content` | `text` | خیر | ندارد | محتوا؛ متن پیام که ممکن است داده خصوصی سفر باشد؛ مستندساز فقط متادیتا می‌خواند. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `message_type` | `text` | خیر | `[redacted string default]` | نوع ـ پیام؛ نوع پیام. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `provider_name` | `text` | بله | ندارد | نام ـ ارائه‌دهنده | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `model_name` | `text` | بله | ندارد | نام ـ مدل | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `input_tokens` | `integer` | بله | ندارد | شمار توکن ورودی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `output_tokens` | `integer` | بله | ندارد | شمار توکن خروجی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `latency_ms` | `integer` | بله | ندارد | زمان پاسخ بر حسب میلی‌ثانیه | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `metadata` | `jsonb` | خیر | `[redacted string default]` | فراداده؛ فراداده ساخت‌یافته پیام؛ قرارداد requirements_candidate و clarification و provisional_itinerary در کد Chat. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `idempotency_key` | `text` | بله | ندارد | کلید جلوگیری از اجرای دوباره درخواست | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی، نه واقعی؛ تمایز رکورد آزمایشی از واقعی. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد؛ زمان ایجاد پیام. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `trip_id` | `uuid` | بله | ندارد | شناسه ـ سفر؛ شناسه سفر مرتبط، در صورت تعیین. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |

قیود جدول:
- `CHECK (((input_tokens IS NULL) OR (input_tokens >= 0)))`
- `CHECK (((latency_ms IS NULL) OR (latency_ms >= 0)))`
- `CHECK ((message_type = ANY (ARRAY['text'::text, 'structured'::text, 'tool_call'::text, 'tool_result'::text, 'system_notice'::text])))`
- `CHECK (((output_tokens IS NULL) OR (output_tokens >= 0)))`
- `CHECK ((role = ANY (ARRAY['system'::text, 'user'::text, 'assistant'::text, 'tool'::text])))`
- `FOREIGN KEY (conversation_id) REFERENCES conversation.conversations(conversation_id) ON DELETE CASCADE`
- `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- `PRIMARY KEY (message_id)`
- `UNIQUE (conversation_id, idempotency_key)`
