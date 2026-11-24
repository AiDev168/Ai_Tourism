# partner.invitations

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** Hashed, expiring organization membership invitations.
- **دسترسی خواندن:** Organization owner/manager only under RLS.
- **دسترسی نوشتن:** No user-facing invitation route currently registered.
- **نمایش عمومی:** Never public; token/email digest are sensitive.
- **API مدل/مسیر:** No application endpoint found in current partner router.
- **فیلد فرم UI:** No UI in this milestone.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'invitation_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier for a membership invitation. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | Organization the invite targets. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'email_digest' | 'bytea' | خیر | — | One-way digest of the target email; raw email is not stored in this field. | دادهٔ دودویی؛ مقدار خام نباید در این مستندات نمایش داده شود |
| 'token_hash' | 'bytea' | خیر | — | Unique one-way invitation token hash; never return the token hash to users. | دادهٔ دودویی؛ مقدار خام نباید در این مستندات نمایش داده شود |
| 'proposed_role' | 'text' | خیر | — | Role offered: manager, editor, availability_operator, or viewer. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'invited_by' | 'uuid' | خیر | — | User account that issued the invitation. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'expires_at' | 'timestamp with time zone' | خیر | — | Timestamp after which the invitation cannot be accepted. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'accepted_at' | 'timestamp with time zone' | بله | — | Timestamp of acceptance, if accepted. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'revoked_at' | 'timestamp with time zone' | بله | — | Timestamp of revocation, if revoked. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **invitations_check** (`c`): `CHECK ((expires_at > created_at))`
- **invitations_check1** (`c`): `CHECK (((accepted_at IS NULL) OR (revoked_at IS NULL)))`
- **invitations_email_digest_check** (`c`): `CHECK ((octet_length(email_digest) = 32))`
- **invitations_proposed_role_check** (`c`): `CHECK ((proposed_role = ANY (ARRAY['manager'::text, 'editor'::text, 'availability_operator'::text, 'viewer'::text])))`
- **invitations_token_hash_check** (`c`): `CHECK ((octet_length(token_hash) = 32))`
- **invitations_invited_by_fkey** (`f`): `FOREIGN KEY (invited_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **invitations_organization_id_fkey** (`f`): `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- **invitations_pkey** (`p`): `PRIMARY KEY (invitation_id)`
- **invitations_token_hash_key** (`u`): `UNIQUE (token_hash)`

## ایندکس‌ها

- `invitations_pkey`: `CREATE UNIQUE INDEX invitations_pkey ON partner.invitations USING btree (invitation_id)`
- `invitations_token_hash_key`: `CREATE UNIQUE INDEX invitations_token_hash_key ON partner.invitations USING btree (token_hash)`
- `ix_partner_invitations_org_expiry`: `CREATE INDEX ix_partner_invitations_org_expiry ON partner.invitations USING btree (organization_id, expires_at)`

## سیاست‌های RLS

- `invitations_insert_manager`: command=a, roles=[], using=`—`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text]) AND (invited_by = partner.current_actor_id()))`
- `invitations_select_manager`: command=r, roles=[], using=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text])`, with_check=`—`
- `invitations_update_manager`: command=w, roles=[], using=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text])`, with_check=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text])`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **10**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
