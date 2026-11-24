# operations.private_pilot_geo_approvals

- **دیتابیس:** `rahgard_pilot_vps_staging`
- **نوع شیء:** جدول معمولی
- **شرح:** No PostgreSQL comment or baseline glossary table description was recorded.
- **دسترسی خواندن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.
- **دسترسی نوشتن:** از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.
- **نمایش عمومی:** نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.
- **API مدل/مسیر:** مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.
- **فیلد فرم UI:** فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.
- **Static SQL operation hints:** no explicit qualified CRUD clause found; not proof of no read/write path (literal source matches only, not runtime proof)
- **PostgreSQL relation owner:** `rahgard_pilot_geo_migrator` (technical ownership only; not product approval)
- **Architecture disposition:** `INVESTIGATE` — No qualified backend/frontend relation reference was found; dynamic queries, contracts, or compatibility use may exist. Preserve until confirmed.
- **DDL provenance:** engineering/pilot/sql/013_private_pilot_geo_audit.sql:65
- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `2026-11-24T11:28:13Z`; no application rows
- **امنیت ردیفی (RLS):** خاموش؛ Forced=خیر
- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.

## ستون‌ها و قرارداد داده

| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |
|---|---|---|---|---|---|---|---|---|
| 'authorization_id' | 'uuid' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'uuid' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/013_private_pilot_geo_audit.sql:65 | restricted_operational_metadata / PostgreSQL owner 'rahgard_pilot_geo_migrator'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'destination_key' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/013_private_pilot_geo_audit.sql:65 | restricted_operational_metadata / PostgreSQL owner 'rahgard_pilot_geo_migrator'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'decision_sha256' | 'character(64)' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'character(64)' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/013_private_pilot_geo_audit.sql:65 | restricted_operational_metadata / PostgreSQL owner 'rahgard_pilot_geo_migrator'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'marker_sha256' | 'character(64)' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'character(64)' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/013_private_pilot_geo_audit.sql:65 | restricted_operational_metadata / PostgreSQL owner 'rahgard_pilot_geo_migrator'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'reviewer' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/013_private_pilot_geo_audit.sql:65 | restricted_operational_metadata / PostgreSQL owner 'rahgard_pilot_geo_migrator'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'approval_reference' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/013_private_pilot_geo_audit.sql:65 | restricted_operational_metadata / PostgreSQL owner 'rahgard_pilot_geo_migrator'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'reviewed_at' | 'timestamp with time zone' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/013_private_pilot_geo_audit.sql:65 | restricted_operational_metadata / PostgreSQL owner 'rahgard_pilot_geo_migrator'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'coordinate_role' | 'text' | خیر | — | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'text' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/013_private_pilot_geo_audit.sql:65 | restricted_operational_metadata / PostgreSQL owner 'rahgard_pilot_geo_migrator'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |
| 'created_at' | 'timestamp with time zone' | خیر | 'now()' | **UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix. | PostgreSQL storage type 'timestamp with time zone' only; business units, accepted values, and validation are not inferred from the SQL type. | engineering/pilot/sql/013_private_pilot_geo_audit.sql:65 | restricted_operational_metadata / PostgreSQL owner 'rahgard_pilot_geo_migrator'; Operational, integration, audit, or migration surface; not a public content contract.; provisional domain classification, not privacy-owner sign-off | qualified backend relation refs: no literal qualified hit; column write path is not inferred |

## محدودیت‌ها و ارتباط‌ها

- **private_pilot_geo_approvals_coordinate_role_check** (`c`): `CHECK ((coordinate_role = ANY (ARRAY['representative_point'::text, 'property_reference'::text])))`
- **private_pilot_geo_approvals_decision_sha256_check** (`c`): `CHECK ((decision_sha256 ~ '^[a-f0-9]{64}$'::text))`
- **private_pilot_geo_approvals_marker_sha256_check** (`c`): `CHECK ((marker_sha256 ~ '^[a-f0-9]{64}$'::text))`
- **private_pilot_geo_approvals_authorization_id_fkey** (`f`): `FOREIGN KEY (authorization_id) REFERENCES operations.private_pilot_geo_authorizations(authorization_id)`
- **private_pilot_geo_approvals_destination_key_fkey** (`f`): `FOREIGN KEY (destination_key) REFERENCES knowledge.destinations(destination_key)`
- **private_pilot_geo_approvals_pkey** (`p`): `PRIMARY KEY (authorization_id)`
- **private_pilot_geo_approvals_destination_key_decision_sha256_key** (`u`): `UNIQUE (destination_key, decision_sha256, marker_sha256)`

## ایندکس‌ها

- `private_pilot_geo_approvals_destination_key_decision_sha256_key`: `CREATE UNIQUE INDEX private_pilot_geo_approvals_destination_key_decision_sha256_key ON operations.private_pilot_geo_approvals USING btree (destination_key, decision_sha256, marker_sha256)`
- `private_pilot_geo_approvals_pkey`: `CREATE UNIQUE INDEX private_pilot_geo_approvals_pkey ON operations.private_pilot_geo_approvals USING btree (authorization_id)`

## سیاست‌های RLS

- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.

## تریگرهای غیرسیستمی

- تریگر غیرسیستمی‌ای ثبت نشده است.

## Glossary coverage (not a requirement count)

- Undocumented first-party base-table occurrences in this object: **0** of **9**. This does not mean the same number of distinct business parameters is needed.
- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.
- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.
- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.
