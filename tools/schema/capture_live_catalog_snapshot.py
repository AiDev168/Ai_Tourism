#!/usr/bin/env python3
"""Capture metadata for the named Rahgard staging database only.

Run this script on stdin inside the existing API container. It reads the
mounted app database credential without printing or exporting it, and uses a
single READ ONLY transaction against pg_catalog. No application rows are read.
This uses the application's least-privilege account, but it is not a dedicated
read-only login; the transaction itself is read-only and that limitation must
be recorded in the resulting manifest.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path

import psycopg


DATABASE = "rahgard_pilot_vps_staging"
DATABASE_USER = "ai_tourism_app"
PASSWORD_FILE = Path("/run/secrets/app_db_password")


def safe_default(value: str | None) -> str | None:
    if value is None:
        return None
    if len(value) > 180 or re.search(r"password|secret|token|private[_ -]?key|api[_ -]?key", value, re.I):
        return "[redacted default]"
    # String literals can carry sensitive values. Preserve non-string SQL
    # expressions; the renderer can still document the field shape safely.
    return "[redacted string default]" if "'" in value else value


def scrub_comment(value: str | None) -> str | None:
    if value is None:
        return None
    if re.search(r"password|secret|token|private[_ -]?key|api[_ -]?key", value, re.I):
        return "[redacted comment containing a sensitive label]"
    value = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[redacted email]", value)
    value = re.sub(r"(?<!\w)\+?\d[\d ()-]{7,}\d(?!\w)", "[redacted phone-like value]", value)
    return value[:1000]


def collect(conn: psycopg.Connection) -> dict:
    conn.execute("BEGIN READ ONLY")
    conn.execute("SET LOCAL statement_timeout = '12s'")
    conn.execute("SET LOCAL lock_timeout = '3s'")
    identity = conn.execute(
        "SELECT current_database(), current_user, current_setting('server_version'), "
        "current_setting('server_version_num'), inet_server_port()"
    ).fetchone()
    if identity[0] != DATABASE or identity[1] != DATABASE_USER:
        raise RuntimeError("unexpected database identity")

    relations = conn.execute("""
        SELECT n.nspname, c.relname, c.oid, c.relkind,
               pg_catalog.obj_description(c.oid, 'pg_class'),
               c.relrowsecurity, c.relforcerowsecurity
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind IN ('r','p','v','m','f')
          AND n.nspname <> 'information_schema'
          AND n.nspname NOT LIKE 'pg\\_%' ESCAPE '\\'
          AND c.relpersistence <> 't'
        ORDER BY n.nspname, c.relname
    """).fetchall()
    output = []
    for schema, name, oid, kind, comment, rls, force_rls in relations:
        columns = conn.execute("""
            SELECT a.attname, pg_catalog.format_type(a.atttypid,a.atttypmod),
                   a.attnotnull, pg_catalog.pg_get_expr(d.adbin,d.adrelid),
                   pg_catalog.col_description(a.attrelid,a.attnum),a.attidentity,a.attgenerated
            FROM pg_catalog.pg_attribute a
            LEFT JOIN pg_catalog.pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
            WHERE a.attrelid=%s AND a.attnum>0 AND NOT a.attisdropped
            ORDER BY a.attnum
        """, (oid,)).fetchall()
        constraints = conn.execute("""
            SELECT conname, contype::text, pg_catalog.pg_get_constraintdef(oid)
            FROM pg_catalog.pg_constraint WHERE conrelid=%s ORDER BY contype, conname
        """, (oid,)).fetchall()
        indexes = conn.execute("""
            SELECT i.relname, pg_catalog.pg_get_indexdef(idx.indexrelid)
            FROM pg_catalog.pg_index idx
            JOIN pg_catalog.pg_class i ON i.oid=idx.indexrelid
            WHERE idx.indrelid=%s ORDER BY i.relname
        """, (oid,)).fetchall()
        policies = conn.execute("""
            SELECT pol.polname, pol.polcmd,
                   ARRAY(SELECT rolname FROM pg_catalog.pg_roles WHERE oid=ANY(pol.polroles)),
                   pg_catalog.pg_get_expr(pol.polqual,pol.polrelid),
                   pg_catalog.pg_get_expr(pol.polwithcheck,pol.polrelid)
            FROM pg_catalog.pg_policy pol WHERE pol.polrelid=%s ORDER BY pol.polname
        """, (oid,)).fetchall()
        triggers = conn.execute("""
            SELECT tgname, pg_catalog.pg_get_triggerdef(oid)
            FROM pg_catalog.pg_trigger WHERE tgrelid=%s AND NOT tgisinternal ORDER BY tgname
        """, (oid,)).fetchall()
        relation = {
            "database": DATABASE,
            "relation": {"schema": schema, "name": name, "oid": oid, "kind": kind,
                         "comment": scrub_comment(comment), "rls": rls, "force_rls": force_rls},
            "columns": [
                {"name": row[0], "pg_type": row[1], "notnull": row[2],
                 "default": safe_default(row[3]), "comment": scrub_comment(row[4]),
                 "identity": row[5], "generated": row[6]} for row in columns
            ],
            "constraints": [{"name": row[0], "type": row[1], "definition": row[2]} for row in constraints],
            "indexes": [{"name": row[0], "definition": row[1]} for row in indexes],
            "policies": [{"name": row[0], "command": row[1], "roles": row[2],
                          "using": row[3], "with_check": row[4]} for row in policies],
            "triggers": [{"name": row[0], "definition": row[1]} for row in triggers],
        }
        output.append(relation)
    conn.rollback()
    return {
        "created_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "selected-databases-only",
        "source_release": os.environ.get("RELEASE_COMMIT", "not exposed by container"),
        "database_identity": {"database": identity[0], "server_version": identity[2],
                              "server_version_num": identity[3], "port": identity[4]},
        "database_role": identity[1],
        "database_access_mode": "application role in read-only transaction; no dedicated read-only login was available",
        "databases_attempted": [DATABASE],
        "databases_inaccessible": [],
        "relations": output,
    }


def main() -> int:
    if not PASSWORD_FILE.is_file():
        print(json.dumps({"error_class": "database_secret_unavailable"}))
        return 2
    password = PASSWORD_FILE.read_text(encoding="utf-8").strip()
    if not password:
        print(json.dumps({"error_class": "database_secret_empty"}))
        return 2
    try:
        with psycopg.connect(
            host="db", port=5432, dbname=DATABASE, user=DATABASE_USER,
            password=password, connect_timeout=6,
            application_name="rahgard_schema_documenter_read_only",
        ) as conn:
            result = collect(conn)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:  # never echo an exception string that may include DSN data
        print(json.dumps({"error_class": type(exc).__name__}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
