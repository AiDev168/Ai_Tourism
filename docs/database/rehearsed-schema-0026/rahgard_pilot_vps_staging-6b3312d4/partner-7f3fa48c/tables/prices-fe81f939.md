# partner.prices

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** اقلام قیمت پیشنهادی همراه واحد و کیفیت/اعتبار ثبت مبلغ.
- **دسترسی خواندن:** Organization member according to price RLS.
- **دسترسی نوشتن:** POST observation only; previous observations are preserved.
- **نمایش عمومی:** Not a guaranteed current price; validity and source provenance must be shown.
- **API مدل/مسیر:** POST /organizations/{organization_id}/prices; workspace GET.
- **فیلد فرم UI:** PartnerWorkspace optional price observation form/history.
- **Static SQL operation hints:** backend/app/api/partners.py:INSERT@1138 | backend/app/api/partners.py:SELECT@1004 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/019_partner_workspace.sql:221
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'price_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه یکتای ردیف قیمت. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'organization_id' | 'uuid' | خیر | — | سازمان مالک رکورد قیمت. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'offer_id' | 'uuid' | خیر | — | پیشنهاد مربوط به قیمت. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'price_state' | 'text' | خیر | — | وضعیت معتبر بودن، اعلام‌نشده بودن یا برآوردی‌بودن مبلغ. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'amount' | 'numeric(14,2)' | بله | — | مقدار عددی مبلغ مطابق precision و scale ستون. | PostgreSQL storage type 'numeric(14,2)' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'currency' | 'character(3)' | بله | — | واحد پول/کد ارز؛ با denomination و unit اشتباه نشود. | PostgreSQL storage type 'character(3)' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'denomination' | 'text' | بله | — | مقیاس نمایشی مبلغ مانند میلیون؛ واحدهای واقعی باید از قرارداد استخراج شوند. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'unit' | 'text' | بله | — | مبنای قیمت مثل نفر/شب/خدمت (بسته به enum/قرارداد). | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'tax_included' | 'boolean' | بله | — | Whether the asserted amount includes tax; nullable when not known or not applicable. | PostgreSQL storage type 'boolean' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'valid_from' | 'timestamp with time zone' | بله | — | Start of the stated price validity interval, when provided. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'valid_until' | 'timestamp with time zone' | بله | — | پایان اعتبار قیمت. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'observed_at' | 'timestamp with time zone' | بله | — | زمان مشاهده/دریافت قیمت. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'source_kind' | 'text' | خیر | — | Price provenance: partner_asserted, approved_feed, or platform_observation. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:221; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |

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

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **14**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
