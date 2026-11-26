# راهنمای قابلیت انتقال، بازیابی و انتشار Rahgard

## وضعیت این checkout

- شاخه: `feat/rahgard-unified-travel-v2`
- مبنای بررسی: `9680a2011815f82387400815fb6c10be26f20169`؛ SHA نهایی پس از commit باید جداگانه ثبت شود.
- مشاهدهٔ فقط‌خواندنی VPS در 2026-11-25: PostgreSQL 17، volume `rahgard_staging_pgdata`، ledger زنده تا 0023، tagهای API/Web گزارش‌شده `9b5b07d...` و marker قدیمی `5e2664f...` که با image identity برابر نیست.
- این checkout/V2 demo را با VPS هم‌شاخه یا هم-image فرض نکنید. هیچ live DDL، freeze، restart، secret provisioning یا deploy در این task اجرا نشده است.

## بستهٔ portability جدید

`deploy/staging/export-portable.sh` فقط در مسیر آپراتوریِ مجاز و پس از freeze کنترل‌شده اجرا می‌شود؛ هرگز برای lint یا تست صوری اجرا نکنید. اکنون منبع release را از `.env.v2` و `RAHGARD_RELEASE_SHA` می‌گیرد و `current/RELEASE_COMMIT` را به‌عنوان identity معتبر استفاده نمی‌کند. پیش‌نیازهای بسته‌ساز:

1. Host release و image tagهای API/Web با SHA کامل 40-رقمی یکی باشند و label هر دو image همان revision را نشان دهد؛ PostgreSQL image نیز با ID و پلتفرم ثبت شود.
2. DB container سالم و در حال اجرا باشد؛ image PostgreSQL و volume name با runtime config یکی باشد؛ marker میزبان و marker داخل DB برابر باشند.
3. `.env.v2` با مجوز 0600 و دایرکتوری secret با مجوز 0700 باشند. Host/SNI و cookie contract باید دقیقاً `hinaa.ir` و HTTPS امن باشد؛ local owner و public provider-admin/RAG خاموش‌اند.
4. V2 API/Web پیش از snapshot متوقف باشند، هیچ Rahgard API writer در حال اجرا نباشد و session کاری DB صفر باشد. خود marker به‌تنهایی writer freeze نیست.
5. فضا برای دو نسخهٔ تخمینی payload به‌اضافهٔ 1GiB آزاد باشد. خروجی fail در میان کار، فایل ناقص را پاک می‌کند؛ backup قدیمی خودکار حذف نمی‌شود.
6. MFA file overlay اگر واقعاً روی API فعال بوده، هر دو فایل `platform_admin_mfa_encryption_key_hex` و `platform_admin_recovery_pepper` باید حاضر و همراه marker وضعیت، در بستهٔ رمز‌شده باشند. مقدار secret هیچ‌گاه در manifest غیررمز‌شده نوشته نمی‌شود.

### قرارداد secretهای Step-up (از validator برنامه)

- متغیرهای مسیر دقیق: `PLATFORM_ADMIN_MFA_ENCRYPTION_KEY_FILE=/run/rahgard-admin-secrets/platform_admin_mfa_encryption_key_hex` و `PLATFORM_ADMIN_RECOVERY_PEPPER_FILE=/run/rahgard-admin-secrets/platform_admin_recovery_pepper`؛ هر دو باید با هم تنظیم شوند و با تزریق مستقیم env هم‌زمان نباشند.
- فایل کلید رمزگذاری باید دقیقاً 64 رقم hexadecimal (32 بایت) باشد. فایل pepper باید دست‌کم 32 بایت UTF-8 داشته باشد؛ newline انتهایی مجاز است، اما مقدار خالی، NUL، newline داخلی، symlink یا فایل غیرعادی رد می‌شود. validator سطح دسترسی فایل را نیز بررسی می‌کند.
- مقدارها فقط اپراتور مجاز از secret manager میزبان در فایل‌های root-controlled با دسترسی محدود قرار می‌دهد. این runbook مقدار، تولید خودکار، گردش/چرخش یا تحویل secret را انجام نمی‌دهد. چرخش کلید رمزگذاری ممکن است دادهٔ MFA موجود را غیرقابل‌خواندن کند؛ پیش از آن باید سازگاری و بازیابی جداگانه تصویب و آزموده شود. Pepper تغییر‌یافته می‌تواند recovery codeهای قبلی را نامعتبر کند.
- Health check فقط باید موجود/ناموجود بودن و اعتبار قالب را گزارش کند؛ مقدار secret، seed، recovery code یا fingerprint قابل‌بازگشت را نباید چاپ یا log کرد.

Bundle شامل PostgreSQL custom dump، ledger/checksum، تعدادهای تجمیعی مجاز، release source، state، runtime imageهای دقیق API/Web/PostgreSQL و secretهای لازم در archive رمز‌شده است. رمزنگاری فایل با OpenSSL AES-256-CBC/PBKDF2 و HMAC مستقل انجام می‌شود؛ HMAC پیش از decrypt بررسی می‌شود. کلید رمزگذاری و کلید HMAC خارج bundle و جدا از هم نگهداری می‌شوند. sidecar SHA برای خطای انتقال است و جای HMAC را نمی‌گیرد.

`inspect-portable.sh` فقط پس از احراز HMAC، checksum داخلی، فهرست/نوع فایل‌های tar، migration metadata و config digest سه image را می‌پذیرد. `restore-portable.sh` فقط DB تازه در PostgreSQL 17 با `network=none`، tmpfs، بدون mount پایدار و بدون پورت host را می‌پذیرد؛ نقش‌های application و geo با حداقل attribute و secret فایل‌های مجاز ساخته می‌شوند. `restore-portable-app-check.sh` tagهای exact را از archive بار می‌کند و ID/label را تطبیق می‌دهد؛ image mismatch باعث توقف می‌شود.

این تغییرات در این جلسه روی VPS اجرا نشده و bundle جدیدی تولید نشده است. R4 موجود فقط restore واقعی DB و مهاجرت‌های 0024–0026 را در clone جداشده ثابت می‌کند؛ آن را دوباره اجرا نکنید مگر کد/پایگاه مبنا تغییر کند.

## اجرای بسته فقط پس از مجوز و gateهای release

نمونهٔ ترتیبی برای اپراتور مجاز؛ این فرمان‌ها **در این task اجرا نشده‌اند**:

```bash
sudo -n /opt/rahgard-staging/releases/<sha>/scripts/ops/freeze_rahgard_v2_live.sh --status
# پس از تأیید جداگانه و maintenance/write freeze مجاز:
sudo -n /opt/rahgard-staging/releases/<sha>/scripts/ops/freeze_rahgard_v2_live.sh --freeze
sudo -n /opt/rahgard-staging/releases/<sha>/deploy/staging/export-portable.sh --cutover-frozen
sudo -n /opt/rahgard-staging/releases/<sha>/deploy/staging/inspect-portable.sh \
  <bundle.tar.enc> <passphrase-file> <independent-hmac-key-file> <new-protected-dir>
```

گام اول status فقط‌خواندنی است؛ گام‌های freeze/export ممکن است سرویس را متوقف کنند و بدون authorization جدا اجرا نشوند. Bundle، passphrase و HMAC key را به سه مقصد/مسیر custody مستقل و رمز‌شده منتقل کنید؛ off-host transfer این اسکریپت خودکار نیست. Retention باید طبق سیاست مالک و پس از اثبات copy/restore انجام شود؛ حذف خودکار backup وجود ندارد.

برای بازیابی، سرور جدا باید Ubuntu سازگار، Docker، Nginx/TLS و پورت/نام‌دامنهٔ مصوب داشته باشد. از bundle احرازشده در **volume تازهٔ مخصوص target** restore کنید؛ هرگز volume زنده را mount یا overwrite نکنید. Hostname، TLS certificate/key، DNS/Arvan NAT، شبکهٔ خصوصی provider vLLM و RAG بیرون bundle هستند و باید جداگانه از secret manager/مدیر خدمت بازتولید شوند. `host.env` نمونهٔ محافظت‌شده است، نه تنظیم آمادهٔ سرور جدید؛ قبل از start باید hostname/secret paths/ports/volume و operator review شوند.

## تفاوت database restore و جابه‌جایی کامل سرور

فعلاً restore کامل روی VM/Ubuntu مستقل انجام نشده است؛ اجرای DB در container `network=none` معادل server relocation نیست. همچنین گواهی TLS/Nginx/DNS، دسترسی بیرونی vLLM/RAG، provider account، off-host backup custody و نشست Owner روی میزبان تازه با شواهد موجود اثبات نشده‌اند. بنابراین **server portability: NOT VERIFIED**.

## CI/CD و release identity

Workflowهای image build و quality باید روی SHA نهایی اجرا و run IDها بررسی شوند؛ وجود YAML به‌تنهایی PASS نیست. Workflow build دستی است و باید immutable source SHA، پلتفرم `linux/amd64`، image ID/RepoDigest و artifact checksums را ثبت کند. Promote باید همان artifact digestها را مصرف کند؛ rebuild یا retag image با SHA دیگر مجاز نیست.

| محیط | وضعیت مشاهده‌شده | نتیجه |
|---|---|---|
| Windows | local owner demo از source محلی؛ branch مبنا `9680a201…` تا پیش از commit نهایی | Docker API/Web image identity ادعا نمی‌شود |
| GitHub | branch مبنا در شروع برابر `9680a201…` | CI run برای این SHA در بررسی اولیه موجود نبود؛ SHA نهایی نیازمند بررسی مجدد workflow است |
| VPS | read-only تصویر قبلی: API/Web `9b5b07d…`, legacy marker `5e2664f…`, ledger 0023 | drift قطعی؛ هیچ تغییر زنده انجام نشده |

## تصمیم فعلی

- دموی محلی قابل اجرا و schema تا 0026: بله؛ ورود Owner/Partner و فرم‌ها هنوز باید توسط اپراتور در مرورگر اختصاصی دستی انجام شود.
- Restore DB واقعی و rehearsal 0024–0026: شواهد R4 موجود است، تکرار نشود.
- Backup قابل‌حمل همراه imageهای exact پس از کد جدید: tooling پیاده‌سازی/بازبینی شده، ولی هنوز با artifact واقعی production اجرا نشده است.
- Independent server relocation، off-host copy، CI run روی SHA نهایی و سه‌محیط parity: اثبات‌نشده.
- Live DDL، MFA secret provisioning، Owner/reviewer grant، Nginx/DNS یا deploy: مجوز اجرای این عملیات در این task داده نشده؛ دست‌نخورده باقی می‌مانند.

### Migration 0027 provider-admin portability scope (isolated rehearsal only)

Migration `0027_server_ai_provider_admin` adds server-side capability and registry support. It has not been applied on the VPS; the last observed live ledger ended at 0023. The opt-in overlays are `deploy/staging/compose.platform-admin-mfa.yaml` and `deploy/staging/compose.server-provider-admin.yaml`. MFA files are read from the dedicated `RAHGARD_ADMIN_SECRET_DIR` at `/run/rahgard-admin-secrets/...`. The separate provider keyring is mounted from `RAHGARD_PROVIDER_KEYRING_DIR` at `/run/rahgard-provider-keyring/ai_provider_vault_keyring.json`; ciphertext is held in `RAHGARD_PROVIDER_VAULT_VOLUME`. These mounts are not yet integrated into `export-portable.sh` or the live backup manifest. Therefore the portability package does not yet include this feature, and these overlays must not be activated on a server until export, restore, deploy, and rollback cover these paths with the same release.
