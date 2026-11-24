# knowledge.production_destination_categories

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
| 'category_id' | 'bigint' | بله | — | Destination category associated with the canonical destination. | PostgreSQL 'bigint'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |
| 'category_key' | 'text' | بله | — | Stable machine-readable category identifier. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |
| 'name_fa' | 'text' | بله | — | Persian display label for the destination category. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |
| 'description' | 'text' | بله | — | Human-readable description of the associated destination/service/category; source and publication state govern public use. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | public_only_when_published_and_source_eligible / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |
| 'sort_order' | 'smallint' | بله | — | Stable ordering value used when presenting categories. | PostgreSQL 'smallint'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/001_core_schema.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |

## محدودیت‌ها و ارتباط‌ها

- محدودیتی در `pg_constraint` برای این شیء مشاهده نشد.

## ایندکس‌ها

- ایندکسی مشاهده نشد / برای View قابل اعمال نیست.

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **5**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
