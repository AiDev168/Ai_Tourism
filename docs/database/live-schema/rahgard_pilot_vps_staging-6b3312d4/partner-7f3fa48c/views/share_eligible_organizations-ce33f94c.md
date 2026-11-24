# partner.share_eligible_organizations

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** View
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
| 'organization_id' | 'uuid' | بله | — | شناسه سازمان گیرنده. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'engineering/pilot/sql/023_partner_trip_responses.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'display_name' | 'text' | بله | — | نام نمایشی گیرنده. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'engineering/pilot/sql/023_partner_trip_responses.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |
| 'organization_type' | 'text' | بله | — | نوع سازمان گیرنده. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/pilot/sql/022_traveler_company_requests.sql', 'engineering/pilot/sql/023_partner_trip_responses.sql', 'backend/app/api/partners.py', 'frontend/src/partners/PartnerWorkspace.tsx', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | confidential_company_data; expose only through tenant and publication policy / organization owner/member for tenant fields; independent platform reviewer for review/audit fields | خواندن: /api/v1/partners organization workspace; filtered by membership/RLS and publication/consent; نوشتن: organization-scoped partner API with CSRF and tenant RLS |

## محدودیت‌ها و ارتباط‌ها

- محدودیتی در `pg_constraint` برای این شیء مشاهده نشد.

## ایندکس‌ها

- ایندکسی مشاهده نشد / برای View قابل اعمال نیست.

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **3**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
