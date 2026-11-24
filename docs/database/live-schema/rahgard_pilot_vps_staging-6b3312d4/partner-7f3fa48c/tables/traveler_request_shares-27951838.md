# partner.traveler_request_shares

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** اشتراک‌گذاری موردی و رضایت‌مندانه درخواست یک سفر با یک سازمان.
- **دسترسی خواندن:** Trip owner or active organization members while share is not revoked.
- **دسترسی نوشتن:** Created only after explicit traveler consent; traveler may revoke.
- **نمایش عمومی:** Private, authenticated, tenant-scoped.
- **API مدل/مسیر:** POST/GET/DELETE /trips/{trip_id}/company-shares.
- **فیلد فرم UI:** Traveler journey company-sharing consent flow.
- **Static SQL operation hints:** backend/app/api/partners.py:INSERT@385 | backend/app/api/partners.py:SELECT@1209 | backend/app/api/partners.py:SELECT@1341 | backend/app/api/partners.py:SELECT@395 | backend/app/api/partners.py:SELECT@425 | backend/app/api/partners.py:UPDATE@446 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/022_traveler_company_requests.sql:24
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-24T11:28:13Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'share_id' | 'uuid' | خیر | 'gen_random_uuid()' | شناسه یکتای اشتراک‌گذاری. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:24; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'trip_id' | 'uuid' | خیر | — | سفر مبدا درخواست. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:24; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'traveler_id' | 'uuid' | خیر | — | مالک درخواست سفر. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:24; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'organization_id' | 'uuid' | خیر | — | سازمان دریافت‌کننده درخواست. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:24; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'consent_policy_version' | 'text' | خیر | — | نسخه قرارداد رضایت معتبر هنگام اشتراک‌گذاری. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:24; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'include_original_request' | 'boolean' | خیر | 'false' | مشخص می‌کند متن اولیه خام درخواست نیز با رضایت صریح ضمیمه شده یا خیر. | PostgreSQL storage type 'boolean' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:24; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'consented_at' | 'timestamp with time zone' | خیر | 'now()' | زمان اخذ رضایت و ایجاد دسترسی. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:24; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'revoked_at' | 'timestamp with time zone' | بله | — | زمان لغو دسترسی، در صورت وقوع. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:24; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Timestamp the explicit traveler-authorized share was created. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/022_traveler_company_requests.sql:24; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **traveler_request_shares_check** (`c`): `CHECK (((revoked_at IS NULL) OR (revoked_at >= consented_at)))`
- **traveler_request_shares_consent_policy_version_check** (`c`): `CHECK (((length(btrim(consent_policy_version)) >= 1) AND (length(btrim(consent_policy_version)) <= 80)))`
- **traveler_request_shares_organization_id_fkey** (`f`): `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- **traveler_request_shares_traveler_id_fkey** (`f`): `FOREIGN KEY (traveler_id) REFERENCES identity.users(user_id) ON DELETE CASCADE`
- **traveler_request_shares_trip_id_fkey** (`f`): `FOREIGN KEY (trip_id) REFERENCES travel.trips(trip_id) ON DELETE CASCADE`
- **traveler_request_shares_pkey** (`p`): `PRIMARY KEY (share_id)`
- **traveler_request_shares_share_id_organization_id_key** (`u`): `UNIQUE (share_id, organization_id)`
- **traveler_request_shares_trip_id_organization_id_key** (`u`): `UNIQUE (trip_id, organization_id)`

## ایندکس‌ها

- `ix_traveler_request_shares_org`: `CREATE INDEX ix_traveler_request_shares_org ON partner.traveler_request_shares USING btree (organization_id, created_at DESC) WHERE (revoked_at IS NULL)`
- `ix_traveler_request_shares_owner`: `CREATE INDEX ix_traveler_request_shares_owner ON partner.traveler_request_shares USING btree (traveler_id, created_at DESC)`
- `traveler_request_shares_pkey`: `CREATE UNIQUE INDEX traveler_request_shares_pkey ON partner.traveler_request_shares USING btree (share_id)`
- `traveler_request_shares_share_id_organization_id_key`: `CREATE UNIQUE INDEX traveler_request_shares_share_id_organization_id_key ON partner.traveler_request_shares USING btree (share_id, organization_id)`
- `traveler_request_shares_trip_id_organization_id_key`: `CREATE UNIQUE INDEX traveler_request_shares_trip_id_organization_id_key ON partner.traveler_request_shares USING btree (trip_id, organization_id)`

## سیاست‌های RLS

- `traveler_share_insert`: command=a, roles=[], using=`—`, with_check=`((traveler_id = partner.current_actor_id()) AND (EXISTS ( SELECT 1    FROM travel.trips t   WHERE ((t.trip_id = traveler_request_shares.trip_id) AND (t.user_id = partner.current_actor_id()) AND (NOT t.is_synthetic)))) AND (EXISTS ( SELECT 1    FROM partner.share_eligible_organizations o   WHERE (o.organization_id = traveler_request_shares.organization_id))))`
- `traveler_share_read`: command=r, roles=[], using=`((traveler_id = partner.current_actor_id()) OR ((revoked_at IS NULL) AND partner.has_active_membership(organization_id, partner.current_actor_id())))`, with_check=`—`
- `traveler_share_revoke`: command=w, roles=[], using=`(traveler_id = partner.current_actor_id())`, with_check=`(traveler_id = partner.current_actor_id())`

## تریگرهای غیرسیستمی

- `trg_trip_request_revision_share`: `CREATE TRIGGER trg_trip_request_revision_share AFTER INSERT ON partner.traveler_request_shares FOR EACH ROW EXECUTE FUNCTION partner.capture_trip_request_revision_from_share()`

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **9**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
