# knowledge.production_culinary_knowledge

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
| 'item_id' | 'uuid' | بله | — | Identifier of the culinary knowledge item. | PostgreSQL 'uuid'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |
| 'item_key' | 'text' | بله | — | Stable canonical key for the culinary knowledge item. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |
| 'category' | 'text' | بله | — | Domain classification for the culinary item, constrained by the import/review taxonomy. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |
| 'record_key' | 'text' | بله | — | Stable dataset-provided key for the imported culinary or destination record. | PostgreSQL 'text'; value range and accepted vocabulary follow listed database constraints and API validation. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype.html](https://www.postgresql.org/docs/17/datatype.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |
| 'names_by_locale' | 'jsonb' | بله | — | Localized culinary item names keyed by locale. | JSON object/array/scalar; exact shape is validated by the consuming contract. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype-json.html](https://www.postgresql.org/docs/17/datatype-json.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |
| 'descriptions_by_locale' | 'jsonb' | بله | — | Localized culinary item descriptions keyed by locale. | JSON object/array/scalar; exact shape is validated by the consuming contract. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype-json.html](https://www.postgresql.org/docs/17/datatype-json.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |
| 'claims' | 'jsonb' | بله | — | Structured claims associated with the content record; each factual claim requires traceable evidence. | JSON object/array/scalar; exact shape is validated by the consuming contract. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype-json.html](https://www.postgresql.org/docs/17/datatype-json.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |
| 'provenance' | 'jsonb' | بله | — | Structured provenance describing the sources/support for the associated published knowledge item. | JSON object/array/scalar; exact shape is validated by the consuming contract. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype-json.html](https://www.postgresql.org/docs/17/datatype-json.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |
| 'updated_at' | 'timestamp with time zone' | بله | — | Timestamp of the last persisted update to this row. | PostgreSQL 'timestamp with time zone'; timezone presence is part of the type and must not be inferred. This is a projection/view column; it is not an independent writable field. | 'docs/database/live-schema/catalog_snapshot.json', 'engineering/database-prep/sql/010_task31_content_privacy_full_itinerary.sql', 'backend/app/api/catalogue_review.py', 'backend/app/modules/retrieval/contracts.py', [https://www.postgresql.org/docs/17/datatype-datetime.html](https://www.postgresql.org/docs/17/datatype-datetime.html) | internal_catalogue_or_recommendation_metadata / catalogue/source editor or import operator; publication fields require an authorized reviewer | خواندن: published catalogue/retrieval API with source/publication filters; نوشتن: database view only; no direct end-user writes |

## محدودیت‌ها و ارتباط‌ها

- محدودیتی در `pg_constraint` برای این شیء مشاهده نشد.

## ایندکس‌ها

- ایندکسی مشاهده نشد / برای View قابل اعمال نیست.

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **9**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
