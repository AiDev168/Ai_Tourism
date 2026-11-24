# partner.platform_grants

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نیازمند توضیح دامنه‌ای تأییدشده از کد و مالک محصول
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T11:28:13Z`
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | معنی کسب‌وکاری | قالب/واحد/enum | منبع شواهد | حساسیت/مالک | سطح خواندن/نوشتن |
|---|---|---|---|---|---|---|---|---|
| 'user_id' | 'uuid' | خیر | — | User receiving the platform capability. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: platform reviewer queue or append-only audit; tenant filters apply; نوشتن: review API only for granted operator; company submits evidence only |
| 'capability' | 'text' | خیر | — | Granted platform permission: organization_review, service_review, or offer_review. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((capability = ANY (ARRAY['organization_review'::text, 'service_review'::text, 'offer_review'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: platform reviewer queue or append-only audit; tenant filters apply; نوشتن: review API only for granted operator; company submits evidence only |
| 'granted_by' | 'uuid' | خیر | — | Operator user that issued the grant. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: platform reviewer queue or append-only audit; tenant filters apply; نوشتن: review API only for granted operator; company submits evidence only |
| 'reason' | 'text' | خیر | — | Required audit rationale, 10?1000 characters. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((length(btrim(reason)) >= 10) AND (length(btrim(reason)) <= 1000))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: platform reviewer queue or append-only audit; tenant filters apply; نوشتن: review API only for granted operator; company submits evidence only |
| 'granted_at' | 'timestamp with time zone' | خیر | 'now()' | Grant timestamp. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. DB CHECK: CHECK (((revoked_at IS NULL) OR (revoked_at >= granted_at))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: platform reviewer queue or append-only audit; tenant filters apply; نوشتن: review API only for granted operator; company submits evidence only |
| 'revoked_at' | 'timestamp with time zone' | بله | — | Revocation timestamp; a non-NULL value disables the grant. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. DB CHECK: CHECK (((revoked_at IS NULL) OR (revoked_at >= granted_at))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: platform reviewer queue or append-only audit; tenant filters apply; نوشتن: review API only for granted operator; company submits evidence only |

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
