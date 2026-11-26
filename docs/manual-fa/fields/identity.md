# فرهنگ فیلدهای حساب و امنیت (identity)

[فهرست اصلی](../README.md). مبنا cab603a7d40cfa35dd20de2ffb12a336d84f56ff؛ metadata پایلوت 0026 + DDL 0027، نه snapshot زنده. NULL قید SQL است نه الزام فرم. پیش‌فرض redacted پالایش شده؛ مقدار را حدس نزنید. توضیح خوانش نام/نوع اثبات معنای تجاری نیست. اطلاعات شخصی، رمز، توکن و ممیزی را مستقیم تغییر ندهید.

[metadata](../../database/rehearsed-schema-0026/catalog_metadata_snapshot.json) | [glossary](../../database/field_descriptions.json) | [DDL 0027](../../../engineering/pilot/sql/027_server_ai_provider_admin.sql) | [مرجع 0027](../../database/rehearsed-schema-0027/PROVIDER_ADMIN_FIELD_REFERENCE.md)

## identity.ai_provider_admin_grant_events

دامنه: حساب و امنیت؛ ai_provider_admin_grant_events (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: DDL 0027.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `event_id` | `uuid` | خیر | `gen_random_uuid()` | event_id؛ Grant event identity. | سامانه/اپراتور مجاز | DDL/مرجع 0027 |
| `actor_user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر ـ عامل؛ Independent authorized operator performing the action. | سامانه/اپراتور مجاز | DDL/مرجع 0027 |
| `target_user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر ـ هدف؛ User receiving/revoking provider capability; cannot equal actor. | سامانه/اپراتور مجاز | DDL/مرجع 0027 |
| `action` | `text` | خیر | ندارد | عملیات؛ Lifecycle event. | سامانه/اپراتور مجاز | DDL/مرجع 0027 |
| `reason` | `text` | خیر | ندارد | دلیل؛ Auditable rationale supplied by operator. | سامانه/اپراتور مجاز | DDL/مرجع 0027 |
| `occurred_at` | `timestamptz` | خیر | `now()` | زمان ـ وقوع؛ Event time. | سامانه/اپراتور مجاز | DDL/مرجع 0027 |

قیود دقیق DDL ستون‌ها:

```sql
event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
actor_user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
target_user_id UUID NOT NULL REFERENCES identity.users(user_id) ON DELETE RESTRICT,
action TEXT NOT NULL CHECK(action IN ('granted','revoked')),
reason TEXT NOT NULL CHECK(length(btrim(reason)) BETWEEN 10 AND 1000),
occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
```

قیود جدول:
- `CHECK(actor_user_id<>target_user_id)`

## identity.ai_provider_admin_grants

دامنه: حساب و امنیت؛ ai_provider_admin_grants (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: DDL 0027.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ Provider-admin principal; requires existing platform-admin capability; grant is never automatic for company/reviewer membership. | سامانه/اپراتور مجاز | DDL/مرجع 0027 |
| `granted_at` | `timestamptz` | خیر | `now()` | زمان ـ اعطا‌شده؛ Grant time. | سامانه/اپراتور مجاز | DDL/مرجع 0027 |
| `granted_by` | `uuid` | بله | ندارد | توسط/بر اساس ـ اعطا‌شده؛ Independent operator who provisioned grant; audit identity. | سامانه/اپراتور مجاز | DDL/مرجع 0027 |
| `grant_reason` | `text` | خیر | ندارد | دلیل ـ مجوز؛ Required operator rationale; not a secret. | سامانه/اپراتور مجاز | DDL/مرجع 0027 |
| `revoked_at` | `timestamptz` | بله | ندارد | زمان ـ لغوشده؛ Revocation time; must not predate grant. | سامانه/اپراتور مجاز | DDL/مرجع 0027 |
| `revoked_by` | `uuid` | بله | ندارد | توسط/بر اساس ـ لغوشده؛ Independent revoking operator. | سامانه/اپراتور مجاز | DDL/مرجع 0027 |
| `revoke_reason` | `text` | بله | ندارد | revoke_reason؛ Required revocation rationale; no grant exists in migration bootstrap. | سامانه/اپراتور مجاز | DDL/مرجع 0027 |

قیود دقیق DDL ستون‌ها:

```sql
user_id UUID PRIMARY KEY REFERENCES identity.users(user_id) ON DELETE CASCADE,
granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
granted_by UUID REFERENCES identity.users(user_id) ON DELETE RESTRICT,
grant_reason TEXT NOT NULL CHECK(length(btrim(grant_reason)) BETWEEN 10 AND 1000),
revoked_at TIMESTAMPTZ,
revoked_by UUID REFERENCES identity.users(user_id) ON DELETE RESTRICT,
revoke_reason TEXT
```

قیود جدول:
- `CHECK(revoked_at IS NULL OR revoked_at>=granted_at)`
- `CHECK((revoked_at IS NULL)=(revoke_reason IS NULL))`
- `CHECK(revoked_at IS NULL OR length(btrim(revoke_reason)) BETWEEN 10 AND 1000)`

## identity.auth_rate_limits

دامنه: حساب و امنیت؛ auth_rate_limits (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `dimension` | `text` | خیر | ندارد | دسته یا بعد محدودیت نرخ | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `subject_digest` | `bytea` | خیر | ندارد | اثر انگشت موضوع محدودیت نرخ؛ امنیتی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `window_started_at` | `timestamp with time zone` | خیر | ندارد | آغاز پنجره زمانی شمارش | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `hit_count` | `integer` | خیر | ندارد | شمار رخدادها در پنجره | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((dimension = ANY (ARRAY['phone'::text, 'ip'::text, 'global'::text, 'verify_challenge'::text, 'verify_phone'::text, 'verify_ip'::text])))`
- `CHECK ((hit_count > 0))`
- `CHECK ((octet_length(subject_digest) = 32))`
- `PRIMARY KEY (dimension, subject_digest, window_started_at)`

## identity.catalogue_review_grants

دامنه: حساب و امنیت؛ catalogue_review_grants (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ ارجاع به identity.users(user_id) ON DELETE RESTRICT | سامانه/اپراتور مجاز | قید FK |
| `capability` | `text` | خیر | ندارد | قابلیت مدیریتی یا مجوز مشخص | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `granted_by` | `uuid` | خیر | ندارد | توسط/بر اساس ـ اعطا‌شده؛ ارجاع به identity.users(user_id) ON DELETE RESTRICT | سامانه/اپراتور مجاز | قید FK |
| `reason` | `text` | خیر | ندارد | دلیل ثبت‌شده برای عملیات یا تصمیم | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `granted_at` | `timestamp with time zone` | خیر | `now()` | زمان اعطای مجوز یا رضایت | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `revoked_at` | `timestamp with time zone` | بله | ندارد | زمان لغو | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((capability = ANY (ARRAY['candidate_review'::text, 'source_review'::text, 'catalogue_publish'::text])))`
- `CHECK (((revoked_at IS NULL) OR (revoked_at >= granted_at)))`
- `CHECK (((length(btrim(reason)) >= 10) AND (length(btrim(reason)) <= 1000)))`
- `FOREIGN KEY (granted_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `PRIMARY KEY (user_id, capability, granted_at)`

## identity.otp_challenges

دامنه: حساب و امنیت؛ otp_challenges (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `challenge_id` | `uuid` | خیر | ندارد | کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `phone_e164` | `text` | خیر | ندارد | شماره تلفن در قالب بین‌المللی E.164؛ خصوصی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `purpose` | `text` | خیر | ندارد | هدف درخواست کد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `verifier_hmac` | `bytea` | خیر | ندارد | تأییدکننده HMAC کد؛ نه خود کد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `key_version` | `text` | خیر | ندارد | نسخه کلید مورد استفاده در تأیید | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `delivery_status` | `text` | خیر | `[redacted string default]` | وضعیت تحویل کد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `failed_attempts` | `smallint` | خیر | `0` | شمار تلاش‌های ناموفق | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | ندارد | زمان ایجاد رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `expires_at` | `timestamp with time zone` | خیر | ندارد | زمان انقضا | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `resend_after` | `timestamp with time zone` | خیر | ندارد | زمانی که ارسال مجدد مجاز می‌شود | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `consumed_at` | `timestamp with time zone` | بله | ندارد | زمان مصرف دعوت‌نامه یا کد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `superseded_at` | `timestamp with time zone` | بله | ندارد | زمان جایگزین شدن با درخواست جدید | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `locked_at` | `timestamp with time zone` | بله | ندارد | زمان قفل امنیتی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((expires_at > created_at))`
- `CHECK ((resend_after >= created_at))`
- `CHECK ((delivery_status = ANY (ARRAY['queued'::text, 'sent'::text, 'failed'::text])))`
- `CHECK (((failed_attempts >= 0) AND (failed_attempts <= 10)))`
- `CHECK ((phone_e164 ~ '^\+989[0-9]{9}$'::text))`
- `CHECK ((purpose = 'login'::text))`
- `CHECK ((octet_length(verifier_hmac) = 32))`
- `PRIMARY KEY (challenge_id)`

## identity.platform_admin_mfa

دامنه: حساب و امنیت؛ platform_admin_mfa (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ ارجاع به identity.users(user_id) ON DELETE CASCADE | سامانه/اپراتور مجاز | قید FK |
| `secret_ciphertext` | `bytea` | بله | ندارد | بذر TOTP رمز‌شده؛ هرگز ورودی عمومی نیست | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `pending_secret_ciphertext` | `bytea` | بله | ندارد | بذر رمز‌شده ثبت‌نام MFA تکمیل‌نشده | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `enabled_at` | `timestamp with time zone` | بله | ندارد | زمان فعال شدن MFA | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `last_totp_counter` | `bigint` | خیر | `[redacted string default]` | آخرین شمارنده پذیرفته‌شده TOTP برای جلوگیری از بازپخش | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `recovery_hashes` | `bytea[]` | خیر | `ARRAY[]::bytea[]` | تأییدکننده‌های کدهای بازیابی یکبارمصرف؛ محرمانه | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `version` | `integer` | خیر | `1` | نسخه رکورد؛ جزئیات افزایش تابع قرارداد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((enabled_at IS NULL) = (secret_ciphertext IS NULL)))`
- `CHECK ((last_totp_counter >= '-1'::integer))`
- `CHECK (((pending_secret_ciphertext IS NULL) OR (octet_length(pending_secret_ciphertext) = 49)))`
- `CHECK ((cardinality(recovery_hashes) <= 20))`
- `CHECK (((secret_ciphertext IS NULL) OR (octet_length(secret_ciphertext) = 49)))`
- `CHECK ((version > 0))`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `PRIMARY KEY (user_id)`

## identity.platform_admin_mfa_events

دامنه: حساب و امنیت؛ platform_admin_mfa_events (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `event_id` | `uuid` | خیر | `gen_random_uuid()` | کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `actor_user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر ـ عامل؛ ارجاع به identity.users(user_id) ON DELETE RESTRICT | سامانه/اپراتور مجاز | قید FK |
| `session_id` | `uuid` | خیر | ندارد | شناسه نشست مرتبط؛ نه توکن نشست | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `action` | `text` | خیر | ندارد | نوع عملیات ثبت‌شده | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `occurred_at` | `timestamp with time zone` | خیر | `now()` | زمان وقوع رویداد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((action = ANY (ARRAY['enrollment_started'::text, 'mfa_enrolled'::text, 'totp_step_up'::text, 'recovery_step_up'::text, 'recovery_reset'::text])))`
- `FOREIGN KEY (actor_user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- `PRIMARY KEY (event_id)`

## identity.platform_admin_step_up

دامنه: حساب و امنیت؛ platform_admin_step_up (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: فعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ ارجاع به identity.platform_admin_mfa(user_id) ON DELETE CASCADE | سامانه/اپراتور مجاز | قید FK |
| `session_id` | `uuid` | خیر | ندارد | شناسه ـ نشست؛ ارجاع به identity.web_sessions(session_id) ON DELETE CASCADE | سامانه/اپراتور مجاز | قید FK |
| `verified_at` | `timestamp with time zone` | خیر | ندارد | زمان تأیید | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `expires_at` | `timestamp with time zone` | خیر | ندارد | زمان انقضا | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `revoked_at` | `timestamp with time zone` | بله | ندارد | زمان لغو | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((expires_at > verified_at) AND (expires_at <= (verified_at + '00:05:00'::interval))))`
- `CHECK (((revoked_at IS NULL) OR (revoked_at >= verified_at)))`
- `FOREIGN KEY (session_id) REFERENCES identity.web_sessions(session_id) ON DELETE CASCADE`
- `FOREIGN KEY (user_id) REFERENCES identity.platform_admin_mfa(user_id) ON DELETE CASCADE`
- `PRIMARY KEY (user_id, session_id)`

## identity.staging_auth_limits

دامنه: حساب و امنیت؛ staging_auth_limits (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `dimension` | `text` | خیر | ندارد | دسته یا بعد محدودیت نرخ | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `subject_digest` | `bytea` | خیر | ندارد | اثر انگشت موضوع محدودیت نرخ؛ امنیتی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `window_started_at` | `timestamp with time zone` | خیر | ندارد | آغاز پنجره زمانی شمارش | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `hit_count` | `integer` | خیر | ندارد | شمار رخدادها در پنجره | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((dimension = ANY (ARRAY['login_name'::text, 'global'::text, 'invite'::text])))`
- `CHECK ((hit_count > 0))`
- `CHECK ((octet_length(subject_digest) = 32))`
- `PRIMARY KEY (dimension, subject_digest, window_started_at)`

## identity.staging_invites

دامنه: حساب و امنیت؛ staging_invites (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `invite_id` | `uuid` | خیر | `gen_random_uuid()` | کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `token_digest` | `bytea` | خیر | ندارد | اثر انگشت توکن دعوت؛ نه توکن اصلی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `expires_at` | `timestamp with time zone` | خیر | ندارد | زمان انقضا | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `consumed_at` | `timestamp with time zone` | بله | ندارد | زمان مصرف دعوت‌نامه یا کد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `consumed_by` | `uuid` | بله | ندارد | توسط/بر اساس ـ مصرف؛ ارجاع به identity.users(user_id) ON DELETE SET NULL | سامانه/اپراتور مجاز | قید FK |

قیود جدول:
- `CHECK (((expires_at > created_at) AND (expires_at <= (created_at + '14 days'::interval))))`
- `CHECK (((consumed_at IS NULL) = (consumed_by IS NULL)))`
- `CHECK ((octet_length(token_digest) = 32))`
- `FOREIGN KEY (consumed_by) REFERENCES identity.users(user_id) ON DELETE SET NULL`
- `PRIMARY KEY (invite_id)`
- `UNIQUE (token_digest)`

## identity.staging_password_credentials

دامنه: حساب و امنیت؛ staging_password_credentials (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ ارجاع به identity.users(user_id) ON DELETE CASCADE | سامانه/اپراتور مجاز | قید FK |
| `login_name` | `text` | خیر | ندارد | نام ورود حساب | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `salt` | `bytea` | خیر | ندارد | مقدار تصادفی مشتق‌سازی رمز | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `verifier` | `bytea` | خیر | ندارد | تأییدکننده رمز، نه رمز قابل خواندن | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `iterations` | `integer` | خیر | ندارد | تعداد تکرار الگوریتم مشتق‌سازی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((iterations = 600000))`
- `CHECK (((login_name = lower(login_name)) AND ((length(login_name) >= 5) AND (length(login_name) <= 254)) AND (login_name ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'::text)))`
- `CHECK ((octet_length(salt) = 32))`
- `CHECK ((octet_length(verifier) = 32))`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `PRIMARY KEY (user_id)`
- `UNIQUE (login_name)`

## identity.user_consents

دامنه: حساب و امنیت؛ user_consents (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `consent_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ رضایت؛ کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ ارجاع به identity.users(user_id) ON DELETE CASCADE | سامانه/اپراتور مجاز | قید FK |
| `consent_type` | `text` | خیر | ندارد | نوع رضایت کاربر | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `policy_version` | `text` | خیر | ندارد | نسخه سیاست مربوط به رضایت یا تصمیم | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_granted` | `boolean` | خیر | ندارد | آیا رضایت داده شده است | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `granted_at` | `timestamp with time zone` | بله | ندارد | زمان اعطای مجوز یا رضایت | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `revoked_at` | `timestamp with time zone` | بله | ندارد | زمان لغو | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `consent_source` | `text` | خیر | `[redacted string default]` | منشأ ثبت رضایت | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((revoked_at IS NULL) OR (granted_at IS NOT NULL)))`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `PRIMARY KEY (consent_id)`
- `UNIQUE (user_id, consent_type, policy_version)`

## identity.user_preferences

دامنه: حساب و امنیت؛ user_preferences (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `preference_id` | `uuid` | خیر | `gen_random_uuid()` | کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ ارجاع به identity.users(user_id) ON DELETE CASCADE | سامانه/اپراتور مجاز | قید FK |
| `preference_key` | `text` | خیر | ندارد | کلید نوع ترجیح کاربر؛ واژگان دقیق نیازمند قرارداد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `preference_value` | `jsonb` | خیر | ندارد | مقدار ترجیح؛ شکل دقیق تابع نوع ترجیح | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `weight` | `numeric(5,4)` | خیر | `0.5` | وزن ترجیح یا امتیاز؛ دامنه از قید و قرارداد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `confidence` | `numeric(5,4)` | بله | ندارد | درجه اطمینان؛ مقیاس را از قید و مصرف کد بخوانید | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `preference_source` | `text` | خیر | `[redacted string default]` | منشأ ترجیح؛ دسته‌های دقیق نیازمند بررسی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_long_term` | `boolean` | خیر | `true` | نشان ترجیح بلندمدت | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK (((confidence IS NULL) OR ((confidence >= (0)::numeric) AND (confidence <= (1)::numeric))))`
- `CHECK (((weight >= (0)::numeric) AND (weight <= (1)::numeric)))`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `PRIMARY KEY (preference_id)`
- `UNIQUE (user_id, preference_key)`

## identity.users

دامنه: حساب و امنیت؛ users (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `user_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ کاربر؛ کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `auth_subject` | `text` | بله | ندارد | شناسه موضوع احراز هویت حساب | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `email` | `text` | بله | ندارد | نشانی ایمیل کاربر؛ خصوصی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `phone_e164` | `text` | بله | ندارد | شماره تلفن در قالب بین‌المللی E.164؛ خصوصی | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `display_name` | `text` | بله | ندارد | نام قابل نمایش برای شخص، مقصد یا خدمت | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `password_hash` | `text` | بله | ندارد | هش رمز عبور؛ هرگز نمایش یا ویرایش مستقیم نشود | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `account_status` | `text` | خیر | `[redacted string default]` | وضعیت حساب | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `is_synthetic` | `boolean` | خیر | `false` | نشان داده مصنوعی یا آزمایشی؛ با داده واقعی اشتباه نشود | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | `now()` | زمان ایجاد رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `updated_at` | `timestamp with time zone` | خیر | `now()` | زمان آخرین تغییر رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((account_status = ANY (ARRAY['active'::text, 'disabled'::text, 'pending_deletion'::text, 'deleted'::text])))`
- `CHECK (((email IS NOT NULL) OR (phone_e164 IS NOT NULL) OR (auth_subject IS NOT NULL)))`
- `PRIMARY KEY (user_id)`
- `UNIQUE (auth_subject)`

## identity.verified_phones

دامنه: حساب و امنیت؛ verified_phones (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `phone_e164` | `text` | خیر | ندارد | شماره تلفن قالب بین‌المللی E.164؛ کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ ارجاع به identity.users(user_id) ON DELETE CASCADE | سامانه/اپراتور مجاز | قید FK |
| `verified_at` | `timestamp with time zone` | خیر | ندارد | زمان تأیید | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `challenge_id` | `uuid` | بله | ندارد | ارجاع به identity.otp_challenges(challenge_id) ON DELETE SET NULL | سامانه/اپراتور مجاز | قید FK |

قیود جدول:
- `CHECK ((phone_e164 ~ '^\+989[0-9]{9}$'::text))`
- `FOREIGN KEY (challenge_id) REFERENCES identity.otp_challenges(challenge_id) ON DELETE SET NULL`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `PRIMARY KEY (phone_e164)`
- `UNIQUE (challenge_id)`
- `UNIQUE (user_id)`

## identity.web_sessions

دامنه: حساب و امنیت؛ web_sessions (عنوان راهنما، نه اثبات ضرورت معماری)

نوع: جدول؛ منبع: metadata ایزوله 0026؛ RLS: غیرفعال.

مسیر دامنه: ورود، MFA یا اپراتور مجاز؛ نه CRUD جدول.

| فیلد | نوع SQL | NULL مجاز؟ | پیش‌فرض | معنی یا توضیح خواندن | محل ورود / منشأ | مبنا |
|---|---|---|---|---|---|---|
| `session_id` | `uuid` | خیر | `gen_random_uuid()` | شناسه ـ نشست؛ کلید یکتای رکورد | سامانه/اپراتور مجاز | قید PK |
| `token_hash` | `bytea` | خیر | ندارد | هش توکن نشست؛ محرمانه | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `user_id` | `uuid` | خیر | ندارد | شناسه ـ کاربر؛ ارجاع به identity.users(user_id) ON DELETE CASCADE | سامانه/اپراتور مجاز | قید FK |
| `csrf_hash` | `bytea` | خیر | ندارد | هش محافظ درخواست CSRF؛ محرمانه | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `created_at` | `timestamp with time zone` | خیر | ندارد | زمان ایجاد رکورد | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `last_seen_at` | `timestamp with time zone` | خیر | ندارد | زمان آخرین فعالیت ثبت‌شده نشست | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `idle_expires_at` | `timestamp with time zone` | خیر | ندارد | زمان انقضای ناشی از عدم فعالیت نشست | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `absolute_expires_at` | `timestamp with time zone` | خیر | ندارد | سقف قطعی عمر نشست | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `revoked_at` | `timestamp with time zone` | بله | ندارد | زمان لغو | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |
| `revoked_reason` | `text` | بله | ندارد | دلیل لغو نشست | سامانه/اپراتور مجاز | شرح کاربردی از نام/نوع و قیود؛ نیازمند تأیید مصرف |

قیود جدول:
- `CHECK ((idle_expires_at <= absolute_expires_at))`
- `CHECK ((absolute_expires_at > created_at))`
- `CHECK ((octet_length(csrf_hash) = 32))`
- `CHECK ((octet_length(token_hash) = 32))`
- `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- `PRIMARY KEY (session_id)`
- `UNIQUE (token_hash)`
