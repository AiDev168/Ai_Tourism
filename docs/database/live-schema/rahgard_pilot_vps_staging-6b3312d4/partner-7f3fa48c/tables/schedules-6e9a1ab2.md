# partner.schedules

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** زمان‌بندی خدمت و بازه اعتبار اطلاعات زمانی.
- **دسترسی خواندن:** Organization owner/manager/editor/availability operator under RLS.
- **دسترسی نوشتن:** Create/edit draft schedule; all instants use ISO timestamp and explicit time zone when times exist.
- **نمایش عمومی:** Private unless independently reviewed. Freshness is controlled by observed_at/valid_until.
- **API مدل/مسیر:** POST/PUT /organizations/{organization_id}/schedules[/{schedule_id}]; workspace GET.
- **فیلد فرم UI:** PartnerWorkspace optional schedule form and edit list.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'schedule_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه یکتای زمان‌بندی. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | سازمان مالک زمان‌بندی. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'service_id' | 'uuid' | خیر | — | خدمت مربوط به زمان‌بندی. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'schedule_type' | 'text' | خیر | — | دسته زمان‌بندی و الگوی اجرای آن. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'timezone' | 'text' | بله | — | شناسه منطقه زمانی معتبر IANA، در صورت انطباق با قرارداد. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'starts_at' | 'timestamp with time zone' | بله | — | لحظه یا زمان شروع. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'ends_at' | 'timestamp with time zone' | بله | — | لحظه یا زمان پایان. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'recurrence' | 'jsonb' | بله | — | قاعده تکرار؛ فرمت دقیق از API/SQL. | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'status' | 'text' | خیر | '[redacted string default]' | وضعیت زمان‌بندی. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'observed_at' | 'timestamp with time zone' | بله | — | زمان آخرین مشاهده/تأیید این داده زمانی. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'valid_until' | 'timestamp with time zone' | بله | — | انقضای اعتبار اطلاع زمان‌بندی. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **schedules_check** (`c`): `CHECK (((ends_at IS NULL) OR (starts_at IS NULL) OR (ends_at >= starts_at)))`
- **schedules_check1** (`c`): `CHECK (((valid_until IS NULL) OR (observed_at IS NULL) OR (valid_until >= observed_at)))`
- **schedules_check2** (`c`): `CHECK ((((starts_at IS NULL) AND (ends_at IS NULL)) OR (timezone IS NOT NULL)))`
- **schedules_recurrence_check** (`c`): `CHECK (((recurrence IS NULL) OR (jsonb_typeof(recurrence) = 'object'::text)))`
- **schedules_schedule_type_check** (`c`): `CHECK ((schedule_type = ANY (ARRAY['opening_window'::text, 'departure'::text, 'appointment'::text, 'event'::text, 'other'::text])))`
- **schedules_status_check** (`c`): `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'withdrawn'::text, 'expired'::text])))`
- **schedules_organization_id_service_id_fkey** (`f`): `FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT`
- **schedules_pkey** (`p`): `PRIMARY KEY (schedule_id)`
- **schedules_organization_id_schedule_id_key** (`u`): `UNIQUE (organization_id, schedule_id)`
- **schedules_organization_id_service_id_schedule_id_key** (`u`): `UNIQUE (organization_id, service_id, schedule_id)`

## ایندکس‌ها

- `ix_partner_schedules_service_state`: `CREATE INDEX ix_partner_schedules_service_state ON partner.schedules USING btree (organization_id, service_id, status, starts_at)`
- `schedules_organization_id_schedule_id_key`: `CREATE UNIQUE INDEX schedules_organization_id_schedule_id_key ON partner.schedules USING btree (organization_id, schedule_id)`
- `schedules_organization_id_service_id_schedule_id_key`: `CREATE UNIQUE INDEX schedules_organization_id_service_id_schedule_id_key ON partner.schedules USING btree (organization_id, service_id, schedule_id)`
- `schedules_pkey`: `CREATE UNIQUE INDEX schedules_pkey ON partner.schedules USING btree (schedule_id)`

## سیاست‌های RLS

- `schedules_platform`: command=w, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text)`, with_check=`partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text)`
- `schedules_select`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text))`, with_check=`—`
- `schedules_write`: command=*, roles=[], using=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text, 'availability_operator'::text])`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text, 'availability_operator'::text]) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text, 'withdrawn'::text, 'expired'::text])))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **12**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
