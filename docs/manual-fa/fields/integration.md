# فرهنگ فیلدهای ارتباطات خارجی (integration)

[فهرست اصلی](../README.md). مبنا cab603a7d40cfa35dd20de2ffb12a336d84f56ff؛ metadata پایلوت 0026 + DDL 0027، نه snapshot زنده. NULL قید SQL است نه الزام فرم. پیش‌فرض redacted پالایش شده؛ مقدار را حدس نزنید. توضیح خوانش نام/نوع اثبات معنای تجاری نیست. اطلاعات شخصی، رمز، توکن و ممیزی را مستقیم تغییر ندهید.

[metadata](../../database/rehearsed-schema-0026/catalog_metadata_snapshot.json) | [glossary](../../database/field_descriptions.json) | [DDL 0027](../../../engineering/pilot/sql/027_server_ai_provider_admin.sql) | [مرجع 0027](../../database/rehearsed-schema-0027/PROVIDER_ADMIN_FIELD_REFERENCE.md)

## integration.chat_daily_global_budget

سقف کلی استفاده روزانه دستیار در سامانه.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: سرویس داخلی؛ نه CRUD عمومی.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `budget_day` | `date` | خیر | ندارد | روز ـ بودجه؛ روز محاسبه سهمیه بر مبنای UTC. | فرم مستقیم احراز نشده | فرهنگ موجود |
| `hit_count` | `integer` | خیر | ندارد | تعداد ـ رخداد؛ تعداد کل نوبت‌های مصرف‌شده در روز. | فرم مستقیم احراز نشده | فرهنگ موجود |

قیود جدول:
- `CHECK (((hit_count >= 1) AND (hit_count <= 100000)))`
- `PRIMARY KEY (budget_day)`

## integration.chat_daily_user_budget

سقف روزانه مصرف نوبت‌های دستیار برای هر کاربر.

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: سرویس داخلی؛ نه CRUD عمومی.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ شناسه کاربر مشمول سقف. | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | فرهنگ موجود |
| `budget_day` | `date` | خیر | ندارد | روز ـ بودجه؛ روز محاسبه سهمیه (در Backend از روز UTC استفاده شده است). | فرم مستقیم احراز نشده | فرهنگ موجود |
| `hit_count` | `integer` | خیر | ندارد | تعداد ـ رخداد؛ تعداد سهمیه مصرف‌شده در روز. | فرم مستقیم احراز نشده | فرهنگ موجود |

قیود جدول:
- `CHECK (((hit_count >= 1) AND (hit_count <= 1000)))`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `PRIMARY KEY (user_id, budget_day)`

## integration.external_links

دامنه: ارتباطات خارجی؛ external_links (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: سرویس داخلی؛ نه CRUD عمومی.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `external_link_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ پیوند ـ خارجی؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `destination_id` | `bigint` | بله | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE SET NULL | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `provider_name` | `text` | خیر | ندارد | نام ارائه‌دهنده مدل یا خدمت | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `service_type` | `text` | خیر | ندارد | نوع خدمت مرتبط | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `label_fa` | `text` | خیر | ندارد | برچسب فارسی پیوند | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `target_url` | `text` | خیر | ندارد | نشانی مقصد پیوند خارجی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_active` | `boolean` | خیر | `true` | آیا رکورد فعال است | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((service_type = ANY (ARRAY['hotel'::text, 'flight'::text, 'train'::text, 'tour'::text, 'car_rental'::text, 'official_info'::text, 'other'::text])))`
- `CHECK ((target_url ~ '^https?://'::text))`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE SET NULL`
- `PRIMARY KEY (external_link_id)`

## integration.outbound_clicks

دامنه: ارتباطات خارجی؛ outbound_clicks (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: سرویس داخلی؛ نه CRUD عمومی.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `outbound_click_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ کلیک ـ خروجی؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `external_link_id` | `uuid` | خیر | ندارد | شناسه ـ پیوند ـ خارجی؛ ارجاع به integration.external_links(external_link_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `user_id` | `uuid` | بله | ندارد | شناسه ـ کاربر؛ ارجاع به identity.users(user_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `trip_id` | `uuid` | بله | ندارد | شناسه ـ سفر؛ ارجاع به travel.trips(trip_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `recommendation_id` | `uuid` | بله | ندارد | شناسه ـ پیشنهاد؛ ارجاع به recommendation.recommendations(recommendation_id) ON DELETE SET NULL | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `session_id` | `uuid` | بله | ندارد | شناسه نشست مرتبط؛ نه توکن نشست | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `clicked_at` | `timestamp with time zone` | خیر | `now()` | زمان کلیک | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `metadata` | `jsonb` | خیر | `[redacted string default]` | فراداده JSON؛ کلیدها تابع قرارداد مصرف‌کننده‌اند | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `FOREIGN KEY (external_link_id) REFERENCES integration.external_links(external_link_id) ON DELETE RESTRICT`
- `FOREIGN KEY (recommendation_id) REFERENCES recommendation.recommendations(recommendation_id) ON DELETE SET NULL`
- `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `PRIMARY KEY (outbound_click_id)`
