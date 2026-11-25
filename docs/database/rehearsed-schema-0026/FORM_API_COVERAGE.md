# نگاشت نقش، فرم و API — طرح تمرین‌شدهٔ 0026

این فهرست از route، مدل و فرم کد همین checkout استخراج شده است؛ اثبات استفادهٔ زنده در VPS نیست. ستون‌های پایگاه داده لزوماً فرم ندارند.

| نقش/مالک داده | مسیر رابط | سطح API/ماژول | دستهٔ داده | سیاست دسترسی و انتشار |
|---|---|---|---|---|
| مسافر | `/` و workspace سفر | `backend/app/api/traveler.py`, `assistant.py`; ماژول‌های `travel`, `conversation`, `recommendation` | درخواست سفر، trip، itinerary، گفتگو | کاربر احراز‌شده؛ مالکیت trip/conversation سمت سرور؛ itinerary موقت باید صریحاً unverified بماند |
| عضو شرکت | `/partners` | `backend/app/api/partner.py` و routeهای درخواست شرکت | سازمان، خدمت، localization، مقصد مرتبط، زمان‌بندی، offer/price/availability | عضویت و RLS محدود به tenant؛ ارسال برای بررسی با تأیید مستقل؛ اطلاعات مسافر تنها پس از share/consent |
| بازبین شرکت | `/admin` | routeهای partner review و capability guard | پروندهٔ بررسی سازمان/خدمت/offer و audit | capability اختصاصی؛ MFA/step-up در تنظیمات حفاظت‌شده؛ خودتأییدی ممنوع |
| بازبین کاتالوگ | `/admin` | routeهای catalogue candidate/source/review/publication | نامزد واردشده، منبع، تصمیم بازبینی و انتشار | grants مستقل؛ انتشار فقط با پیش‌شرط provenance/review؛ ورودی خام عمومی نمی‌شود |
| مالک/اپراتور سامانه | `/admin` | `backend/app/api/platform_admin*`, `admin_guards.py`, provisioning CLI | نمای محدود سامانه و grants مجاز | MFA، step-up، audit و اصل حداقل دسترسی؛ هیچ self-registration برای نقش مدیر وجود ندارد |
| فرایند مهاجرت/عملیات | UI عمومی ندارد | `engineering/pilot/sql`, `system.schema_migrations`, ابزارهای backup/release | ledger، checksum، نقش‌ها و سیاست‌ها | فقط عملیات کنترل‌شده؛ هیچ فرم SQL عمومی یا ویرایش مستقیم ledger |
| سامانه/extension | UI عمومی ندارد | زمان‌سنجی، UUID، hash، PostGIS catalog | شناسه/مهرزمان/فرادادهٔ خودکار | خودکار یا read-only؛ PostGIS طبق مستند رسمی، نه فیلد تجاری |

## تفکیک ورودی و خواندن

- **قابل‌ویرایش توسط مسافر:** ورودی‌های trip و ویرایش‌های مجاز itinerary در API مسافر؛ پیشنهاد LLM منبع قطعی facts نیست.
- **قابل‌ویرایش توسط tenant:** فرم‌های سازمان و خدمت و جزئیات تجاری از `/partners`; هر write باید به organization عضویت‌یافته متصل باشد.
- **صرفاً پس از بررسی:** verification/review/publication و ثبت audit؛ شرکت نمی‌تواند خودش را تأیید یا داده را public کند.
- **واردشده/دارای منشأ:** کاندیدا و source evidence؛ خام ورودی با canonical منتشرشده یکی نیست.
- **خودکار/سیستمی:** شناسه، revision، زمان‌ها، digest، session/MFA state و migration ledger؛ کنترل مستقیم فرم ندارد.
- **محسوب‌شده:** viewها و خروجی‌های فهرست؛ نگاشت lineage در [manifest](manifest.json) و سند هر view است.

## پوشش و محدودیت

این نگاشت route-to-domain است، نه اثبات پوشش تک‌تک 1,132 رخداد ستون. برای جزئیات منبع هر ستون به فایل رابطه در [فهرست snapshot](README.md) رجوع کنید. موارد `not assessed` یا بی‌معنا از کد به‌صورت صریح حل‌نشده می‌مانند. تغییر فرم یا schema فقط پس از اثبات نیاز و تست دسترسی انجام می‌شود.
