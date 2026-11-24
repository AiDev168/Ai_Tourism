# knowledge.destination_candidate_reviews

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نیازمند توضیح دامنه‌ای تأییدشده از کد و مالک محصول
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'review_id' | 'uuid' | خیر | 'gen_random_uuid()' | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'candidate_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'identity_relation' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'target_destination_id' | 'bigint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'decision' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'reason' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'evidence_refs' | 'jsonb' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'reviewer_user_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'policy_version' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'decided_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **destination_candidate_reviews_check** (`c`): `CHECK (((decision <> 'accept'::text) OR ((identity_relation <> 'unresolved'::text) AND (target_destination_id IS NOT NULL) AND (jsonb_array_length(evidence_refs) > 0))))`
- **destination_candidate_reviews_check1** (`c`): `CHECK (((decision <> ALL (ARRAY['reject'::text, 'defer'::text, 'request_evidence'::text])) OR (target_destination_id IS NULL)))`
- **destination_candidate_reviews_check2** (`c`): `CHECK (((decision <> 'approve_new_identity'::text) OR ((identity_relation = 'unresolved'::text) AND (target_destination_id IS NULL) AND (jsonb_array_length(evidence_refs) > 0))))`
- **destination_candidate_reviews_decision_check** (`c`): `CHECK ((decision = ANY (ARRAY['accept'::text, 'approve_new_identity'::text, 'reject'::text, 'defer'::text, 'request_evidence'::text])))`
- **destination_candidate_reviews_evidence_refs_check** (`c`): `CHECK ((jsonb_typeof(evidence_refs) = 'array'::text))`
- **destination_candidate_reviews_identity_relation_check** (`c`): `CHECK ((identity_relation = ANY (ARRAY['same_entity'::text, 'part_of_or_within'::text, 'nearby_distinct'::text, 'unresolved'::text])))`
- **destination_candidate_reviews_policy_version_check** (`c`): `CHECK (((length(btrim(policy_version)) >= 1) AND (length(btrim(policy_version)) <= 80)))`
- **destination_candidate_reviews_reason_check** (`c`): `CHECK (((length(btrim(reason)) >= 1) AND (length(btrim(reason)) <= 2000)))`
- **destination_candidate_reviews_candidate_id_fkey** (`f`): `FOREIGN KEY (candidate_id) REFERENCES knowledge.destination_candidates(candidate_id) ON DELETE RESTRICT`
- **destination_candidate_reviews_reviewer_user_id_fkey** (`f`): `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **destination_candidate_reviews_target_destination_id_fkey** (`f`): `FOREIGN KEY (target_destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- **destination_candidate_reviews_pkey** (`p`): `PRIMARY KEY (review_id)`

## ایندکس‌ها

- `destination_candidate_reviews_pkey`: `CREATE UNIQUE INDEX destination_candidate_reviews_pkey ON knowledge.destination_candidate_reviews USING btree (review_id)`
- `ix_candidate_reviews_candidate_time`: `CREATE INDEX ix_candidate_reviews_candidate_time ON knowledge.destination_candidate_reviews USING btree (candidate_id, decided_at DESC)`

## سیاست‌های RLS

- `candidate_reviews_insert`: command=a, roles=[], using=`—`, with_check=`((reviewer_user_id = identity.current_app_actor_id()) AND identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text))`
- `candidate_reviews_select`: command=r, roles=[], using=`identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text)`, with_check=`—`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **10** از **10**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
