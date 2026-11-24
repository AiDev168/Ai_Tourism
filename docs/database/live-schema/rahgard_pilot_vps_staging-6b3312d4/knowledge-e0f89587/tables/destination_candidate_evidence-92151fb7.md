# knowledge.destination_candidate_evidence

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
| 'evidence_id' | 'uuid' | خیر | 'gen_random_uuid()' | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'candidate_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'source_id' | 'bigint' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'field_key' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'claim_value' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'source_url' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'evidence_excerpt' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'retrieved_at' | 'timestamp with time zone' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'reviewer_user_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'policy_version' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **destination_candidate_evidence_claim_value_check** (`c`): `CHECK (((length(btrim(claim_value)) >= 1) AND (length(btrim(claim_value)) <= 8000)))`
- **destination_candidate_evidence_evidence_excerpt_check** (`c`): `CHECK (((length(btrim(evidence_excerpt)) >= 1) AND (length(btrim(evidence_excerpt)) <= 600)))`
- **destination_candidate_evidence_field_key_check** (`c`): `CHECK ((field_key = ANY (ARRAY['identity'::text, 'province'::text, 'city'::text, 'coordinates'::text, 'description'::text])))`
- **destination_candidate_evidence_policy_version_check** (`c`): `CHECK (((length(btrim(policy_version)) >= 1) AND (length(btrim(policy_version)) <= 80)))`
- **destination_candidate_evidence_source_url_check** (`c`): `CHECK ((source_url ~ '^https://'::text))`
- **destination_candidate_evidence_candidate_id_fkey** (`f`): `FOREIGN KEY (candidate_id) REFERENCES knowledge.destination_candidates(candidate_id) ON DELETE RESTRICT`
- **destination_candidate_evidence_reviewer_user_id_fkey** (`f`): `FOREIGN KEY (reviewer_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **destination_candidate_evidence_source_id_fkey** (`f`): `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- **destination_candidate_evidence_pkey** (`p`): `PRIMARY KEY (evidence_id)`
- **destination_candidate_evidenc_candidate_id_source_id_field__key** (`u`): `UNIQUE (candidate_id, source_id, field_key, claim_value, source_url)`

## ایندکس‌ها

- `destination_candidate_evidenc_candidate_id_source_id_field__key`: `CREATE UNIQUE INDEX destination_candidate_evidenc_candidate_id_source_id_field__key ON knowledge.destination_candidate_evidence USING btree (candidate_id, source_id, field_key, claim_value, source_url)`
- `destination_candidate_evidence_pkey`: `CREATE UNIQUE INDEX destination_candidate_evidence_pkey ON knowledge.destination_candidate_evidence USING btree (evidence_id)`
- `ix_candidate_evidence_candidate`: `CREATE INDEX ix_candidate_evidence_candidate ON knowledge.destination_candidate_evidence USING btree (candidate_id, field_key, created_at DESC)`

## سیاست‌های RLS

- `candidate_evidence_insert`: command=a, roles=[], using=`—`, with_check=`((reviewer_user_id = identity.current_app_actor_id()) AND identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'source_review'::text))`
- `candidate_evidence_reviewers`: command=r, roles=[], using=`(identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text) OR identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'catalogue_publish'::text))`, with_check=`—`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **11** از **11**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
