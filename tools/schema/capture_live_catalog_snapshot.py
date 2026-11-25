#!/usr/bin/env python3
"""Capture metadata for the authorized Rahgard database namespace only.

Run this script on stdin inside the existing API container. It reads the
mounted app database credential without printing or exporting it, inventories
connectable non-template database names, and attempts only databases with the
explicit Rahgard prefix. Metadata is read in READ ONLY transactions. Database
names outside that namespace are recorded as skipped and never opened. No
application rows are read. The app login is not a dedicated read-only role;
each inspection transaction is explicitly read-only.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path

import psycopg


BASE_DATABASE = "rahgard_pilot_vps_staging"
DATABASE_USER = "ai_tourism_app"
TARGET = os.environ.get("RAHGARD_SCHEMA_TARGET", "staging_container")
if TARGET not in {"staging_container", "local_demo"}:
    raise SystemExit("schema_target_invalid")
if TARGET == "local_demo":
    DB_HOST = os.environ.get("RAHGARD_SCHEMA_HOST", "")
    DB_PORT = int(os.environ.get("RAHGARD_SCHEMA_PORT", "0"))
    PASSWORD_FILE = Path(os.environ.get("RAHGARD_SCHEMA_PASSWORD_FILE", ""))
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    expected_password_file = local_app_data / "Rahgard" / "Issue27OwnerDemo" / "secrets" / "app_db_password"
    try:
        password_isolated = (local_app_data.is_absolute()
                             and PASSWORD_FILE.resolve(strict=True) == expected_password_file.resolve(strict=False)
                             and not PASSWORD_FILE.is_symlink())
    except OSError:
        password_isolated = False
    if DB_HOST != "127.0.0.1" or DB_PORT != 18543 or not password_isolated:
        raise SystemExit("local_demo_target_invalid")
else:
    if any(name in os.environ for name in ("RAHGARD_SCHEMA_HOST", "RAHGARD_SCHEMA_PORT", "RAHGARD_SCHEMA_PASSWORD_FILE")):
        raise SystemExit("staging_target_override_forbidden")
    DB_HOST, DB_PORT = "db", 5432
    PASSWORD_FILE = Path("/run/secrets/app_db_password")
RAHGARD_DATABASE_PREFIX = "rahgard_"


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


def discover_databases(conn: psycopg.Connection) -> list[str]:
    """List connectable non-template database names, without opening them."""
    conn.execute("BEGIN READ ONLY")
    conn.execute("SET LOCAL statement_timeout = '5s'")
    rows = conn.execute(
        """SELECT datname FROM pg_catalog.pg_database
           WHERE datallowconn AND NOT datistemplate
             AND datname NOT LIKE 'template%'
           ORDER BY datname"""
    ).fetchall()
    conn.rollback()
    return [row[0] for row in rows]


def collect(conn: psycopg.Connection, database: str) -> dict:
    conn.execute("BEGIN READ ONLY")
    conn.execute("SET LOCAL statement_timeout = '12s'")
    conn.execute("SET LOCAL lock_timeout = '3s'")
    identity = conn.execute(
        "SELECT current_database(), current_user, current_setting('server_version'), "
        "current_setting('server_version_num'), inet_server_port()"
    ).fetchone()
    if identity[0] != database or identity[1] != DATABASE_USER:
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
            "database": database,
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
        "scope": "authorized-rahgard-databases-only",
        "source_release": os.environ.get("RELEASE_COMMIT", "not exposed by container"),
        "database_identity": {"database": identity[0], "server_version": identity[2],
                              "server_version_num": identity[3], "port": identity[4]},
        "database_role": identity[1],
        "database_access_mode": "application role in read-only transaction; no dedicated read-only login was available",
        "relations": output,
    }


def collect_instance(password: str) -> dict:
    """Inventory one known Rahgard PostgreSQL instance, metadata only.

    Database names outside the explicit Rahgard namespace are listed as
    skipped and are never opened, preventing accidental cross-application
    catalog inspection on a shared PostgreSQL server.
    """
    with psycopg.connect(
        host=DB_HOST, port=DB_PORT, dbname=BASE_DATABASE, user=DATABASE_USER,
        password=password, connect_timeout=6,
        application_name="rahgard_schema_documenter_ro_inventory",
    ) as inventory_conn:
        discovered = discover_databases(inventory_conn)
    if BASE_DATABASE not in discovered:
        raise RuntimeError("authorized_base_database_not_discovered")

    attempted: list[str] = []
    inaccessible: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []
    database_results: list[dict] = []
    for database in discovered:
        if not database.startswith(RAHGARD_DATABASE_PREFIX):
            skipped.append({"database": database, "reason": "outside_rahgard_database_namespace"})
            continue
        attempted.append(database)
        try:
            with psycopg.connect(
                host=DB_HOST, port=DB_PORT, dbname=database, user=DATABASE_USER,
                password=password, connect_timeout=6,
                application_name="rahgard_schema_documenter_ro",
            ) as conn:
                database_results.append(collect(conn, database))
        except psycopg.Error as exc:
            # Record only a database name and SQLSTATE class; never echo the
            # connection exception, which may contain network/config details.
            inaccessible.append({
                "database": database,
                "sqlstate": (exc.sqlstate or "unknown")[:5],
            })
    relations = [relation for database_result in database_results for relation in database_result["relations"]]
    image_ids = {
        key: os.environ.get(env_name, "")
        for key, env_name in (("api", "RAHGARD_API_IMAGE_ID"), ("web", "RAHGARD_WEB_IMAGE_ID"))
        if os.environ.get(env_name)
    }
    if any(not re.fullmatch(r"sha256:[a-f0-9]{64}", value) for value in image_ids.values()):
        raise RuntimeError("invalid OCI image identity")
    observations = [{
        "database": result.get("database_identity", {}).get("database"),
        "database_identity": result.get("database_identity", {}),
        "database_role": result.get("database_role"),
    } for result in database_results]
    return {
        "created_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "scope": "authorized-rahgard-databases-only",
        "environment_scope": "isolated_local_demo" if TARGET == "local_demo" else "staging_container",
        "source_release": os.environ.get("RELEASE_COMMIT", "not exposed by container"),
        "source_release_images": image_ids,
        "instance_database_inventory": "read-only pg_database scan via ai_tourism_app",
        "database_access_mode": "application role; metadata catalog queries inside READ ONLY transactions; no application rows read",
        "discovered_non_template_databases": discovered,
        "databases_attempted": attempted,
        "databases_inaccessible": inaccessible,
        "databases_skipped": skipped,
        "database_observations": observations,
        "relations": relations,
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
        result = collect_instance(password)
        print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
        return 0
    except Exception as exc:  # never echo an exception string that may include DSN data
        print(json.dumps({"error_class": type(exc).__name__}))
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
