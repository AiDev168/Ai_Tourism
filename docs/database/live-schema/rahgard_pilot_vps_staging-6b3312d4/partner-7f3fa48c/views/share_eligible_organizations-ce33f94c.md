# partner.share_eligible_organizations

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** View
- **شرح:** نمای فقط‌خواندنی سازمان‌های فعال و تأییدشده که می‌توانند درخواست مسافر دریافت کنند.
- **دسترسی خواندن:** Application can read the view; rows are not directly writable.
- **دسترسی نوشتن:** Read-only view.
- **نمایش عمومی:** Visible as recipient choices only through traveler share-options endpoint after authentication.
- **API مدل/مسیر:** GET /trips/{trip_id}/company-share-options reads this projection.
- **فیلد فرم UI:** TravelerWorkspace company-sharing selector; absent when there are no eligible organizations.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'organization_id' | 'uuid' | بله | — | شناسه سازمان گیرنده. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'display_name' | 'text' | بله | — | نام نمایشی گیرنده. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'organization_type' | 'text' | بله | — | نوع سازمان گیرنده. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |

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
