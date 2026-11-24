#!/usr/bin/env python3
"""Read-only PostgreSQL catalogue -> one Markdown file per accessible relation.

Security contract: Never selects table rows, writes schema, exposes DSNs, or logs secrets.
Database connection comes only from the specified ENV var. PostgreSQL metadata is
read in a READ ONLY transaction with bounded lock and statement timeouts.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sys


def safe_part(raw: str) -> str:
    """Safe reversible-ish single filesystem component; hash avoids slug collisions."""
    clean = re.sub(r"[^a-zA-Z0-9_.-]+", "_", raw).strip("._") or "unnamed"
    return clean[:64] + "-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


def escape_cell(value: object) -> str:
    s = str(value) if value is not None else "—"
    return s.replace("|", "\\|").replace("\n", " ").replace("\r", " ").replace("`", "'")


def type_hint(pg_type: str) -> str:
    t = pg_type.lower()
    if t.endswith("[]"):
        return "آرایه‌ای از مقادیر؛ قالب عنصر مطابق نوع پایه"
    if t == "uuid":
        return "UUID استاندارد با ۳۶ نویسه و خط تیره، مانند xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    if t in {"json", "jsonb"}:
        return "ساختار معتبر JSON؛ قرارداد کلیدها باید در مستندات API مشخص شود"
    if t.startswith("character varying") or t.startswith("varchar"):
        return "رشته Unicode؛ سقف طول از تعریف نوع PostgreSQL استخراج می‌شود"
    if t.startswith("character(") or t.startswith("char("):
        return "رشته با طول ثابت مشخص‌شده در PostgreSQL"
    if t in {"text", "citext"}:
        return "رشته Unicode؛ سقف کاربردی باید از اعتبارسنجی API استخراج شود"
    if t in {"boolean", "bool"}:
        return "true / false"
    if t in {"integer", "bigint", "smallint", "int4", "int8", "int2"}:
        return "عدد صحیح در بازهٔ نوع ثبت‌شده؛ واحد دامنه‌ای باید مشخص شود"
    if t.startswith("numeric") or t.startswith("decimal"):
        return "عدد ده‌دهی؛ precision و scale از PostgreSQL؛ واحد/ارز باید مستند شود"
    if t in {"real", "double precision"}:
        return "عدد ممیز شناور؛ دقت و واحد کاربردی نیازمند قرارداد دامنه است"
    if t == "date":
        return "تاریخ میلادی ISO 8601: YYYY-MM-DD (تبدیل جلالی صرفاً در UI)"
    if t.startswith("timestamp"):
        return "زمان ISO 8601؛ وجود/نبود منطقهٔ زمانی مطابق نوع PostgreSQL"
    if t.startswith("time"):
        return "زمان روز؛ قالب HH:MM:SS و منطقهٔ زمانی مطابق نوع PostgreSQL"
    if t == "interval":
        return "بازهٔ زمانی PostgreSQL (مدت/واحد دقیق وابسته به قرارداد دامنه)"
    if t in {"inet", "cidr"}:
        return "نشانی IP یا شبکه در قالب استاندارد IPv4/IPv6"
    if t in {"bytea"}:
        return "دادهٔ دودویی؛ مقدار خام نباید در این مستندات نمایش داده شود"
    if t in {"tsvector", "tsquery"}:
        return "ساختار جست‌وجوی متنی PostgreSQL"
    return "نوع سفارشی یا قالب وابسته به دامنه؛ اعتبارسنجی API/enum را بررسی کنید"


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


def markdown_for_relation(db: str, rel: dict, cols: list[dict], cons: list[dict],
                          indexes: list[dict], policies: list[dict], descriptions: dict,
                          recorded_at: str, triggers: list[dict] | None = None) -> tuple[str, int]:
    dbkey = f"{db}.{rel['schema']}.{rel['name']}"
    more = descriptions.get(dbkey, descriptions.get(f"{rel['schema']}.{rel['name']}", {}))
    if not isinstance(more, dict):
        more = {}
    obj = more.get("_object", {}) if isinstance(more.get("_object", {}), dict) else {}
    table_comment = rel.get("comment") or more.get("_table") or "نیازمند توضیح دامنه‌ای تأییدشده از کد و مالک محصول"
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
        f"- **منبع:** PostgreSQL `pg_catalog`، تراکنش فقط‌خواندنی، استخراج‌شده در `{recorded_at}`",
        f"- **امنیت ردیفی (RLS):** {'روشن' if rel['rls'] else 'خاموش'}؛ Forced={'بله' if rel['force_rls'] else 'خیر'}",
        "- **هشدار:** هیچ دادهٔ ردیفی، رمز، کوکی یا مقدار شخصی در این فایل استخراج نشده است.",
        "", "## ستون‌ها و قرارداد داده", "",
        "| ستون | نوع PostgreSQL | Nullable | مقدار پیش‌فرض امن | پارامتر/معنی | قالب و اعتبارسنجی پایه |",
        "|---|---|---|---|---|---|",
    ]
    undocumented = 0
    for c in cols:
        meaning = c.get("comment") or more.get(c["name"])
        if not meaning:
            meaning = "**نیازمند تکمیل از API / منطق دامنه**"
            undocumented += 1
        details = type_hint(c["pg_type"])
        if c.get("identity"):
            details += "; ستون Identity"
        if c.get("generated"):
            details += "; مقدار تولیدشده در DB"
        lines.append("| " + " | ".join(escape_cell(v) for v in (
            f"`{c['name']}`", f"`{c['pg_type']}`", "خیر" if c["notnull"] else "بله",
            f"`{safe_default(c.get('default'))}`" if c.get("default") is not None else "—",
            meaning, details)) + " |")
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
    lines += ["", "## نیازمندی تکمیل دامنه", "",
              f"- تعداد ستون‌های فاقد شرح صریح: **{undocumented}** از **{len(cols)}**.",
              "- مالک دامنه و توسعه‌دهنده باید تعریف تجاری، مقادیر مجاز، واحد پول/اندازه، مثال غیرواقعی، قواعد اعتبارسنجی و سطح دسترسی هر فیلد را از کد و API تأیید کنند.",
              "- ستون‌ها را با فرم عمومیِ ویرایش SQL در اختیار کاربر قرار ندهید. فرم‌ها باید براساس نقش/قرارداد API باشند.", ""]
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
    relations = snapshot.get("relations", [])
    if not isinstance(inaccessible, list) or not isinstance(relations, list):
        raise ValueError("snapshot collections are invalid")
    root = output_root.resolve()
    created: list[dict] = []
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
        markdown, gaps = markdown_for_relation(
            db, rel, cols, cons, indexes, policies, descriptions, created_at, triggers
        )
        dbdir_name = safe_part(db)
        subdir = "views" if rel.get("kind") in {"v", "m"} else "tables"
        target = root / dbdir_name / safe_part(str(rel.get("schema", ""))) / subdir / f"{safe_part(str(rel.get('name', '')))}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")
        created.append({"database": db, "schema": rel.get("schema"), "name": rel.get("name"),
                        "kind": rel.get("kind"), "columns": len(cols),
                        "undocumented_columns": gaps, "path": target.relative_to(root).as_posix()})
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
    manifest = {
        "schema": "rahgard.schema-catalogue.v1", "created_utc": created_at,
        "source": "PostgreSQL pg_catalog read-only transaction",
        "source_release": snapshot.get("source_release"),
        "database_identity": snapshot.get("database_identity", {}),
        "database_role": snapshot.get("database_role"),
        "databases_attempted": databases, "databases_inaccessible": inaccessible,
        "relations": created, "relation_count": len(created),
        "missing_field_descriptions": missing,
        "complete": not inaccessible and snapshot.get("scope") == "all-accessible-databases",
        "coverage_scope": snapshot.get("scope", "selected-databases-only"),
        "warning": "Complete means metadata coverage of databases accessible to the tested role; it does not mean all business meanings are known.",
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    index = ["# کاتالوگ زنده دیتابیس Rahgard", "", f"تهیه: `{created_at}`", "",
             f"- Release source: `{manifest['source_release'] or 'not supplied'}`",
             f"- پایگاه‌های تلاش‌شده: {len(databases)}", f"- اشیا: {len(created)}",
             f"- فیلدهای نیازمند شرح: {missing}", ""]
    if inaccessible:
        index += ["## پایگاه‌های غیرقابل‌دسترسی", ""] + [
            f"- `{item.get('database', 'unknown')}`: {item.get('error_class', 'unknown error')}" for item in inaccessible
        ] + [""]
    index += ["## فهرست اشیا", ""] + [
        f"- [{item['database']}.{item['schema']}.{item['name']}]({item['path']}) — {item['columns']} ستون؛ {item['undocumented_columns']} شرح ناقص"
        for item in created
    ]
    (root / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    return {"databases_attempted": len(databases), "inaccessible": len(inaccessible),
            "relations_documented": len(created), "missing_field_descriptions": missing,
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
    with connect_ro(dsn) as base:
        if args.all_accessible_databases:
            dbnames = list_databases(base)
        elif args.database:
            dbnames = sorted(set(args.database))
        else:
            dbnames = [run_ro(base, lambda c: c.execute('SELECT current_database()').fetchone()[0])]
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
                'databases_inaccessible': failures, 'relations': created,
                'complete': not failures and args.all_accessible_databases,
                'coverage_scope': 'all-accessible-databases' if args.all_accessible_databases else 'selected-databases-only',
                'warning': 'Complete only means metadata of enumerated, accessible DBs; not server-wide role access or domain field-meaning review.'}
    root.mkdir(parents=True, exist_ok=True)
    (root/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    index = ['# کاتالوگ دیتابیس‌های Rahgard', '',f'استخراج: `{now}`','',
             'این کاتالوگ فقط از متادیتای واقعی PostgreSQL تهیه می‌شود؛ هیچ ردیفی یا اطلاعات هویتی صادر نشده است.', '',
             f'- دیتابیس‌های قابل تلاش: **{len(dbnames)}**',f'- اشیای مستندشده: **{len(created)}**',
             f'- تعداد ستون بدون توضیح تأییدشده: **{sum(x["undocumented_columns"] for x in created)}**','']
    if failures:
        index += ['## دیتابیس‌های دسترس‌ناپذیر',''] + [f'- `{f["database"]}`: {f["error_class"]}' for f in failures]+['']
    index += ['## فهرست جدول‌ها و Viewها', '']
    for r in created:
        index.append(f'- [{r["database"]}.{r["schema"]}.{r["name"]}]({r["path"]}) — {r["columns"]} ستون؛ {r["undocumented_columns"]} شرح ناقص')
    (root/'README.md').write_text('\n'.join(index)+'\n',encoding='utf-8')
    print(json.dumps({'databases_attempted':len(dbnames),'inaccessible':len(failures),'relations_documented':len(created),
                      'missing_field_descriptions':sum(x['undocumented_columns'] for x in created),'output_root':str(root)},ensure_ascii=False))
    return 0 if not failures else 3


if __name__ == '__main__':
    raise SystemExit(main())
