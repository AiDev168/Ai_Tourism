# partner.service_destinations

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** Relationship from a company service to a canonical published destination.
- **دسترسی خواندن:** Organization membership RLS; destination must resolve through production catalogue view.
- **دسترسی نوشتن:** POST only in current API; relationship is not a publication decision.
- **نمایش عمومی:** Private draft link; destination identity remains canonical.
- **API مدل/مسیر:** POST /organizations/{organization_id}/services/{service_id}/destinations.
- **فیلد فرم UI:** PartnerWorkspace optional destination-link form; only API-returned published choices.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'organization_id' | 'uuid' | خیر | — | Owning organization and tenant boundary. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'service_id' | 'uuid' | خیر | — | Organization-owned service related to the canonical destination. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'destination_id' | 'bigint' | خیر | — | Canonical destination identifier; API accepts only currently published destinations. | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'relation_type' | 'text' | خیر | — | Relationship: at, serves, near, or route_endpoint. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'evidence_note' | 'text' | بله | — | Optional partner-supplied context for this association; not verification evidence by itself. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'status' | 'text' | خیر | '[redacted string default]' | Review lifecycle: draft, submitted, approved, rejected, or withdrawn. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **service_destinations_relation_type_check** (`c`): `CHECK ((relation_type = ANY (ARRAY['at'::text, 'serves'::text, 'near'::text, 'route_endpoint'::text])))`
- **service_destinations_status_check** (`c`): `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'rejected'::text, 'withdrawn'::text])))`
- **service_destinations_destination_id_fkey** (`f`): `FOREIGN KEY (destination_id) REFERENCES knowledge.destinations(destination_id) ON DELETE RESTRICT`
- **service_destinations_organization_id_service_id_fkey** (`f`): `FOREIGN KEY (organization_id, service_id) REFERENCES partner.services(organization_id, service_id) ON DELETE RESTRICT`
- **service_destinations_pkey** (`p`): `PRIMARY KEY (service_id, destination_id)`

## ایندکس‌ها

- `ix_partner_service_destinations_destination`: `CREATE INDEX ix_partner_service_destinations_destination ON partner.service_destinations USING btree (destination_id, status)`
- `service_destinations_pkey`: `CREATE UNIQUE INDEX service_destinations_pkey ON partner.service_destinations USING btree (service_id, destination_id)`

## سیاست‌های RLS

- `service_destinations_platform`: command=w, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`, with_check=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`
- `service_destinations_select`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text))`, with_check=`—`
- `service_destinations_write`: command=*, roles=[], using=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text])`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text]) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text, 'rejected'::text, 'withdrawn'::text])))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **7**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
