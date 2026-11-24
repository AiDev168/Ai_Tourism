# partner.offers

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** پیشنهاد تجاری/بسته خدمت که ممکن است زمان‌بندی و ظرفیت داشته باشد.
- **دسترسی خواندن:** Organization owner/manager/editor under RLS.
- **دسترسی نوشتن:** Create/edit unpublished offer; capacity is non-negative and published state is reviewer-controlled.
- **نمایش عمومی:** Private until separate publication.
- **API مدل/مسیر:** POST/PUT /organizations/{organization_id}/offers[/{offer_id}]; workspace GET.
- **فیلد فرم UI:** PartnerWorkspace optional offer form and edit list.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'offer_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه یکتای پیشنهاد. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | سازمان مالک پیشنهاد. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'service_id' | 'uuid' | خیر | — | خدمت پایه پیشنهاد. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'schedule_id' | 'uuid' | بله | — | زمان‌بندی مرتبط، در صورت وجود. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'offer_type' | 'text' | خیر | — | نوع پیشنهاد با قرارداد ثابت. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'status' | 'text' | خیر | '[redacted string default]' | وضعیت پیشنهاد. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'valid_from' | 'timestamp with time zone' | بله | — | آغاز دوره اعتبار پیشنهاد. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'valid_until' | 'timestamp with time zone' | بله | — | پایان دوره اعتبار پیشنهاد. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'capacity_limit' | 'integer' | بله | — | حداکثر ظرفیت قابل ارائه؛ واحد از قرارداد API. | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'created_by' | 'uuid' | خیر | — | User account that created the offer. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp of the latest editable offer change. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'published_at' | 'timestamp with time zone' | بله | — | Publication timestamp; a published offer must have this value and publication is reviewer-controlled. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **offers_capacity_limit_check** (`c`): `CHECK (((capacity_limit IS NULL) OR (capacity_limit >= 0)))`
- **offers_check** (`c`): `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- **offers_check1** (`c`): `CHECK (((status <> 'published'::text) OR (published_at IS NOT NULL)))`
- **offers_offer_type_check** (`c`): `CHECK (((length(btrim(offer_type)) >= 1) AND (length(btrim(offer_type)) <= 80)))`
- **offers_status_check** (`c`): `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'published'::text, 'suspended'::text, 'withdrawn'::text, 'rejected'::text])))`
- **offers_created_by_fkey** (`f`): `FOREIGN KEY (created_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **offers_organization_id_service_id_fkey** (`f`): `FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT`
- **offers_organization_id_service_id_schedule_id_fkey** (`f`): `FOREIGN KEY (organization_id, service_id, schedule_id) REFERENCES partner.schedules(organization_id, service_id, schedule_id) ON DELETE RESTRICT`
- **offers_pkey** (`p`): `PRIMARY KEY (offer_id)`
- **offers_organization_id_offer_id_key** (`u`): `UNIQUE (organization_id, offer_id)`
- **offers_organization_id_offer_id_schedule_id_key** (`u`): `UNIQUE (organization_id, offer_id, schedule_id)`

## ایندکس‌ها

- `ix_partner_offers_service_state`: `CREATE INDEX ix_partner_offers_service_state ON partner.offers USING btree (organization_id, service_id, status, valid_from, valid_until)`
- `offers_organization_id_offer_id_key`: `CREATE UNIQUE INDEX offers_organization_id_offer_id_key ON partner.offers USING btree (organization_id, offer_id)`
- `offers_organization_id_offer_id_schedule_id_key`: `CREATE UNIQUE INDEX offers_organization_id_offer_id_schedule_id_key ON partner.offers USING btree (organization_id, offer_id, schedule_id)`
- `offers_pkey`: `CREATE UNIQUE INDEX offers_pkey ON partner.offers USING btree (offer_id)`

## سیاست‌های RLS

- `offers_platform`: command=w, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text)`, with_check=`partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text)`
- `offers_select`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text))`, with_check=`—`
- `offers_write`: command=*, roles=[], using=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text])`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text]) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text, 'withdrawn'::text, 'rejected'::text])) AND (published_at IS NULL))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **13**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
