# partner.services

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** خدمات قابل ارائه توسط سازمان؛ اطلاعات عمومی خدمت از قرارداد انتشار جداست.
- **دسترسی خواندن:** Active organization owner/manager/editor through membership RLS.
- **دسترسی نوشتن:** Create/update private draft or submitted values; service key is generated server-side.
- **نمایش عمومی:** Private until separately reviewed and published.
- **API مدل/مسیر:** POST/PUT /organizations/{organization_id}/services[/{service_id}]; GET /organizations/{organization_id}/workspace.
- **فیلد فرم UI:** PartnerWorkspace first-service form and editable service list.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'service_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه یکتای خدمت. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | سازمان مالک خدمت. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'branch_id' | 'uuid' | بله | — | شعبه مرتبط، اگر خدمت شعبه‌محور باشد. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'service_type' | 'text' | خیر | — | نوع خدمت با مقادیر مجاز تعریف‌شده در API/دیتابیس. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'service_key' | 'text' | خیر | — | شناسه/کلید کسب‌وکاری خدمت نزد سازمان. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'status' | 'text' | خیر | '[redacted string default]' | وضعیت چرخه عمر خدمت. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'public_fields' | 'jsonb' | خیر | '[redacted string default]' | فراداده/فیلدهای عمومی‌شدنی خدمت؛ کلیدهای JSON باید جداگانه مستند شوند. | ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود |
| 'internal_notes' | 'text' | بله | — | Private organization-side notes; never part of public service output. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'created_by' | 'uuid' | خیر | — | کاربر ثبت‌کننده خدمت. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | زمان ایجاد خدمت. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp of the latest service change. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'published_at' | 'timestamp with time zone' | بله | — | Publication timestamp; required only for published state and set by an authorized review path. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **services_check** (`c`): `CHECK (((status <> 'published'::text) OR (published_at IS NOT NULL)))`
- **services_public_fields_check** (`c`): `CHECK ((jsonb_typeof(public_fields) = 'object'::text))`
- **services_service_key_check** (`c`): `CHECK (((length(btrim(service_key)) >= 1) AND (length(btrim(service_key)) <= 160)))`
- **services_service_type_check** (`c`): `CHECK (((length(btrim(service_type)) >= 1) AND (length(btrim(service_type)) <= 80)))`
- **services_status_check** (`c`): `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'published'::text, 'suspended'::text, 'withdrawn'::text, 'rejected'::text])))`
- **services_created_by_fkey** (`f`): `FOREIGN KEY (created_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **services_organization_id_branch_id_fkey** (`f`): `FOREIGN KEY (organization_id, branch_id) REFERENCES partner.branches(organization_id, branch_id) ON DELETE RESTRICT`
- **services_organization_id_fkey** (`f`): `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- **services_pkey** (`p`): `PRIMARY KEY (service_id)`
- **services_organization_id_service_id_key** (`u`): `UNIQUE (organization_id, service_id)`
- **services_organization_id_service_key_key** (`u`): `UNIQUE (organization_id, service_key)`

## ایندکس‌ها

- `ix_partner_services_org_status`: `CREATE INDEX ix_partner_services_org_status ON partner.services USING btree (organization_id, status, updated_at DESC)`
- `services_organization_id_service_id_key`: `CREATE UNIQUE INDEX services_organization_id_service_id_key ON partner.services USING btree (organization_id, service_id)`
- `services_organization_id_service_key_key`: `CREATE UNIQUE INDEX services_organization_id_service_key_key ON partner.services USING btree (organization_id, service_key)`
- `services_pkey`: `CREATE UNIQUE INDEX services_pkey ON partner.services USING btree (service_id)`

## سیاست‌های RLS

- `services_insert_editor`: command=a, roles=[], using=`—`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text]) AND (created_by = partner.current_actor_id()) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text])) AND (published_at IS NULL))`
- `services_platform_review`: command=w, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`, with_check=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`
- `services_select_member`: command=r, roles=[], using=`partner.has_active_membership(organization_id, partner.current_actor_id())`, with_check=`—`
- `services_select_reviewer`: command=r, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`, with_check=`—`
- `services_update_editor`: command=w, roles=[], using=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text]) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text])))`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text]) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text])) AND (published_at IS NULL))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **12**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
