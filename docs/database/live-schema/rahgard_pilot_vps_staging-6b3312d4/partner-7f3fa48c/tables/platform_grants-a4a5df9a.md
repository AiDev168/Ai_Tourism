# partner.platform_grants

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** Operator-controlled platform capability grants.
- **دسترسی خواندن:** Capability-check function is used by the server; table is operator-only.
- **دسترسی نوشتن:** No application-role INSERT/UPDATE after migration 0024; no self-service grant route.
- **نمایش عمومی:** Never public.
- **API مدل/مسیر:** No user-facing route; operator provisioning only.
- **فیلد فرم UI:** No UI. Do not expose generic admin CRUD.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'user_id' | 'uuid' | خیر | — | User receiving the platform capability. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'capability' | 'text' | خیر | — | Granted platform permission: organization_review, service_review, or offer_review. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'granted_by' | 'uuid' | خیر | — | Operator user that issued the grant. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'reason' | 'text' | خیر | — | Required audit rationale, 10?1000 characters. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'granted_at' | 'timestamp with time zone' | خیر | 'now()' | Grant timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'revoked_at' | 'timestamp with time zone' | بله | — | Revocation timestamp; a non-NULL value disables the grant. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **platform_grants_capability_check** (`c`): `CHECK ((capability = ANY (ARRAY['organization_review'::text, 'service_review'::text, 'offer_review'::text])))`
- **platform_grants_check** (`c`): `CHECK (((revoked_at IS NULL) OR (revoked_at >= granted_at)))`
- **platform_grants_reason_check** (`c`): `CHECK (((length(btrim(reason)) >= 10) AND (length(btrim(reason)) <= 1000)))`
- **platform_grants_granted_by_fkey** (`f`): `FOREIGN KEY (granted_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **platform_grants_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **platform_grants_pkey** (`p`): `PRIMARY KEY (user_id, capability, granted_at)`

## ایندکس‌ها

- `ix_partner_platform_grants_active`: `CREATE INDEX ix_partner_platform_grants_active ON partner.platform_grants USING btree (user_id, capability) WHERE (revoked_at IS NULL)`
- `platform_grants_pkey`: `CREATE UNIQUE INDEX platform_grants_pkey ON partner.platform_grants USING btree (user_id, capability, granted_at)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **6**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
