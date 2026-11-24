# partner.branches

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** Optional service-location record with explicit coordinate role.
- **دسترسی خواندن:** RLS is present; no branch endpoint is implemented in the current API router.
- **دسترسی نوشتن:** No user-facing write API currently found.
- **نمایش عمومی:** Not public absent later review/publication. Coordinates are not presumed to be entrances.
- **API مدل/مسیر:** No endpoint in backend/app/api/partners.py.
- **فیلد فرم UI:** No form in this workspace; location entry is intentionally absent.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'branch_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier for an organization branch/service location. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | Owning organization and tenant boundary. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'display_name' | 'text' | خیر | — | Human-readable name of the branch. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'address_text' | 'text' | بله | — | Partner-provided address text; not independently geocoded. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'admin_area_id' | 'bigint' | بله | — | Reference to a canonical administrative-area record when resolved. | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'location' | 'geometry(Point,4326)' | بله | — | PostGIS Point in SRID 4326; the role column determines whether it is an approximate reference, service location, or entrance. | نوع سفارشی یا قالب وابسته به دامنه؛ اعتبارسنجی API/enum را بررسی کنید |
| 'location_role' | 'text' | خیر | '[redacted string default]' | Coordinate role: service_location, entrance, approximate_reference, or unknown; entrance requires a coordinate source. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'coordinate_source' | 'text' | بله | — | Provenance for coordinates; required for an entrance role. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'contact_public' | 'text' | بله | — | Partner-provided contact detail intended for public display only after applicable review. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'status' | 'text' | خیر | '[redacted string default]' | Lifecycle state: draft, submitted, approved, suspended, or withdrawn. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'updated_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp of the latest profile update. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **branches_check** (`c`): `CHECK (((location IS NULL) OR (location_role <> 'unknown'::text)))`
- **branches_check1** (`c`): `CHECK (((location_role <> 'entrance'::text) OR ((location IS NOT NULL) AND (coordinate_source IS NOT NULL))))`
- **branches_display_name_check** (`c`): `CHECK (((length(btrim(display_name)) >= 1) AND (length(btrim(display_name)) <= 240)))`
- **branches_location_role_check** (`c`): `CHECK ((location_role = ANY (ARRAY['service_location'::text, 'entrance'::text, 'approximate_reference'::text, 'unknown'::text])))`
- **branches_status_check** (`c`): `CHECK ((status = ANY (ARRAY['draft'::text, 'submitted'::text, 'approved'::text, 'suspended'::text, 'withdrawn'::text])))`
- **branches_admin_area_id_fkey** (`f`): `FOREIGN KEY (admin_area_id) REFERENCES geo.admin_areas(admin_area_id) ON DELETE RESTRICT`
- **branches_organization_id_fkey** (`f`): `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- **branches_pkey** (`p`): `PRIMARY KEY (branch_id)`
- **branches_organization_id_branch_id_key** (`u`): `UNIQUE (organization_id, branch_id)`

## ایندکس‌ها

- `branches_organization_id_branch_id_key`: `CREATE UNIQUE INDEX branches_organization_id_branch_id_key ON partner.branches USING btree (organization_id, branch_id)`
- `branches_pkey`: `CREATE UNIQUE INDEX branches_pkey ON partner.branches USING btree (branch_id)`
- `ix_partner_branches_location`: `CREATE INDEX ix_partner_branches_location ON partner.branches USING gist (location) WHERE (location IS NOT NULL)`
- `ix_partner_branches_org_status`: `CREATE INDEX ix_partner_branches_org_status ON partner.branches USING btree (organization_id, status)`

## سیاست‌های RLS

- `branches_insert_editor`: command=a, roles=[], using=`—`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text]) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text])) AND (status <> 'approved'::text))`
- `branches_platform_review`: command=w, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`, with_check=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`
- `branches_select_member`: command=r, roles=[], using=`partner.has_active_membership(organization_id, partner.current_actor_id())`, with_check=`—`
- `branches_select_reviewer`: command=r, roles=[], using=`partner.has_platform_capability(partner.current_actor_id(), 'service_review'::text)`, with_check=`—`
- `branches_update_editor`: command=w, roles=[], using=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text])`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text]) AND (status = ANY (ARRAY['draft'::text, 'submitted'::text, 'suspended'::text, 'withdrawn'::text])))`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **12**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
