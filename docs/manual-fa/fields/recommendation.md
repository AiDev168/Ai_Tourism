# فرهنگ فیلدهای پیشنهاد سفر (recommendation)

[فهرست اصلی](../README.md). مبنا cab603a7d40cfa35dd20de2ffb12a336d84f56ff؛ metadata پایلوت 0026 + DDL 0027، نه snapshot زنده. NULL قید SQL است نه الزام فرم. پیش‌فرض redacted پالایش شده؛ مقدار را حدس نزنید. توضیح خوانش نام/نوع اثبات معنای تجاری نیست. اطلاعات شخصی، رمز، توکن و ممیزی را مستقیم تغییر ندهید.

[metadata](../../database/rehearsed-schema-0026/catalog_metadata_snapshot.json) | [glossary](../../database/field_descriptions.json) | [DDL 0027](../../../engineering/pilot/sql/027_server_ai_provider_admin.sql) | [مرجع 0027](../../database/rehearsed-schema-0027/PROVIDER_ADMIN_FIELD_REFERENCE.md)

## recommendation.recommendation_requests

دامنه: پیشنهاد سفر؛ recommendation_requests (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: محاسبه خودکار؛ نه فرم امتیاز.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `recommendation_request_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ درخواست ـ پیشنهاد؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `trip_id` | `uuid` | خیر | ندارد | شناسه ـ سفر؛ ارجاع به travel.trips(trip_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `conversation_id` | `uuid` | بله | ندارد | شناسه ـ گفتگو؛ ارجاع به conversation.conversations(conversation_id) ON DELETE SET NULL | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `algorithm_version` | `text` | خیر | ندارد | نسخه ـ الگوریتم | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `retrieval_version` | `text` | بله | ندارد | نسخه ـ بازیابی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `input_snapshot` | `jsonb` | خیر | `[redacted string default]` | تصویر ثابت ـ ورودی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `request_status` | `text` | خیر | `[redacted string default]` | وضعیت ـ درخواست | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی، نه واقعی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `completed_at` | `timestamp with time zone` | بله | ندارد | زمان ـ تکمیل | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((request_status = ANY (ARRAY['created'::text, 'processing'::text, 'completed'::text, 'failed'::text, 'cancelled'::text])))`
- `FOREIGN KEY (conversation_id) REFERENCES conversation.conversations(conversation_id) ON DELETE SET NULL`
- `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- `PRIMARY KEY (recommendation_request_id)`

## recommendation.recommendation_score_components

دامنه: پیشنهاد سفر؛ recommendation_score_components (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: محاسبه خودکار؛ نه فرم امتیاز.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `score_component_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ مؤلفه ـ امتیاز؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `recommendation_id` | `uuid` | خیر | ندارد | شناسه ـ پیشنهاد؛ ارجاع به recommendation.recommendations(recommendation_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `component_key` | `text` | خیر | ندارد | کلید ـ مؤلفه | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `raw_score` | `numeric(12,6)` | بله | ندارد | امتیاز ـ خام | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `normalized_score` | `numeric(7,6)` | بله | ندارد | امتیاز ـ نرمال‌شده | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `weight` | `numeric(7,6)` | خیر | ندارد | وزن | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `weighted_score` | `numeric(12,6)` | خیر | ندارد | امتیاز ـ وزن‌دار | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `component_reason` | `text` | بله | ندارد | دلیل ـ مؤلفه | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی، نه واقعی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((normalized_score IS NULL) OR ((normalized_score >= (0)::numeric) AND (normalized_score <= (1)::numeric))))`
- `CHECK (((weight >= (0)::numeric) AND (weight <= (1)::numeric)))`
- `FOREIGN KEY (recommendation_id) REFERENCES recommendation.recommendations(recommendation_id) ON DELETE CASCADE`
- `PRIMARY KEY (score_component_id)`
- `UNIQUE (recommendation_id, component_key)`

## recommendation.recommendations

دامنه: پیشنهاد سفر؛ recommendations (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: محاسبه خودکار؛ نه فرم امتیاز.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `recommendation_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ پیشنهاد؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `recommendation_request_id` | `uuid` | خیر | ندارد | شناسه ـ درخواست ـ پیشنهاد؛ ارجاع به recommendation.recommendation_requests(recommendation_request_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `rank` | `smallint` | خیر | ندارد | رتبه | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `final_score` | `numeric(7,6)` | خیر | ندارد | امتیاز ـ نهایی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `confidence` | `numeric(5,4)` | بله | ندارد | اطمینان | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `explanation_fa` | `text` | خیر | ندارد | فارسی ـ توضیح | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `warnings` | `jsonb` | خیر | `[redacted string default]` | هشدارها | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی، نه واقعی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `evidence` | `jsonb` | خیر | `[redacted string default]` | شاهد | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `explanation_by_locale` | `jsonb` | خیر | `[redacted string default]` | زبان/منطقه ـ توسط/بر اساس ـ توضیح | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))))`
- `CHECK ((jsonb_typeof(evidence) = 'array'::text))`
- `CHECK ((jsonb_typeof(explanation_by_locale) = 'object'::text))`
- `CHECK (((final_score >= (0)::numeric) AND (final_score <= (1)::numeric)))`
- `CHECK ((rank > 0))`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- `FOREIGN KEY (recommendation_request_id) REFERENCES recommendation.recommendation_requests(recommendation_request_id) ON DELETE CASCADE`
- `PRIMARY KEY (recommendation_id)`
- `UNIQUE (recommendation_request_id, destination_id)`
- `UNIQUE (recommendation_request_id, rank)`
