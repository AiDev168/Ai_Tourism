# partner.memberships

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** عضویت کاربران در یک سازمان و نقش/فعال‌بودن آن‌ها.
- **دسترسی خواندن:** Organization members and reviewer capabilities only where policies allow.
- **دسترسی نوشتن:** Created with company registration or invitation flow; no generic membership editor.
- **نمایش عمومی:** Never public.
- **API مدل/مسیر:** Created internally by POST /organizations; no general membership CRUD route.
- **فیلد فرم UI:** No ordinary user form; owner/member management is not exposed in this workspace.
- **Static SQL operation hints:** backend/app/api/partners.py:INSERT@571 | backend/app/api/partners.py:SELECT@1213 (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `ai_tourism_owner` (technical ownership only; not product approval)
- **Architecture disposition:** `KEEP` — Runtime source contains a qualified relation reference; this proves a code dependency, not that every column is necessary.
- **DDL provenance:** engineering/pilot/sql/019_partner_workspace.sql:47
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-25T13:08:55Z`; no application rows
- **امنیت ردیفی (RLS):** روشن؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'membership_id' | 'uuid' | خیر | 'gen_random_uuid()' | Unique identifier for the organization membership. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:47; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'organization_id' | 'uuid' | خیر | — | ارجاع به سازمان عضوپذیر. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:47; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'user_id' | 'uuid' | خیر | — | ارجاع به حساب شخص عضو سازمان. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:47; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'role' | 'text' | خیر | — | نقش عضو در سازمان؛ محدوده دسترسی از سیاست‌های مجوز استخراج شود. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:47; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'status' | 'text' | خیر | '[redacted string default]' | وضعیت عضویت. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:47; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'invited_by' | 'uuid' | بله | — | Inviting user when membership originated from an invitation; nullable for owner registration. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:47; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'accepted_at' | 'timestamp with time zone' | بله | — | زمان پذیرش عضویت یا دعوت. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:47; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'revoked_at' | 'timestamp with time zone' | بله | — | Timestamp that an active membership was revoked; must match revoked status. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:47; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | Database creation timestamp. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/019_partner_workspace.sql:47; existing baseline glossary | tenant_private_until_reviewed / PostgreSQL owner 'ai_tourism_owner'; Partner tenant data; publication requires independent review/eligibility policy.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: backend/app/api/partners.py; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **memberships_check** (`c`): `CHECK (((status = 'revoked'::text) = (revoked_at IS NOT NULL)))`
- **memberships_role_check** (`c`): `CHECK ((role = ANY (ARRAY['owner'::text, 'manager'::text, 'editor'::text, 'availability_operator'::text, 'viewer'::text])))`
- **memberships_status_check** (`c`): `CHECK ((status = ANY (ARRAY['invited'::text, 'active'::text, 'revoked'::text, 'suspended'::text])))`
- **memberships_invited_by_fkey** (`f`): `FOREIGN KEY (invited_by) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **memberships_organization_id_fkey** (`f`): `FOREIGN KEY (organization_id) REFERENCES partner.organizations(organization_id) ON DELETE RESTRICT`
- **memberships_user_id_fkey** (`f`): `FOREIGN KEY (user_id) REFERENCES identity.users(user_id) ON DELETE RESTRICT`
- **memberships_pkey** (`p`): `PRIMARY KEY (membership_id)`
- **memberships_organization_id_membership_id_key** (`u`): `UNIQUE (organization_id, membership_id)`
- **memberships_organization_id_user_id_key** (`u`): `UNIQUE (organization_id, user_id)`

## ایندکس‌ها

- `ix_partner_memberships_user_status`: `CREATE INDEX ix_partner_memberships_user_status ON partner.memberships USING btree (user_id, status, organization_id)`
- `memberships_organization_id_membership_id_key`: `CREATE UNIQUE INDEX memberships_organization_id_membership_id_key ON partner.memberships USING btree (organization_id, membership_id)`
- `memberships_organization_id_user_id_key`: `CREATE UNIQUE INDEX memberships_organization_id_user_id_key ON partner.memberships USING btree (organization_id, user_id)`
- `memberships_pkey`: `CREATE UNIQUE INDEX memberships_pkey ON partner.memberships USING btree (membership_id)`

## سیاست‌های RLS

- `memberships_insert_owner_self`: command=a, roles=[], using=`—`, with_check=`((user_id = partner.current_actor_id()) AND (role = 'owner'::text) AND (status = 'active'::text) AND (EXISTS ( SELECT 1    FROM partner.organizations o   WHERE ((o.organization_id = memberships.organization_id) AND (o.created_by = partner.current_actor_id())))))`
- `memberships_read_scoped`: command=r, roles=[], using=`((user_id = partner.current_actor_id()) OR partner.has_active_membership(organization_id, partner.current_actor_id()))`, with_check=`—`
- `memberships_update_scoped`: command=w, roles=[], using=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text])`, with_check=`partner.has_active_role(organization_id, partner.current_actor_id(), ARRAY['owner'::text, 'manager'::text])`

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **9**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
