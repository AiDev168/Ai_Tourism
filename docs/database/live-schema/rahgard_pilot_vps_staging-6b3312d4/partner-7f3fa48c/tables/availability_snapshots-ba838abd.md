# partner.availability_snapshots

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** Time-bounded availability observation, not a future guarantee.
- **دسترسی خواندن:** Organization member according to availability RLS.
- **دسترسی نوشتن:** POST observation only; do not overwrite history.
- **نمایش عمومی:** Freshness limited by observed_at/valid_until; unknown remains unknown.
- **API مدل/مسیر:** POST /organizations/{organization_id}/availability; workspace GET.
- **فیلد فرم UI:** PartnerWorkspace optional availability observation form/history.
- **Static SQL operation hints:** backend/app/api/partners.py:INSERT@1171 | backend/app/api/partners.py:SELECT@1005 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/019_partner_workspace.sql:245
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-24T11:28:13Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'snapshot_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier for one time-bounded availability observation. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'organization_id' | 'uuid' | خیر | — | Owning partner organization; tenant boundary used by foreign keys and RLS. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'offer_id' | 'uuid' | خیر | — | Offer whose availability was observed. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'schedule_id' | 'uuid' | بله | — | Related schedule occurrence source; nullable when the observation is not schedule-specific. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'occurrence_starts_at' | 'timestamp with time zone' | بله | — | Start instant of the observed service occurrence, stored as timestamptz. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'occurrence_ends_at' | 'timestamp with time zone' | بله | — | End instant of that occurrence when known; must not precede its start. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'availability_state' | 'text' | خیر | — | Observed state: available, unavailable, limited, unknown, or conflicting. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'available_count' | 'integer' | بله | — | Non-negative observed count when applicable; NULL is required for unknown state. | PostgreSQL storage type 'integer' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'source_kind' | 'text' | خیر | — | Provenance class: partner_asserted, approved_feed, or platform_observation. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'observed_at' | 'timestamp with time zone' | بله | — | Instant when availability was observed; required for available state. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'valid_from' | 'timestamp with time zone' | بله | — | Start of the interval for which this observation is represented as valid. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'valid_until' | 'timestamp with time zone' | بله | — | End of the validity interval; do not treat stale data as current. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_by' | 'uuid' | بله | — | User account that submitted the observation, if recorded. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:245; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **availability_snapshots_availability_state_check** (`c`): `CHECK ((availability_state = ANY (ARRAY['available'::text, 'unavailable'::text, 'limited'::text, 'unknown'::text, 'conflicting'::text])))`
- **availability_snapshots_available_count_check** (`c`): `CHECK (((available_count IS NULL) OR (available_count >= 0)))`
- **availability_snapshots_check** (`c`): `CHECK ((((availability_state = 'unknown'::text) AND (available_count IS NULL)) OR (availability_state <> 'unknown'::text)))`
- **availability_snapshots_check1** (`c`): `CHECK (((availability_state <> 'available'::text) OR (observed_at IS NOT NULL)))`
- **availability_snapshots_check2** (`c`): `CHECK (((occurrence_ends_at IS NULL) OR (occurrence_starts_at IS NULL) OR (occurrence_ends_at >= occurrence_starts_at)))`
- **availability_snapshots_check3** (`c`): `CHECK (((valid_until IS NULL) OR (valid_from IS NULL) OR (valid_until >= valid_from)))`
- **availability_snapshots_source_kind_check** (`c`): `CHECK ((source_kind = ANY (ARRAY['partner_asserted'::text, 'approved_feed'::text, 'platform_observation'::text])))`
- **availability_snapshots_created_by_fkey** (`f`): `FOREIGN KEY (created_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **availability_snapshots_organization_id_offer_id_schedule_i_fkey** (`f`): `FOREIGN KEY (organization_id, offer_id, schedule_id) REFERENCES partner.offers(organization_id, offer_id, schedule_id) ON DELETE RESTRICT`
- **availability_snapshots_pkey** (`p`): `PRIMARY KEY (snapshot_id)`

## ایندکس‌ها

- `availability_snapshots_pkey`: `CREATE UNIQUE INDEX availability_snapshots_pkey ON partner.availability_snapshots USING btree (snapshot_id)`
- `ix_partner_availability_offer_occurrence`: `CREATE INDEX ix_partner_availability_offer_occurrence ON partner.availability_snapshots USING btree (organization_id, offer_id, occurrence_starts_at, observed_at DESC)`

## سیاست‌های RLS

- `availability_insert`: command=a, roles=[], using=`—`, with_check=`(partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text, 'availability_operator'::text]) AND ((created_by IS NULL) OR (created_by = partner.current_actor_id())))`
- `availability_select`: command=r, roles=[], using=`(partner.has_active_membership(organization_id, partner.current_actor_id()) OR partner.has_platform_capability(partner.current_actor_id(), 'offer_review'::text))`, with_check=`—`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **14**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
