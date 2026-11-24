# identity.staging_password_credentials

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نیازمند توضیح دامنه‌ای تأییدشده از کد و مالک محصول
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'user_id' | 'uuid' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'login_name' | 'text' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'salt' | 'bytea' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | دادهٔ دودویی؛ مقدار خام نباید در این مستندات نمایش داده شود |
| 'verifier' | 'bytea' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | دادهٔ دودویی؛ مقدار خام نباید در این مستندات نمایش داده شود |
| 'iterations' | 'integer' | خیر | — | **نیازمند تکمیل از API / منطق دامنه** | عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **نیازمند تکمیل از API / منطق دامنه** | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **staging_password_credentials_iterations_check** (`c`): `CHECK ((iterations = 600000))`
- **staging_password_credentials_login_name_check** (`c`): `CHECK (((login_name = lower(login_name)) AND ((length(login_name) >= 5) AND (length(login_name) <= 254)) AND (login_name ~ '^[^@[:space:]]+@[^@[:space:]]+\.[^@[:space:]]+$'::text)))`
- **staging_password_credentials_salt_check** (`c`): `CHECK ((octet_length(salt) = 32))`
- **staging_password_credentials_verifier_check** (`c`): `CHECK ((octet_length(verifier) = 32))`
- **staging_password_credentials_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **staging_password_credentials_pkey** (`p`): `PRIMARY KEY (user_id)`
- **staging_password_credentials_login_name_key** (`u`): `UNIQUE (login_name)`

## ایندکس‌ها

- `staging_password_credentials_login_name_key`: `CREATE UNIQUE INDEX staging_password_credentials_login_name_key ON identity.staging_password_credentials USING btree (login_name)`
- `staging_password_credentials_pkey`: `CREATE UNIQUE INDEX staging_password_credentials_pkey ON identity.staging_password_credentials USING btree (user_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **6** از **6**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
