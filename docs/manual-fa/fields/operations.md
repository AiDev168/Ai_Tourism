# فرهنگ فیلدهای عملیات و ممیزی (operations)

[فهرست اصلی](../README.md). مبنا cab603a7d40cfa35dd20de2ffb12a336d84f56ff؛ metadata پایلوت 0026 + DDL 0027، نه snapshot زنده. NULL قید SQL است نه الزام فرم. پیش‌فرض redacted پالایش شده؛ مقدار را حدس نزنید. توضیح خوانش نام/نوع اثبات معنای تجاری نیست. اطلاعات شخصی، رمز، توکن و ممیزی را مستقیم تغییر ندهید.

[metadata](../../database/rehearsed-schema-0026/catalog_metadata_snapshot.json) | [glossary](../../database/field_descriptions.json) | [DDL 0027](../../../engineering/pilot/sql/027_server_ai_provider_admin.sql) | [مرجع 0027](../../database/rehearsed-schema-0027/PROVIDER_ADMIN_FIELD_REFERENCE.md)

## operations.ai_model_calls

دامنه: عملیات و ممیزی؛ ai_model_calls (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: سامانه/اپراتور؛ نه فرم عمومی.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `ai_model_call_id` | `uuid` | خیر | `gen_random_uuid()` | کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `correlation_id` | `uuid` | بله | ندارد | شناسه مرتبط‌کننده رخدادهای یک عملیات | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `provider_name` | `text` | خیر | ندارد | نام ارائه‌دهنده مدل یا خدمت | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `model_name` | `text` | خیر | ندارد | نام مدل استفاده‌شده | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `task_type` | `text` | خیر | ندارد | نوع وظیفه مدل | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `call_status` | `text` | خیر | ندارد | وضعیت فراخوانی مدل | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `input_tokens` | `integer` | بله | ندارد | تعداد توکن ورودی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `output_tokens` | `integer` | بله | ندارد | تعداد توکن خروجی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `latency_ms` | `integer` | بله | ندارد | زمان پاسخ بر حسب میلی‌ثانیه | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `estimated_cost` | `numeric(14,8)` | بله | ندارد | هزینه برآوردی فراخوانی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `cost_currency` | `character(3)` | بله | ندارد | ارز هزینه | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((call_status = ANY (ARRAY['success'::text, 'timeout'::text, 'rate_limited'::text, 'provider_error'::text, 'validation_error'::text])))`
- `CHECK (((estimated_cost IS NULL) OR (estimated_cost >= (0)::numeric)))`
- `CHECK (((input_tokens IS NULL) OR (input_tokens >= 0)))`
- `CHECK (((latency_ms IS NULL) OR (latency_ms >= 0)))`
- `CHECK (((output_tokens IS NULL) OR (output_tokens >= 0)))`
- `PRIMARY KEY (ai_model_call_id)`

## operations.audit_events

دامنه: عملیات و ممیزی؛ audit_events (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: سامانه/اپراتور؛ نه فرم عمومی.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `audit_event_id` | `uuid` | خیر | `gen_random_uuid()` | کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `actor_user_id` | `uuid` | بله | ندارد | شناسه ـ کاربر ـ عامل؛ ارجاع به identity.users(user_id) ON DELETE SET NULL | سامانه/اپراتور مجاز | قید FK |
| `actor_type` | `text` | خیر | `[redacted string default]` | نوع عامل انجام‌دهنده عملیات | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `action` | `text` | خیر | ندارد | نوع عملیات ثبت‌شده | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `resource_type` | `text` | خیر | ندارد | نوع منبع تحت عملیات | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `resource_id` | `text` | بله | ندارد | شناسه منبع تحت عملیات | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `correlation_id` | `uuid` | بله | ندارد | شناسه مرتبط‌کننده رخدادهای یک عملیات | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `metadata` | `jsonb` | خیر | `[redacted string default]` | فراداده JSON؛ کلیدها تابع قرارداد مصرف‌کننده‌اند | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((actor_type = ANY (ARRAY['user'::text, 'system'::text, 'administrator'::text, 'service'::text])))`
- `FOREIGN KEY (actor_user_id) REFERENCES identity.users(user_id) ON DELETE SET NULL`
- `PRIMARY KEY (audit_event_id)`

## operations.dataset_import_batches

دامنه: عملیات و ممیزی؛ dataset_import_batches (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: سامانه/اپراتور؛ نه فرم عمومی.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `dataset_import_batch_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ دسته ـ ورود ـ مجموعه داده؛ کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `batch_key` | `text` | خیر | ندارد | کلید دسته ورود داده | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `data_class` | `text` | خیر | ندارد | طبقه داده ورودی؛ مقادیر از قید | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_id` | `bigint` | بله | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE SET NULL | سامانه/اپراتور مجاز | قید FK |
| `record_counts` | `jsonb` | خیر | `[redacted string default]` | شمار رکوردها به صورت ساخت‌یافته؛ کلیدها طبق قرارداد ورود | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_checksum` | `character(64)` | بله | ندارد | چک‌سام منبع | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `imported_at` | `timestamp with time zone` | خیر | `now()` | زمان ورود دسته داده | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `notes` | `text` | بله | ندارد | یادداشت تکمیلی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((data_class = ANY (ARRAY['verified_external'::text, 'user_supplied_unverified'::text, 'synthetic_fixture'::text])))`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE SET NULL`
- `PRIMARY KEY (dataset_import_batch_id)`
- `UNIQUE (batch_key)`

## operations.dataset_import_files

دامنه: عملیات و ممیزی؛ dataset_import_files (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: سامانه/اپراتور؛ نه فرم عمومی.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `file_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ فایل؛ کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `dataset_import_batch_id` | `uuid` | خیر | ندارد | شناسه ـ دسته ـ ورود ـ مجموعه داده؛ ارجاع به operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT | سامانه/اپراتور مجاز | قید FK |
| `relative_path` | `text` | خیر | ندارد | مسیر نسبی فایل ورودی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `file_sha256` | `character(64)` | خیر | ندارد | اثر انگشت SHA-256 فایل | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `byte_size` | `bigint` | خیر | ندارد | اندازه فایل به بایت | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `format` | `text` | خیر | ندارد | قالب فایل | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `schema_signature` | `character(64)` | بله | ندارد | امضای ساختار فایل ورودی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_locale` | `text` | بله | ندارد | زبان/منطقه منبع | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_dataset_key` | `text` | بله | ندارد | کلید مجموعه داده مبدأ | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `row_count` | `bigint` | بله | ندارد | شمار سطرهای فایل | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `accepted_count` | `bigint` | بله | ندارد | شمار سطرهای پذیرفته‌شده | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `rejected_count` | `bigint` | بله | ندارد | شمار سطرهای ردشده | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `import_status` | `text` | خیر | `[redacted string default]` | وضعیت ورود فایل | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `parsed_at` | `timestamp with time zone` | بله | ندارد | زمان تجزیه فایل | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((accepted_count IS NULL) OR (accepted_count >= 0)))`
- `CHECK ((byte_size >= 0))`
- `CHECK (((accepted_count IS NULL) OR (row_count IS NULL) OR (accepted_count <= row_count)))`
- `CHECK (((rejected_count IS NULL) OR (row_count IS NULL) OR (rejected_count <= row_count)))`
- `CHECK ((file_sha256 ~ '^[a-f0-9]{64}$'::text))`
- `CHECK ((format = ANY (ARRAY['csv'::text, 'json'::text, 'geojson'::text, 'xlsx'::text, 'other'::text])))`
- `CHECK ((import_status = ANY (ARRAY['received'::text, 'parsed'::text, 'review_ready'::text, 'failed'::text, 'quarantined'::text, 'conflict'::text])))`
- `CHECK (((rejected_count IS NULL) OR (rejected_count >= 0)))`
- `CHECK ((((length(btrim(relative_path)) >= 1) AND (length(btrim(relative_path)) <= 1024)) AND (relative_path !~ '(^/\|(^\|/)\.\.(/\|$))'::text)))`
- `CHECK (((row_count IS NULL) OR (row_count >= 0)))`
- `CHECK (((schema_signature IS NULL) OR (schema_signature ~ '^[a-f0-9]{64}$'::text)))`
- `CHECK (((source_locale IS NULL) OR (source_locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text, 'und'::text]))))`
- `FOREIGN KEY (dataset_import_batch_id) REFERENCES operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT`
- `PRIMARY KEY (file_id)`
- `UNIQUE (dataset_import_batch_id, relative_path, file_sha256)`

## operations.feedback

دامنه: عملیات و ممیزی؛ بازخورد (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: سامانه/اپراتور؛ نه فرم عمومی.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `feedback_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ بازخورد؛ کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `user_id` | `uuid` | بله | ندارد | شناسه ـ کاربر؛ ارجاع به identity.users(user_id) ON DELETE CASCADE | سامانه/اپراتور مجاز | قید FK |
| `conversation_id` | `uuid` | بله | ندارد | شناسه ـ گفتگو؛ ارجاع به conversation.conversations(conversation_id) ON DELETE CASCADE | سامانه/اپراتور مجاز | قید FK |
| `trip_id` | `uuid` | بله | ندارد | شناسه ـ سفر؛ ارجاع به travel.trips(trip_id) ON DELETE CASCADE | سامانه/اپراتور مجاز | قید FK |
| `recommendation_id` | `uuid` | بله | ندارد | شناسه ـ پیشنهاد؛ ارجاع به recommendation.recommendations(recommendation_id) ON DELETE CASCADE | سامانه/اپراتور مجاز | قید FK |
| `feedback_type` | `text` | خیر | ندارد | نوع بازخورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `rating` | `smallint` | بله | ندارد | امتیاز بازخورد؛ دامنه از قید | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `comment` | `text` | بله | ندارد | متن بازخورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((user_id IS NOT NULL) OR (conversation_id IS NOT NULL) OR (trip_id IS NOT NULL) OR (recommendation_id IS NOT NULL)))`
- `CHECK ((feedback_type = ANY (ARRAY['recommendation_rating'::text, 'answer_quality'::text, 'itinerary_quality'::text, 'bug_report'::text, 'other'::text])))`
- `CHECK (((rating IS NULL) OR ((rating >= 1) AND (rating <= 5))))`
- `FOREIGN KEY (conversation_id) REFERENCES conversation.conversations(conversation_id) ON DELETE CASCADE`
- `FOREIGN KEY (recommendation_id) REFERENCES recommendation.recommendations(recommendation_id) ON DELETE CASCADE`
- `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `PRIMARY KEY (feedback_id)`

## operations.private_pilot_geo_approvals

دامنه: عملیات و ممیزی؛ private_pilot_geo_approvals (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: سامانه/اپراتور؛ نه فرم عمومی.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `authorization_id` | `uuid` | خیر | ندارد | شناسه ـ مجوز؛ ارجاع به operations.private_pilot_geo_authorizations(authorization_id) | سامانه/اپراتور مجاز | قید FK |
| `destination_key` | `text` | خیر | ندارد | کلید ـ مقصد؛ ارجاع به knowledge.destinations(destination_key) | سامانه/اپراتور مجاز | قید FK |
| `decision_sha256` | `character(64)` | خیر | ندارد | اثر انگشت تصمیم | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `marker_sha256` | `character(64)` | خیر | ندارد | اثر انگشت نشانگر محیط | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `reviewer` | `text` | خیر | ندارد | بازبین ثبت‌شده | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `approval_reference` | `text` | خیر | ندارد | مرجع تأیید | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `reviewed_at` | `timestamp with time zone` | خیر | ندارد | زمان بازبینی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `coordinate_role` | `text` | خیر | ندارد | نقش مختصات؛ نقطه نماینده لزوما ورودی نیست | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((coordinate_role = ANY (ARRAY['representative_point'::text, 'property_reference'::text])))`
- `CHECK ((decision_sha256 ~ '^[a-f0-9]{64}$'::text))`
- `CHECK ((marker_sha256 ~ '^[a-f0-9]{64}$'::text))`
- `FOREIGN KEY (authorization_id) REFERENCES operations.private_pilot_geo_authorizations(authorization_id)`
- `FOREIGN KEY (destination_key) REFERENCES knowledge.destinations(destination_key)`
- `PRIMARY KEY (authorization_id)`
- `UNIQUE (destination_key, decision_sha256, marker_sha256)`

## operations.private_pilot_geo_authorizations

دامنه: عملیات و ممیزی؛ private_pilot_geo_authorizations (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: سامانه/اپراتور؛ نه فرم عمومی.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `authorization_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ مجوز؛ کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `destination_key` | `text` | خیر | ندارد | کلید ـ مقصد؛ ارجاع به knowledge.destinations(destination_key) | سامانه/اپراتور مجاز | قید FK |
| `decision_sha256` | `character(64)` | خیر | ندارد | اثر انگشت تصمیم | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `marker_sha256` | `character(64)` | خیر | ندارد | اثر انگشت نشانگر محیط | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `canonical_name` | `text` | خیر | ندارد | نام معیار مکان گردشگری | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `destination_type` | `text` | خیر | ندارد | نوع مکان گردشگری | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `province_name` | `text` | خیر | ندارد | نام استان | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `city_name` | `text` | بله | ندارد | نام شهر | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `latitude` | `double precision` | خیر | ندارد | عرض جغرافیایی به درجه | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `longitude` | `double precision` | خیر | ندارد | طول جغرافیایی به درجه | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `coordinate_role` | `text` | خیر | ندارد | نقش مختصات؛ نقطه نماینده لزوما ورودی نیست | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_url` | `text` | خیر | ندارد | نشانی منبع این داده | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `reviewer` | `text` | خیر | ندارد | بازبین ثبت‌شده | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `approval_reference` | `text` | خیر | ندارد | مرجع تأیید | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `reviewed_at` | `timestamp with time zone` | خیر | ندارد | زمان بازبینی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `expires_at` | `timestamp with time zone` | خیر | ندارد | زمان انقضا | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((length(btrim(approval_reference)) >= 1) AND (length(btrim(approval_reference)) <= 240)))`
- `CHECK (((reviewed_at <= created_at) AND (expires_at > created_at) AND (expires_at <= (created_at + '01:00:00'::interval))))`
- `CHECK ((((destination_key = 'shiraz-hafezieh-v1'::text) AND (coordinate_role = 'representative_point'::text) AND (source_url = 'https://en.wikipedia.org/wiki/Tomb_of_Hafez'::text)) OR ((destination_key = 'shiraz-eram-garden-v1'::text) AND (coordinate_role = 'representative_point'::text) AND (source_url = 'https://en.wikipedia.org/wiki/Eram_Garden'::text)) OR ((destination_key = 'shiraz-vakil-bazaar-v1'::text) AND (coordinate_role = 'representative_point'::text) AND (source_url = 'https://en.wikipedia.org/wiki/Vakil_Bazaar'::text)) OR ((destination_key = 'unesco-persepolis-v1'::text) AND (coordinate_role = 'property_reference'::text) AND (source_url = 'https://whc.unesco.org/en/list/114/maps/'::text))))`
- `CHECK ((decision_sha256 ~ '^[a-f0-9]{64}$'::text))`
- `CHECK (((latitude >= ('-90'::integer)::double precision) AND (latitude <= (90)::double precision)))`
- `CHECK (((longitude >= ('-180'::integer)::double precision) AND (longitude <= (180)::double precision)))`
- `CHECK ((marker_sha256 ~ '^[a-f0-9]{64}$'::text))`
- `CHECK (((length(btrim(reviewer)) >= 1) AND (length(btrim(reviewer)) <= 240)))`
- `FOREIGN KEY (destination_key) REFERENCES knowledge.destinations(destination_key)`
- `PRIMARY KEY (authorization_id)`
- `UNIQUE (destination_key, decision_sha256, marker_sha256)`
