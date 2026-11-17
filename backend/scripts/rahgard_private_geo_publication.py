"""Explicitly authorized geographic publication to a marked private pilot.

This path is separate from disposable QA. It never provisions or connects to a
database until the reviewed batch, target authorization, and configuration pass.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.rahgard_geo_visibility import (  # noqa: E402
    ApprovalBlocked, validate_packet,
)

AUTH_SCHEMA = "rahgard.private-pilot-geo-authorization.v1"
AUTH_FIELDS = frozenset({"schema", "host", "port", "database", "marker_sha256", "decision_sha256", "reviewer", "approval_reference", "issued_at", "expires_at", "signature_sha256"})
PILOT_NAME = re.compile(r"^rahgard_pilot_[a-z0-9_]{3,40}$")
MARKER = re.compile(r"^[a-fA-F0-9]{32,128}$")
HOST = re.compile(r"^[a-zA-Z0-9.-]{1,253}$")
ROLE = "rahgard_pilot_geo_publisher"
MIGRATION_ID = "0012_task5_published_claim_evidence"
MIGRATION_FILE = (BACKEND_ROOT.parent / "engineering" / "database-prep" / "sql"
                  / "012_task5_published_claim_evidence.sql")
PILOT_MIGRATION_ID = "0013_private_pilot_geo_audit"
PILOT_MIGRATION_FILE = (BACKEND_ROOT.parent / "engineering" / "pilot" / "sql"
                        / "013_private_pilot_geo_audit.sql")


def parse_unique_json(raw: bytes | str) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique_object)


def validate_authorization(packet: dict[str, Any], packet_bytes: bytes, authorization: object,
                           host: str, port: int, database: str, marker: str, owner_key: bytes) -> list[dict[str, Any]]:
    try:
        if parse_unique_json(packet_bytes) != packet:
            raise ValueError
    except (TypeError, ValueError, UnicodeError):
        raise ApprovalBlocked("reviewed batch differs from signed bytes") from None
    approved = validate_packet(packet)
    if not approved:
        raise ApprovalBlocked("no geo points have been approved")
    if not isinstance(authorization, dict) or set(authorization) != AUTH_FIELDS:
        raise ApprovalBlocked("private pilot authorization is malformed")
    signature = authorization["signature_sha256"]
    unsigned = {key: value for key, value in authorization.items() if key != "signature_sha256"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    expected = hmac.new(owner_key, canonical, hashlib.sha256).hexdigest()
    if (len(owner_key) < 32 or not isinstance(signature, str)
            or not hmac.compare_digest(signature, expected)):
        raise ApprovalBlocked("private pilot target authorization signature is invalid")
    try:
        issued = datetime.fromisoformat(authorization["issued_at"])
        expires = datetime.fromisoformat(authorization["expires_at"])
        now = datetime.now(UTC)
        if (issued.utcoffset() != timedelta(0) or expires.utcoffset() != timedelta(0)
                or issued > now or expires <= now or not timedelta(0) < expires - issued <= timedelta(hours=1)):
            raise ValueError
    except (TypeError, ValueError, OverflowError):
        raise ApprovalBlocked("private pilot target authorization has expired or invalid dates") from None
    if (authorization["schema"] != AUTH_SCHEMA or authorization["host"] != host
            or type(authorization["port"]) is not int or authorization["port"] != port
            or authorization["database"] != database
            or authorization["marker_sha256"] != hashlib.sha256(marker.encode("ascii")).hexdigest()
            or authorization["reviewer"] != packet["reviewer"]
            or authorization["approval_reference"] != packet["approval_reference"]
            or authorization["decision_sha256"] != hashlib.sha256(packet_bytes).hexdigest()):
        raise ApprovalBlocked("private pilot authorization does not match target and batch")
    if any(re.search(r"qa[ _-]*only|synthetic|fixture", str(value), re.I)
           for value in (packet["reviewer"], packet["approval_reference"])):
        raise ApprovalBlocked("QA authorization cannot be used for a private pilot")
    return approved


def publish_private(packet: dict[str, Any], packet_bytes: bytes, authorization: object,
                    *, explicitly_authorized: bool) -> dict[str, Any]:
    if explicitly_authorized is not True:
        raise ApprovalBlocked("explicit publication flag is required")
    host = os.environ.get("RAHGARD_PILOT_PGHOST", "")
    database = os.environ.get("RAHGARD_PILOT_DATABASE", "")
    marker = os.environ.get("RAHGARD_PILOT_DATABASE_MARKER", "")
    password = os.environ.get("RAHGARD_PILOT_GEO_PUBLISHER_PASSWORD", "")
    owner_key = os.environ.get("RAHGARD_PILOT_OWNER_AUTHORIZATION_KEY", "").encode("utf-8")
    root_cert = os.environ.get("PGSSLROOTCERT", "")
    try:
        port = int(os.environ.get("RAHGARD_PILOT_PGPORT", ""))
    except ValueError:
        raise ApprovalBlocked("private pilot port is invalid") from None
    if (not HOST.fullmatch(host) or not PILOT_NAME.fullmatch(database) or not 1024 <= port <= 65535
            or port == 55433 or not MARKER.fullmatch(marker) or not password or len(owner_key) < 32
            or not root_cert or not Path(root_cert).is_file()):
        raise ApprovalBlocked("private pilot database guard is incomplete")
    approved = validate_authorization(packet, packet_bytes, authorization, host, port, database, marker, owner_key)
    connection = None
    stage = "connect"
    try:
        expected_migration_hash = hashlib.sha256(MIGRATION_FILE.read_bytes()).hexdigest()
        expected_pilot_migration_hash = hashlib.sha256(PILOT_MIGRATION_FILE.read_bytes()).hexdigest()
        connection = psycopg.connect(host=host, port=port, dbname=database, user=ROLE,
                                     password=password, sslmode="verify-full", sslrootcert=root_cert,
                                     connect_timeout=3, row_factory=dict_row,
                                     options="-c statement_timeout=10000 -c lock_timeout=3000",
                                     application_name="rahgard-private-geo-publication")
        stage = "publisher_identity_check"
        with connection.transaction():
            identity = connection.execute(
                """SELECT current_database() AS name, current_user AS role, session_user AS session_role,
                          current_setting('server_version_num')::integer AS version,
                          (SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls
                             FROM pg_catalog.pg_roles WHERE rolname=current_user) AS privileged,
                          (SELECT count(*) FROM pg_catalog.pg_roles r
                           WHERE pg_has_role(current_user, r.oid, 'MEMBER')
                             AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole
                                  OR r.rolreplication OR r.rolbypassrls)) AS privileged_memberships,
                          has_table_privilege(current_user, 'operations.private_pilot_geo_approvals', 'INSERT,UPDATE,DELETE,TRUNCATE') OR
                          has_any_column_privilege(current_user, 'operations.private_pilot_geo_approvals', 'INSERT,UPDATE') OR
                          has_table_privilege(current_user, 'operations.private_pilot_geo_approvals', 'DELETE') OR
                          has_table_privilege(current_user, 'operations.private_pilot_geo_authorizations', 'INSERT,UPDATE,DELETE,TRUNCATE') OR
                          has_any_column_privilege(current_user, 'operations.private_pilot_geo_authorizations', 'INSERT,UPDATE') AS mutable_audit,
                          (SELECT pg_has_role(current_user, c.relowner, 'MEMBER') FROM pg_catalog.pg_class c
                           WHERE c.oid='operations.private_pilot_geo_approvals'::regclass) AS owns_audit,
                          (SELECT pg_has_role(current_user, c.relowner, 'MEMBER') FROM pg_catalog.pg_class c
                           WHERE c.oid='knowledge.destinations'::regclass) AS owns_destinations,
                          has_table_privilege(current_user, 'operations.audit_events', 'SELECT') OR
                          has_any_column_privilege(current_user, 'operations.audit_events', 'SELECT') OR
                          has_table_privilege(current_user, 'operations.audit_events', 'INSERT') OR
                          has_any_column_privilege(current_user, 'operations.audit_events', 'INSERT') AS shared_audit_access,
                          has_table_privilege(current_user, 'knowledge.destinations', 'INSERT,UPDATE,DELETE,TRUNCATE') OR
                          has_any_column_privilege(current_user, 'knowledge.destinations', 'INSERT,UPDATE') OR
                          has_database_privilege(current_user, current_database(), 'CREATE') OR
                          has_schema_privilege(current_user, 'operations', 'CREATE') OR
                          has_schema_privilege(current_user, 'knowledge', 'CREATE') OR
                          has_schema_privilege(current_user, 'public', 'CREATE') AS excessive_destination_privileges,
                          has_function_privilege(current_user, 'operations.apply_private_geo_approval(text,text,text,text,text,timestamptz)', 'EXECUTE') AS function_allowed,
                          (SELECT p.prosecdef AND p.proconfig @> ARRAY['search_path=pg_catalog']
                                  AND NOT pg_has_role(current_user,p.proowner,'MEMBER')
                                  AND NOT r.rolcanlogin
                                  AND NOT (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole
                                           OR r.rolreplication OR r.rolbypassrls)
                                  AND NOT EXISTS (SELECT 1 FROM pg_catalog.pg_roles parent
                                      WHERE pg_has_role(r.oid,parent.oid,'MEMBER')
                                        AND (parent.rolsuper OR parent.rolcreatedb OR parent.rolcreaterole
                                             OR parent.rolreplication OR parent.rolbypassrls))
                             FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_roles r ON r.oid=p.proowner
                            WHERE p.oid='operations.apply_private_geo_approval(text,text,text,text,text,timestamptz)'::regprocedure) AS function_boundary,
                          (SELECT count(*) FROM public.rahgard_private_pilot_marker) AS marker_count,
                          (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) AS marker,
                          (SELECT sha256 FROM system.schema_migrations WHERE migration_id=%s) AS migration_hash,
                          (SELECT sha256 FROM system.schema_migrations WHERE migration_id=%s) AS pilot_migration_hash""",
                (MIGRATION_ID, PILOT_MIGRATION_ID),
            ).fetchone()
            if (identity["name"] != database or identity["role"] != ROLE or identity["session_role"] != ROLE
                    or not 170000 <= identity["version"] < 180000 or identity["privileged"] is not False
                    or identity["privileged_memberships"] != 0
                    or identity["mutable_audit"] is not False
                    or identity["owns_audit"] is not False or identity["owns_destinations"] is not False
                    or identity["shared_audit_access"] is not False
                    or identity["excessive_destination_privileges"] is not False
                    or identity["function_allowed"] is not True or identity["function_boundary"] is not True
                    or identity["marker_count"] != 1
                    or str(identity["migration_hash"]).strip() != expected_migration_hash
                    or str(identity["pilot_migration_hash"]).strip() != expected_pilot_migration_hash
                    or not hmac.compare_digest(str(identity["marker"]), marker)):
                raise ApprovalBlocked("private pilot identity or marker does not match")
            activated = 0
            stage = "controlled_geo_approval_function"
            for record in approved:
                validate_authorization(packet, packet_bytes, authorization, host, port, database, marker, owner_key)
                result = connection.execute(
                    "SELECT operations.apply_private_geo_approval(%s,%s,%s,%s,%s,%s::timestamptz) AS activated",
                    (record["destination_key"], hashlib.sha256(packet_bytes).hexdigest(),
                     authorization["marker_sha256"], packet["reviewer"], packet["approval_reference"],
                     packet["reviewed_at"]),
                ).fetchone()
                if result["activated"] is not True and result["activated"] is not False:
                    raise ApprovalBlocked("private pilot geographic activation returned an invalid result")
                activated += int(result["activated"])
            stage = "production_view_verification"
            rows = connection.execute(
                "SELECT destination_key, latitude, longitude, coordinate_role FROM knowledge.production_destinations WHERE destination_key = ANY(%s::text[])",
                ([record["destination_key"] for record in approved],),
            ).fetchall()
            if {row["destination_key"] for row in rows} != {record["destination_key"] for record in approved}:
                raise ApprovalBlocked("approved points are not visible through the production view")
            visible = {row["destination_key"]: row for row in rows}
            for record in approved:
                row = visible[record["destination_key"]]
                if (row["coordinate_role"] != record["coordinate_role"]
                        or abs(float(row["latitude"]) - record["latitude"]) > 0.0000001
                        or abs(float(row["longitude"]) - record["longitude"]) > 0.0000001):
                    raise ApprovalBlocked("published point differs from owner-reviewed batch")
        return {"status": "private_pilot_geo_published", "approved": len(approved), "activated": activated}
    except ApprovalBlocked:
        raise
    except Exception as exc:
        # Preserve a non-sensitive diagnostic class/SQLSTATE for the protected
        # local operator log without exposing SQL values, credentials, or data.
        sqlstate = getattr(exc, "sqlstate", None) or "none"
        primary = getattr(getattr(exc, "diag", None), "message_primary", None) or "no-diagnostic"
        raise ApprovalBlocked(f"private pilot publication failed at {stage} ({type(exc).__name__}, sqlstate={sqlstate}, diagnostic={primary})") from None
    finally:
        if connection is not None:
            connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--target-authorization", type=Path, required=True)
    parser.add_argument("--apply-approved-geo", action="store_true")
    args = parser.parse_args()
    try:
        raw = args.decisions.read_bytes()
        if len(raw) > 32768:
            raise ApprovalBlocked("decision batch is too large")
        packet = parse_unique_json(raw)
        authorization_raw = args.target_authorization.read_bytes()
        if len(authorization_raw) > 32768:
            raise ApprovalBlocked("authorization is too large")
        authorization = parse_unique_json(authorization_raw)
        result = publish_private(packet, raw, authorization, explicitly_authorized=args.apply_approved_geo)
        print(json.dumps(result, sort_keys=True))
        return 0
    except ApprovalBlocked as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError):
        print("BLOCKED: private pilot geo publication was not applied.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
