# knowledge.destination_access_points

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
| 'access_point_id' | 'uuid' | خیر | 'gen_random_uuid()' | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'destination_id' | 'bigint' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'point' | 'geometry(Point,4326)' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | نوع سفارشی یا قالب وابسته به دامنه؛ اعتبارسنجی API/enum را بررسی کنید |
| 'point_role' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'label' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'accessibility_state' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'source_id' | 'bigint' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'source_url' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'evidence_note' | 'text' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'coordinate_precision_m' | 'numeric(8,2)' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | عدد ده‌دهی؛ precision و scale از PostgreSQL؛ واحد/ارز باید مستند شود |
| 'status' | 'text' | خیر | '[redacted string default]' | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'observed_at' | 'timestamp with time zone' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'reviewed_at' | 'timestamp with time zone' | بله | — | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **destination_access_points_accessibility_state_check** (`c`): `CHECK ((accessibility_state = ANY (ARRAY['known'::text, 'unknown'::text, 'not_applicable'::text, 'conflicting'::text])))`
- **destination_access_points_check** (`c`): `CHECK (((status <> 'approved'::text) OR ((point IS NOT NULL) AND ((source_id IS NOT NULL) OR (source_url IS NOT NULL)))))`
- **destination_access_points_coordinate_precision_m_check** (`c`): `CHECK (((coordinate_precision_m IS NULL) OR (coordinate_precision_m > (0)::numeric)))`
- **destination_access_points_point_role_check** (`c`): `CHECK ((point_role = ANY (ARRAY['visitor_entrance'::text, 'visitor_access'::text, 'trailhead'::text, 'boat_landing'::text, 'parking_access'::text, 'other'::text])))`
- **destination_access_points_status_check** (`c`): `CHECK ((status = ANY (ARRAY['needs_review'::text, 'approved'::text, 'withdrawn'::text])))`
- **destination_access_points_destination_id_fkey** (`f`): `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE CASCADE`
- **destination_access_points_source_id_fkey** (`f`): `FOREIGN KEY (source_id) REFERENCES knowledge.knowledge_sources(source_id) ON DELETE RESTRICT`
- **destination_access_points_pkey** (`p`): `PRIMARY KEY (access_point_id)`

## ایندکس‌ها

- `destination_access_points_pkey`: `CREATE UNIQUE INDEX destination_access_points_pkey ON knowledge.destination_access_points USING btree (access_point_id)`
- `ix_access_points_destination_status`: `CREATE INDEX ix_access_points_destination_status ON knowledge.destination_access_points USING btree (destination_id, status)`
- `ix_access_points_geom`: `CREATE INDEX ix_access_points_geom ON knowledge.destination_access_points USING gist (point) WHERE (point IS NOT NULL)`

## سیاست‌های RLS

- `access_points_reviewers`: command=*, roles=[], using=`(identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text) OR identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'catalogue_publish'::text))`, with_check=`(((status <> 'approved'::text) AND identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'candidate_review'::text)) OR identity.has_catalogue_review_capability(identity.current_app_actor_id(), 'catalogue_publish'::text))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **14** از **14**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
