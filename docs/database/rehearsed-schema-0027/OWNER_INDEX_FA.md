# راهنمای مالک: مرجع پایگاه‌دادهٔ Issue 27

## دامنه و وضعیت

- [مرجع زندهٔ تاریخی](../live-schema/README.md): snapshot فقط‌خواندنی قبلی PostgreSQL 17 VPS؛ این مرجع با دیتابیس local یکی نیست.
- [ماتریس معماری و استفاده](../architecture-usage/ARCHITECTURE_AND_USAGE_REVIEW.md): شمارش occurrence، منبع مهاجرت، روابط و تصمیم‌های نگهداری/بررسی؛ اثبات ضرورت معماری نیست.
- [شاخص coverage/glossary](../architecture-usage/glossary_coverage.json): وضعیت baseline؛ 902 شکاف post-0026 طبق manifest زمان صدور گزارش، ستون business لازم محسوب نمی‌شوند.
- [فرهنگ دادهٔ rehearsed 0024–0026](../rehearsed-schema-0026/README.md) و [فهرست فارسی نقش‌ها و فرم‌ها](../rehearsed-schema-0026/OWNER_INDEX_FA.md): clone محلی قبلی؛ نه snapshot زنده.
- [فهرست فیلدهای AI Provider پس از migration 0027](PROVIDER_ADMIN_FIELD_REFERENCE.md): قرارداد دقیق از SQL/code و local Issue27OwnerAcceptance؛ نه production.

## فرم‌ها و مسئولیت داده

فیلدهای Owner، شرکت و مسافر در Form/API coverage مرجع 0026 فهرست شده‌اند. تنظیم provider یک سطح دسترسی جدا از مدیریت شرکت/catalogue است؛ grant آن فقط به حسابی داده می‌شود که از قبل platform-admin باشد. MFA از جدول و مسیر مشترک Owner/reviewer در migration 0026 می‌آید. migration 0027 جدول MFA موازی نمی‌سازد. مقدار secret در PostgreSQL نیست؛ `secret_ref` فقط به فایل رمز‌شدهٔ vault اشاره دارد.

## حدود تأیید

- هر توضیح فقط با migration، check/FK، کد API و رابط قابل استناد افزوده شود.
- viewها به lineage/عبارت مبدأ ارجاع می‌دهند؛ PostGIS به مستند رسمی و fieldهای سیستم به مالک فنی.
- منشأ واقعی ردیف‌ها، نیاز کسب‌وکار و تأیید معماری از روی شمارش ستون‌ها استنتاج نمی‌شود.
- migration 0027 فقط روی volume محلی/isolated بررسی شده است. هیچ اجرای live، grant زنده، secret زنده یا انتشار provider انجام نشده است.
