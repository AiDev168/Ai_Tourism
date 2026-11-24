# partner.memberships

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** عضویت کاربران در یک سازمان و نقش/فعال‌بودن آن‌ها.
- **دسترسی خواندن:** Organization members and reviewer capabilities only where policies allow.
- **دسترسی نوشتن:** Created with company registration or invitation flow; no generic membership editor.
- **نمایش عمومی:** Never public.
- **API مدل/مسیر:** Created internally by POST /organizations; no general membership CRUD route.
- **فیلد فرم UI:** No ordinary user form; owner/member management is not exposed in this workspace.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'membership_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier for the organization membership. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | ارجاع به سازمان عضوپذیر. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'user_id' | 'uuid' | خیر | — | ارجاع به حساب شخص عضو سازمان. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'role' | 'text' | خیر | — | نقش عضو در سازمان؛ محدوده دسترسی از سیاست‌های مجوز استخراج شود. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'status' | 'text' | خیر | '[redacted string default]' | وضعیت عضویت. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'invited_by' | 'uuid' | بله | — | Inviting user when membership originated from an invitation; nullable for owner registration. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'accepted_at' | 'timestamp with time zone' | بله | — | زمان پذیرش عضویت یا دعوت. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'revoked_at' | 'timestamp with time zone' | بله | — | Timestamp that an active membership was revoked; must match revoked status. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **memberships_check** (`c`): `CHECK (((status = 'revoked'::text) = (revoked_at IS NOT NULL)))`
- **memberships_role_check** (`c`): `CHECK ((role = ANY (ARRAY['owner'::text, 'manager'::text, 'editor'::text, 'availability_operator'::text, 'viewer'::text])))`
- **memberships_status_check** (`c`): `CHECK ((status = ANY (ARRAY['invited'::text, 'active'::text, 'revoked'::text, 'suspended'::text])))`
- **memberships_invited_by_fkey** (`f`): `FOREIGN KEY (invited_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **memberships_organization_id_fkey** (`f`): `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- **memberships_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **memberships_pkey** (`p`): `PRIMARY KEY (membership_id)`
- **memberships_organization_id_membership_id_key** (`u`): `UNIQUE (organization_id, membership_id)`
- **memberships_organization_id_user_id_key** (`u`): `UNIQUE (organization_id, user_id)`

## ایندکس‌ها

- `ix_partner_memberships_user_status`: `CREATE INDEX ix_partner_memberships_user_status ON partner.memberships USING btree (user_id, status, organization_id)`
- `memberships_organization_id_membership_id_key`: `CREATE UNIQUE INDEX memberships_organization_id_membership_id_key ON partner.memberships USING btree (organization_id, membership_id)`
- `memberships_organization_id_user_id_key`: `CREATE UNIQUE INDEX memberships_organization_id_user_id_key ON partner.memberships USING btree (organization_id, user_id)`
- `memberships_pkey`: `CREATE UNIQUE INDEX memberships_pkey ON partner.memberships USING btree (membership_id)`

## سیاست‌های RLS

- `memberships_insert_owner_self`: command=a, roles=[], using=`—`, with_check=`((user_id = partner.current_actor_id()) AND (role = 'owner'::text) AND (status = 'active'::text) AND (EXISTS ( SELECT 1    FROM partner.organizations o   WHERE ((o.organization_id = memberships.organization_id) AND (o.created_by = partner.current_actor_id())))))`
- `memberships_read_scoped`: command=r, roles=[], using=`((user_id = partner.current_actor_id()) OR partner.has_active_membership(organization_id, partner.current_actor_id()))`, with_check=`—`
- `memberships_update_scoped`: command=w, roles=[], using=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text])`, with_check=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text])`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **9**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
