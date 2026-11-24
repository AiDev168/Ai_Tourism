# partner.memberships

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نیازمند توضیح دامنه‌ای تأییدشده از کد و مالک محصول
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T11:28:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | معنی کسب‌وکاری | قالب/واحد/enum | منبع شواهد | حساسیت/مالک | سطح خواندن/نوشتن |
|---|---|---|---|---|---|---|---|---|
| 'membership_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier for the organization membership. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'organization_id' | 'uuid' | خیر | — | ارجاع به سازمان عضوپذیر. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'user_id' | 'uuid' | خیر | — | ارجاع به حساب شخص عضو سازمان. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'role' | 'text' | خیر | — | نقش عضو در سازمان؛ محدوده دسترسی از سیاست‌های مجوز استخراج شود. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((role = ANY (ARRAY['owner'::text, 'manager'::text, 'editor'::text, 'availability_operator'::text, 'viewer'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'status' | 'text' | خیر | '[redacted string default]' | وضعیت عضویت. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK (((status = 'revoked'::text) = (revoked_at IS NOT NULL))) \| CHECK ((status = ANY (ARRAY['invited'::text, 'active'::text, 'revoked'::text, 'suspended'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'invited_by' | 'uuid' | بله | — | Inviting user when membership originated from an invitation; nullable for owner registration. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'accepted_at' | 'timestamp with time zone' | بله | — | زمان پذیرش عضویت یا دعوت. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'revoked_at' | 'timestamp with time zone' | بله | — | Timestamp that an active membership was revoked; must match revoked status. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. DB CHECK: CHECK (((status = 'revoked'::text) = (revoked_at IS NOT NULL))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |

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
