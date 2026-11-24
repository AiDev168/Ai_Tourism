# partner.invitations

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
| 'invitation_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier for a membership invitation. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'organization_id' | 'uuid' | خیر | — | Organization the invite targets. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'email_digest' | 'bytea' | خیر | — | One-way digest of the target email; raw email is not stored in this field. | PostgreSQL 'bytea'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((octet_length(email_digest) = 32)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_direct_identifier / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'token_hash' | 'bytea' | خیر | — | Unique one-way invitation token hash; never return the token hash to users. | PostgreSQL 'bytea'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((octet_length(token_hash) = 32)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | restricted_authentication_or_direct_identifier / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'proposed_role' | 'text' | خیر | — | Role offered: manager, editor, availability_operator, or viewer. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((proposed_role = ANY (ARRAY['manager'::text, 'editor'::text, 'availability_operator'::text, 'viewer'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'invited_by' | 'uuid' | خیر | — | User account that issued the invitation. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'expires_at' | 'timestamp with time zone' | خیر | — | Timestamp after which the invitation cannot be accepted. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. DB CHECK: CHECK ((expires_at > created_at)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'accepted_at' | 'timestamp with time zone' | بله | — | Timestamp of acceptance, if accepted. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. DB CHECK: CHECK (((accepted_at IS NULL) OR (revoked_at IS NULL))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'revoked_at' | 'timestamp with time zone' | بله | — | Timestamp of revocation, if revoked. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. DB CHECK: CHECK (((accepted_at IS NULL) OR (revoked_at IS NULL))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. DB CHECK: CHECK ((expires_at > created_at)) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/019_partner_workspace.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |

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
