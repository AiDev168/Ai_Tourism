# فرهنگ فیلدهای سفر (travel)

[فهرست اصلی](../README.md). مبنا cab603a7d40cfa35dd20de2ffb12a336d84f56ff؛ metadata پایلوت 0026 + DDL 0027، نه snapshot زنده. NULL قید SQL است نه الزام فرم. پیش‌فرض redacted پالایش شده؛ مقدار را حدس نزنید. توضیح خوانش نام/نوع اثبات معنای تجاری نیست. اطلاعات شخصی، رمز، توکن و ممیزی را مستقیم تغییر ندهید.

[metadata](../../database/rehearsed-schema-0026/catalog_metadata_snapshot.json) | [glossary](../../database/field_descriptions.json) | [DDL 0027](../../../engineering/pilot/sql/027_server_ai_provider_admin.sql) | [مرجع 0027](../../database/rehearsed-schema-0027/PROVIDER_ADMIN_FIELD_REFERENCE.md)

## travel.itineraries

دامنه: سفر؛ itineraries (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: فرم سفر/برنامه؛ traveler.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `itinerary_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ برنامه سفر؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `trip_id` | `uuid` | خیر | ندارد | شناسه ـ سفر؛ ارجاع به travel.trips(trip_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `recommendation_request_id` | `uuid` | بله | ندارد | شناسه ـ درخواست ـ پیشنهاد؛ ارجاع به recommendation.recommendation_requests(recommendation_request_id) ON DELETE SET NULL | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `version` | `integer` | خیر | `1` | نسخه | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `title` | `text` | خیر | ندارد | عنوان | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `day_count` | `smallint` | خیر | ندارد | تعداد ـ روز | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `itinerary_status` | `text` | خیر | `[redacted string default]` | وضعیت ـ برنامه سفر | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی، نه واقعی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `revision` | `integer` | خیر | `1` | بازبینی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `title_by_locale` | `jsonb` | خیر | `[redacted string default]` | زبان/منطقه ـ توسط/بر اساس ـ عنوان | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((day_count >= 1) AND (day_count <= 365)))`
- `CHECK ((itinerary_status = ANY (ARRAY['draft'::text, 'presented'::text, 'accepted'::text, 'edited'::text, 'archived'::text])))`
- `CHECK ((revision > 0))`
- `CHECK ((jsonb_typeof(title_by_locale) = 'object'::text))`
- `CHECK ((version > 0))`
- `FOREIGN KEY (recommendation_request_id) REFERENCES recommendation.recommendation_requests(recommendation_request_id) ON DELETE SET NULL`
- `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- `PRIMARY KEY (itinerary_id)`
- `UNIQUE (trip_id, version)`

## travel.itinerary_stops

دامنه: سفر؛ itinerary_stops (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: فرم سفر/برنامه؛ traveler.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `itinerary_stop_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ توقف ـ برنامه سفر؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `itinerary_id` | `uuid` | خیر | ندارد | شناسه ـ برنامه سفر؛ ارجاع به travel.itineraries(itinerary_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `day_number` | `smallint` | خیر | ندارد | شماره ـ روز | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `stop_order` | `smallint` | خیر | ندارد | ترتیب ـ توقف | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `planned_start_time` | `time without time zone` | بله | ندارد | زمان ـ شروع ـ برنامه‌ریزی‌شده | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `duration_minutes` | `smallint` | بله | ندارد | دقیقه ـ مدت | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `travel_to_next_estimate_minutes` | `smallint` | بله | ندارد | زمان تخمینی حرکت تا توقف بعد به دقیقه | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `notes_fa` | `text` | بله | ندارد | فارسی ـ یادداشت‌ها | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی، نه واقعی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `notes_by_locale` | `jsonb` | خیر | `[redacted string default]` | زبان/منطقه ـ توسط/بر اساس ـ یادداشت‌ها | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `recommendation_id` | `uuid` | بله | ندارد | شناسه ـ پیشنهاد؛ ارجاع به recommendation.recommendations(recommendation_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |

قیود جدول:
- `CHECK (((day_number >= 1) AND (day_number <= 365)))`
- `CHECK (((duration_minutes IS NULL) OR ((duration_minutes >= 1) AND (duration_minutes <= 1440))))`
- `CHECK ((jsonb_typeof(notes_by_locale) = 'object'::text))`
- `CHECK (((stop_order >= 1) AND (stop_order <= 50)))`
- `CHECK (((travel_to_next_estimate_minutes IS NULL) OR (travel_to_next_estimate_minutes >= 0)))`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- `FOREIGN KEY (itinerary_id) REFERENCES travel.itineraries(itinerary_id) ON DELETE CASCADE`
- `FOREIGN KEY (recommendation_id) REFERENCES recommendation.recommendations(recommendation_id) ON DELETE CASCADE`
- `PRIMARY KEY (itinerary_stop_id)`
- `UNIQUE (itinerary_id, day_number, stop_order)`

## travel.provisional_itineraries

دامنه: سفر؛ provisional_itineraries (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: فرم سفر/برنامه؛ traveler.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `provisional_itinerary_id` | `uuid` | خیر | `gen_random_uuid()` | کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `trip_id` | `uuid` | خیر | ندارد | شناسه ـ سفر | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ ارجاع به identity.users(user_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `revision` | `integer` | خیر | `1` | بازبینی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `day_count` | `integer` | خیر | ندارد | تعداد ـ روز | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `locale` | `text` | خیر | ندارد | زبان/منطقه | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `title_by_locale` | `jsonb` | خیر | `[redacted string default]` | زبان/منطقه ـ توسط/بر اساس ـ عنوان | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `days` | `jsonb` | خیر | ندارد | روزها | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `status` | `text` | خیر | `[redacted string default]` | وضعیت | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((day_count >= 1) AND (day_count <= 365)))`
- `CHECK ((jsonb_typeof(days) = 'array'::text))`
- `CHECK ((locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text])))`
- `CHECK ((revision > 0))`
- `CHECK ((status = 'provisional_unverified'::text))`
- `CHECK ((jsonb_typeof(title_by_locale) = 'object'::text))`
- `FOREIGN KEY (trip_id, user_id) REFERENCES travel.trips(trip_id, user_id) ON DELETE CASCADE`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `PRIMARY KEY (provisional_itinerary_id)`
- `UNIQUE (trip_id)`

## travel.trip_constraints

دامنه: سفر؛ trip_constraints (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: فرم سفر/برنامه؛ traveler.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `constraint_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ محدودیت؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `trip_id` | `uuid` | خیر | ندارد | شناسه ـ سفر؛ ارجاع به travel.trips(trip_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `constraint_key` | `text` | خیر | ندارد | کلید ـ محدودیت | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `operator` | `text` | خیر | `[redacted string default]` | عملگر | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `constraint_value` | `jsonb` | خیر | ندارد | مقدار ـ محدودیت | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `constraint_strength` | `text` | خیر | `[redacted string default]` | شدت ـ محدودیت | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `weight` | `numeric(5,4)` | خیر | `1.0` | وزن | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `confidence` | `numeric(5,4)` | بله | ندارد | اطمینان | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `source_message_id` | `uuid` | بله | ندارد | شناسه ـ پیام ـ منبع؛ ارجاع به conversation.messages(message_id) ON DELETE SET NULL | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی، نه واقعی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))))`
- `CHECK ((constraint_strength = ANY (ARRAY['hard'::text, 'soft'::text])))`
- `CHECK (((weight >= (0)::numeric) AND (weight <= (1)::numeric)))`
- `FOREIGN KEY (source_message_id) REFERENCES conversation.messages(message_id) ON DELETE SET NULL`
- `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- `PRIMARY KEY (constraint_id)`
- `UNIQUE (trip_id, constraint_key)`

## travel.trip_interests

دامنه: سفر؛ trip_interests (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: فرم سفر/برنامه؛ traveler.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `trip_interest_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ علاقه ـ سفر؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `trip_id` | `uuid` | خیر | ندارد | شناسه ـ سفر؛ ارجاع به travel.trips(trip_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `interest_key` | `text` | خیر | ندارد | کلید ـ علاقه | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `weight` | `numeric(5,4)` | خیر | `0.5` | وزن | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `is_required` | `boolean` | خیر | `false` | الزامی ـ نشان | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی، نه واقعی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((weight >= (0)::numeric) AND (weight <= (1)::numeric)))`
- `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- `PRIMARY KEY (trip_interest_id)`
- `UNIQUE (trip_id, interest_key)`

## travel.trip_requirement_revisions

دامنه: سفر؛ trip_requirement_revisions (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: فرم سفر/برنامه؛ traveler.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `trip_id` | `uuid` | خیر | ندارد | شناسه ـ سفر | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `revision_number` | `integer` | خیر | ندارد | شماره ـ بازبینی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `trip_version` | `integer` | خیر | ندارد | نسخه ـ سفر | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `requirement_snapshot` | `jsonb` | خیر | ندارد | تصویر ثابت نیازمندی سفر | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی، نه واقعی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((jsonb_typeof(requirement_snapshot) = 'object'::text))`
- `CHECK ((revision_number > 0))`
- `CHECK ((trip_version > 0))`
- `FOREIGN KEY (trip_id, user_id) REFERENCES travel.trips(trip_id, user_id) ON DELETE CASCADE`
- `PRIMARY KEY (trip_id, revision_number)`

## travel.trips

دامنه: سفر؛ trips (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: فرم سفر/برنامه؛ traveler.py.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `trip_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ سفر؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `user_id` | `uuid` | بله | ندارد | شناسه ـ کاربر؛ ارجاع به identity.users(user_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `conversation_id` | `uuid` | بله | ندارد | شناسه ـ گفتگو؛ ارجاع به conversation.conversations(conversation_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `trip_title` | `text` | بله | ندارد | عنوان ـ سفر | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `origin_text` | `text` | بله | ندارد | متن ـ منشأ | فرم/API دامنه؛ راهنمای ورود | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `origin_location` | `geography(Point,4326)` | بله | ندارد | موقعیت ـ منشأ | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `start_date` | `date` | بله | ندارد | معنای دقیق احراز نشده؛ نام به تنهایی کافی نیست | فرم/API دامنه؛ راهنمای ورود | نامشخص |
| `end_date` | `date` | بله | ندارد | معنای دقیق احراز نشده؛ نام به تنهایی کافی نیست | فرم/API دامنه؛ راهنمای ورود | نامشخص |
| `duration_days` | `smallint` | بله | ندارد | روزها ـ مدت | فرم/API دامنه؛ راهنمای ورود | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `budget_min` | `numeric(14,2)` | بله | ندارد | حداقل ـ بودجه | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `budget_max` | `numeric(14,2)` | بله | ندارد | حداکثر ـ بودجه | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `currency` | `character(3)` | خیر | `[redacted string default]` | ارز | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `traveler_count` | `smallint` | بله | ندارد | تعداد ـ مسافر | فرم/API دامنه؛ راهنمای ورود | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `extracted_requirements` | `jsonb` | خیر | `[redacted string default]` | نیازمندی‌ها ـ استخراج‌شده | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `extraction_confidence` | `numeric(5,4)` | بله | ندارد | اطمینان ـ استخراج | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `trip_status` | `text` | خیر | `[redacted string default]` | وضعیت ـ سفر | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی، نه واقعی | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `version` | `integer` | خیر | `1` | نسخه | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `create_idempotency_key` | `text` | بله | ندارد | کلید جلوگیری از ایجاد دوباره | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `confirmed_requirements` | `jsonb` | خیر | `[redacted string default]` | نیازهای تأییدشده مسافر | فرم/API دامنه؛ راهنمای ورود | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `budget_amount_original` | `numeric(20,4)` | بله | ندارد | مقدار عددی بودجه اعلام‌شده | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `budget_currency_iso` | `character(3)` | بله | ندارد | کد ISO ارز بودجه | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `budget_unit` | `text` | بله | ندارد | واحد بیان بودجه | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `budget_raw_text` | `text` | بله | ندارد | عبارت اولیه بودجه مسافر | فرم/API دامنه؛ راهنمای ورود | خوانش نام/نوع؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((budget_max IS NULL) OR (budget_max >= (0)::numeric)))`
- `CHECK (((budget_min IS NULL) OR (budget_min >= (0)::numeric)))`
- `CHECK ((((budget_amount_original IS NULL) AND (budget_currency_iso IS NULL) AND (budget_unit IS NULL) AND (budget_raw_text IS NULL)) OR ((budget_amount_original IS NOT NULL) AND (budget_currency_iso IS NOT NULL) AND (budget_currency_iso = 'IRR'::bpchar) AND (budget_unit IS NOT NULL) AND (budget_unit = ANY (ARRAY['rial'::text, 'toman'::text])) AND (budget_raw_text IS NOT NULL) AND (budget_amount_original >= (0)::numeric))))`
- `CHECK (((end_date IS NULL) OR (start_date IS NULL) OR (end_date >= start_date)))`
- `CHECK (((budget_min IS NULL) OR (budget_max IS NULL) OR (budget_max >= budget_min)))`
- `CHECK ((currency ~ '^[A-Z]{3}$'::text))`
- `CHECK (((duration_days IS NULL) OR ((duration_days >= 1) AND (duration_days <= 365))))`
- `CHECK (((extraction_confidence IS NULL) OR ((extraction_confidence >= (0)::numeric) AND (extraction_confidence <= (1)::numeric))))`
- `CHECK (((traveler_count >= 1) AND (traveler_count <= 50)))`
- `CHECK (((traveler_count IS NULL) OR ((traveler_count >= 1) AND (traveler_count <= 50))))`
- `CHECK ((trip_status = ANY (ARRAY['draft'::text, 'ready'::text, 'planned'::text, 'completed'::text, 'cancelled'::text, 'archived'::text])))`
- `CHECK ((version > 0))`
- `FOREIGN KEY (conversation_id) REFERENCES conversation.conversations(conversation_id) ON DELETE CASCADE`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `PRIMARY KEY (trip_id)`
