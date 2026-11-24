# partner.service_localizations

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نام و توضیح ترجمه‌شده خدمت در زبان‌های قابل پشتیبانی.
- **دسترسی خواندن:** Same organization membership and service-review policy.
- **دسترسی نوشتن:** Written as part of service create/update API; no independent SQL form.
- **نمایش عمومی:** Only approved published content can be public.
- **API مدل/مسیر:** POST/PUT service routes accept locale, display_name and description.
- **فیلد فرم UI:** PartnerWorkspace service name/description fields.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'organization_id' | 'uuid' | خیر | — | مالک سازمانی ترجمه. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'service_id' | 'uuid' | خیر | — | ارجاع به خدمت. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'locale' | 'text' | خیر | — | زبان/محل نمایشی، مانند fa-IR یا en-US بر اساس قرارداد API. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'display_name' | 'text' | خیر | — | نام نمایشی خدمت در آن زبان. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'description' | 'text' | بله | — | توضیحات خدمت در همان زبان. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'content_status' | 'text' | خیر | '[redacted string default]' | Locale content lifecycle: draft, submitted, approved, rejected, or withdrawn. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'reviewed_at' | 'timestamp with time zone' | بله | — | Timestamp of editorial review when present. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp of the latest localization update. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **service_localizations_content_status_check** (`c`): `CHECK ((content_status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'rejected'::text, 'withdrawn'::text])))`
- **service_localizations_display_name_check** (`c`): `CHECK (((length(btrim(display_name)) >= 1) AND (length(btrim(display_name)) <= 240)))`
- **service_localizations_locale_check** (`c`): `CHECK ((locale = ANY (ARRAY['fa-IR'::text, 'en-US'::text, 'ar'::text])))`
- **service_localizations_organization_id_service_id_fkey** (`f`): `FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT`
- **service_localizations_pkey** (`p`): `PRIMARY KEY (service_id, locale)`

## ایندکس‌ها

- `service_localizations_pkey`: `CREATE UNIQUE INDEX service_localizations_pkey ON partner.service_localizations USING btree (service_id, locale)`

## سیاست‌های RLS

- `service_localizations_platform`: command=w, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`, with_check=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`
- `service_localizations_select`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text))`, with_check=`—`
- `service_localizations_write`: command=*, roles=[], using=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text])`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text]) AND (content_status = ANY (ARRAY['draft'::text, 'submitted'::text, 'withdrawn'::text])))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **9**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
