# راهنمای بازیابی و rehearsal نسخهٔ Rahgard — Issue 27

## وضعیت و مرزهای این راهنما

- آخرین بررسی فقط‌خواندنی VPS: PostgreSQL `17.11`، پایگاه `rahgard_pilot_vps_staging`، volume موجود `rahgard_staging_pgdata`، ۲۲ ردیف ledger تا `0023_partner_trip_responses`.
- Imageهای مشاهده‌شدهٔ API/Web در snapshot: `9b5b07d0786578abdfac56848baf3c6d1260832e`. مقدار قدیمی `RELEASE_COMMIT` جداست و نباید به‌جای SHA واقعی image به‌کار رود.
- snapshot فقط یک database مجاز Rahgard را پوشش می‌دهد. پایگاه `postgres` عمداً بیرون از دامنه مانده است؛ این سند موجودی همهٔ سرویس‌ها یا tenantهای VPS نیست.
- در این ماموریت هیچ DDL، تغییر ردیف، volume، کانتینر یا سرویس زنده انجام نشد. مهاجرت ۰۰۲۴–۰۰۲۶ فقط روی clone موقت اعمال شد. migration count زنده همچنان ۲۲ تا ۰۰۲۳ است.

## بکاپ واقعیِ استفاده‌شده

ابزار `scripts/ops/capture_rahgard_0023_backup.py` قبل از `pg_dump`، نام DB، marker، release marker، image، volume، نسخهٔ PG، ledger و شمار تجمیعی ردیف‌ها را با snapshot دقیق تطبیق می‌دهد. فرمان‌های خواندنی با `default_transaction_read_only=on` اجرا می‌شوند. هیچ writer متوقف نمی‌شود؛ `pg_dump` از snapshot تراکنشی PostgreSQL استفاده می‌کند.

نمونهٔ اجرا در Windows PowerShell (مسیرها باید بیرون checkout و با ACL خصوصی باشند؛ فایل کلید از فایل بکاپ جدا نگه داشته شود):

```powershell
$Root = Join-Path $env:LOCALAPPDATA ('Rahgard\Issue27-Rehearsal-' + [guid]::NewGuid().ToString('N'))
$BackupDir = Join-Path $Root 'backups'
$KeyDir = Join-Path $Root 'keys'
New-Item -ItemType Directory -Force -Path $BackupDir,$KeyDir | Out-Null
uv run python scripts/ops/capture_rahgard_0023_backup.py `
  d4c8a6e0c306d8e171f65d805313e28612f35cfe $BackupDir $KeyDir
```

خروجی ابزار نام فایل، SHA-256، بایت، ledger head/count و دامنهٔ داده را گزارش می‌کند؛ مقدار کلید/عبارت رمز را چاپ نمی‌کند. sidecarهای SHA-256 و HMAC در کنار فایل رمز‌شده، کلید HMAC و عبارت رمز فقط در پوشهٔ کلید ACL‌شده می‌مانند. فایل رمز‌شده و کلید باید با دسترسی جدا منتقل و در حداقل یک رسانهٔ مستقل دیگر نگهداری شوند. **پاک‌سازی خودکار retention فعال نیست** تا ابزار نتواند آخرین نسخهٔ قابل‌بازیابی را حذف کند؛ archive قدیمی فقط پس از تأیید نسخهٔ جدید در مقصد مستقل و تأیید مالک پاک شود.

بکاپ تازهٔ این اجرا:

- UTC: `2026-11-25T09:47:26Z`
- اندازه: `603184` بایت
- SHA-256: `36612d03512f295450504f29046c3a96a52eb884f64064e5a5da13051e7f7aee`
- قالب: PostgreSQL custom archive، رمز AES-256-CBC با PBKDF2-HMAC-SHA256، ۶۰۰٬۰۰۰ iteration؛ HMAC مستقل پیش از رمزگشایی بررسی شد.
- دامنه: فقط محتوای یک database. فایل‌ها/assetهای میزبان، TLS، تنظیمات runtime، globals/role passwordها، نسخه/مدل خارجی و RAG بیرونی داخل archive نیستند.

## بازیابی ایزوله و مهاجرت ۰۰۲۴–۰۰۲۶

فرمان زیر ابتدا checksum و HMAC را تأیید، archive را در حافظه رمزگشایی، `pg_restore --list` را اجرا و سپس یک PG17 تازه در Docker با `--network none`، بدون port binding و فقط `tmpfs` می‌سازد. volume زنده mount نمی‌شود. cleanup فقط وقتی انجام می‌شود که label تصادفی کانتینر با همین اجرا برابر باشد.

```powershell
$Archive = Get-ChildItem $BackupDir -Filter '*.dump.enc' | Select-Object -First 1 -ExpandProperty FullName
uv run python scripts/ops/rehearse_rahgard_v2_migrations.py `
  docs/operations/evidence/issue27/R3-live-snapshot-2026-11-25.json `
  d4c8a6e0c306d8e171f65d805313e28612f35cfe $Archive $KeyDir `
  --evidence-output docs/operations/evidence/issue27/R4-restore-migrations-2026-11-25.json
```

ثبت‌شده در اجرای واقعی: restore ledger از ۲۲ ردیف و PG17.11؛ اعمال متوالی ۰۰۲۴، ۰۰۲۵، ۰۰۲۶؛ ledger نهایی ۲۵ ردیف (به‌دلیل حذف عمدی ۰۰۱۴ و ۰۰۱۵ در runtime، نه ۲۷ ردیف). شمار سطرهای قبل/بعد برابر بود: کاربران ۲۲، sessionها ۳۶، سفرها ۱۶، گفتگوها ۱۶، itineraryها ۱؛ تمام شمارهای ثبت‌شده در فایل evidence یکسان ماندند. credential row fingerprint برابر ماند؛ RLS، نقش کم‌اختیار `ai_tourism_app`، عدم دسترسی مستقیم به جدول audit/grant و عدم ایجاد grant/MFA/shared row تأیید شد.

آزمون خرابی تراکنش: migration ۰۰۲۴ در clone با خطای تزریقی قبل از `COMMIT` شکست داده شد؛ ledger پایه، شمار ردیف‌ها و check constraint قبلی دست‌نخورده ماندند. پس از آن سه migration عادی در clone با موفقیت اعمال شدند. آزمون unit فایل corrupted checksum و HMAC نامعتبر را پیش از restore رد می‌کند. این فرایند rollback معکوس DDL نیست: در live هیچ‌گاه migration را با حذف دستی schema «برنگردانید»؛ از backup معتبر در محیط جایگزین بازیابی کنید یا forward-repair نسخهٔ کنترل‌شده را با مجوز اجرا کنید.

محتویات رکوردهای واقعی، پیام‌ها، email، credential، marker، MFA seed و recovery code در evidence نیستند. صورت شمارها و checksumهای migration در `R4-restore-migrations-2026-11-25.json` ثبت شده‌اند.

در آخرین اجرای محلی، آزمون کامل API برابر **۵۰۸ موفق، ۲۰ ردشده به‌صورت skip** بود؛
Frontend **۲۰۸ آزمون موفق** و build/typecheck/PWA build نیز موفق شدند. آزمون‌های
تنظیم امن فایل MFA و حفاظت backup برابر **۱۹ موفق و ۲ skip** در اجرای CI-focused
بودند. اجرای focused نهایی پس از افزودن آزمونِ حفاظت از FKها **۲۰ موفق و ۲ skip**
شد. فایل `R4-restore-migrations-2026-11-25.json` نتیجهٔ clone واقعی از ledger
۰۰۲۳ را نگه می‌دارد؛ فیلد `migration_sql_source_sha` فقط به نسخهٔ SQL مبنا اشاره
می‌کند و به معنی اجرای همان release روی VPS نیست.

## MFA: دو راز سروری و Owner/reviewer

کد `backend/app/core/config.py` و `backend/app/api/platform_admin_mfa.py` نام و شکل را تعیین می‌کنند:

- `PLATFORM_ADMIN_MFA_ENCRYPTION_KEY_HEX`: دقیقاً ۶۴ رقم هگز، ۳۲ بایت.
- `PLATFORM_ADMIN_RECOVERY_PEPPER`: حداقل ۳۲ بایت UTF-8.
- `AUTH_RATE_LIMIT_SECRET`, HTTPS امن، `AUTH_ENABLED=true` و APP_ENV staging/production نیز لازم‌اند؛ موجودبودن این دو MFA key به‌تنهایی مسیر auth را فعال نمی‌کند.

در Compose از `deploy/staging/compose.platform-admin-mfa.yaml` فقط پس از آن استفاده شود که secret manager دایرکتوری اختصاصی `RAHGARD_ADMIN_SECRET_DIR` را آماده کرده باشد. این دایرکتوری فقط دو فایل MFA را نگه می‌دارد، mode آن `0700` و owner آن UID برنامه (10001 در image فعلی) است؛ فایل‌ها regular، بدون symlink و mode `0400` یا `0600` هستند. Overlay کل دایرکتوری را فقط‌خواندنی bind می‌کند تا هم permission واقعی فایل و هم parent خصوصی بمانند. هیچ secret از argv، shell history، `.env` عمومی، GitHub Actions یا log عبور نمی‌کند.

نمونهٔ اعتبارسنجی بی‌مقدار (باید قبل از restart در terminal محافظت‌شده اجرا شود):

```bash
docker compose --env-file /opt/rahgard-staging/.env \
  -f /opt/rahgard-staging/current/deploy/staging/compose.yaml \
  -f /opt/rahgard-staging/current/deploy/staging/compose.platform-admin-mfa.yaml \
  config --quiet
docker compose --env-file /opt/rahgard-staging/.env \
  -f /opt/rahgard-staging/current/deploy/staging/compose.yaml \
  -f /opt/rahgard-staging/current/deploy/staging/compose.platform-admin-mfa.yaml \
  exec -T api python -c 'from app.core.config import get_settings; s=get_settings(); print("platform_mfa=" + ("configured" if s.platform_admin_mfa_encryption_key_hex and s.platform_admin_recovery_pepper else "disabled"))'
```

فرمان دوم فقط پس از restart کنترل‌شدهٔ API معنی دارد؛ هیچ‌یک در این ماموریت روی VPS اجرا نشد. جایگزینی فایل و restart، rotation کلید، grant بازبین، Owner enrollment و migration live هرکدام نیازمند هماهنگی عملیات و تأیید مستقل هستند. یک Owner با `admin_overview_read` از ابزار اپراتوری جداگانه provision می‌شود؛ reviewer نیز capability محدود خودش را می‌گیرد. خودثبت‌نام admin، default owner، universal token و auto-promotion وجود ندارد. Owner بعد از login همان `/admin` را باز می‌کند، TOTP را enroll می‌کند، recovery codes را یک‌بار در vault امن نگه می‌دارد، سپس step-up پنج‌دقیقه‌ای و محدود به همان session می‌گیرد. مدیریت AI Provider فقط پس از migration 0027، overlay/keyring امن، grant مستقل و validation مجاز است؛ وضعیت آن روی VPS در این کار تغییر یا فعال نشده است.

## چه چیزی هنوز portability کامل نیست

1. این archive کامل relocation نیست: PostgreSQL globals، role membership/attributes، passwordهای DB، secrets runtime، فایل‌های میزبان و TLS بیرون آن هستند. clone برای rehearsal فقط roleهای تستیِ لازم را جدا ساخت؛ restore کامل cluster roles اثبات نشده است.
2. نسخهٔ پشتیبان به Windows امن منتقل شد، اما مقصد دوم مستقل/immutable (object storage یا رسانهٔ جدا با retention و restore مجدد) هنوز تأیید نشده است.
3. هیچ target مستقل Ubuntu/VM برای relocation ساخته نشد؛ restore واقعی فعلی فقط clone محلی Docker با `network none` و `tmpfs` است.
4. دو MFA key در محیط live provision/validate نشده‌اند؛ هیچ حساب reviewer یا Owner تازه provision نشده است.
5. پایداری فایل‌ها، Compose start/stop/status، login دستی و دور کامل Owner/Partner/Traveler در local Windows demo تا این اجرا به‌صورت interactive مشاهده نشد. تست‌های قبلی Chromium مربوط به E2E ایزوله‌اند و معادل دمو دستی نیستند.
6. VPS هنوز روی runtime `9b5b07d...` و migration ۰۰۲۳ است؛ Windows/GitHub شاخهٔ این کار باید پس از commit با هم برابر شوند، اما VPS عمداً release/deploy نشد.
