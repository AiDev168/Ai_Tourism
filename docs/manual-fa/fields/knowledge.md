# فرهنگ فیلدهای دانش مقاصد (knowledge)

[فهرست اصلی](../README.md). مبنا cab603a7d40cfa35dd20de2ffb12a336d84f56ff؛ metadata پایلوت 0026 + DDL 0027، نه snapshot زنده. NULL قید SQL است نه الزام فرم. پیش‌فرض redacted پالایش شده؛ مقدار را حدس نزنید. توضیح خوانش نام/نوع اثبات معنای تجاری نیست. اطلاعات شخصی، رمز، توکن و ممیزی را مستقیم تغییر ندهید.

[metadata](../../database/rehearsed-schema-0026/catalog_metadata_snapshot.json) | [glossary](../../database/field_descriptions.json) | [DDL 0027](../../../engineering/pilot/sql/027_server_ai_provider_admin.sql) | [مرجع 0027](../../database/rehearsed-schema-0027/PROVIDER_ADMIN_FIELD_REFERENCE.md)

## knowledge.active_embedding_spaces

دامنه: دانش مقاصد؛ active_embedding_spaces (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `embedding_space_id` | `uuid` | بله | ندارد | شناسه ـ فضا ـ بردار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `space_key` | `text` | بله | ندارد | کلید ـ فضا | نمای مشتق؛ بدون ورود | View؛ lineage |
| `provider_type` | `text` | بله | ندارد | نوع ـ ارائه‌دهنده | نمای مشتق؛ بدون ورود | View؛ lineage |
| `provider_name` | `text` | بله | ندارد | نام ـ ارائه‌دهنده | نمای مشتق؛ بدون ورود | View؛ lineage |
| `model_name` | `text` | بله | ندارد | نام ـ مدل | نمای مشتق؛ بدون ورود | View؛ lineage |
| `model_revision` | `text` | بله | ندارد | بازبینی ـ مدل | نمای مشتق؛ بدون ورود | View؛ lineage |
| `vector_dimension` | `smallint` | بله | ندارد | بعد ـ بردار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `similarity_metric` | `text` | بله | ندارد | معیار ـ شباهت | نمای مشتق؛ بدون ورود | View؛ lineage |
| `preprocessing_version` | `text` | بله | ندارد | نسخه ـ پیش‌پردازش | نمای مشتق؛ بدون ورود | View؛ lineage |
| `lifecycle_status` | `text` | بله | ندارد | وضعیت ـ چرخه عمر | نمای مشتق؛ بدون ورود | View؛ lineage |
| `created_at` | `timestamp with time zone` | بله | ندارد | زمان ایجاد رکورد | نمای مشتق؛ بدون ورود | View؛ lineage |

[مرجع lineage](../../database/architecture-usage/view_column_lineage.csv)؛ تطبیق هر خروجی با مبدأ لازم است.

## knowledge.catalogue_publication_events

دامنه: دانش مقاصد؛ catalogue_publication_events (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `publication_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ انتشار؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `candidate_id` | `uuid` | خیر | ندارد | شناسه ـ نامزد؛ ارجاع به knowledge.destination_candidates(candidate_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `evidence_ids` | `jsonb` | خیر | ندارد | شناسه‌های شواهد مرتبط با انتشار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `reviewer_user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر ـ بازبین؛ ارجاع به identity.users(user_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `policy_version` | `text` | خیر | ندارد | نسخه سیاست مربوط به رضایت یا تصمیم | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `published_at` | `timestamp with time zone` | خیر | `now()` | زمان انتشار رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((jsonb_typeof(evidence_ids) = 'array'::text) AND (jsonb_array_length(evidence_ids) >= 4)))`
- `CHECK (((length(btrim(policy_version)) >= 1) AND (length(btrim(policy_version)) <= 80)))`
- `FOREIGN KEY (candidate_id) REFERENCES knowledge.destination_candidates(candidate_id) ON DELETE RESTRICT`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `PRIMARY KEY (publication_id)`
- `UNIQUE (candidate_id)`
- `UNIQUE (destination_id)`

## knowledge.chunk_embeddings

دامنه: دانش مقاصد؛ chunk_embeddings (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `chunk_embedding_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ بردار ـ قطعه متن؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `chunk_id` | `uuid` | خیر | ندارد | شناسه ـ قطعه متن؛ ارجاع به knowledge.knowledge_chunks(chunk_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `embedding_space_id` | `uuid` | خیر | ندارد | شناسه ـ فضا ـ بردار؛ ارجاع به knowledge.embedding_spaces(embedding_space_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `embedding` | `vector` | خیر | ندارد | بردار عددی تولیدشده برای بازیابی متنی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `FOREIGN KEY (chunk_id) REFERENCES knowledge.knowledge_chunks(chunk_id) ON DELETE CASCADE`
- `FOREIGN KEY (embedding_space_id) REFERENCES knowledge.embedding_spaces(embedding_space_id) ON DELETE CASCADE`
- `PRIMARY KEY (chunk_embedding_id)`
- `UNIQUE (chunk_id, embedding_space_id)`

## knowledge.culinary_item_sources

دامنه: دانش مقاصد؛ culinary_item_sources (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `item_source_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ منبع ـ قلم؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `item_id` | `uuid` | خیر | ندارد | شناسه ـ قلم؛ ارجاع به knowledge.culinary_knowledge_items(item_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `claim_key` | `text` | خیر | ندارد | کلید گزاره یا ویژگی مورد استناد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_key` | `text` | خیر | ندارد | کلید منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_id` | `bigint` | بله | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `source_name` | `text` | خیر | ندارد | نام منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_url` | `text` | خیر | ندارد | نشانی منبع این داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_license` | `text` | بله | ندارد | مجوز استفاده از منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_role` | `text` | خیر | ندارد | نقش منبع در پشتیبانی داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `evidence_note` | `text` | بله | ندارد | یادداشت توضیح شاهد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `retrieved_at` | `timestamp with time zone` | بله | ندارد | زمان دریافت اطلاعات منبع | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_from` | `timestamp with time zone` | بله | ندارد | شروع اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_until` | `timestamp with time zone` | بله | ندارد | پایان اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((length(btrim(claim_key)) > 0) AND (length(btrim(source_key)) > 0)))`
- `CHECK (((length(btrim(source_name)) > 0) AND (length(btrim(source_role)) > 0)))`
- `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- `CHECK ((source_url ~ '^https?://[^[:space:]]+$'::text))`
- `FOREIGN KEY (item_id) REFERENCES knowledge.culinary_knowledge_items(item_id) ON DELETE CASCADE`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (item_source_id)`
- `UNIQUE (item_id, claim_key, source_key, source_role)`

## knowledge.culinary_knowledge_items

دامنه: دانش مقاصد؛ culinary_knowledge_items (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `item_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ قلم؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `item_key` | `text` | خیر | ندارد | کلید قلم دانش | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `record_key` | `text` | خیر | ندارد | کلید رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `dataset_import_batch_id` | `uuid` | خیر | ندارد | شناسه ـ دسته ـ ورود ـ مجموعه داده؛ ارجاع به operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `record_action` | `text` | خیر | ندارد | نوع عملیات پیشنهادی یا ثبت‌شده بر رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `legacy_destination_id` | `bigint` | بله | ندارد | ارجاع به knowledge.destinations(destination_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `category` | `text` | خیر | ندارد | دسته‌بندی قلم | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `names_by_locale` | `jsonb` | خیر | ندارد | نام‌ها به تفکیک زبان | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `descriptions_by_locale` | `jsonb` | خیر | ندارد | توضیحات به تفکیک زبان | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `claims` | `jsonb` | خیر | ندارد | گزاره‌های ساخت‌یافته؛ کلیدها از قرارداد دامنه | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `payload` | `jsonb` | خیر | ندارد | محتوای ساخت‌یافته رکورد یا پیشنهاد؛ قرارداد JSON مستقل است | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `payload_sha256` | `character(64)` | خیر | ندارد | اثر انگشت SHA-256 محتوای ساخت‌یافته | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `review_status` | `text` | خیر | `[redacted string default]` | وضعیت بازبینی رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `record_origin` | `text` | خیر | `[redacted string default]` | منشأ رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `verification_status` | `text` | خیر | `[redacted string default]` | وضعیت راستی‌آزمایی یا احراز | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `approval_confidence` | `numeric(5,4)` | خیر | `0` | اطمینان مرتبط با تأیید؛ مقیاس طبق قید و قرارداد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `publishable` | `boolean` | خیر | `false` | نشان واجد شرایط انتشار بودن؛ نه انتشار بالفعل | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `published_at` | `timestamp with time zone` | بله | ندارد | زمان انتشار رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((approval_confidence >= (0)::numeric) AND (approval_confidence <= (1)::numeric)))`
- `CHECK ((category ~ '^[a-z][a-z0-9_]{1,63}$'::text))`
- `CHECK (((length(btrim(item_key)) > 0) AND (length(btrim(record_key)) > 0)))`
- `CHECK ((((record_action = 'stage_existing_record_enrichment_review'::text) AND (legacy_destination_id IS NOT NULL)) OR ((record_action = 'stage_new_non_spatial_candidate_review'::text) AND (legacy_destination_id IS NULL))))`
- `CHECK ((((review_status = 'approved'::text) AND (publishable = true) AND (verification_status = 'verified'::text) AND (approval_confidence > (0)::numeric) AND (published_at IS NOT NULL)) OR ((review_status <> 'approved'::text) AND (publishable = false) AND (published_at IS NULL) AND (approval_confidence = (0)::numeric))))`
- `CHECK (((jsonb_typeof(claims) = 'array'::text) AND (jsonb_array_length(claims) > 0)))`
- `CHECK (((jsonb_typeof(descriptions_by_locale) = 'object'::text) AND (descriptions_by_locale ?& ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text]) AND (jsonb_typeof((descriptions_by_locale -> 'fa-IR'::text)) = 'string'::text) AND (jsonb_typeof((descriptions_by_locale -> 'en-US'::text)) = 'string'::text) AND (jsonb_typeof((descriptions_by_locale -> 'ar'::text)) = 'string'::text) AND (length(btrim((descriptions_by_locale ->> 'fa-IR'::text))) > 0) AND (length(btrim((descriptions_by_locale ->> 'en-US'::text))) > 0) AND (length(btrim((descriptions_by_locale ->> 'ar'::text))) > 0)))`
- `CHECK ((is_synthetic = false))`
- `CHECK (((jsonb_typeof(names_by_locale) = 'object'::text) AND (names_by_locale ?& ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text]) AND (jsonb_typeof((names_by_locale -> 'fa-IR'::text)) = 'string'::text) AND (jsonb_typeof((names_by_locale -> 'en-US'::text)) = 'string'::text) AND (jsonb_typeof((names_by_locale -> 'ar'::text)) = 'string'::text) AND (length(btrim((names_by_locale ->> 'fa-IR'::text))) > 0) AND (length(btrim((names_by_locale ->> 'en-US'::text))) > 0) AND (length(btrim((names_by_locale ->> 'ar'::text))) > 0)))`
- `CHECK ((jsonb_typeof(payload) = 'object'::text))`
- `CHECK ((payload_sha256 ~ '^[0-9a-f]{64}$'::text))`
- `CHECK ((record_action = ANY (ARRAY['stage_existing_record_enrichment_review'::text, 'stage_new_non_spatial_candidate_review'::text])))`
- `CHECK ((record_origin = 'verified_external'::text))`
- `CHECK ((review_status = ANY (ARRAY['pending_review'::text, 'approved'::text, 'rejected'::text, 'withdrawn'::text])))`
- `CHECK ((verification_status = ANY (ARRAY['pending'::text, 'verified'::text, 'rejected'::text, 'stale'::text])))`
- `FOREIGN KEY (dataset_import_batch_id) REFERENCES operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT`
- `FOREIGN KEY (legacy_destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- `PRIMARY KEY (item_id)`
- `UNIQUE (item_key)`

## knowledge.destination_access_points

دامنه: دانش مقاصد؛ destination_access_points (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `access_point_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ نقطه ـ دسترسی؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `point` | `geometry(Point,4326)` | بله | ندارد | نقطه مکانی ثبت‌شده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `point_role` | `text` | خیر | ندارد | نقش نقطه مکانی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `label` | `text` | بله | ندارد | عنوان کوتاه | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `accessibility_state` | `text` | خیر | `[redacted string default]` | وضعیت دسترس‌پذیری | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_id` | `bigint` | بله | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `source_url` | `text` | بله | ندارد | نشانی منبع این داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `evidence_note` | `text` | بله | ندارد | یادداشت توضیح شاهد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `coordinate_precision_m` | `numeric(8,2)` | بله | ندارد | دقت مکانی گزارش‌شده بر حسب متر | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `status` | `text` | خیر | `[redacted string default]` | وضعیت | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `observed_at` | `timestamp with time zone` | بله | ندارد | زمان مشاهده واقعیت | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `reviewed_at` | `timestamp with time zone` | بله | ندارد | زمان بازبینی | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((accessibility_state = ANY (ARRAY['known'::text, 'unknown'::text, 'not_applicable'::text, 'conflicting'::text])))`
- `CHECK (((status <> 'approved'::text) OR ((point IS NOT NULL) AND ((source_id IS NOT NULL) OR (source_url IS NOT NULL)))))`
- `CHECK (((coordinate_precision_m IS NULL) OR (coordinate_precision_m > (0)::numeric)))`
- `CHECK ((point_role = ANY (ARRAY['visitor_entrance'::text, 'visitor_access'::text, 'trailhead'::text, 'boat_landing'::text, 'parking_access'::text, 'other'::text])))`
- `CHECK ((status = ANY (ARRAY['needs_review'::text, 'approved'::text, 'withdrawn'::text])))`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (access_point_id)`

## knowledge.destination_aliases

دامنه: دانش مقاصد؛ نام‌های جایگزین ـ مقصد (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `alias_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ نام جایگزین؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `alias` | `text` | خیر | ندارد | نام جایگزین که ممکن است در جستجو به کار رود | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `normalized_key` | `text` | خیر | ندارد | کلید نرمال‌شده برای تطبیق نام‌ها | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `locale` | `text` | بله | ندارد | کد زبان و منطقه متن | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `alias_type` | `text` | خیر | ندارد | نوع نام جایگزین | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_id` | `bigint` | بله | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `source_url` | `text` | بله | ندارد | نشانی منبع این داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `review_status` | `text` | خیر | `[redacted string default]` | وضعیت بازبینی رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((length(btrim(alias)) >= 1) AND (length(btrim(alias)) <= 320)))`
- `CHECK ((alias_type = ANY (ARRAY['source_spelling'::text, 'local_name'::text, 'transliteration'::text, 'historical'::text, 'other'::text])))`
- `CHECK (((source_id IS NOT NULL) OR (source_url IS NOT NULL)))`
- `CHECK (((locale IS NULL) OR (locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text, 'und'::text]))))`
- `CHECK (((length(btrim(normalized_key)) >= 1) AND (length(btrim(normalized_key)) <= 400)))`
- `CHECK ((review_status = ANY (ARRAY['needs_review'::text, 'approved'::text, 'rejected'::text])))`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (alias_id)`

## knowledge.destination_candidate_evidence

دامنه: دانش مقاصد؛ شاهد ـ نامزد ـ مقصد (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `evidence_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ شاهد؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `candidate_id` | `uuid` | خیر | ندارد | شناسه ـ نامزد؛ ارجاع به knowledge.destination_candidates(candidate_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `source_id` | `bigint` | خیر | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | فرم/API دامنه؛ راهنمای ورود | قید FK |
| `field_key` | `text` | خیر | ندارد | کلید یکی از identity/province/city/coordinates/description که شاهد برای آن ثبت می‌شود؛ CandidateEvidenceInput | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `claim_value` | `text` | خیر | ندارد | مقدار گزاره‌ای که ثبت می‌شود؛ ۱–۸۰۰۰ نویسه؛ CandidateEvidenceInput | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `source_url` | `text` | خیر | ندارد | نشانی منبع این داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `evidence_excerpt` | `text` | خیر | ندارد | گزیده شاهد؛ ۱–۶۰۰ نویسه؛ CandidateEvidenceInput | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `retrieved_at` | `timestamp with time zone` | خیر | ندارد | زمان دریافت شاهد؛ datetime؛ CandidateEvidenceInput | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `reviewer_user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر ـ بازبین؛ ارجاع به identity.users(user_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `policy_version` | `text` | خیر | ندارد | نسخه سیاست شاهد؛ پیش‌فرض API candidate-field-evidence-v1 | فرم مستقیم احراز نشده | قرارداد API: catalogue_review.py |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((length(btrim(claim_value)) >= 1) AND (length(btrim(claim_value)) <= 8000)))`
- `CHECK (((length(btrim(evidence_excerpt)) >= 1) AND (length(btrim(evidence_excerpt)) <= 600)))`
- `CHECK ((field_key = ANY (ARRAY['identity'::text, 'province'::text, 'city'::text, 'coordinates'::text, 'description'::text])))`
- `CHECK (((length(btrim(policy_version)) >= 1) AND (length(btrim(policy_version)) <= 80)))`
- `CHECK ((source_url ~ '^https://'::text))`
- `FOREIGN KEY (candidate_id) REFERENCES knowledge.destination_candidates(candidate_id) ON DELETE RESTRICT`
- `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (evidence_id)`
- `UNIQUE (candidate_id, source_id, field_key, claim_value, source_url)`

## knowledge.destination_candidate_reviews

دامنه: دانش مقاصد؛ destination_candidate_reviews (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `review_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ بازبینی؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `candidate_id` | `uuid` | خیر | ندارد | شناسه ـ نامزد؛ ارجاع به knowledge.destination_candidates(candidate_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `identity_relation` | `text` | خیر | ندارد | رابطه هویتی: same_entity، part_of_or_within، nearby_distinct یا unresolved؛ ReviewDecision | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `target_destination_id` | `bigint` | بله | ندارد | شناسه ـ مقصد ـ هدف؛ ارجاع به knowledge.destinations(destination_id) ON DELETE RESTRICT | فرم/API دامنه؛ راهنمای ورود | قید FK |
| `decision` | `text` | خیر | ندارد | تصمیم accept/approve_new_identity/reject/defer/request_evidence؛ ReviewDecision | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `reason` | `text` | خیر | ندارد | دلیل تصمیم؛ ۱–۲۰۰۰ نویسه؛ ReviewDecision | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `evidence_refs` | `jsonb` | خیر | `[redacted string default]` | ارجاعات شاهد؛ حداکثر ۳۰؛ ReviewDecision | فرم مستقیم احراز نشده | قرارداد API: catalogue_review.py |
| `reviewer_user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر ـ بازبین؛ ارجاع به identity.users(user_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `policy_version` | `text` | خیر | ندارد | نسخه سیاست؛ پیش‌فرض API catalogue-review-v1 | فرم مستقیم احراز نشده | قرارداد API: catalogue_review.py |
| `decided_at` | `timestamp with time zone` | خیر | `now()` | زمان ثبت تصمیم | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((decision <> 'accept'::text) OR ((identity_relation <> 'unresolved'::text) AND (target_destination_id IS NOT NULL) AND (jsonb_array_length(evidence_refs) > 0))))`
- `CHECK (((decision <> ALL (ARRAY['reject'::text, 'defer'::text, 'request_evidence'::text])) OR (target_destination_id IS NULL)))`
- `CHECK (((decision <> 'approve_new_identity'::text) OR ((identity_relation = 'unresolved'::text) AND (target_destination_id IS NULL) AND (jsonb_array_length(evidence_refs) > 0))))`
- `CHECK ((decision = ANY (ARRAY['accept'::text, 'approve_new_identity'::text, 'reject'::text, 'defer'::text, 'request_evidence'::text])))`
- `CHECK ((jsonb_typeof(evidence_refs) = 'array'::text))`
- `CHECK ((identity_relation = ANY (ARRAY['same_entity'::text, 'part_of_or_within'::text, 'nearby_distinct'::text, 'unresolved'::text])))`
- `CHECK (((length(btrim(policy_version)) >= 1) AND (length(btrim(policy_version)) <= 80)))`
- `CHECK (((length(btrim(reason)) >= 1) AND (length(btrim(reason)) <= 2000)))`
- `FOREIGN KEY (candidate_id) REFERENCES knowledge.destination_candidates(candidate_id) ON DELETE RESTRICT`
- `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (target_destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- `PRIMARY KEY (review_id)`

## knowledge.destination_candidates

دامنه: دانش مقاصد؛ destination_candidates (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `candidate_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ نامزد؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `candidate_kind` | `text` | خیر | `[redacted string default]` | نوع نامزد ورودی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `dataset_import_batch_id` | `uuid` | خیر | ندارد | شناسه ـ دسته ـ ورود ـ مجموعه داده؛ ارجاع به operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `file_id` | `uuid` | خیر | ندارد | شناسه ـ فایل؛ ارجاع به operations.dataset_import_files(file_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `source_file_sha256` | `character(64)` | خیر | ندارد | اثر انگشت فایل منبع | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_record_key` | `text` | خیر | ندارد | کلید رکورد در فایل یا منبع مبدأ | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `row_sha256` | `character(64)` | خیر | ندارد | اثر انگشت سطر ورودی | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `raw_record` | `jsonb` | خیر | ندارد | رکورد خام ورودی پیش از پردازش | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `raw_name` | `text` | بله | ندارد | نام خام منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `raw_province` | `text` | بله | ندارد | استان خام منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `raw_city` | `text` | بله | ندارد | شهر خام منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `raw_coordinate_role` | `text` | بله | ندارد | نقش مختصات گزارش‌شده در منبع خام | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `proposed_destination_key` | `text` | بله | ندارد | کلید پیشنهادی مقصد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `proposed_name_fa` | `text` | بله | ندارد | نام فارسی پیشنهادی مقصد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `proposed_destination_type` | `text` | بله | ندارد | نوع پیشنهادی مقصد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `proposed_latitude` | `double precision` | بله | ندارد | عرض جغرافیایی پیشنهادی به درجه | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `proposed_longitude` | `double precision` | بله | ندارد | طول جغرافیایی پیشنهادی به درجه | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `canonical_destination_id` | `bigint` | بله | ندارد | شناسه ـ مقصد ـ معیار؛ ارجاع به knowledge.destinations(destination_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `candidate_status` | `text` | خیر | `[redacted string default]` | وضعیت پردازش نامزد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((candidate_kind = ANY (ARRAY['destination_identity'::text, 'discovery_lead'::text])))`
- `CHECK ((candidate_status = ANY (ARRAY['needs_review'::text, 'in_review'::text, 'resolved_existing'::text, 'approved_new_identity'::text, 'rejected'::text, 'conflict'::text])))`
- `CHECK (((proposed_latitude IS NULL) = (proposed_longitude IS NULL)))`
- `CHECK (((proposed_latitude IS NULL) OR ((proposed_latitude >= ('-90'::integer)::double precision) AND (proposed_latitude <= (90)::double precision))))`
- `CHECK (((proposed_longitude IS NULL) OR ((proposed_longitude >= ('-180'::integer)::double precision) AND (proposed_longitude <= (180)::double precision))))`
- `CHECK ((jsonb_typeof(raw_record) = 'object'::text))`
- `CHECK ((row_sha256 ~ '^[a-f0-9]{64}$'::text))`
- `CHECK ((source_file_sha256 ~ '^[a-f0-9]{64}$'::text))`
- `CHECK (((length(btrim(source_record_key)) >= 1) AND (length(btrim(source_record_key)) <= 512)))`
- `FOREIGN KEY (canonical_destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- `FOREIGN KEY (dataset_import_batch_id) REFERENCES operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT`
- `FOREIGN KEY (file_id) REFERENCES operations.dataset_import_files(file_id) ON DELETE RESTRICT`
- `PRIMARY KEY (candidate_id)`
- `UNIQUE (dataset_import_batch_id, source_file_sha256, source_record_key)`

## knowledge.destination_categories

دامنه: دانش مقاصد؛ destination_categories (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `category_id` | `bigint` | خیر | `[redacted string default]` | شناسه ـ دسته؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `category_key` | `text` | خیر | ندارد | کلید دسته‌بندی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `name_fa` | `text` | خیر | ندارد | نام فارسی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `description` | `text` | بله | ندارد | شرح قابل خواندن | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_active` | `boolean` | خیر | `true` | آیا رکورد فعال است | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `sort_order` | `smallint` | خیر | `0` | ترتیب نمایش | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `PRIMARY KEY (category_id)`
- `UNIQUE (category_key)`

## knowledge.destination_category_map

دامنه: دانش مقاصد؛ destination_category_map (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `category_id` | `bigint` | خیر | ندارد | شناسه ـ دسته؛ ارجاع به knowledge.destination_categories(category_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `mapping_source` | `text` | خیر | `[redacted string default]` | منشأ ارتباط مقصد و دسته | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `FOREIGN KEY (category_id) REFERENCES knowledge.destination_categories(category_id) ON DELETE RESTRICT`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE`
- `PRIMARY KEY (destination_id, category_id)`

## knowledge.destination_claim_evidence

دامنه: دانش مقاصد؛ شاهد ـ گزاره ـ مقصد (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `claim_evidence_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ شاهد ـ گزاره؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `document_id` | `uuid` | خیر | ندارد | شناسه ـ سند؛ ارجاع به knowledge.knowledge_documents(document_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `chunk_id` | `uuid` | خیر | ندارد | شناسه قطعه متن مرتبط؛ قیود رابطه را بررسی کنید | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `claim_key` | `text` | خیر | ندارد | کلید گزاره یا ویژگی مورد استناد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `locale` | `text` | خیر | ندارد | کد زبان و منطقه متن | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `corpus` | `text` | خیر | `[redacted string default]` | مجموعه متنی که شاهد در آن قرار دارد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `content_hash` | `character(64)` | خیر | ندارد | اثر انگشت محتوا | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_id` | `bigint` | خیر | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `source_name` | `text` | خیر | ندارد | نام منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_url` | `text` | خیر | ندارد | نشانی منبع این داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_role` | `text` | خیر | ندارد | نقش منبع در پشتیبانی داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_license` | `text` | بله | ندارد | مجوز استفاده از منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `retrieved_at` | `timestamp with time zone` | بله | ندارد | زمان دریافت اطلاعات منبع | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_from` | `timestamp with time zone` | بله | ندارد | شروع اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_until` | `timestamp with time zone` | بله | ندارد | پایان اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `review_status` | `text` | خیر | `[redacted string default]` | وضعیت بازبینی رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `verification_status` | `text` | خیر | `[redacted string default]` | وضعیت راستی‌آزمایی یا احراز | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `published_at` | `timestamp with time zone` | بله | ندارد | زمان انتشار رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `revoked_at` | `timestamp with time zone` | بله | ندارد | زمان لغو | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- `CHECK (((review_status = 'approved'::text) = (published_at IS NOT NULL)))`
- `CHECK (((review_status <> 'approved'::text) OR ((verification_status = 'verified'::text) AND (is_synthetic = false))))`
- `CHECK (((verification_status = 'revoked'::text) = (revoked_at IS NOT NULL)))`
- `CHECK (((length(btrim(claim_key)) >= 1) AND (length(btrim(claim_key)) <= 240)))`
- `CHECK ((content_hash ~ '^[0-9a-f]{64}$'::text))`
- `CHECK ((corpus = 'spatial_destinations'::text))`
- `CHECK ((locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text])))`
- `CHECK ((review_status = ANY (ARRAY['needs_review'::text, 'approved'::text, 'rejected'::text])))`
- `CHECK (((length(btrim(source_name)) >= 1) AND (length(btrim(source_name)) <= 500)))`
- `CHECK (((length(btrim(source_role)) >= 1) AND (length(btrim(source_role)) <= 64)))`
- `CHECK ((source_url ~ '^https://[^[:space:]]+$'::text))`
- `CHECK ((verification_status = ANY (ARRAY['pending'::text, 'verified'::text, 'revoked'::text])))`
- `FOREIGN KEY (chunk_id, document_id) REFERENCES knowledge.knowledge_chunks(chunk_id, document_id) ON DELETE CASCADE`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE`
- `FOREIGN KEY (document_id) REFERENCES knowledge.knowledge_documents(document_id) ON DELETE CASCADE`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (claim_evidence_id)`
- `UNIQUE (chunk_id, claim_key, locale, source_id)`

## knowledge.destination_enrichment_proposal_sources

دامنه: دانش مقاصد؛ destination_enrichment_proposal_sources (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `proposal_source_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ منبع ـ پیشنهاد تکمیل؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `proposal_id` | `uuid` | خیر | ندارد | شناسه ـ پیشنهاد تکمیل؛ ارجاع به knowledge.destination_enrichment_proposals(proposal_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `claim_key` | `text` | خیر | ندارد | کلید گزاره یا ویژگی مورد استناد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_key` | `text` | خیر | ندارد | کلید منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_id` | `bigint` | بله | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `source_name` | `text` | خیر | ندارد | نام منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_url` | `text` | خیر | ندارد | نشانی منبع این داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_license` | `text` | بله | ندارد | مجوز استفاده از منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_role` | `text` | خیر | ندارد | نقش منبع در پشتیبانی داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `evidence_note` | `text` | بله | ندارد | یادداشت توضیح شاهد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `retrieved_at` | `timestamp with time zone` | بله | ندارد | زمان دریافت اطلاعات منبع | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_from` | `timestamp with time zone` | بله | ندارد | شروع اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_until` | `timestamp with time zone` | بله | ندارد | پایان اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((length(btrim(claim_key)) > 0) AND (length(btrim(source_key)) > 0)))`
- `CHECK (((length(btrim(source_name)) > 0) AND (length(btrim(source_role)) > 0)))`
- `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- `CHECK ((source_url ~ '^https?://[^[:space:]]+$'::text))`
- `FOREIGN KEY (proposal_id) REFERENCES knowledge.destination_enrichment_proposals(proposal_id) ON DELETE CASCADE`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (proposal_source_id)`
- `UNIQUE (proposal_id, claim_key, source_key, source_role)`

## knowledge.destination_enrichment_proposals

دامنه: دانش مقاصد؛ destination_enrichment_proposals (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `proposal_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ پیشنهاد تکمیل؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `proposal_key` | `text` | خیر | ندارد | کلید پیشنهاد غنی‌سازی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `dataset_import_batch_id` | `uuid` | خیر | ندارد | شناسه ـ دسته ـ ورود ـ مجموعه داده؛ ارجاع به operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `target_destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد ـ هدف؛ ارجاع به knowledge.destinations(destination_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `target_destination_key` | `text` | خیر | ندارد | کلید مقصدی که پیشنهاد درباره آن است | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `record_action` | `text` | خیر | ندارد | نوع عملیات پیشنهادی یا ثبت‌شده بر رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `payload` | `jsonb` | خیر | ندارد | محتوای ساخت‌یافته رکورد یا پیشنهاد؛ قرارداد JSON مستقل است | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `payload_sha256` | `character(64)` | خیر | ندارد | اثر انگشت SHA-256 محتوای ساخت‌یافته | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `review_status` | `text` | خیر | `[redacted string default]` | وضعیت بازبینی رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `record_origin` | `text` | خیر | `[redacted string default]` | منشأ رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `verification_status` | `text` | خیر | `[redacted string default]` | وضعیت راستی‌آزمایی یا احراز | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `approval_confidence` | `numeric(5,4)` | خیر | `0` | اطمینان مرتبط با تأیید؛ مقیاس طبق قید و قرارداد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `publishable` | `boolean` | خیر | `false` | نشان واجد شرایط انتشار بودن؛ نه انتشار بالفعل | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((approval_confidence = (0)::numeric))`
- `CHECK ((is_synthetic = false))`
- `CHECK ((jsonb_typeof(payload) = 'object'::text))`
- `CHECK ((payload_sha256 ~ '^[0-9a-f]{64}$'::text))`
- `CHECK ((length(btrim(proposal_key)) > 0))`
- `CHECK ((publishable = false))`
- `CHECK ((record_action = 'stage_existing_record_enrichment_review'::text))`
- `CHECK ((record_origin = 'verified_external'::text))`
- `CHECK ((review_status = 'needs_review'::text))`
- `CHECK ((length(btrim(target_destination_key)) > 0))`
- `CHECK ((verification_status = 'pending'::text))`
- `FOREIGN KEY (dataset_import_batch_id) REFERENCES operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT`
- `FOREIGN KEY (target_destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- `PRIMARY KEY (proposal_id)`
- `UNIQUE (proposal_key)`

## knowledge.destination_localizations

دامنه: دانش مقاصد؛ destination_localizations (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `locale` | `text` | خیر | ندارد | کد زبان و منطقه متن | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `display_name` | `text` | خیر | ندارد | نام قابل نمایش برای شخص، مقصد یا خدمت | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `short_description` | `text` | بله | ندارد | توضیح کوتاه | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `description` | `text` | بله | ندارد | شرح قابل خواندن | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `translation_status` | `text` | خیر | `[redacted string default]` | وضعیت ترجمه | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `content_status` | `text` | خیر | `[redacted string default]` | وضعیت محتوای متنی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `content_version` | `integer` | خیر | `1` | نسخه محتوا | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `reviewed_at` | `timestamp with time zone` | بله | ندارد | زمان بازبینی | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((content_status = ANY (ARRAY['draft'::text, 'approved'::text, 'rejected'::text, 'withdrawn'::text])))`
- `CHECK ((content_version > 0))`
- `CHECK (((length(btrim(display_name)) >= 1) AND (length(btrim(display_name)) <= 240)))`
- `CHECK ((locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text])))`
- `CHECK ((translation_status = ANY (ARRAY['draft'::text, 'editor_reviewed'::text, 'native_review_required'::text, 'blocked'::text])))`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE`
- `PRIMARY KEY (destination_id, locale)`

## knowledge.destination_operational_assertions

دامنه: دانش مقاصد؛ destination_operational_assertions (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `assertion_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ واقعیت ثبت‌شده؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `access_point_id` | `uuid` | بله | ندارد | شناسه ـ نقطه ـ دسترسی؛ ارجاع به knowledge.destination_access_points(access_point_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `fact_type` | `text` | خیر | ندارد | نوع واقعیت عملیاتی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `value_state` | `text` | خیر | ندارد | وضعیت معلوم بودن مقدار واقعیت | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `value` | `jsonb` | بله | ندارد | مقدار واقعیت؛ تفسیر تابع نوع واقعیت | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `value_schema_version` | `text` | خیر | ندارد | نسخه قرارداد ساختار مقدار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `freshness_policy_key` | `text` | خیر | ندارد | کلید سیاست تازگی واقعیت | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_id` | `bigint` | بله | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `source_url` | `text` | بله | ندارد | نشانی منبع این داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `evidence_note` | `text` | بله | ندارد | یادداشت توضیح شاهد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `observed_at` | `timestamp with time zone` | بله | ندارد | زمان مشاهده واقعیت | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_from` | `timestamp with time zone` | بله | ندارد | شروع اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_until` | `timestamp with time zone` | بله | ندارد | پایان اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `review_status` | `text` | خیر | `[redacted string default]` | وضعیت بازبینی رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `recorded_by` | `uuid` | بله | ندارد | توسط/بر اساس ـ ثبت؛ ارجاع به identity.users(user_id) ON DELETE RESTRICT | فرم مستقیم احراز نشده | قید FK |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((value_state = 'known'::text) = (value IS NOT NULL)))`
- `CHECK (((value_state <> 'known'::text) OR (observed_at IS NOT NULL)))`
- `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- `CHECK (((value_state <> 'known'::text) OR (source_id IS NOT NULL) OR (source_url IS NOT NULL)))`
- `CHECK ((fact_type = ANY (ARRAY['opening_hours'::text, 'access_status'::text, 'access_restriction'::text, 'fee'::text, 'permit'::text, 'hazard'::text, 'seasonality'::text])))`
- `CHECK ((review_status = ANY (ARRAY['needs_review'::text, 'approved'::text, 'rejected'::text, 'withdrawn'::text])))`
- `CHECK ((value_state = ANY (ARRAY['known'::text, 'unknown'::text, 'not_applicable'::text, 'conflicting'::text, 'temporarily_unavailable'::text])))`
- `FOREIGN KEY (access_point_id) REFERENCES knowledge.destination_access_points(access_point_id) ON DELETE RESTRICT`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE`
- `FOREIGN KEY (recorded_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (assertion_id)`

## knowledge.destination_sources

دامنه: دانش مقاصد؛ destination_sources (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `source_id` | `bigint` | خیر | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `source_role` | `text` | خیر | `[redacted string default]` | نقش منبع در پشتیبانی داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `evidence_note` | `text` | بله | ندارد | یادداشت توضیح شاهد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `retrieved_at` | `timestamp with time zone` | بله | ندارد | زمان دریافت اطلاعات منبع | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_from` | `timestamp with time zone` | بله | ندارد | شروع اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_until` | `timestamp with time zone` | بله | ندارد | پایان اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((source_role = ANY (ARRAY['primary'::text, 'secondary'::text, 'verification'::text, 'discovery'::text])))`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (destination_id, source_id)`

## knowledge.destination_tags

دامنه: دانش مقاصد؛ destination_tags (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `tag` | `text` | خیر | ندارد | برچسب موضوعی مقصد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE`
- `PRIMARY KEY (destination_id, tag)`

## knowledge.destination_visit_duration_evidence

دامنه: دانش مقاصد؛ شاهد ـ مدت ـ بازدید ـ مقصد (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `duration_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ مدت؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `destination_id` | `bigint` | خیر | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `source_id` | `bigint` | خیر | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `minimum_minutes` | `integer` | بله | ندارد | حداقل مدت بازدید به دقیقه | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `maximum_minutes` | `integer` | بله | ندارد | حداکثر مدت بازدید به دقیقه | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `visit_context` | `text` | خیر | ندارد | شرایط یا زمینه بازدید | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `evidence_note` | `text` | خیر | ندارد | یادداشت توضیح شاهد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_url` | `text` | بله | ندارد | نشانی منبع این داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `observed_at` | `timestamp with time zone` | خیر | ندارد | زمان مشاهده واقعیت | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_from` | `timestamp with time zone` | بله | ندارد | شروع اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_until` | `timestamp with time zone` | بله | ندارد | پایان اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `review_status` | `text` | خیر | `[redacted string default]` | وضعیت بازبینی رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((minimum_minutes IS NOT NULL) OR (maximum_minutes IS NOT NULL)))`
- `CHECK (((maximum_minutes IS NULL) OR (minimum_minutes IS NULL) OR (maximum_minutes >= minimum_minutes)))`
- `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- `CHECK (((length(btrim(evidence_note)) >= 1) AND (length(btrim(evidence_note)) <= 2000)))`
- `CHECK (((maximum_minutes IS NULL) OR (maximum_minutes > 0)))`
- `CHECK (((minimum_minutes IS NULL) OR (minimum_minutes > 0)))`
- `CHECK ((review_status = ANY (ARRAY['needs_review'::text, 'approved'::text, 'rejected'::text, 'withdrawn'::text])))`
- `CHECK (((length(btrim(visit_context)) >= 1) AND (length(btrim(visit_context)) <= 1000)))`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (duration_id)`

## knowledge.destinations

دامنه: دانش مقاصد؛ destinations (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `destination_id` | `bigint` | خیر | `[redacted string default]` | شناسه ـ مقصد؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `canonical_name` | `text` | خیر | ندارد | نام معیار مکان گردشگری | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `destination_type` | `text` | خیر | `[redacted string default]` | نوع مکان گردشگری | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `province_name` | `text` | خیر | ندارد | نام استان | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `city_name` | `text` | بله | ندارد | نام شهر | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `description` | `text` | خیر | ندارد | شرح قابل خواندن | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `difficulty` | `text` | بله | ندارد | دشواری بازدید؛ دامنه دقیق از قرارداد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `suitable_transport` | `text` | بله | ندارد | شیوه حمل‌ونقل مناسب | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `local_language` | `text` | بله | ندارد | زبان محلی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `local_food` | `text` | بله | ندارد | غذای محلی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `local_souvenirs` | `text` | بله | ندارد | سوغات محلی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `best_travel_time` | `text` | بله | ندارد | زمان مناسب سفر یا بازدید | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `latitude` | `double precision` | بله | ندارد | عرض جغرافیایی به درجه | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `longitude` | `double precision` | بله | ندارد | طول جغرافیایی به درجه | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `status` | `text` | خیر | `[redacted string default]` | وضعیت | فرم مستقیم احراز نشده | خوانش نام/نوع؛ نیازمند تأیید مصرف |
| `data_confidence` | `numeric(5,4)` | خیر | `0` | امتیاز اطمینان داده؛ نه تضمین صحت، مقیاس طبق قید | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `destination_key` | `text` | خیر | ندارد | کلید پایدار مقصد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `country_code` | `character(2)` | خیر | `[redacted string default]` | کد کشور مقصد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `aliases` | `text[]` | خیر | `ARRAY[]::text[]` | نام‌های جایگزین | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `parent_destination_id` | `bigint` | بله | ندارد | شناسه ـ مقصد ـ والد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE SET NULL | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `record_origin` | `text` | خیر | `[redacted string default]` | منشأ رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `verification_status` | `text` | خیر | `[redacted string default]` | وضعیت راستی‌آزمایی یا احراز | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `coordinate_role` | `text` | خیر | `[redacted string default]` | نقش مختصات؛ نقطه نماینده لزوما ورودی نیست | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `location` | `geography(Point,4326)` | بله | ندارد | موقعیت جغرافیایی در نوع مکانی SQL | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `admin_area_id` | `bigint` | بله | ندارد | شناسه ـ محدوده ـ اداری/مدیریتی؛ ارجاع به geo.admin_areas(admin_area_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |

قیود جدول:
- `CHECK (((data_confidence >= (0)::numeric) AND (data_confidence <= (1)::numeric)))`
- `CHECK ((((latitude IS NULL) AND (longitude IS NULL) AND (coordinate_role = 'unknown'::text)) OR ((latitude IS NOT NULL) AND (longitude IS NOT NULL) AND (coordinate_role = ANY (ARRAY['property_reference'::text, 'representative_point'::text, 'visitor_entrance'::text, 'test_fixture'::text])))))`
- `CHECK (((latitude IS NULL) = (longitude IS NULL)))`
- `CHECK ((country_code ~ '^[A-Z]{2}$'::text))`
- `CHECK ((record_origin = ANY (ARRAY['user_supplied_unverified'::text, 'verified_external'::text, 'synthetic_fixture'::text])))`
- `CHECK ((status = ANY (ARRAY['draft'::text, 'active'::text, 'inactive'::text, 'archived'::text, 'needs_review'::text, 'test_only'::text])))`
- `CHECK ((is_synthetic = (record_origin = 'synthetic_fixture'::text)))`
- `CHECK ((destination_type ~ '^[a-z][a-z0-9_]{1,63}$'::text))`
- `CHECK ((verification_status = ANY (ARRAY['pending'::text, 'verified'::text, 'rejected'::text, 'stale'::text, 'not_applicable'::text])))`
- `CHECK (((latitude IS NULL) OR ((latitude >= ('-90'::integer)::double precision) AND (latitude <= (90)::double precision))))`
- `CHECK (((longitude IS NULL) OR ((longitude >= ('-180'::integer)::double precision) AND (longitude <= (180)::double precision))))`
- `FOREIGN KEY (admin_area_id) REFERENCES geo.admin_areas(admin_area_id) ON DELETE RESTRICT`
- `FOREIGN KEY (parent_destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE SET NULL`
- `PRIMARY KEY (destination_id)`
- `UNIQUE (canonical_name, province_name, city_name)`

## knowledge.embedding_spaces

دامنه: دانش مقاصد؛ embedding_spaces (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `embedding_space_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ فضا ـ بردار؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `space_key` | `text` | خیر | ندارد | کلید فضای برداری | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `provider_type` | `text` | خیر | ندارد | نوع ارائه‌دهنده مدل | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `provider_name` | `text` | خیر | ندارد | نام ارائه‌دهنده مدل یا خدمت | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `model_name` | `text` | خیر | ندارد | نام مدل استفاده‌شده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `model_revision` | `text` | خیر | `[redacted string default]` | نسخه مدل بردارساز | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `vector_dimension` | `smallint` | خیر | ندارد | تعداد ابعاد بردار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `similarity_metric` | `text` | خیر | `[redacted string default]` | معیار شباهت بردارها | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `preprocessing_version` | `text` | خیر | `[redacted string default]` | نسخه پیش‌پردازش | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_active` | `boolean` | خیر | `false` | آیا رکورد فعال است | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `lifecycle_status` | `text` | خیر | `[redacted string default]` | وضعیت چرخه عمر | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((lifecycle_status = ANY (ARRAY['candidate'::text, 'active'::text, 'retired'::text, 'test_only'::text])))`
- `CHECK ((provider_type = ANY (ARRAY['local'::text, 'remote'::text, 'test'::text])))`
- `CHECK ((similarity_metric = ANY (ARRAY['cosine'::text, 'l2'::text, 'inner_product'::text])))`
- `CHECK (((vector_dimension >= 1) AND (vector_dimension <= 16000)))`
- `PRIMARY KEY (embedding_space_id)`
- `UNIQUE (provider_type, provider_name, model_name, model_revision, vector_dimension, preprocessing_version)`
- `UNIQUE (space_key)`

## knowledge.knowledge_chunks

دامنه: دانش مقاصد؛ knowledge_chunks (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `chunk_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ قطعه متن؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `document_id` | `uuid` | خیر | ندارد | شناسه ـ سند؛ ارجاع به knowledge.knowledge_documents(document_id) ON DELETE CASCADE | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `chunk_index` | `integer` | خیر | ندارد | ترتیب قطعه در سند | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `content` | `text` | خیر | ندارد | محتوای قطعه یا رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `char_count` | `integer` | خیر | ندارد | تعداد نویسه‌ها | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `token_count` | `integer` | بله | ندارد | تعداد توکن‌ها | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `content_sha256` | `character(64)` | خیر | ندارد | اثر انگشت SHA-256 محتوا برای مقایسه و تشخیص تغییر | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `metadata` | `jsonb` | خیر | `[redacted string default]` | فراداده JSON؛ کلیدها تابع قرارداد مصرف‌کننده‌اند | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((char_count >= 0))`
- `CHECK ((chunk_index >= 0))`
- `CHECK (((token_count IS NULL) OR (token_count >= 0)))`
- `FOREIGN KEY (document_id) REFERENCES knowledge.knowledge_documents(document_id) ON DELETE CASCADE`
- `PRIMARY KEY (chunk_id)`
- `UNIQUE (document_id, chunk_index)`

## knowledge.knowledge_documents

دامنه: دانش مقاصد؛ knowledge_documents (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `document_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ سند؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `document_key` | `text` | خیر | ندارد | کلید سند | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_id` | `bigint` | خیر | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `destination_id` | `bigint` | بله | ندارد | شناسه ـ مقصد؛ ارجاع به knowledge.destinations(destination_id) ON DELETE SET NULL | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `title` | `text` | خیر | ندارد | عنوان قابل نمایش | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `language_code` | `text` | خیر | `[redacted string default]` | کد زبان متن | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `document_type` | `text` | خیر | `[redacted string default]` | نوع سند | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `canonical_url` | `text` | بله | ندارد | نشانی معیار سند | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `raw_content` | `text` | خیر | ندارد | محتوای خام سند | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `content_sha256` | `character(64)` | خیر | ندارد | اثر انگشت SHA-256 محتوا برای مقایسه و تشخیص تغییر | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `ingestion_status` | `text` | خیر | `[redacted string default]` | وضعیت ورود و پردازش داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `record_origin` | `text` | خیر | ندارد | منشأ رکورد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `retrieved_at` | `timestamp with time zone` | بله | ندارد | زمان دریافت اطلاعات منبع | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_from` | `timestamp with time zone` | بله | ندارد | شروع اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `valid_until` | `timestamp with time zone` | بله | ندارد | پایان اعتبار | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((is_synthetic = (record_origin = 'synthetic_fixture'::text)))`
- `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- `CHECK ((ingestion_status = ANY (ARRAY['pending'::text, 'processed'::text, 'failed'::text, 'stale'::text, 'test_only'::text])))`
- `CHECK ((record_origin = ANY (ARRAY['user_supplied_unverified'::text, 'verified_external'::text, 'synthetic_fixture'::text])))`
- `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE SET NULL`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (document_id)`
- `UNIQUE (document_key)`

## knowledge.knowledge_sources

دامنه: دانش مقاصد؛ knowledge_sources (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `source_id` | `bigint` | خیر | `[redacted string default]` | شناسه ـ منبع؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `source_name` | `text` | خیر | ندارد | نام منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_type` | `text` | خیر | `[redacted string default]` | نوع منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `verification_status` | `text` | خیر | `[redacted string default]` | وضعیت راستی‌آزمایی یا احراز | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `reliability_score` | `numeric(5,4)` | بله | ندارد | امتیاز اعتبار منبع؛ مقیاس از قید | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `url` | `text` | بله | ندارد | نشانی منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `notes` | `text` | بله | ندارد | یادداشت تکمیلی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((reliability_score IS NULL) OR ((reliability_score >= (0)::numeric) AND (reliability_score <= (1)::numeric))))`
- `CHECK ((verification_status = ANY (ARRAY['pending'::text, 'verified'::text, 'rejected'::text, 'stale'::text])))`
- `PRIMARY KEY (source_id)`

## knowledge.production_chunk_embeddings

دامنه: دانش مقاصد؛ production_chunk_embeddings (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `chunk_embedding_id` | `uuid` | بله | ندارد | شناسه ـ بردار ـ قطعه متن | نمای مشتق؛ بدون ورود | View؛ lineage |
| `chunk_id` | `uuid` | بله | ندارد | شناسه ـ قطعه متن | نمای مشتق؛ بدون ورود | View؛ lineage |
| `embedding_space_id` | `uuid` | بله | ندارد | شناسه ـ فضا ـ بردار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `space_key` | `text` | بله | ندارد | کلید ـ فضا | نمای مشتق؛ بدون ورود | View؛ lineage |
| `provider_type` | `text` | بله | ندارد | نوع ـ ارائه‌دهنده | نمای مشتق؛ بدون ورود | View؛ lineage |
| `provider_name` | `text` | بله | ندارد | نام ـ ارائه‌دهنده | نمای مشتق؛ بدون ورود | View؛ lineage |
| `model_name` | `text` | بله | ندارد | نام ـ مدل | نمای مشتق؛ بدون ورود | View؛ lineage |
| `model_revision` | `text` | بله | ندارد | بازبینی ـ مدل | نمای مشتق؛ بدون ورود | View؛ lineage |
| `vector_dimension` | `smallint` | بله | ندارد | بعد ـ بردار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `similarity_metric` | `text` | بله | ندارد | معیار ـ شباهت | نمای مشتق؛ بدون ورود | View؛ lineage |
| `preprocessing_version` | `text` | بله | ندارد | نسخه ـ پیش‌پردازش | نمای مشتق؛ بدون ورود | View؛ lineage |
| `embedding` | `vector` | بله | ندارد | بردار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `created_at` | `timestamp with time zone` | بله | ندارد | زمان ایجاد رکورد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `updated_at` | `timestamp with time zone` | بله | ندارد | زمان آخرین تغییر | نمای مشتق؛ بدون ورود | View؛ lineage |

[مرجع lineage](../../database/architecture-usage/view_column_lineage.csv)؛ تطبیق هر خروجی با مبدأ لازم است.

## knowledge.production_culinary_knowledge

دامنه: دانش مقاصد؛ production_culinary_knowledge (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `item_id` | `uuid` | بله | ندارد | شناسه ـ قلم | نمای مشتق؛ بدون ورود | View؛ lineage |
| `item_key` | `text` | بله | ندارد | کلید ـ قلم | نمای مشتق؛ بدون ورود | View؛ lineage |
| `category` | `text` | بله | ندارد | دسته | نمای مشتق؛ بدون ورود | View؛ lineage |
| `record_key` | `text` | بله | ندارد | کلید ـ رکورد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `names_by_locale` | `jsonb` | بله | ندارد | زبان/منطقه ـ توسط/بر اساس ـ نام‌ها | نمای مشتق؛ بدون ورود | View؛ lineage |
| `descriptions_by_locale` | `jsonb` | بله | ندارد | زبان/منطقه ـ توسط/بر اساس ـ شرح‌ها | نمای مشتق؛ بدون ورود | View؛ lineage |
| `claims` | `jsonb` | بله | ندارد | گزاره‌ها | نمای مشتق؛ بدون ورود | View؛ lineage |
| `provenance` | `jsonb` | بله | ندارد | منشأ | نمای مشتق؛ بدون ورود | View؛ lineage |
| `updated_at` | `timestamp with time zone` | بله | ندارد | زمان آخرین تغییر | نمای مشتق؛ بدون ورود | View؛ lineage |

[مرجع lineage](../../database/architecture-usage/view_column_lineage.csv)؛ تطبیق هر خروجی با مبدأ لازم است.

## knowledge.production_destination_categories

دامنه: دانش مقاصد؛ production_destination_categories (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `category_id` | `bigint` | بله | ندارد | شناسه ـ دسته | نمای مشتق؛ بدون ورود | View؛ lineage |
| `category_key` | `text` | بله | ندارد | کلید ـ دسته | نمای مشتق؛ بدون ورود | View؛ lineage |
| `name_fa` | `text` | بله | ندارد | فارسی ـ نام | نمای مشتق؛ بدون ورود | View؛ lineage |
| `description` | `text` | بله | ندارد | شرح | نمای مشتق؛ بدون ورود | View؛ lineage |
| `sort_order` | `smallint` | بله | ندارد | ترتیب ـ مرتب‌سازی | نمای مشتق؛ بدون ورود | View؛ lineage |

[مرجع lineage](../../database/architecture-usage/view_column_lineage.csv)؛ تطبیق هر خروجی با مبدأ لازم است.

## knowledge.production_destination_category_map

دامنه: دانش مقاصد؛ production_destination_category_map (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `destination_id` | `bigint` | بله | ندارد | شناسه ـ مقصد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `category_id` | `bigint` | بله | ندارد | شناسه ـ دسته | نمای مشتق؛ بدون ورود | View؛ lineage |
| `mapping_source` | `text` | بله | ندارد | منبع ـ ارتباط | نمای مشتق؛ بدون ورود | View؛ lineage |
| `created_at` | `timestamp with time zone` | بله | ندارد | زمان ایجاد رکورد | نمای مشتق؛ بدون ورود | View؛ lineage |

[مرجع lineage](../../database/architecture-usage/view_column_lineage.csv)؛ تطبیق هر خروجی با مبدأ لازم است.

## knowledge.production_destination_claim_evidence

دامنه: دانش مقاصد؛ production_destination_claim_evidence (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `canonical_entity_key` | `text` | بله | ندارد | خروجی مشتق‌شده: canonical_entity_key | نمای مشتق؛ بدون ورود | View؛ lineage |
| `destination_id` | `bigint` | بله | ندارد | شناسه ـ مقصد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `document_id` | `text` | بله | ندارد | شناسه ـ سند | نمای مشتق؛ بدون ورود | View؛ lineage |
| `chunk_id` | `text` | بله | ندارد | شناسه ـ قطعه متن | نمای مشتق؛ بدون ورود | View؛ lineage |
| `claim_key` | `text` | بله | ندارد | کلید ـ گزاره | نمای مشتق؛ بدون ورود | View؛ lineage |
| `content_hash` | `text` | بله | ندارد | هش ـ محتوا | نمای مشتق؛ بدون ورود | View؛ lineage |
| `locale` | `text` | بله | ندارد | زبان/منطقه | نمای مشتق؛ بدون ورود | View؛ lineage |
| `corpus` | `text` | بله | ندارد | مجموعه متنی | نمای مشتق؛ بدون ورود | View؛ lineage |
| `valid_from` | `timestamp with time zone` | بله | ندارد | از ـ اعتبار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `valid_until` | `timestamp with time zone` | بله | ندارد | تا ـ اعتبار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `is_published` | `boolean` | بله | ندارد | منتشرشده ـ نشان | نمای مشتق؛ بدون ورود | View؛ lineage |
| `is_destination_verified` | `boolean` | بله | ندارد | تأییدشده ـ مقصد ـ نشان | نمای مشتق؛ بدون ورود | View؛ lineage |
| `is_document_processed` | `boolean` | بله | ندارد | پردازش‌شده ـ سند ـ نشان | نمای مشتق؛ بدون ورود | View؛ lineage |
| `is_synthetic` | `boolean` | بله | ندارد | نشان داده مصنوعی، نه واقعی | نمای مشتق؛ بدون ورود | View؛ lineage |
| `is_revoked` | `boolean` | بله | ندارد | لغوشده ـ نشان | نمای مشتق؛ بدون ورود | View؛ lineage |
| `source_id` | `text` | بله | ندارد | شناسه ـ منبع | نمای مشتق؛ بدون ورود | View؛ lineage |
| `source_name` | `text` | بله | ندارد | نام ـ منبع | نمای مشتق؛ بدون ورود | View؛ lineage |
| `source_url` | `text` | بله | ندارد | نشانی ـ منبع | نمای مشتق؛ بدون ورود | View؛ lineage |
| `source_role` | `text` | بله | ندارد | نقش ـ منبع | نمای مشتق؛ بدون ورود | View؛ lineage |
| `license` | `text` | بله | ندارد | مجوز استفاده | نمای مشتق؛ بدون ورود | View؛ lineage |
| `retrieved_at` | `timestamp with time zone` | بله | ندارد | زمان ـ دریافت | نمای مشتق؛ بدون ورود | View؛ lineage |
| `source_valid_from` | `timestamp with time zone` | بله | ندارد | از ـ اعتبار ـ منبع | نمای مشتق؛ بدون ورود | View؛ lineage |
| `source_valid_until` | `timestamp with time zone` | بله | ندارد | تا ـ اعتبار ـ منبع | نمای مشتق؛ بدون ورود | View؛ lineage |
| `is_source_verified` | `boolean` | بله | ندارد | تأییدشده ـ منبع ـ نشان | نمای مشتق؛ بدون ورود | View؛ lineage |
| `is_source_synthetic` | `boolean` | بله | ندارد | مصنوعی ـ منبع ـ نشان | نمای مشتق؛ بدون ورود | View؛ lineage |
| `is_source_revoked` | `boolean` | بله | ندارد | لغوشده ـ منبع ـ نشان | نمای مشتق؛ بدون ورود | View؛ lineage |

[مرجع lineage](../../database/architecture-usage/view_column_lineage.csv)؛ تطبیق هر خروجی با مبدأ لازم است.

## knowledge.production_destination_sources

دامنه: دانش مقاصد؛ production_destination_sources (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `destination_id` | `bigint` | بله | ندارد | شناسه ـ مقصد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `source_id` | `bigint` | بله | ندارد | شناسه ـ منبع | نمای مشتق؛ بدون ورود | View؛ lineage |
| `source_role` | `text` | بله | ندارد | نقش ـ منبع | نمای مشتق؛ بدون ورود | View؛ lineage |
| `evidence_note` | `text` | بله | ندارد | یادداشت ـ شاهد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `retrieved_at` | `timestamp with time zone` | بله | ندارد | زمان ـ دریافت | نمای مشتق؛ بدون ورود | View؛ lineage |
| `valid_from` | `timestamp with time zone` | بله | ندارد | از ـ اعتبار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `valid_until` | `timestamp with time zone` | بله | ندارد | تا ـ اعتبار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `source_name` | `text` | بله | ندارد | نام ـ منبع | نمای مشتق؛ بدون ورود | View؛ lineage |
| `source_type` | `text` | بله | ندارد | نوع ـ منبع | نمای مشتق؛ بدون ورود | View؛ lineage |
| `source_url` | `text` | بله | ندارد | نشانی ـ منبع | نمای مشتق؛ بدون ورود | View؛ lineage |
| `reliability_score` | `numeric(5,4)` | بله | ندارد | امتیاز ـ اعتبار | نمای مشتق؛ بدون ورود | View؛ lineage |

[مرجع lineage](../../database/architecture-usage/view_column_lineage.csv)؛ تطبیق هر خروجی با مبدأ لازم است.

## knowledge.production_destination_tags

دامنه: دانش مقاصد؛ production_destination_tags (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `destination_id` | `bigint` | بله | ندارد | شناسه ـ مقصد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `tag` | `text` | بله | ندارد | برچسب | نمای مشتق؛ بدون ورود | View؛ lineage |

[مرجع lineage](../../database/architecture-usage/view_column_lineage.csv)؛ تطبیق هر خروجی با مبدأ لازم است.

## knowledge.production_destinations

دامنه: دانش مقاصد؛ production_destinations (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `destination_id` | `bigint` | بله | ندارد | شناسه ـ مقصد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `canonical_name` | `text` | بله | ندارد | نام ـ معیار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `destination_type` | `text` | بله | ندارد | نوع ـ مقصد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `province_name` | `text` | بله | ندارد | نام ـ استان | نمای مشتق؛ بدون ورود | View؛ lineage |
| `city_name` | `text` | بله | ندارد | نام ـ شهر | نمای مشتق؛ بدون ورود | View؛ lineage |
| `description` | `text` | بله | ندارد | شرح | نمای مشتق؛ بدون ورود | View؛ lineage |
| `difficulty` | `text` | بله | ندارد | دشواری | نمای مشتق؛ بدون ورود | View؛ lineage |
| `suitable_transport` | `text` | بله | ندارد | حمل‌ونقل ـ مناسب | نمای مشتق؛ بدون ورود | View؛ lineage |
| `local_language` | `text` | بله | ندارد | زبان ـ محلی | نمای مشتق؛ بدون ورود | View؛ lineage |
| `local_food` | `text` | بله | ندارد | غذا ـ محلی | نمای مشتق؛ بدون ورود | View؛ lineage |
| `local_souvenirs` | `text` | بله | ندارد | سوغات ـ محلی | نمای مشتق؛ بدون ورود | View؛ lineage |
| `best_travel_time` | `text` | بله | ندارد | زمان ـ سفر ـ مناسب‌ترین | نمای مشتق؛ بدون ورود | View؛ lineage |
| `latitude` | `double precision` | بله | ندارد | عرض جغرافیایی به درجه | نمای مشتق؛ بدون ورود | View؛ lineage |
| `longitude` | `double precision` | بله | ندارد | طول جغرافیایی به درجه | نمای مشتق؛ بدون ورود | View؛ lineage |
| `status` | `text` | بله | ندارد | وضعیت | نمای مشتق؛ بدون ورود | View؛ lineage |
| `data_confidence` | `numeric(5,4)` | بله | ندارد | خروجی مشتق‌شده: data_confidence | نمای مشتق؛ بدون ورود | View؛ lineage |
| `created_at` | `timestamp with time zone` | بله | ندارد | زمان ایجاد رکورد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `updated_at` | `timestamp with time zone` | بله | ندارد | زمان آخرین تغییر | نمای مشتق؛ بدون ورود | View؛ lineage |
| `destination_key` | `text` | بله | ندارد | کلید ـ مقصد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `country_code` | `character(2)` | بله | ندارد | کد ـ کشور | نمای مشتق؛ بدون ورود | View؛ lineage |
| `aliases` | `text[]` | بله | ندارد | نام‌های جایگزین | نمای مشتق؛ بدون ورود | View؛ lineage |
| `parent_destination_id` | `bigint` | بله | ندارد | شناسه ـ مقصد ـ والد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `record_origin` | `text` | بله | ندارد | منشأ ـ رکورد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `verification_status` | `text` | بله | ندارد | وضعیت ـ راستی‌آزمایی | نمای مشتق؛ بدون ورود | View؛ lineage |
| `is_synthetic` | `boolean` | بله | ندارد | نشان داده مصنوعی، نه واقعی | نمای مشتق؛ بدون ورود | View؛ lineage |
| `coordinate_role` | `text` | بله | ندارد | نقش مختصات؛ نقطه نماینده لزوما ورودی نیست | نمای مشتق؛ بدون ورود | View؛ lineage |
| `location` | `geography(Point,4326)` | بله | ندارد | موقعیت | نمای مشتق؛ بدون ورود | View؛ lineage |

[مرجع lineage](../../database/architecture-usage/view_column_lineage.csv)؛ تطبیق هر خروجی با مبدأ لازم است.

## knowledge.production_retrieval_chunks

دامنه: دانش مقاصد؛ production_retrieval_chunks (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `chunk_id` | `uuid` | بله | ندارد | شناسه ـ قطعه متن | نمای مشتق؛ بدون ورود | View؛ lineage |
| `document_id` | `uuid` | بله | ندارد | شناسه ـ سند | نمای مشتق؛ بدون ورود | View؛ lineage |
| `destination_id` | `bigint` | بله | ندارد | شناسه ـ مقصد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `document_key` | `text` | بله | ندارد | کلید ـ سند | نمای مشتق؛ بدون ورود | View؛ lineage |
| `title` | `text` | بله | ندارد | عنوان | نمای مشتق؛ بدون ورود | View؛ lineage |
| `language_code` | `text` | بله | ندارد | کد ـ زبان | نمای مشتق؛ بدون ورود | View؛ lineage |
| `document_type` | `text` | بله | ندارد | نوع ـ سند | نمای مشتق؛ بدون ورود | View؛ lineage |
| `canonical_url` | `text` | بله | ندارد | نشانی ـ معیار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `provenance_source_name` | `text` | بله | ندارد | نام ـ منبع ـ منشأ | نمای مشتق؛ بدون ورود | View؛ lineage |
| `provenance_source_type` | `text` | بله | ندارد | نوع ـ منبع ـ منشأ | نمای مشتق؛ بدون ورود | View؛ lineage |
| `provenance_source_url` | `text` | بله | ندارد | نشانی ـ منبع ـ منشأ | نمای مشتق؛ بدون ورود | View؛ lineage |
| `provenance_reliability_score` | `numeric(5,4)` | بله | ندارد | امتیاز ـ اعتبار ـ منشأ | نمای مشتق؛ بدون ورود | View؛ lineage |
| `chunk_index` | `integer` | بله | ندارد | ترتیب ـ قطعه متن | نمای مشتق؛ بدون ورود | View؛ lineage |
| `content` | `text` | بله | ندارد | محتوا | نمای مشتق؛ بدون ورود | View؛ lineage |
| `char_count` | `integer` | بله | ندارد | تعداد ـ نویسه | نمای مشتق؛ بدون ورود | View؛ lineage |
| `token_count` | `integer` | بله | ندارد | تعداد ـ توکن | نمای مشتق؛ بدون ورود | View؛ lineage |
| `content_sha256` | `character(64)` | بله | ندارد | اثر انگشت SHA-256 محتوا | نمای مشتق؛ بدون ورود | View؛ lineage |
| `metadata` | `jsonb` | بله | ندارد | فراداده | نمای مشتق؛ بدون ورود | View؛ lineage |
| `created_at` | `timestamp with time zone` | بله | ندارد | زمان ایجاد رکورد | نمای مشتق؛ بدون ورود | View؛ lineage |

[مرجع lineage](../../database/architecture-usage/view_column_lineage.csv)؛ تطبیق هر خروجی با مبدأ لازم است.

## knowledge.production_retrieval_documents

دامنه: دانش مقاصد؛ production_retrieval_documents (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: View خواندنی؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `document_id` | `uuid` | بله | ندارد | شناسه ـ سند | نمای مشتق؛ بدون ورود | View؛ lineage |
| `document_key` | `text` | بله | ندارد | کلید ـ سند | نمای مشتق؛ بدون ورود | View؛ lineage |
| `source_id` | `bigint` | بله | ندارد | شناسه ـ منبع | نمای مشتق؛ بدون ورود | View؛ lineage |
| `destination_id` | `bigint` | بله | ندارد | شناسه ـ مقصد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `title` | `text` | بله | ندارد | عنوان | نمای مشتق؛ بدون ورود | View؛ lineage |
| `language_code` | `text` | بله | ندارد | کد ـ زبان | نمای مشتق؛ بدون ورود | View؛ lineage |
| `document_type` | `text` | بله | ندارد | نوع ـ سند | نمای مشتق؛ بدون ورود | View؛ lineage |
| `canonical_url` | `text` | بله | ندارد | نشانی ـ معیار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `raw_content` | `text` | بله | ندارد | محتوا ـ خام | نمای مشتق؛ بدون ورود | View؛ lineage |
| `content_sha256` | `character(64)` | بله | ندارد | اثر انگشت SHA-256 محتوا | نمای مشتق؛ بدون ورود | View؛ lineage |
| `ingestion_status` | `text` | بله | ندارد | وضعیت ـ ورود داده | نمای مشتق؛ بدون ورود | View؛ lineage |
| `record_origin` | `text` | بله | ندارد | منشأ ـ رکورد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `is_synthetic` | `boolean` | بله | ندارد | نشان داده مصنوعی، نه واقعی | نمای مشتق؛ بدون ورود | View؛ lineage |
| `retrieved_at` | `timestamp with time zone` | بله | ندارد | زمان ـ دریافت | نمای مشتق؛ بدون ورود | View؛ lineage |
| `valid_from` | `timestamp with time zone` | بله | ندارد | از ـ اعتبار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `valid_until` | `timestamp with time zone` | بله | ندارد | تا ـ اعتبار | نمای مشتق؛ بدون ورود | View؛ lineage |
| `created_at` | `timestamp with time zone` | بله | ندارد | زمان ایجاد رکورد | نمای مشتق؛ بدون ورود | View؛ lineage |
| `updated_at` | `timestamp with time zone` | بله | ندارد | زمان آخرین تغییر | نمای مشتق؛ بدون ورود | View؛ lineage |
| `provenance_source_name` | `text` | بله | ندارد | نام ـ منبع ـ منشأ | نمای مشتق؛ بدون ورود | View؛ lineage |
| `provenance_source_type` | `text` | بله | ندارد | نوع ـ منبع ـ منشأ | نمای مشتق؛ بدون ورود | View؛ lineage |
| `provenance_source_url` | `text` | بله | ندارد | نشانی ـ منبع ـ منشأ | نمای مشتق؛ بدون ورود | View؛ lineage |
| `provenance_reliability_score` | `numeric(5,4)` | بله | ندارد | امتیاز ـ اعتبار ـ منشأ | نمای مشتق؛ بدون ورود | View؛ lineage |

[مرجع lineage](../../database/architecture-usage/view_column_lineage.csv)؛ تطبیق هر خروجی با مبدأ لازم است.

## knowledge.source_candidate_reviews

دامنه: دانش مقاصد؛ source_candidate_reviews (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `source_review_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ بازبینی ـ منبع؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `source_candidate_id` | `uuid` | خیر | ندارد | شناسه ـ نامزد ـ منبع؛ ارجاع به knowledge.source_candidates(source_candidate_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `decision` | `text` | خیر | ندارد | register_pending/reject/defer/request_evidence؛ SourceReviewDecision | فرم مستقیم احراز نشده | قرارداد API: catalogue_review.py |
| `source_id` | `bigint` | بله | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `reason` | `text` | خیر | ندارد | دلیل تصمیم؛ ۱–۲۰۰۰؛ SourceReviewDecision | فرم مستقیم احراز نشده | قرارداد API: catalogue_review.py |
| `evidence_refs` | `jsonb` | خیر | `[redacted string default]` | ارجاعات شاهد؛ حداکثر ۳۰؛ SourceReviewDecision | فرم مستقیم احراز نشده | قرارداد API: catalogue_review.py |
| `reviewer_user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر ـ بازبین؛ ارجاع به identity.users(user_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `policy_version` | `text` | خیر | ندارد | نسخه سیاست؛ source-review-v1 | فرم مستقیم احراز نشده | قرارداد API: catalogue_review.py |
| `decided_at` | `timestamp with time zone` | خیر | `now()` | زمان ثبت تصمیم | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((decision = 'register_pending'::text) = (source_id IS NOT NULL)))`
- `CHECK ((decision = ANY (ARRAY['register_pending'::text, 'reject'::text, 'defer'::text, 'request_evidence'::text])))`
- `CHECK ((jsonb_typeof(evidence_refs) = 'array'::text))`
- `CHECK (((length(btrim(policy_version)) >= 1) AND (length(btrim(policy_version)) <= 80)))`
- `CHECK (((length(btrim(reason)) >= 1) AND (length(btrim(reason)) <= 2000)))`
- `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (source_candidate_id) REFERENCES knowledge.source_candidates(source_candidate_id) ON DELETE RESTRICT`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (source_review_id)`

## knowledge.source_candidates

دامنه: دانش مقاصد؛ source_candidates (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `source_candidate_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ نامزد ـ منبع؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `dataset_import_batch_id` | `uuid` | خیر | ندارد | شناسه ـ دسته ـ ورود ـ مجموعه داده؛ ارجاع به operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `file_id` | `uuid` | خیر | ندارد | شناسه ـ فایل؛ ارجاع به operations.dataset_import_files(file_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `source_file_sha256` | `character(64)` | خیر | ندارد | اثر انگشت فایل منبع | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_record_key` | `text` | خیر | ندارد | کلید رکورد در فایل یا منبع مبدأ | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `row_sha256` | `character(64)` | خیر | ندارد | اثر انگشت سطر ورودی | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `raw_record` | `jsonb` | خیر | ندارد | رکورد خام ورودی پیش از پردازش | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `proposed_source_key` | `text` | بله | ندارد | کلید پیشنهادی منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `proposed_source_name` | `text` | بله | ندارد | نام پیشنهادی منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `proposed_publisher` | `text` | بله | ندارد | ناشر پیشنهادی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `proposed_source_type` | `text` | بله | ندارد | نوع پیشنهادی منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `proposed_url` | `text` | بله | ندارد | نشانی پیشنهادی منبع | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `proposed_license` | `text` | بله | ندارد | مجوز پیشنهادی استفاده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `candidate_status` | `text` | خیر | `[redacted string default]` | وضعیت پردازش نامزد | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `registered_source_id` | `bigint` | بله | ندارد | شناسه ـ منبع ـ ثبت‌شده؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((candidate_status = ANY (ARRAY['needs_review'::text, 'registered_pending'::text, 'rejected'::text, 'conflict'::text])))`
- `CHECK (((candidate_status = 'registered_pending'::text) = (registered_source_id IS NOT NULL)))`
- `CHECK ((jsonb_typeof(raw_record) = 'object'::text))`
- `CHECK ((row_sha256 ~ '^[a-f0-9]{64}$'::text))`
- `CHECK ((source_file_sha256 ~ '^[a-f0-9]{64}$'::text))`
- `CHECK (((length(btrim(source_record_key)) >= 1) AND (length(btrim(source_record_key)) <= 512)))`
- `FOREIGN KEY (dataset_import_batch_id) REFERENCES operations.dataset_import_batches(dataset_import_batch_id) ON DELETE RESTRICT`
- `FOREIGN KEY (file_id) REFERENCES operations.dataset_import_files(file_id) ON DELETE RESTRICT`
- `FOREIGN KEY (registered_source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (source_candidate_id)`
- `UNIQUE (dataset_import_batch_id, source_file_sha256, source_record_key)`

## knowledge.source_registry_registration_events

دامنه: دانش مقاصد؛ source_registry_registration_events (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `registration_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ ثبت؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `source_id` | `bigint` | خیر | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `publisher` | `text` | خیر | ندارد | نام ناشر؛ ۱–۲۴۰؛ SourceRegistrationInput | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `page_title` | `text` | خیر | ندارد | عنوان صفحه؛ ۱–۵۰۰؛ SourceRegistrationInput | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `registered_url` | `text` | خیر | ندارد | نشانی HTTPS ثبت‌شده از url فرم؛ ۱۲–۲۰۴۸؛ SourceRegistrationInput | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `license_note` | `text` | بله | ندارد | یادداشت مجوز اختیاری تا ۵۰۰؛ SourceRegistrationInput | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `registration_note` | `text` | خیر | ندارد | توضیح ثبت ۱–۱۰۰۰؛ SourceRegistrationInput | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `registrar_user_id` | `uuid` | خیر | ندارد | ارجاع به identity.users(user_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `policy_version` | `text` | خیر | ندارد | نسخه سیاست ثبت؛ direct-source-registration-v1 | فرم مستقیم احراز نشده | قرارداد API: catalogue_review.py |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((length(btrim(page_title)) >= 1) AND (length(btrim(page_title)) <= 500)))`
- `CHECK (((length(btrim(policy_version)) >= 1) AND (length(btrim(policy_version)) <= 80)))`
- `CHECK (((length(btrim(publisher)) >= 1) AND (length(btrim(publisher)) <= 240)))`
- `CHECK ((registered_url ~ '^https://[^[:space:]]+$'::text))`
- `CHECK (((length(btrim(registration_note)) >= 1) AND (length(btrim(registration_note)) <= 1000)))`
- `FOREIGN KEY (registrar_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (registration_id)`

## knowledge.source_verification_reviews

دامنه: دانش مقاصد؛ source_verification_reviews (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: /admin/catalogue-review برای نامزد، منبع، شاهد و انتشار؛ پردازش داخلی سایر اشیا.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `verification_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ راستی‌آزمایی؛ کلید یکتای رکورد | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید PK |
| `source_id` | `bigint` | خیر | ندارد | شناسه ـ منبع؛ ارجاع به knowledge.knowledge_sources(source_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `decision` | `text` | خیر | ندارد | تصمیم ثبت‌شده در فرایند بازبینی | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `source_url` | `text` | خیر | ندارد | نشانی منبع این داده | فرم مستقیم احراز نشده | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `publisher` | `text` | خیر | ندارد | ناشر؛ ۱–۲۴۰؛ SourceVerificationInput | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `page_title` | `text` | خیر | ندارد | عنوان صفحه؛ ۱–۵۰۰؛ SourceVerificationInput | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `evidence_excerpt` | `text` | خیر | ندارد | گزیده شاهد؛ ۱–۶۰۰؛ SourceVerificationInput | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `inspected_at` | `timestamp with time zone` | خیر | ندارد | زمان مشاهده مستقیم؛ datetime؛ SourceVerificationInput | فرم/API دامنه؛ راهنمای ورود | قرارداد API: catalogue_review.py |
| `reviewer_user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر ـ بازبین؛ ارجاع به identity.users(user_id) ON DELETE RESTRICT | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | قید FK |
| `policy_version` | `text` | خیر | ندارد | نسخه سیاست؛ source-direct-inspection-v1 | فرم مستقیم احراز نشده | قرارداد API: catalogue_review.py |
| `decided_at` | `timestamp with time zone` | خیر | `now()` | زمان ثبت تصمیم | سیستم یا انتخاب مرجع؛ نه شناسه آزاد | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((decision = ANY (ARRAY['verified'::text, 'rejected'::text])))`
- `CHECK (((length(btrim(evidence_excerpt)) >= 1) AND (length(btrim(evidence_excerpt)) <= 600)))`
- `CHECK (((length(btrim(page_title)) >= 1) AND (length(btrim(page_title)) <= 500)))`
- `CHECK (((length(btrim(policy_version)) >= 1) AND (length(btrim(policy_version)) <= 80)))`
- `CHECK (((length(btrim(publisher)) >= 1) AND (length(btrim(publisher)) <= 240)))`
- `CHECK ((source_url ~ '^https://'::text))`
- `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- `PRIMARY KEY (verification_id)`
