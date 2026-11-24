#!/usr/bin/env python3
"""Read-only PostgreSQL catalogue -> one Markdown file per accessible relation.

Security contract: Never selects table rows, writes schema, exposes DSNs, or logs secrets.
Database connection comes only from the specified ENV var. PostgreSQL metadata is
read in a READ ONLY transaction with bounded lock and statement timeouts.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
EXTENSION_DOCUMENTATION = {
    "spatial_ref_sys": "https://postgis.net/docs/using_postgis_dbmanagement.html",
    "geometry_columns": "https://postgis.net/docs/using_postgis_dbmanagement.html",
    "geography_columns": "https://postgis.net/docs/using_postgis_dbmanagement.html",
}


def safe_part(raw: str) -> str:
    """Safe reversible-ish single filesystem component; hash avoids slug collisions."""
    clean = re.sub(r"[^a-zA-Z0-9_.-]+", "_", raw).strip("._") or "unnamed"
    return clean[:64] + "-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


def object_owner(schema: str, name: str) -> str:
    """Separate PostGIS-owned catalog relations from Rahgard application objects."""
    if schema == "public" and name in {"spatial_ref_sys", "geometry_columns", "geography_columns"}:
        return "extension"
    return "application"


def escape_cell(value: object) -> str:
    s = str(value) if value is not None else "—"
    return s.replace("|", "\\|").replace("\n", " ").replace("\r", " ").replace("`", "'")


def type_hint(pg_type: str) -> str:
    return f"PostgreSQL storage type `{pg_type}` only; business units, accepted values, and validation are not inferred from the SQL type."


def safe_default(value: str | None) -> str:
    if value is None:
        return "—"
    # Avoid leaking accidental static credential values in a column default.
    if len(value) > 180:
        return "[پنهان: پیش‌فرض بلند]"
    normalized = value.lower()
    if any(x in normalized for x in ["password", "secret", "token", "private_key", "api_key"]):
        return "[پنهان: احتمال اطلاعات حساس]"
    if "'" in value:
        return "[پنهان: مقدار ثابت متنی/عبارت دارای رشته؛ در مخزن خصوصی بازبینی شود]"
    return value


def read_csv_index(path: Path, key_fields: tuple[str, ...]) -> dict[tuple[str, ...], dict]:
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return {tuple(row[field] for field in key_fields): row for row in csv.DictReader(stream)}


def markdown_for_relation(db: str, rel: dict, cols: list[dict], cons: list[dict],
                          indexes: list[dict], policies: list[dict], descriptions: dict,
                          recorded_at: str, triggers: list[dict] | None = None,
                          architecture_metadata: dict | None = None) -> tuple[str, int]:
    dbkey = f"{db}.{rel['schema']}.{rel['name']}"
    more = descriptions.get(dbkey, descriptions.get(f"{rel['schema']}.{rel['name']}", {}))
    if not isinstance(more, dict):
        more = {}
    obj = more.get("_object", {}) if isinstance(more.get("_object", {}), dict) else {}
    architecture_metadata = architecture_metadata or {}
    table_comment = rel.get("comment") or more.get("_table") or "No PostgreSQL comment or baseline glossary table description was recorded."
    kind = {"r": "جدول معمولی", "p": "جدول پارتیشن‌بندی‌شده", "v": "View", "m": "Materialized view", "f": "Foreign table"}.get(rel["kind"], rel["kind"])
    lines = [
        f"# {rel['schema']}.{rel['name']}", "",
        f"- **دیتابیس:** `{db}`",
        f"- **نوع شیء:** {kind}",
        f"- **شرح:** {table_comment}",
        f"- **دسترسی خواندن:** {obj.get('read_access', 'از RLS/GRANT واقعی و مسیر API تطبیق شود؛ این مستند مقدار ردیفی نمی‌خواند.')}",
        f"- **دسترسی نوشتن:** {obj.get('write_access', 'از RLS/GRANT واقعی و مسیر API تطبیق شود؛ دسترسی مستقیم SQL به کاربر ندهید.')}",
        f"- **نمایش عمومی:** {obj.get('public_exposure', 'نامشخص تا تطبیق با View انتشار و API؛ پیش‌فرض خصوصی.')}",
        f"- **API مدل/مسیر:** {obj.get('api', 'مسیر مشخصی در کد پیدا نشده؛ نیازمند بررسی مالک ماژول.')}",
        f"- **فیلد فرم UI:** {obj.get('ui', 'فرم مشخصی در فهرست نگاشت پیدا نشده؛ نیازمند بررسی UI.')}",
        f"- **Static SQL operation hints:** {architecture_metadata.get('static_sql_operation_hints', 'not identified; static absence does not prove no read/write path')} (literal source matches only, not runtime proof)",
        f"- **PostgreSQL relation owner:** `{architecture_metadata.get('database_owner', 'not captured')}` (technical ownership only; not product approval)",
        f"- **Architecture disposition:** `{architecture_metadata.get('decision', 'not assessed')}` — {architecture_metadata.get('decision_rationale', 'see architecture usage audit')}",
        f"- **DDL provenance:** {architecture_metadata.get('ddl_provenance', 'not linked; see architecture usage audit')}",
        f"- **Metadata snapshot:** PostgreSQL `pg_catalog`, read-only, captured `{recorded_at}`; no application rows",
        f"- **امنیت ردیفی (RLS):** {'روشن' if rel['rls'] else 'خاموش'}؛ Forced={'بله' if rel['force_rls'] else 'خیر'}",
        "- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.",
        "", "## ستون‌ها و قرارداد داده", "",
        "| Column occurrence | PostgreSQL type | Nullable | Sanitized default | Existing meaning / classification | Format evidence | Provenance | Sensitivity / owner | Read/write evidence |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    undocumented = 0
    for c in cols:
        col_meta = architecture_metadata.get("columns", {}).get(c["name"], {})
        meaning = c.get("comment")
        meaning_source = "PostgreSQL column comment" if meaning else ""
        if not meaning:
            meaning = more.get(c["name"])
            meaning_source = "existing baseline glossary" if meaning else ""
        is_extension = architecture_metadata.get("origin_class") == "extension_managed"
        is_view = rel["kind"] in {"v", "m"}
        if is_extension:
            meaning = "Extension-managed PostgreSQL/PostGIS metadata; not an independent Rahgard business field. See [official PostGIS database management documentation](https://postgis.net/docs/using_postgis_dbmanagement.html)."
        elif is_view:
            expression = col_meta.get("view_source_expression", "")
            status = col_meta.get("view_lineage_status", "lineage unresolved")
            meaning = f"Derived view output; not independently writable. SQL projection: `{expression or 'unresolved; inspect live view definition'}` (lineage: {status})."
        elif not meaning:
            meaning = "**UNDOCUMENTED:** no baseline glossary/comment evidence. Business meaning, necessity, and write owner have not been established; see the architecture/usage matrix."
        is_application_base = architecture_metadata.get("origin_class", "first_party_application_base") == "first_party_application_base"
        if is_application_base and not is_view and not is_extension and not meaning_source:
            undocumented += 1
        details = type_hint(c["pg_type"])
        if c.get("identity"):
            details += "; identity-generated database key"
        if c.get("generated"):
            details += "; database-generated"
        if c.get("comment"):
            details += f"; comment evidence: {c['comment']}"
        evidence_text = col_meta.get("source_evidence", "")
        if meaning_source:
            evidence_text = (evidence_text + "; " if evidence_text else "") + meaning_source
        sensitivity = col_meta.get("sensitivity_class", "not assessed")
        sensitivity_basis = col_meta.get("sensitivity_basis", "no column-level assessment")
        owner = architecture_metadata.get("database_owner", "unknown")
        access_evidence = architecture_metadata.get("backend_relation_refs", "")
        lines.append("| " + " | ".join(escape_cell(v) for v in (
            f"`{c['name']}`", f"`{c['pg_type']}`", "خیر" if c["notnull"] else "بله",
            f"`{safe_default(c.get('default'))}`" if c.get("default") is not None else "—",
            meaning,
            details,
            evidence_text or "not separately source-linked",
            f"{sensitivity} / PostgreSQL owner `{owner}`; {sensitivity_basis}",
            f"qualified backend relation refs: {access_evidence or 'none found by static scan'}; column write path is not inferred")) + " |")
    lines += ["", "## محدودیت‌ها و ارتباط‌ها", ""]
    if cons:
        for c in cons:
            lines.append(f"- **{escape_cell(c['name'])}** (`{escape_cell(c['type'])}`): `{escape_cell(c['definition'])}`")
    else:
        lines.append("- محدودیتی در `pg_constraint` برای این شیء مشاهده نشد.")
    lines += ["", "## ایندکس‌ها", ""]
    if indexes:
        for i in indexes:
            lines.append(f"- `{escape_cell(i['name'])}`: `{escape_cell(i['definition'])}`")
    else:
        lines.append("- ایندکسی مشاهده نشد / برای View قابل اعمال نیست.")
    lines += ["", "## سیاست‌های RLS", ""]
    if policies:
        for p in policies:
            lines.append(f"- `{escape_cell(p['name'])}`: command={escape_cell(p['command'])}, roles={escape_cell(p['roles'])}, using=`{escape_cell(p['using'])}`, with_check=`{escape_cell(p['with_check'])}`")
    else:
        lines.append("- سیاستی در `pg_policy` ثبت نشده یا برای این شیء صدق نمی‌کند.")
    lines += ["", "## تریگرهای غیرسیستمی", ""]
    if triggers:
        for trigger in triggers:
            lines.append(f"- `{escape_cell(trigger['name'])}`: `{escape_cell(trigger['definition'])}`")
    else:
        lines.append("- تریگر غیرسیستمی‌ای ثبت نشده است.")
    lines += ["", "## Glossary coverage (not a requirement count)", "",
              f"- Undocumented first-party base-table occurrences in this object: **{undocumented}** of **{len(cols)}**. This does not mean the same number of distinct business parameters is needed.",
              "- Derived-view columns are projections; consult `docs/database/architecture-usage/view_column_lineage.csv` rather than adding duplicate glossary prose.",
              "- Extension-owned fields refer to PostgreSQL/PostGIS documentation and are not Rahgard user-form fields.",
              "- Do not expose a generic SQL editor. User forms must follow an authorized API and role contract.", ""]
    return "\n".join(lines), undocumented


def fetch_catalog(conn) -> tuple[list[dict], dict]:
    # Current connection MUST already be enclosed in a read-only transaction.
    with conn.cursor() as cur:
        cur.execute("""
            SELECT n.nspname, c.relname, c.oid, c.relkind,
                   obj_description(c.oid, 'pg_class'), c.relrowsecurity, c.relforcerowsecurity
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind IN ('r','p','v','m','f')
              AND n.nspname <> 'information_schema'
              AND n.nspname NOT LIKE 'pg\\_%' ESCAPE '\\'
              AND c.relpersistence <> 't'
            ORDER BY n.nspname, c.relname
        """)
        relations = [dict(schema=r[0], name=r[1], oid=r[2], kind=r[3], comment=r[4], rls=r[5], force_rls=r[6]) for r in cur.fetchall()]
        output = {}
        for rel in relations:
            oid = rel["oid"]
            cur.execute("""
                SELECT a.attname, pg_catalog.format_type(a.atttypid,a.atttypmod),
                       a.attnotnull, pg_catalog.pg_get_expr(d.adbin,d.adrelid),
                       pg_catalog.col_description(a.attrelid,a.attnum),a.attidentity,a.attgenerated
                FROM pg_catalog.pg_attribute a
                LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
                WHERE a.attrelid=%s AND a.attnum>0 AND NOT a.attisdropped
                ORDER BY a.attnum
            """, (oid,))
            columns = [dict(name=r[0], pg_type=r[1], notnull=r[2], default=r[3], comment=r[4], identity=r[5], generated=r[6]) for r in cur.fetchall()]
            cur.execute("""
                SELECT conname, contype::text, pg_catalog.pg_get_constraintdef(oid)
                FROM pg_catalog.pg_constraint WHERE conrelid=%s ORDER BY contype, conname
            """, (oid,))
            constraints = [dict(name=r[0],type=r[1],definition=r[2]) for r in cur.fetchall()]
            cur.execute("""
                SELECT i.relname, pg_catalog.pg_get_indexdef(idx.indexrelid)
                FROM pg_catalog.pg_index idx
                JOIN pg_catalog.pg_class i ON i.oid=idx.indexrelid
                WHERE idx.indrelid=%s ORDER BY i.relname
            """, (oid,))
            indexes = [dict(name=r[0],definition=r[1]) for r in cur.fetchall()]
            cur.execute("""
                SELECT pol.polname, pol.polcmd,
                       ARRAY(SELECT rolname FROM pg_catalog.pg_roles WHERE oid=ANY(pol.polroles)),
                       pg_catalog.pg_get_expr(pol.polqual,pol.polrelid),
                       pg_catalog.pg_get_expr(pol.polwithcheck,pol.polrelid)
                FROM pg_catalog.pg_policy pol WHERE pol.polrelid=%s ORDER BY pol.polname
            """, (oid,))
            policies = [dict(name=r[0],command=r[1],roles=r[2],using=r[3],with_check=r[4]) for r in cur.fetchall()]
            cur.execute("""
                SELECT tgname, pg_catalog.pg_get_triggerdef(oid)
                FROM pg_catalog.pg_trigger
                WHERE tgrelid=%s AND NOT tgisinternal
                ORDER BY tgname
            """, (oid,))
            triggers = [dict(name=r[0],definition=r[1]) for r in cur.fetchall()]
            output[(rel["schema"],rel["name"])] = (columns, constraints, indexes, policies, triggers)
    return relations, output


def connect_ro(dsn: str, dbname: str | None = None):
    try:
        import psycopg
        from psycopg.conninfo import make_conninfo
    except ImportError as exc:
        raise RuntimeError('psycopg 3 must be installed in the OPERATOR environment') from exc
    conninfo = make_conninfo(dsn, dbname=dbname) if dbname else dsn
    return psycopg.connect(conninfo, connect_timeout=8, application_name='rahgard_schema_documenter_ro')


def run_ro(conn, action):
    with conn.transaction():
        conn.execute("SET TRANSACTION READ ONLY")
        conn.execute("SET LOCAL statement_timeout = '12s'")
        conn.execute("SET LOCAL lock_timeout = '3s'")
        return action(conn)


def list_databases(conn) -> list[str]:
    def query(c):
        return [row[0] for row in c.execute("""
            SELECT datname FROM pg_catalog.pg_database
            WHERE datallowconn AND NOT datistemplate
              AND datname NOT LIKE 'template%'
            ORDER BY datname
        """).fetchall()]
    return run_ro(conn, query)


def write_catalog_snapshot(snapshot: dict, output_root: Path, descriptions: dict) -> dict:
    """Render a sanitized metadata snapshot captured by the read-only live runner."""
    databases = snapshot.get("databases_attempted", [])
    if not isinstance(databases, list) or not all(isinstance(item, str) for item in databases):
        raise ValueError("snapshot databases_attempted is invalid")
    created_at = snapshot.get("created_utc")
    if not isinstance(created_at, str) or not created_at.endswith("Z"):
        raise ValueError("snapshot timestamp must be UTC")
    inaccessible = snapshot.get("databases_inaccessible", [])
    discovered = snapshot.get("discovered_non_template_databases", databases)
    skipped = snapshot.get("databases_skipped", [])
    relations = snapshot.get("relations", [])
    if not isinstance(inaccessible, list) or not isinstance(relations, list):
        raise ValueError("snapshot collections are invalid")
    root = output_root.resolve()
    created: list[dict] = []
    architecture_root = REPO_ROOT / "docs/database/architecture-usage"
    object_metadata = read_csv_index(architecture_root / "object_decision_matrix.csv", ("database", "schema", "relation"))
    column_metadata = read_csv_index(architecture_root / "column_occurrence_matrix.csv", ("database", "schema", "relation", "column_name"))
    relation_count_by_kind: Counter[str] = Counter()
    column_occurrences_by_kind: Counter[str] = Counter()
    baseline_glossary_coverage: Counter[str] = Counter()
    glossary_by_origin: dict[str, Counter[str]] = defaultdict(Counter)
    extension_names = {"spatial_ref_sys", "geometry_columns", "geography_columns"}
    for item in relations:
        if not isinstance(item, dict):
            raise ValueError("snapshot relation is invalid")
        db = item.get("database")
        rel = item.get("relation")
        cols = item.get("columns")
        cons = item.get("constraints", [])
        indexes = item.get("indexes", [])
        policies = item.get("policies", [])
        triggers = item.get("triggers", [])
        if not isinstance(db, str) or not isinstance(rel, dict) or not all(
            isinstance(collection, list) for collection in (cols, cons, indexes, policies, triggers)
        ):
            raise ValueError("snapshot relation fields are invalid")
        source_description = descriptions.get(
            f"{db}.{rel.get('schema')}.{rel.get('name')}",
            descriptions.get(f"{rel.get('schema')}.{rel.get('name')}", {}),
        )
        for column in cols:
            field = column.get("name")
            baseline_entry = source_description.get(field) if isinstance(source_description, dict) else None
            has_baseline = isinstance(baseline_entry, str) and bool(baseline_entry.strip())
            baseline_glossary_coverage["described" if has_baseline else "undocumented"] += 1
            if rel.get("schema") == "public" and rel.get("name") in extension_names:
                origin_class = "extension_managed"
                column_occurrences_by_kind[origin_class] += 1
            elif rel.get("kind") in {"v", "m"}:
                origin_class = "derived_view"
                column_occurrences_by_kind[origin_class] += 1
            elif rel.get("schema") in {"system", "operations", "integration"} or (rel.get("schema"), rel.get("name")) == ("public", "rahgard_private_pilot_marker"):
                origin_class = "first_party_system_or_operations"
                column_occurrences_by_kind[origin_class] += 1
            else:
                origin_class = "first_party_application_base"
                column_occurrences_by_kind[origin_class] += 1
            glossary_by_origin[origin_class]["described" if has_baseline else "undocumented"] += 1
        relation_count_by_kind[rel.get("kind", "unknown")] += 1
        object_key = (db, rel.get("schema"), rel.get("name"))
        object_meta = object_metadata.get(object_key, {})
        object_meta = {**object_meta, "columns": {
            column.get("name"): column_metadata.get((db, rel.get("schema"), rel.get("name"), column.get("name")), {})
            for column in cols
        }}
        markdown, gaps = markdown_for_relation(
            db, rel, cols, cons, indexes, policies, descriptions, created_at, triggers, object_meta
        )
        dbdir_name = safe_part(db)
        subdir = "views" if rel.get("kind") in {"v", "m"} else "tables"
        target = root / dbdir_name / safe_part(str(rel.get("schema", ""))) / subdir / f"{safe_part(str(rel.get('name', '')))}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")
        created.append({"database": db, "schema": rel.get("schema"), "name": rel.get("name"),
                        "kind": rel.get("kind"), "columns": len(cols),
                        "undocumented_columns": gaps,
                        "origin_class": object_meta.get("origin_class", "not assessed"),
                        "database_owner": object_meta.get("database_owner", "not captured"),
                        "object_category": object_owner(str(rel.get("schema", "")), str(rel.get("name", ""))),
                        "path": target.relative_to(root).as_posix()})
    for dbname in databases:
        subset = [entry for entry in created if entry["database"] == dbname]
        if not subset:
            continue
        dbdir = root / safe_part(dbname)
        schemas = sorted({str(entry["schema"]) for entry in subset})
        lines = [f"# دیتابیس `{dbname}`", "", "این فایل فقط از کاتالوگ PostgreSQL خوانده شده است؛ مقدار ردیفی ندارد.",
                 "", f"- زمان UTC: `{created_at}`", f"- اشیای مستندشده: {len(subset)}", "", "## Schemaها", ""]
        for schema in schemas:
            lines.append(f"- `{schema}`: {sum(entry['schema'] == schema for entry in subset)} شیء")
        lines.extend(["", "## اشیا", ""])
        for entry in subset:
            lines.append(f"- [{entry['schema']}.{entry['name']}]({Path(entry['path']).relative_to(safe_part(dbname)).as_posix()}) — {entry['columns']} ستون")
        (dbdir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    missing = sum(item["undocumented_columns"] for item in created)
    scope = snapshot.get("scope", "selected-databases-only")
    inventory_complete = set(discovered) == set(databases) | {
        item.get("database") for item in skipped if isinstance(item, dict)
    } | {item.get("database") for item in inaccessible if isinstance(item, dict)}
    technical_catalog_complete = (
        not inaccessible
        and scope == "authorized-rahgard-databases-only"
        and inventory_complete
    )
    total_column_occurrences = sum(column_occurrences_by_kind.values())
    glossary_total = baseline_glossary_coverage["described"] + baseline_glossary_coverage["undocumented"]
    architecture_objects = list(object_metadata.values())
    decision_counts = Counter(item.get("decision", "not assessed") for item in architecture_objects)
    manifest = {
        "schema": "rahgard.schema-catalogue.v1", "created_utc": created_at,
        "source": "PostgreSQL pg_catalog read-only transaction",
        "source_release": snapshot.get("source_release"),
        "source_release_evidence": snapshot.get("source_release_evidence"),
        "source_release_images": snapshot.get("source_release_images", {}),
        "source_snapshot_sha256": hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "catalog_metadata_snapshot_sha256": hashlib.sha256(
            (REPO_ROOT / "docs/database/live-schema/catalog_metadata_snapshot.json").read_bytes()
        ).hexdigest() if (REPO_ROOT / "docs/database/live-schema/catalog_metadata_snapshot.json").is_file() else None,
        "database_identity": snapshot.get("database_identity", {}),
        "database_role": snapshot.get("database_role"),
        "database_observations": snapshot.get("database_observations", []),
        "databases_discovered_non_template": discovered,
        "databases_attempted": databases, "databases_inaccessible": inaccessible,
        "databases_skipped_outside_authorized_namespace": skipped,
        "database_inventory_complete": inventory_complete,
        "relations": created, "relation_count": len(created),
        "missing_field_descriptions": baseline_glossary_coverage["undocumented"],
        "undocumented_first_party_base_occurrences": missing,
        "undocumented_first_party_system_or_operations_occurrences": glossary_by_origin["first_party_system_or_operations"]["undocumented"],
        "undocumented_derived_view_occurrences": glossary_by_origin["derived_view"]["undocumented"],
        "undocumented_extension_occurrences": glossary_by_origin["extension_managed"]["undocumented"],
        "undocumented_occurrences_by_origin": {
            origin: counts.get("undocumented", 0) for origin, counts in sorted(glossary_by_origin.items())
        },
        "catalog_counts": {
            "relations": len(created),
            "tables": relation_count_by_kind.get("r", 0) + relation_count_by_kind.get("p", 0),
            "views": relation_count_by_kind.get("v", 0) + relation_count_by_kind.get("m", 0),
            "column_occurrences": total_column_occurrences,
        },
        "column_occurrence_classification": dict(column_occurrences_by_kind),
        "baseline_glossary_coverage": {
            "described_occurrences": baseline_glossary_coverage["described"],
            "undocumented_occurrences": baseline_glossary_coverage["undocumented"],
            "total_occurrences": glossary_total,
            "distinct_business_requirement_count": None,
        },
        "glossary_coverage_by_origin": {origin: dict(counts) for origin, counts in sorted(glossary_by_origin.items())},
        "architecture_usage_review": {
            "objects_with_decision": len(architecture_objects),
            "decision_counts": dict(decision_counts),
            "business_necessity_approved": False,
            "static_usage_matrix": "docs/database/architecture-usage/object_decision_matrix.csv",
            "column_occurrence_matrix": "docs/database/architecture-usage/column_occurrence_matrix.csv",
            "view_lineage": "docs/database/architecture-usage/view_column_lineage.csv",
        },
        "technical_catalog_complete": technical_catalog_complete,
        "business_glossary_complete": baseline_glossary_coverage["undocumented"] == 0,
        "complete": False,
        "coverage_scope": scope,
        "database_access_mode": snapshot.get("database_access_mode", "not recorded"),
        "warning": "This catalog describes one authorized database only. Column occurrences are not distinct requirements. Glossary gaps are not validated business requirements. Derived and extension metadata are classified separately; architecture necessity is not approved by catalog extraction.",
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index = ["# کاتالوگ زنده دیتابیس Rahgard", "", f"تهیه: `{created_at}`", "",
             "Scope is limited to the authorized Rahgard database namespace; names outside scope were not opened.",
             f"Discovered non-template names: {len(discovered)}; attempted: {len(databases)}; skipped outside scope: {len(skipped)}; inaccessible: {len(inaccessible)}.",
             f"Relations: {len(created)} ({relation_count_by_kind.get('r', 0) + relation_count_by_kind.get('p', 0)} tables, {relation_count_by_kind.get('v', 0) + relation_count_by_kind.get('m', 0)} views); column occurrences: {total_column_occurrences}; baseline glossary entries: {baseline_glossary_coverage['described']}; undocumented glossary occurrences: {baseline_glossary_coverage['undocumented']}. This is not a distinct business parameter count.", "",
             "## Occurrence classification", "",
             "| Class | Occurrences | Existing glossary entries | No baseline glossary entry |", "|---|---:|---:|---:|"]
    for origin in ["first_party_application_base", "first_party_system_or_operations", "derived_view", "extension_managed"]:
        counts = glossary_by_origin[origin]
        index.append(f"| {origin} | {counts['described'] + counts['undocumented']} | {counts['described']} | {counts['undocumented']} |")
    index += ["", "Undocumented counts are glossary gaps, not validated business requirements. View outputs have separate lineage; extension-managed objects use PostgreSQL/PostGIS documentation. Architecture necessity is not approved by this catalog.", "",
             f"- Release source: `{manifest['source_release'] or 'not supplied'}`",
             f"- پایگاه‌های تلاش‌شده: {len(databases)}", f"- اشیا: {len(created)}",
             f"- undocumented glossary column occurrences: {baseline_glossary_coverage['undocumented']} (not distinct requirements)", ""]
    if inaccessible:
        index += ["## پایگاه‌های غیرقابل‌دسترسی", ""] + [
            f"- `{item.get('database', 'unknown')}`: SQLSTATE `{item.get('sqlstate', item.get('error_class', 'unknown'))}`" for item in inaccessible
        ] + [""]
    index += ["## فهرست اشیا", ""] + [
        f"- [{item['database']}.{item['schema']}.{item['name']}]({item['path']}) — {item['columns']} column occurrences; {item['undocumented_columns']} undocumented first-party base occurrences"
        for item in created
    ]
    (root / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return {"databases_attempted": len(databases), "inaccessible": len(inaccessible),
            "relations_documented": len(created), "missing_field_descriptions": baseline_glossary_coverage["undocumented"],
            "output_root": str(root)}


def main() -> int:
    parser = argparse.ArgumentParser(description='Metadata-only docs for PostgreSQL. NEVER reads table rows.')
    parser.add_argument('--dsn-env', default='RAHGARD_SCHEMA_DSN', help='Env var holding private libpq DSN')
    parser.add_argument('--output-root', default='docs/database/live-schema')
    parser.add_argument('--descriptions-json', help='Curated per-db.schema.table field descriptions; no secrets')
    parser.add_argument('--database', action='append', default=[], help='Repeat to restrict documentation to named DBs')
    parser.add_argument('--all-accessible-databases', action='store_true', help='Enumerate every connectable non-template DB')
    parser.add_argument('--catalog-snapshot-json', help='Sanitized metadata-only JSON produced by the remote read-only runner')
    args = parser.parse_args()
    descriptions = {}
    if args.descriptions_json:
        descriptions = json.loads(Path(args.descriptions_json).read_text(encoding='utf-8'))
    dsn = os.environ.get(args.dsn_env)
    if not dsn:
        if args.catalog_snapshot_json:
            # PowerShell's Set-Content -Encoding UTF8 writes a BOM on Windows.
            # Accept either UTF-8 form so a sanitized live snapshot can be
            # transferred without platform-specific post-processing.
            snapshot = json.loads(Path(args.catalog_snapshot_json).read_text(encoding='utf-8-sig'))
            result = write_catalog_snapshot(snapshot, Path(args.output_root), descriptions)
            print(json.dumps(result, ensure_ascii=False))
            return 0 if not snapshot.get('databases_inaccessible') else 3
        print(f'Missing connection value in environment variable {args.dsn_env}', file=sys.stderr)
        return 2
    if args.database and args.all_accessible_databases:
        parser.error('Use --database or --all-accessible-databases, not both')
    root = Path(args.output_root).resolve()
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    failures: list[dict] = []
    created: list[dict] = []
    discovered: list[str] = []
    skipped: list[dict[str, str]] = []
    with connect_ro(dsn) as base:
        if args.all_accessible_databases:
            discovered = list_databases(base)
            dbnames = [name for name in discovered if name.startswith("rahgard_")]
            skipped = [{"database": name, "reason": "outside_rahgard_database_namespace_not_opened"}
                       for name in discovered if name not in dbnames]
        elif args.database:
            dbnames = sorted(set(args.database))
            discovered = list(dbnames)
        else:
            dbnames = [run_ro(base, lambda c: c.execute('SELECT current_database()').fetchone()[0])]
            discovered = list(dbnames)
    for dbname in dbnames:
        try:
            with connect_ro(dsn, dbname) as conn:
                relations, items = run_ro(conn, fetch_catalog)
        except Exception as exc:
            failures.append({'database': dbname, 'error_class': type(exc).__name__})
            continue
        base_dir = root / safe_part(dbname)
        for rel in relations:
            cols, cons, inds, policies, triggers = items[(rel['schema'], rel['name'])]
            markdown, gaps = markdown_for_relation(dbname, rel, cols, cons, inds, policies, descriptions, now, triggers)
            sub = 'views' if rel['kind'] in {'v','m'} else 'tables'
            target = base_dir / safe_part(rel['schema']) / sub / f"{safe_part(rel['name'])}.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(markdown, encoding='utf-8')
            created.append({'database': dbname, 'schema': rel['schema'], 'name': rel['name'], 'kind': rel['kind'],
                            'columns': len(cols), 'undocumented_columns': gaps,
                            'path': target.relative_to(root).as_posix()})
    for dbname in dbnames:
        this_db = [entry for entry in created if entry['database'] == dbname]
        if not this_db:
            continue
        dbdir = root / safe_part(dbname)
        schemas = sorted(set(entry['schema'] for entry in this_db))
        db_lines = [f"# دیتابیس `{dbname}`", "", "این فایل از کاتالوگ PostgreSQL فقط‌خواندنی استخراج شده است؛ اطلاعات واقعی کاربران در آن نیست.", "",
                    f"- زمان تهیه: `{now}`", f"- تعداد Schemaها: {len(schemas)}", f"- تعداد جدول و View: {len(this_db)}", "",
                    "## Schemaها", ""]
        for schema in schemas:
            subset = [entry for entry in this_db if entry['schema'] == schema]
            db_lines.append(f"- `{schema}`: {len(subset)} شیء")
        db_lines += ["", "## همه اشیا", ""]
        for entry in this_db:
            relpath = Path(entry['path'])
            innerpath = relpath.relative_to(safe_part(dbname))
            db_lines.append(f"- [{entry['schema']}.{entry['name']}]({innerpath.as_posix()}): {entry['columns']} ستون")
        (dbdir / 'README.md').write_text('\n'.join(db_lines)+'\n',encoding='utf-8')
    manifest = {'schema': 'rahgard.schema-catalogue.v1', 'created_utc': now,
                'source': 'PostgreSQL pg_catalog read-only', 'databases_attempted': dbnames,
                'databases_discovered_non_template': discovered,
                'databases_skipped_outside_authorized_namespace': skipped,
                'databases_inaccessible': failures, 'relations': created,
                'technical_catalog_complete': not failures and bool(dbnames),
                'business_glossary_complete': False, 'architecture_necessity_approved': False,
                'complete': False,
                'coverage_scope': 'authorized-rahgard-databases-only' if args.all_accessible_databases else 'explicitly-selected-database-only',
                'warning': 'Column occurrences are not distinct requirements. Glossary gaps are not validated business requirements. Derived, extension, system, and legacy fields require separate classification and source evidence.'}
    root.mkdir(parents=True, exist_ok=True)
    (root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    index = ['# کاتالوگ دیتابیس‌های Rahgard', '',f'استخراج: `{now}`','',
             'این کاتالوگ فقط از متادیتای واقعی PostgreSQL تهیه می‌شود؛ هیچ ردیفی یا اطلاعات هویتی صادر نشده است.', '',
             f'- دیتابیس‌های قابل تلاش: **{len(dbnames)}**',f'- اشیای مستندشده: **{len(created)}**',
              f'- Undocumented first-party base-column occurrences: **{sum(x["undocumented_columns"] for x in created)}**; this is not a distinct requirement count.','']
    if failures:
        index += ['## دیتابیس‌های دسترس‌ناپذیر',''] + [f'- `{f["database"]}`: {f["error_class"]}' for f in failures]+['']
    index += ['## فهرست جدول‌ها و Viewها', '']
    for r in created:
        index.append(f'- [{r["database"]}.{r["schema"]}.{r["name"]}]({r["path"]}) — {r["columns"]} column occurrences; {r["undocumented_columns"]} undocumented first-party base occurrences')
    (root/'README.md').write_text('\n'.join(index)+'\n',encoding='utf-8')
    print(json.dumps({'databases_attempted':len(dbnames),'inaccessible':len(failures),'relations_documented':len(created),
                      'undocumented_first_party_base_occurrences':sum(x['undocumented_columns'] for x in created),'output_root':str(root)},ensure_ascii=False))
    return 0 if not failures else 3


if __name__ == '__main__':
    raise SystemExit(main())
