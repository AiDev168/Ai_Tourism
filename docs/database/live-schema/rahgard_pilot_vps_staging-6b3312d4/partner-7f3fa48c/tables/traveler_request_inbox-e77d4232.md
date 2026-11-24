# partner.traveler_request_inbox

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
| 'inbox_event_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier of the organization inbox event. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'organization_id' | 'uuid' | خیر | — | Recipient organization and tenant boundary. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'revision_id' | 'uuid' | خیر | — | Private request revision represented by the inbox event. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'event_kind' | 'text' | خیر | — | Event type: request_shared or request_revised. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. DB CHECK: CHECK ((event_kind = ANY (ARRAY['request_shared'::text, 'request_revised'::text]))) | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp when the inbox event was created. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'viewed_at' | 'timestamp with time zone' | بله | — | Timestamp the authorized member marked the event viewed. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |

## محدودیت‌ها و ارتباط‌ها

- **traveler_request_inbox_event_kind_check** (`c`): `CHECK ((event_kind = ANY (ARRAY['request_shared'::text, 'request_revised'::text])))`
- **traveler_request_inbox_revision_id_fkey** (`f`): `FOREIGN KEY (revision_id) REFERENCES partner.traveler_request_revisions(revision_id) ON DELETE CASCADE`
- **traveler_request_inbox_revision_id_organization_id_fkey** (`f`): `FOREIGN KEY (revision_id, organization_id) REFERENCES partner.traveler_request_revisions(revision_id, organization_id) ON DELETE CASCADE`
- **traveler_request_inbox_pkey** (`p`): `PRIMARY KEY (inbox_event_id)`
- **traveler_request_inbox_revision_id_key** (`u`): `UNIQUE (revision_id)`

## ایندکس‌ها

- `ix_traveler_request_inbox_org_unread`: `CREATE INDEX ix_traveler_request_inbox_org_unread ON partner.traveler_request_inbox USING btree (organization_id, created_at DESC) WHERE (viewed_at IS NULL)`
- `traveler_request_inbox_pkey`: `CREATE UNIQUE INDEX traveler_request_inbox_pkey ON partner.traveler_request_inbox USING btree (inbox_event_id)`
- `traveler_request_inbox_revision_id_key`: `CREATE UNIQUE INDEX traveler_request_inbox_revision_id_key ON partner.traveler_request_inbox USING btree (revision_id)`

## سیاست‌های RLS

- `traveler_inbox_read`: command=r, roles=[], using=`partner.has_active_membership(organization_id, partner.current_actor_id())`, with_check=`—`
- `traveler_inbox_view`: command=w, roles=[], using=`partner.has_active_membership(organization_id, partner.current_actor_id())`, with_check=`partner.has_active_membership(organization_id, partner.current_actor_id())`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **6**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
