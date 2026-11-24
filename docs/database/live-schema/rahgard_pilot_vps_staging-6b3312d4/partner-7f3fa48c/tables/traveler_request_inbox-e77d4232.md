# partner.traveler_request_inbox

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** Organization-scoped notification for a request revision.
- **دسترسی خواندن:** Active members of that organization.
- **دسترسی نوشتن:** System-created on each revision; client can mark viewed only.
- **نمایش عمومی:** Private and tenant-scoped.
- **API مدل/مسیر:** GET organization requests; POST /organizations/{organization_id}/requests/{inbox_event_id}/viewed.
- **فیلد فرم UI:** PartnerWorkspace eligible request inbox.
- **Static SQL operation hints:** backend/app/api/partners.py:SELECT@473 | backend/app/api/partners.py:UPDATE@519 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/022_traveler_company_requests.sql:79
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-24T11:28:13Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'inbox_event_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier of the organization inbox event. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:79; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'organization_id' | 'uuid' | خیر | — | Recipient organization and tenant boundary. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:79; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'revision_id' | 'uuid' | خیر | — | Private request revision represented by the inbox event. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:79; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'event_kind' | 'text' | خیر | — | Event type: request_shared or request_revised. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:79; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp when the inbox event was created. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:79; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'viewed_at' | 'timestamp with time zone' | بله | — | Timestamp the authorized member marked the event viewed. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:79; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **traveler_request_inbox_event_kind_check** (`c`): `CHECK ((event_kind = ANY (ARRAY['request_shared'::text, 'request_revised'::text])))`
- **traveler_request_inbox_revision_id_fkey** (`f`): `FOREIGN KEY (revision_id) REFERENCES partner.traveler_request_revisions(revision_id) ON DELETE CASCADE`
- **traveler_request_inbox_revision_id_organization_id_fkey** (`f`): `FOREIGN KEY (revision_id, organization_id) REFERENCES partner.traveler_request_revisions(revision_id, organization_id) ON DELETE CASCADE`
- **traveler_request_inbox_pkey** (`p`): `PRIMARY KEY (inbox_event_id)`
- **traveler_request_inbox_revision_id_key** (`u`): `UNIQUE (revision_id)`

## ایندکس‌ها

- `ix_traveler_request_inbox_org_unread`: `CREATE INDEX ix_traveler_request_inbox_org_unread ON partner.traveler_request_inbox USING btree (organization_id, created_at DESC) WHERE (viewed_at IS NULL)`
- `traveler_request_inbox_pkey`: `CREATE UNIQUE INDEX traveler_request_inbox_pkey ON partner.traveler_request_inbox USING btree (inbox_event_id)`
- `traveler_request_inbox_revision_id_key`: `CREATE UNIQUE INDEX traveler_request_inbox_revision_id_key ON partner.traveler_request_inbox USING btree (revision_id)`

## سیاست‌های RLS

- `traveler_inbox_read`: command=r, roles=[], using=`partner.has_active_membership(organization_id, partner.current_actor_id())`, with_check=`—`
- `traveler_inbox_view`: command=w, roles=[], using=`partner.has_active_membership(organization_id, partner.current_actor_id())`, with_check=`partner.has_active_membership(organization_id, partner.current_actor_id())`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **6**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
