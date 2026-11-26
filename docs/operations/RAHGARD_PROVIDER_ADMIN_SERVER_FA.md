# راهنمای عملیاتی سرور AI Provider و MFA — Rahgard Issue #27

## مرز دسترسی

پنل موجود `/admin` از همان نشست Rahgard استفاده می‌کند. فعال‌بودن feature flag به‌تنهایی دسترسی نمی‌دهد: حساب باید platform-admin معتبر و جداگانه دارای capability `ai_provider_admin` باشد، TOTP مشترک MFA را ثبت کند، و برای عملیات حساس step-up همان نشست را انجام دهد. ثبت‌نام عمومی هیچ مجوز مدیریتی نمی‌دهد. شرکت یا reviewer به‌صورت خودکار provider admin نمی‌شود. grant/revoke فقط با ابزار اپراتوری audited و از مسیر مجاز انجام می‌شود؛ account نمی‌تواند به خودش grant بدهد.

## متغیرها و قالب معتبر

| نام | قرارداد از کد | نگهداری |
|---|---|---|
| `AI_PROVIDER_ADMIN_ENABLED` | پیش‌فرض false؛ فقط در `staging`/`production` با auth و Secure cookie می‌تواند true باشد. | env غیرمحرمانه؛ deployment opt-in. |
| `AI_PROVIDER_VAULT_DIR` | مسیر directory فایل‌های ciphertext. Directory باید واقعی، بدون symlink و در Linux با دسترسی owner-only باشد. | persistent volume خصوصی، فقط UID برنامه (Docker UID 10001) و اپراتور مجاز. |
| `AI_PROVIDER_VAULT_KEY_FILE` | JSON با `format_version: 1`، `active_key_id` و `keys`; key ID از 1 تا 32 کاراکتر `[A-Za-z0-9_-]`; مقدار هر key دقیقاً 64 hex (32-byte AES-256); حداکثر 8 version. | فایل در دایرکتوری مستقل `RAHGARD_PROVIDER_KEYRING_DIR`، mode فایل `0400`/`0600`، directory `0700` و مالک UID برنامه. از MFA secretها جدا بماند. |
| `PLATFORM_ADMIN_MFA_ENCRYPTION_KEY_FILE` | محتوای UTF-8 با دقیقاً 64 کاراکتر hex (32 bytes). | secret manager یا bind-mount فقط‌خواندنی با owner-only file/parent و مالک UID برنامه. |
| `PLATFORM_ADMIN_RECOVERY_PEPPER_FILE` | UTF-8 با حداقل 32 بایت. | مستقل از MFA encryption key؛ همان سطح حفاظت/backup. |

کد `Settings` منع می‌کند همزمان فایل و env raw برای MFA key/pepper تزریق شود؛ provider key نیز باید فقط فایل باشد، نه `AI_PROVIDER_VAULT_KEY_HEX`. هیچ مقدار محرمانه را به issue، chat، shell history، artifact یا log منتقل نکنید.

## اجرای محافظت‌شدهٔ Compose

از Compose staging اصلی و overlayهای ثبت‌شده استفاده شود. `RAHGARD_ADMIN_SECRET_DIR` فقط دو فایل MFA را نگه می‌دارد و `RAHGARD_PROVIDER_KEYRING_DIR` فقط keyring provider را؛ هر directory باید `0700` و owner آن UID برنامه (10001 در image فعلی) باشد؛ فایل‌ها `0400`/`0600`. Overlay MFA دایرکتوری MFA را read-only bind می‌کند. `compose.server-provider-admin.yaml` فقط وقتی `RAHGARD_PROVIDER_ADMIN_ENABLED=true` به همان Compose set اضافه شود؛ آن overlay keyring را read-only و ciphertext را در volume persistent جدا mount می‌کند. Provider secret value داخل PostgreSQL نیست. هر سه مسیر عملیاتی باید در backup رمز‌شدهٔ مجاز نگهداری شوند؛ backup encryption/HMAC keys مستقل می‌مانند.

ترتیب rollout بعد از approvalهای مستقل: backup کامل و restore آزمایشی؛ migration 0027 guard/checksum rehearsal؛ provision امن فایل keyring و دو secret MFA؛ اجرای API با feature flag خاموش؛ check غیرمحرمانهٔ config/health؛ فعال‌سازی guarded feature؛ operator grant یک Owner platform-admin موجود؛ ورود و TOTP enrollment؛ بررسی audit و denial برای user عادی؛ ساخت profile، افزودن secret در فرم HTTPS، test واقعی محدود، فعال‌سازی route و یک traveler inference آزمایشی با consent. Migration یا grant زنده پیش از تأیید جداگانه اجرا نشود.

## Vault key rotation

این ابزار باید فقط با API متوقف، backup رمز‌شدهٔ volume و keyring تأییدشده، و مسیرهای protected اجرا شود. ابزار را از image دقیق همان release به‌صورت one-shot، شبکه‌قطع و بدون root اجرا کنید. در فرمان زیر مقادیر متغیرها non-secret path/identity هستند؛ هیچ secret value در argv قرار نمی‌گیرد. برای `rotate` و `reencrypt` keyring mount باید writable و فقط حاوی keyring باشد؛ برای `verify` read-only بماند:

```bash
# Read-only verification. The API must be stopped; these are non-secret paths.
docker run --rm --network none --read-only --user 10001:10001 --cap-drop ALL \
  --security-opt no-new-privileges:true --workdir /app/backend \
  --mount "type=volume,source=$RAHGARD_PROVIDER_VAULT_VOLUME,target=/var/lib/rahgard/provider-vault,readonly" \
  --mount "type=bind,src=$RAHGARD_PROVIDER_KEYRING_DIR,dst=/run/rahgard-provider-keyring,readonly" \
  --entrypoint python "rahgard-api:$RAHGARD_RELEASE_SHA" \
  /app/backend/scripts/manage_provider_vault.py --vault-dir /var/lib/rahgard/provider-vault \
  --key-file /run/rahgard-provider-keyring/ai_provider_vault_keyring.json verify
```

`rotate`, `reencrypt`, and `prune` need write access. Run only with API stopped and after verified backup of both ciphertext volume and keyring. Use the same command but remove `,readonly` from both mounts and replace the final action with the intended subcommand. The container remains network-isolated, read-only except for these explicit mounts, non-root, and uses the exact API image. Afterward repeat the read-only `verify` command and restore normal read-only mounts. For `prune`, pass `prune --key-id <version>` only after re-encryption and verification confirm that version has no ciphertext. Recovery owner must separately retain host/secret-manager access and backup-key custody. This task did not provision any live MFA key or provider credential.

برای `rotate` همان فرمان با mount keyring writable و subcommand `rotate` اجرا شود؛ پس از `reencrypt` و `verify`، فقط key version غیرفعال و بدون ciphertext را می‌توان با `prune --key-id <version>` حذف کرد. پیش از rotation، keyring و ciphertext باید با هم backup و در restore rehearsal قابل decrypt باشند. Recovery owner باید credential سرور/secret manager و backup key custody را جداگانه در اختیار داشته باشد. این handoff هیچ MFA key یا credential live را provision نکرده است.

## واقعیت acceptance

`AI_PROVIDER_ADMIN_ENABLED=true` یک interface/runtime capability است، نه شاهد provider واقعی. برای inference باید account دارای grant و TOTP، endpoint allowlist، provider credential معتبر، revision validation و active route داشته باشیم. آزمون با fake/local mock یا صرفاً `/models` نباید inference واقعی گزارش شود. تا زمان فراهم‌شدن دسترسی/مجوزهای عملیاتی، VPS و provider settings آن دست‌نخورده باقی می‌مانند.
