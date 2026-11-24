# partner.prices

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** اقلام قیمت پیشنهادی همراه واحد و کیفیت/اعتبار ثبت مبلغ.
- **دسترسی خواندن:** Organization member according to price RLS.
- **دسترسی نوشتن:** POST observation only; previous observations are preserved.
- **نمایش عمومی:** Not a guaranteed current price; validity and source provenance must be shown.
- **API مدل/مسیر:** POST /organizations/{organization_id}/prices; workspace GET.
- **فیلد فرم UI:** PartnerWorkspace optional price observation form/history.
- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `2026-11-24T06:58:13Z`
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |
|---|---|---|---|---|---|
| 'price_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه یکتای ردیف قیمت. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'organization_id' | 'uuid' | خیر | — | سازمان مالک رکورد قیمت. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'offer_id' | 'uuid' | خیر | — | پیشنهاد مربوط به قیمت. | UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| 'price_state' | 'text' | خیر | — | وضعیت معتبر بودن، اعلام‌نشده بودن یا برآوردی‌بودن مبلغ. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'amount' | 'numeric(14,2)' | بله | — | مقدار عددی مبلغ مطابق precision و scale ستون. | عدد ده‌دهی؛ precision و scale از PostgreSQL؛ واحد/ارز باید مستند شود |
| 'currency' | 'character(3)' | بله | — | واحد پول/کد ارز؛ با denomination و unit اشتباه نشود. | رشته با طول ثابت مشخص‌شده در PostgreSQL |
| 'denomination' | 'text' | بله | — | مقیاس نمایشی مبلغ مانند میلیون؛ واحدهای واقعی باید از قرارداد استخراج شوند. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'unit' | 'text' | بله | — | مبنای قیمت مثل نفر/شب/خدمت (بسته به enum/قرارداد). | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'tax_included' | 'boolean' | بله | — | Whether the asserted amount includes tax; nullable when not known or not applicable. | true / false |
| 'valid_from' | 'timestamp with time zone' | بله | — | Start of the stated price validity interval, when provided. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'valid_until' | 'timestamp with time zone' | بله | — | پایان اعتبار قیمت. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'observed_at' | 'timestamp with time zone' | بله | — | زمان مشاهده/دریافت قیمت. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |
| 'source_kind' | 'text' | خیر | — | Price provenance: partner_asserted, approved_feed, or platform_observation. | رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL |

## محدودیت‌ها و ارتباط‌ها

- **prices_amount_check** (`c`): `CHECK (((amount IS NULL) OR (amount >= (0)::numeric)))`
- **prices_check** (`c`): `CHECK (((price_state <> 'known'::text) OR ((amount IS NOT NULL) AND (currency IS NOT NULL) AND (denomination IS NOT NULL) AND (unit IS NOT NULL) AND (observed_at IS NOT NULL))))`
- **prices_check1** (`c`): `CHECK (((price_state = 'known'::text) OR ((amount IS NULL) AND (currency IS NULL) AND (denomination IS NULL) AND (unit IS NULL) AND (tax_included IS NULL))))`
- **prices_check2** (`c`): `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- **prices_currency_check** (`c`): `CHECK (((currency IS NULL) OR (currency ~ '^[A-Z]{3}$'::text)))`
- **prices_price_state_check** (`c`): `CHECK ((price_state = ANY (ARRAY['known'::text, 'unknown'::text, 'not_applicable'::text, 'conflicting'::text])))`
- **prices_source_kind_check** (`c`): `CHECK ((source_kind = ANY (ARRAY['partner_asserted'::text, 'approved_feed'::text, 'platform_observation'::text])))`
- **prices_organization_id_offer_id_fkey** (`f`): `FOREIGN KEY (organization_id, offer_id) REFERENCES partner.offers(organization_id, offer_id) ON DELETE RESTRICT`
- **prices_pkey** (`p`): `PRIMARY KEY (price_id)`

## ایندکس‌ها

- `ix_partner_prices_offer_observed`: `CREATE INDEX ix_partner_prices_offer_observed ON partner.prices USING btree (organization_id, offer_id, observed_at DESC)`
- `prices_pkey`: `CREATE UNIQUE INDEX prices_pkey ON partner.prices USING btree (price_id)`

## سیاست‌های RLS

- `prices_insert`: command=a, roles=[], using=`—`, with_check=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'editor'::text, 'availability_operator'::text])`
- `prices_select`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text))`, with_check=`—`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## نیازمندی تکمیل دامنه

- تعداد ستون‌های فاقد شرح صریح: **0** از **14**.
- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.
- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.
