# راهنمای اجرای پایلوت محلی Rahgard برای مالک، شرکت و مسافر

## وضعیت و مرز ایمنی

این راهنما برای دموی محلی Issue 27 روی Windows 11 است. PostgreSQL آن از VPS، پایگاه اشتراکی محلی و پایلوت قبلی جداست. داده در volume اختصاصی `rahgard_issue27_pg_<شناسه>` باقی می‌ماند. این اجرا فقط روی loopback گوش می‌دهد و هیچ پورت عمومی ندارد.

در این دمو، ثبت‌نام ایمیل محلی فعال است؛ تحویل SMS، Chat و RAG خاموش‌اند. پنل مدیریت AI Provider سمت سرور در runtime محلی فعال است، ولی تا grant مستقل، TOTP و پیکربندی پروفایل، برای استفاده آماده نیست. MFA از مسیر مشترک Owner و با TOTP واقعی کار می‌کند. هیچ credential زنده یا فراخوانی پولی استفاده نشده است. ورود Owner و پذیرش دستی هنوز باید تکمیل شود.

## پیش‌نیاز

- Windows 11 و PowerShell 5.1
- Docker Desktop با backend لینوکس و image محلی `rahgard-postgres:17-postgis36-vector087`
- Node/npm و `uv` نصب‌شده برای همین مخزن
- پورت‌های loopback `443`، `8801` و `18543` آزاد
- فضای دیسک برای volume پایدار PostgreSQL

Launcher در این محیط از Docker Hub image جدید دریافت نمی‌کند. API با Python محیط مخزن و PWA با build محلی اجرا می‌شوند؛ بنابراین این دمو، image release لینوکس یا CI را تأیید نمی‌کند.

## اجرا و آدرس‌ها

از ریشهٔ مخزن:

```powershell
& .\engineering\pilot\issue27-local-demo\Rahgard-OwnerDemo.ps1 -Action Start -OpenBrowser
```

URLهای واقعی:

- Owner: <https://localhost/admin>
- شرکت: <https://localhost/partners>
- مسافر: <https://localhost/>
- وضعیت API: <https://localhost/health/live>
- PostgreSQL فقط روی loopback: `127.0.0.1:18543`

گواهی HTTPS محلی self-signed است. مرورگر اختصاصی دمو با profile مجزا باز می‌شود و فقط همان مرورگر اجازهٔ نادیده‌گرفتن هشدار گواهی محلی را دارد. رمزها یا cookie مرورگر شخصی استفاده نمی‌شوند.

بررسی وضعیت و توقف امن:

```powershell
& .\engineering\pilot\issue27-local-demo\Rahgard-OwnerDemo.ps1 -Action Status
& .\engineering\pilot\issue27-local-demo\Rahgard-OwnerDemo.ps1 -Action Stop
```

`Stop` فقط فرایندهای ثبت‌شدهٔ همین launcher را پس از تطبیق PID، زمان شروع و command line متوقف می‌کند و سرویس DB همین compose را خاموش می‌کند. volume حذف نمی‌شود. برای ادامه، دوباره `Start` اجرا کنید. از `docker compose down -v` یا حذف دستی volume استفاده نکنید.

## حساب‌های جدا و دسترسی Owner

1. در صفحهٔ ثبت‌نام محلی یک حساب عادی برای مالک بسازید. گذرواژه را در چت، issue، shell history یا log ننویسید.
2. یک حساب عادی دوم برای اپراتور مستقل محلی بسازید. ثبت‌نام عادی هیچ دسترسی مدیریتی نمی‌دهد.
3. در PowerShell محلی، ابزار محدود زیر را اجرا کنید:

   ```powershell
   uv run --project . python .\engineering\pilot\issue27-local-demo\provision_capability.py
   ```

   هدف را حساب Owner و اپراتور را حساب دوم تعیین کنید؛ capability آغازین `admin_overview_read` را تنها با تأیید محلی اعمال کنید. این bootstrap فقط هنگامی مجاز است که هیچ مدیر فعالی وجود نداشته باشد. ابزار ایمیل را فقط در ترمینال می‌گیرد، فقط شناسهٔ حساب را از DB می‌خواند و grant به self را رد می‌کند. این ابزار برای VPS نیست.
4. مالک با حساب خودش وارد `/admin` شود و در بخش MFA، TOTP را در authenticator شخصی فعال کند. seed و recovery code فقط در همان نشست یک‌بار نمایش داده می‌شوند؛ آن‌ها را در password manager نگهداری کنید و screenshot/log نگیرید.
5. برای اعطای مجوز به اپراتور مستقل، helper را دوباره اجرا کنید: این بار هدف حساب اپراتور، operator حساب Owner، و capability برابر `admin_overview_read` باشد. اکنون اپراتور مستقل می‌تواند فقط grantهای مجاز را به دیگران بدهد.
6. با اپراتور مستقل به‌عنوان actor، capabilityهای لازم را جداگانه و همراه دلیل audit به Owner بدهید: `organization_review`, `service_review`, `offer_review`, `candidate_review`, `source_review`, `catalogue_publish`. Self-grant/self-revoke رد می‌شود؛ مجوزهای catalogue و partner در دامنه‌های جدا ثبت می‌شوند.

در صورت خطای دسترسی، حساب عادی را به مدیر تبدیل نکنید. وضعیت capability، MFA/step-up و رویداد audit را بررسی کنید؛ اگر grant لازم نیست، لغو آن را نیز با اپراتور مستقل و دلیل ثبت کنید. از حذف/بازسازی دیتابیس به‌عنوان رفع خطا استفاده نکنید.

## سناریوهای تعاملی مالک باید خودش تأیید کند

- در `/admin` ورود، TOTP/step-up، navigation بر مبنای capability و پیام خطای دسترسی را بررسی کنید.
- در `/partners` با حساب شرکت ثبت‌نام کنید، سازمان و اولین خدمت را ذخیره کنید؛ صفحه را refresh کنید و بازشدن دادهٔ ذخیره‌شده را ببینید. بررسی/فعال‌سازی مستقل را فقط با حساب دارای reviewer capability انجام دهید.
- در Owner Control Center، نامزد/منبع تستی را بررسی و اقدام مجاز را ثبت کنید. هیچ محتوای تستی یا مقصد مصنوعی به live منتقل نمی‌شود.
- در workspace مسافر، درخواست سفر را ثبت، پاسخ/برنامهٔ موقت را ویرایش و ذخیره کنید. پس از logout/login و نیز پس از `Stop` و `Start` باید رکورد محلی باقی بماند. Chat در این اجرا خاموش است؛ پاسخ شبیه‌سازی‌شده را مدل زنده تلقی نکنید.

وضعیت نمونهٔ قبلی در `%LOCALAPPDATA%\Rahgard\Issue27OwnerDemo`: آخرین شمارش ثبت‌شده 1 user، 1 trip، 1 conversation و 0 organization بود. نمونهٔ پذیرش جداگانه در `%LOCALAPPDATA%\Rahgard\Issue27OwnerAcceptance` روی volume مستقل و پورت loopback جدا اجرا شده است؛ در آن هیچ account مدیریتی یا شرکت provision نشده است.

## داده و حریم خصوصی

داده‌ها در پوشهٔ خصوصی `%LOCALAPPDATA%\Rahgard\Issue27OwnerDemo` و volume مخصوص همین پروژه نگهداری می‌شوند. secretها به‌صورت فایل ACL-protected ساخته شده‌اند و مقدارشان چاپ/ثبت نمی‌شود. volume را reset نکنید. اگر قصد حذف این دمو دارید، ابتدا از طریق پشتیبان امن و تأیید مالک دربارهٔ ماندگاری داده تصمیم بگیرید؛ این راهنما فرمان حذف ارائه نمی‌کند.

## محدودیت‌های release

راهنمای جداگانهٔ portability و وضعیت release در [این سند](RAHGARD_ISSUE27_PORTABILITY_FA.md) است.

- DDL زنده، secret یا reviewer زنده، restart/deploy VPS، DNS و Nginx دستکاری نشده‌اند.
- Release زنده در مشاهدهٔ read-only قبلی هنوز image `9b5b07d...` و ledger 0023 داشت؛ این checkout و دموی لوپ‌بک هم‌SHA با VPS نیستند.
- طرح کاتالوگ 0026 از DB محلی ثبت شده است؛ مرجع زندهٔ تاریخی جداست و کامل/تأیید معماری نیست.
- بازیابی archive و مهاجرت 0024–0026 در clone محلی قبلاً با موفقیت انجام شده و در [شواهد R4](../evidence/issue27/R4-restore-migrations-2026-11-25.json) آمده است؛ آن شواهد شامل راه‌اندازی کامل image/API و ورود apex نیست.
- یک VM/سرور Ubuntu مستقل برای relocation مجاز و در دسترس نبود؛ portability کامل، image CI، off-host restore و live Owner login تأیید نشده‌اند.

## پذیرش محلی مستقل روی volume جدا

نسخهٔ اصلی در `%LOCALAPPDATA%\Rahgard\Issue27OwnerDemo` حفظ می‌شود. نمونهٔ پذیرش جداگانه در `%LOCALAPPDATA%\Rahgard\Issue27OwnerAcceptance` قرار دارد و از PostgreSQL volume مستقل استفاده می‌کند. اجرای تأییدشده:

```powershell
& .\engineering\pilot\issue27-local-demo\Rahgard-OwnerDemo.ps1 -Action Start -DataRoot (Join-Path $env:LOCALAPPDATA 'Rahgard\Issue27OwnerAcceptance') -WebPort 18443 -ApiPort 18801 -DatabasePort 19543 -OpenBrowser
& .\engineering\pilot\issue27-local-demo\Rahgard-OwnerDemo.ps1 -Action Status -DataRoot (Join-Path $env:LOCALAPPDATA 'Rahgard\Issue27OwnerAcceptance') -WebPort 18443 -ApiPort 18801 -DatabasePort 19543
& .\engineering\pilot\issue27-local-demo\Rahgard-OwnerDemo.ps1 -Action Stop -DataRoot (Join-Path $env:LOCALAPPDATA 'Rahgard\Issue27OwnerAcceptance') -WebPort 18443 -ApiPort 18801 -DatabasePort 19543
```

نشانی‌ها: `https://localhost:18443/admin`، `https://localhost:18443/partners` و `https://localhost:18443/`. دو حساب محلی مستقل را در خود برنامه بسازید؛ ثبت‌نام عادی هیچ مجوز مدیریتی نمی‌دهد. پس از آن، اپراتور از terminal محلی، helper محدود را برای grant آغازین اجرا می‌کند. ایمیل‌ها فقط در prompt محلی وارد می‌شوند و گذرواژه در command line یا history قرار نمی‌گیرد:

```powershell
$env:RAHGARD_DEMO_ROOT = Join-Path $env:LOCALAPPDATA 'Rahgard\Issue27OwnerAcceptance'
$env:RAHGARD_DEMO_DATABASE_PORT = '19543'
uv run --project . python .\engineering\pilot\issue27-local-demo\provision_capability.py
Remove-Item Env:\RAHGARD_DEMO_ROOT,Env:\RAHGARD_DEMO_DATABASE_PORT
```

bootstrap `admin_overview_read` فقط وقتی مجاز است که هیچ مدیر فعالی وجود نداشته باشد؛ حساب اپراتور مستقل سپس جداگانه provision می‌شود. Owner خودش TOTP را در authenticator ثبت می‌کند. seed و recovery code یک‌بار نمایش داده می‌شوند؛ آن‌ها را در چت، issue یا screenshot قرار ندهید. Owner باید صفحات admin/partners، ذخیره و بازگشایی شرکت/service، بررسی مستقل و traveler save/reopen را دستی مرور کند. تا انجام این مرور انسانی، پذیرش Owner کامل محسوب نمی‌شود.

در این دمو، ثبت‌نام ایمیل محلی فعال است؛ تحویل SMS، Chat و RAG خاموش‌اند. پنل مدیریت AI Provider سمت سرور در runtime محلی فعال است، ولی تا grant مستقل، TOTP و پیکربندی پروفایل، برای استفاده آماده نیست. MFA از مسیر مشترک Owner و با TOTP واقعی کار می‌کند. هیچ credential زنده یا فراخوانی پولی استفاده نشده است. ورود Owner و پذیرش دستی هنوز باید تکمیل شود.
