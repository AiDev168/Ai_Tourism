# partner.traveler_request_revisions

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** نسخه‌های تغییرناپذیر/بازنگری‌شده درخواست و برنامه اشتراک‌گذاری‌شده با سازمان.
- **دسترسی خواندن:** Only active recipient members and traveler while share remains active.
- **دسترسی نوشتن:** Created by the revision-capture function; no direct client write grant.
- **نمایش عمومی:** Private; snapshots can contain sensitive trip requirements.
- **API مدل/مسیر:** Read through protected organization request/revision routes.
- **فیلد فرم UI:** PartnerWorkspace protected inbox and request/itinerary views.
- **Static SQL operation hints:** backend/app/api/partners.py:JOIN@474 | backend/app/api/partners.py:SELECT@1223 | backend/app/api/partners.py:SELECT@1344 | backend/app/api/partners.py:SELECT@424 | backend/app/api/partners.py:SELECT@497 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/022_traveler_company_requests.sql:60
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-24T11:28:13Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'revision_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه نسخه بازنگری. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:60; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'share_id' | 'uuid' | خیر | — | اشتراک مرتبط. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:60; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'organization_id' | 'uuid' | خیر | — | سازمان دریافت‌کننده. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:60; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'revision_number' | 'integer' | خیر | — | شماره ترتیبی نسخه برای همان اشتراک. | PostgreSQL storage type 'integer' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:60; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'trip_version' | 'integer' | خیر | — | نسخه برنامه/سفر مرجع. | PostgreSQL storage type 'integer' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:60; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'event_kind' | 'text' | خیر | — | نوع رویداد نسخه مانند اشتراک جدید یا بازنگری. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:60; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'request_snapshot' | 'jsonb' | خیر | — | نمای ثابت و محدودشده شرایط سفر در لحظه ارسال؛ اطلاعات شخصی باید کنترل دسترسی داشته باشد. | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:60; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'itinerary_snapshot' | 'jsonb' | خیر | '[redacted string default]' | نمای ثابت برنامه سفر در لحظه ارسال. | PostgreSQL storage type 'jsonb' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:60; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_by' | 'uuid' | خیر | — | Traveler account whose authorized change generated this immutable revision. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:60; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | زمان ایجاد نسخه. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:60; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'is_synthetic' | 'boolean' | خیر | 'false' | علامت داده آزمایشی؛ نباید در صندوق تولیدی به کاربر واقعی نشان داده شود. | PostgreSQL storage type 'boolean' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:60; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **traveler_request_revisions_event_kind_check** (`c`): `CHECK ((event_kind = ANY (ARRAY['request_shared'::text, 'request_revised'::text])))`
- **traveler_request_revisions_itinerary_snapshot_check** (`c`): `CHECK ((jsonb_typeof(itinerary_snapshot) = 'object'::text))`
- **traveler_request_revisions_request_snapshot_check** (`c`): `CHECK ((jsonb_typeof(request_snapshot) = 'object'::text))`
- **traveler_request_revisions_revision_number_check** (`c`): `CHECK ((revision_number > 0))`
- **traveler_request_revisions_trip_version_check** (`c`): `CHECK ((trip_version > 0))`
- **traveler_request_revisions_created_by_fkey** (`f`): `FOREIGN KEY (created_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **traveler_request_revisions_share_id_organization_id_fkey** (`f`): `FOREIGN KEY (share_id, organization_id) REFERENCES partner.traveler_request_shares(share_id, organization_id) ON DELETE CASCADE`
- **traveler_request_revisions_pkey** (`p`): `PRIMARY KEY (revision_id)`
- **traveler_request_revisions_revision_id_organization_id_key** (`u`): `UNIQUE (revision_id, organization_id)`
- **traveler_request_revisions_share_id_revision_number_key** (`u`): `UNIQUE (share_id, revision_number)`

## ایندکس‌ها

- `ix_traveler_request_revisions_org`: `CREATE INDEX ix_traveler_request_revisions_org ON partner.traveler_request_revisions USING btree (organization_id, created_at DESC)`
- `traveler_request_revisions_pkey`: `CREATE UNIQUE INDEX traveler_request_revisions_pkey ON partner.traveler_request_revisions USING btree (revision_id)`
- `traveler_request_revisions_revision_id_organization_id_key`: `CREATE UNIQUE INDEX traveler_request_revisions_revision_id_organization_id_key ON partner.traveler_request_revisions USING btree (revision_id, organization_id)`
- `traveler_request_revisions_share_id_revision_number_key`: `CREATE UNIQUE INDEX traveler_request_revisions_share_id_revision_number_key ON partner.traveler_request_revisions USING btree (share_id, revision_number)`

## سیاست‌های RLS

- `traveler_revision_insert`: command=a, roles=[], using=`—`, with_check=`((created_by = partner.current_actor_id()) AND (EXISTS ( SELECT 1    FROM partner.traveler_request_shares s   WHERE ((s.share_id = traveler_request_revisions.share_id) AND (s.traveler_id = partner.current_actor_id()) AND (s.revoked_at IS NULL)))))`
- `traveler_revision_read`: command=r, roles=[], using=`(EXISTS ( SELECT 1    FROM partner.traveler_request_shares s   WHERE ((s.share_id = traveler_request_revisions.share_id) AND (s.revoked_at IS NULL) AND ((s.traveler_id = partner.current_actor_id()) OR partner.has_active_membership(s.organization_id, partner.current_actor_id())))))`, with_check=`—`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **11**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
