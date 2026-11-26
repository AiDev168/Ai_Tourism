# آموزش کاربردی رهگرد برای مالک، شرکت و مسافر

[فهرست اصلی](README.md) — مبنای کد cab603a7d40cfa35dd20de2ffb12a336d84f56ff

## محیط درست
Windows فقط توسعه و پذیرش؛ VPS مرجع داده واقعی. پایلوت گزارش‌شده https://localhost:18443/، /admin و /partners است. 200 اثبات ورود نیست. https://hinaa.ir/admin هدف بعد از انتشار است، نه نسخه پذیرفته‌شده فعلی. داده یا کلید واقعی سرور در دمو استفاده نشود.

## اجرای Windows
از ریشه مخزن:
```powershell
& .\engineering\pilot\issue27-local-demo\Rahgard-OwnerDemo.ps1 -Action Status -DataRoot (Join-Path $env:LOCALAPPDATA 'Rahgard\Issue27OwnerAcceptance') -WebPort 18443 -ApiPort 18801 -DatabasePort 19543
```
اگر متوقف است همین فرمان را با -Action Start -OpenBrowser اجرا کنید. Stop با همان DataRoot و پورت‌ها حجم داده را نگه می‌دارد. گواهی محلی self-signed فقط در مرورگر اختصاصی؛ در سایت عمومی هشدار TLS را نادیده نگیرید.

## Owner و اپراتور
۱. دو حساب عادی محلی مستقل در خود برنامه بسازید؛ ثبت‌نام مدیر نمی‌سازد.
۲. در PowerShell فقط برای همین دمو:
```powershell
$env:RAHGARD_DEMO_ROOT = Join-Path $env:LOCALAPPDATA 'Rahgard\Issue27OwnerAcceptance'
$env:RAHGARD_DEMO_DATABASE_PORT = '19543'
uv run --project . python .\engineering\pilot\issue27-local-demo\provision_capability.py
Remove-Item Env:\RAHGARD_DEMO_ROOT,Env:\RAHGARD_DEMO_DATABASE_PORT
```
در prompt: grant، admin_overview_read، ایمیل هدف Owner، ایمیل اپراتور مستقل، دلیل غیرمحرمانه، APPLY_LOCAL_CAPABILITY. bootstrap فقط بدون مدیر فعال. بعد طبق راهنمای اصلی، اپراتور مستقل admin_overview_read می‌گیرد و مجوزهای organization_review، candidate_review، source_review، catalogue_publish و در صورت نیاز service_review/offer_review و ai_provider_admin جداگانه اعطا می‌شوند. خوداعطایی و SQL دستی ممنوع. اگر ابزار رد کرد، متوقف شوید.
۳. در https://localhost:18443/admin با Owner وارد شوید. MFA را با authenticator فعال کنید. recovery code را خصوصی نگه دارید. عملیات حساس step-up همان نشست پنج‌دقیقه‌ای می‌خواهد.
۴. منوها بر حسب قابلیت: شرکت‌ها، مقاصد، کاربران/مجوزها، سلامت و AI. نبود منو ممکن است ناشی از نبود مجوز یا قابلیت باشد. شرکت خود را تأیید نکنید. تصمیم‌های احراز، پذیرش و فعال‌سازی مستقل‌اند.
۵. تنظیم AI نیازمند capability جدا، Vault و allowlist آماده است. [فرم‌ها](DATA_ENTRY_FA.md) را ببینید.

## شرکت
با حساب مستقل در /partners ثبت سازمان، خدمت، ارتباط مقصد، برنامه، پیشنهاد، قیمت، ظرفیت و ارسال مدارک را انجام دهید. همه اطلاعات اختیاری را فقط اگر کاربرد دارد پر کنید. بعد از ذخیره refresh و ورود دوباره را امتحان کنید. برای دریافت درخواست مسافر شرکت باید واجد شرایط باشد و مسافر صریحاً رضایت دهد. شرکت فقط نسخه مشترک را می‌بیند و قبول یا پیشنهاد متقابل می‌دهد؛ برنامه مسافر را تغییر نمی‌دهد.

## مسافر
در / وارد شوید. نمونه تست: «مشهد به شیراز، ۵ روز، ۵ نفر، بودجه کل ۳۰ میلیون تومان، تاریخ و باغ». تاریخ واقعی، مبدأ، مقصد، تعداد و واحد بودجه را در فرم تأیید کنید. Chat/RAG در نمونه محلی ممکن است خاموش باشد؛ پاسخ شبیه‌سازی‌شده inference واقعی نیست. اگر کاتالوگ منتشرشده خالی است، برنامه موقت را تأییدشده معرفی نکنید. ذخیره/ویرایش و بازگشایی پس از ورود مجدد را بررسی کنید. اشتراک با شرکت اختیاری و نیازمند رضایت مستقل است.

## خطاها
401: ورود/نشست؛ 403: مجوز یا step-up کافی نیست؛ 409: نسخه/وضعیت تغییر کرده؛ 422: ورودی نامعتبر؛ 503: سرویس آماده نیست. در هیچ مورد رمز، seed یا API key را در چت یا Git ننویسید. برای رفع خطا volume را reset نکنید.

## نسخه سرور
پس از انتشار پذیرفته‌شده، HTTPS عمومی با همان نشست و مجوزهای سرور. ابزار bootstrap محلی به VPS متصل نشود. مسیر اپراتوری جدا با مجوز واقعی.
[راهنمای دمو](../operations/RAHGARD_ISSUE27_LOCAL_OWNER_DEMO_FA.md) | [راهنمای امنیت Provider](../operations/RAHGARD_PROVIDER_ADMIN_SERVER_FA.md) | [راهنمای انتقال](../operations/RAHGARD_ISSUE27_PORTABILITY_FA.md).
