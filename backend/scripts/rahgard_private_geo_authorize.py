"""Provision owner-signed, short-lived geographic approvals in a private pilot.

This command does not publish destinations. It requires a separately managed
authorizer role and a signed review packet; publication remains a second,
explicit command using the publisher role.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.rahgard_private_geo_publication import (  # noqa: E402
    ApprovalBlocked,
    MIGRATION_FILE,
    MIGRATION_ID,
    PILOT_MIGRATION_FILE,
    PILOT_MIGRATION_ID,
    parse_unique_json,
    validate_authorization,
)

ROLE = "rahgard_pilot_geo_authorizer"
PILOT_NAME = re.compile(r"^rahgard_pilot_[a-z0-9_]{3,40}$")
MARKER = re.compile(r"^[a-fA-F0-9]{32,128}$")
HOST = re.compile(r"^[a-zA-Z0-9.-]{1,253}$")


def authorize_private(packet: dict[str, Any], packet_bytes: bytes, authorization: object) -> dict[str, int | str]:
    host = os.environ.get("RAHGARD_PILOT_PGHOST", "")
    database = os.environ.get("RAHGARD_PILOT_DATABASE", "")
    marker = os.environ.get("RAHGARD_PILOT_DATABASE_MARKER", "")
    password = os.environ.get("RAHGARD_PILOT_GEO_AUTHORIZER_PASSWORD", "")
    owner_key = os.environ.get("RAHGARD_PILOT_OWNER_AUTHORIZATION_KEY", "").encode("utf-8")
    root_cert = os.environ.get("PGSSLROOTCERT", "")
    try:
        port = int(os.environ.get("RAHGARD_PILOT_PGPORT", ""))
    except ValueError:
        raise ApprovalBlocked("private pilot port is invalid") from None
    if (not HOST.fullmatch(host) or host.lower() in {"localhost", "localhost.localdomain"}
            or not PILOT_NAME.fullmatch(database) or not 1024 <= port <= 65535 or port == 55433
            or not MARKER.fullmatch(marker) or not password or len(owner_key) < 32
            or not root_cert or not Path(root_cert).is_file()):
        raise ApprovalBlocked("private pilot authorization guard is incomplete")
    records = validate_authorization(packet, packet_bytes, authorization, host, port,
                                     database, marker, owner_key)
    if len(records) > 4:
        raise ApprovalBlocked("private pilot authorization record bound exceeded")
    connection = None
    try:
        expected_0012 = hashlib.sha256(MIGRATION_FILE.read_bytes()).hexdigest()
        expected_0013 = hashlib.sha256(PILOT_MIGRATION_FILE.read_bytes()).hexdigest()
        connection = psycopg.connect(host=host, port=port, dbname=database, user=ROLE,
                                     password=password, sslmode="verify-full", sslrootcert=root_cert,
                                     connect_timeout=3, row_factory=dict_row,
                                     options="-c statement_timeout=10000 -c lock_timeout=3000",
                                     application_name="rahgard-private-geo-authorization")
        with connection.transaction():
            identity = connection.execute(
                """SELECT current_database() AS name, current_user AS role, session_user AS session_role,
                          current_setting('server_version_num')::integer AS version,
                          (SELECT rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls
                             FROM pg_catalog.pg_roles WHERE rolname=current_user) AS privileged,
                          (SELECT count(*) FROM pg_catalog.pg_roles r
                           WHERE pg_has_role(current_user,r.oid,'MEMBER')
                             AND (r.rolsuper OR r.rolcreatedb OR r.rolcreaterole
                                  OR r.rolreplication OR r.rolbypassrls)) AS privileged_memberships,
                          (SELECT pg_has_role(current_user,c.relowner,'MEMBER') FROM pg_catalog.pg_class c
                           WHERE c.oid='operations.private_pilot_geo_authorizations'::regclass) AS owns_authorizations,
                          pg_has_role(current_user,'rahgard_pilot_geo_publisher','MEMBER') OR
                          pg_has_role(current_user,'rahgard_pilot_geo_executor','MEMBER') AS elevated_membership,
                          has_table_privilege(current_user,'operations.private_pilot_geo_authorizations','INSERT') AS can_insert,
                          has_table_privilege(current_user,'operations.private_pilot_geo_authorizations','UPDATE,DELETE,TRUNCATE') OR
                          has_any_column_privilege(current_user,'operations.private_pilot_geo_authorizations','UPDATE') AS can_mutate,
                          has_table_privilege(current_user,'operations.private_pilot_geo_approvals','SELECT,INSERT,UPDATE,DELETE,TRUNCATE') OR
                          has_any_column_privilege(current_user,'operations.private_pilot_geo_approvals','SELECT,INSERT,UPDATE') AS audit_access,
                          has_table_privilege(current_user,'knowledge.destinations','INSERT,UPDATE,DELETE,TRUNCATE') OR
                          has_any_column_privilege(current_user,'knowledge.destinations','INSERT,UPDATE') AS destination_write,
                          has_table_privilege(current_user,'operations.audit_events','SELECT,INSERT,UPDATE,DELETE,TRUNCATE') OR
                          has_any_column_privilege(current_user,'operations.audit_events','SELECT,INSERT,UPDATE') AS shared_audit_access,
                          (SELECT count(*) FROM public.rahgard_private_pilot_marker) AS marker_count,
                          (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) AS marker,
                          (SELECT sha256 FROM system.schema_migrations WHERE migration_id=%s) AS migration_hash,
                          (SELECT sha256 FROM system.schema_migrations WHERE migration_id=%s) AS pilot_migration_hash""",
                (MIGRATION_ID, PILOT_MIGRATION_ID),
            ).fetchone()
            if (identity["name"] != database or identity["role"] != ROLE
                    or identity["session_role"] != ROLE or not 170000 <= identity["version"] < 180000
                    or identity["privileged"] is not False or identity["privileged_memberships"] != 0
                    or identity["owns_authorizations"] is not False or identity["elevated_membership"] is not False
                    or identity["can_insert"] is not True
                    or identity["can_mutate"] is not False or identity["audit_access"] is not False
                    or identity["destination_write"] is not False or identity["shared_audit_access"] is not False
                    or identity["marker_count"] != 1 or not hmac.compare_digest(identity["marker"], marker)
                    or str(identity["migration_hash"]).strip() != expected_0012
                    or str(identity["pilot_migration_hash"]).strip() != expected_0013):
                raise ApprovalBlocked("private pilot authorization role or target is unsafe")
            marker_hash = authorization["marker_sha256"]
            decision_hash = authorization["decision_sha256"]
            for record in records:
                row = connection.execute(
                    """SELECT d.destination_id, d.canonical_name, d.destination_type, d.province_name,
                              d.city_name, d.latitude, d.longitude, d.coordinate_role, d.status,
                              d.record_origin, d.verification_status, d.is_synthetic,
                              ST_Y(d.location::geometry) AS stored_latitude,
                              ST_X(d.location::geometry) AS stored_longitude,
                              (SELECT count(*) FROM knowledge.destination_sources ds
                                JOIN knowledge.knowledge_sources s ON s.source_id=ds.source_id
                               WHERE ds.destination_id=d.destination_id AND s.url=%s
                                 AND s.verification_status='verified' AND s.is_synthetic=FALSE
                                 AND (ds.valid_from IS NULL OR ds.valid_from <= now())
                                 AND (ds.valid_until IS NULL OR ds.valid_until >= now())) AS source_count
                         FROM knowledge.destinations d WHERE d.destination_key=%s""",
                    (record["source_url"], record["destination_key"]),
                ).fetchall()
                if len(row) != 1:
                    raise ApprovalBlocked("approved destination identity is missing or ambiguous")
                current = row[0]
                for field in ("canonical_name", "destination_type", "province_name", "city_name", "coordinate_role"):
                    if current[field] != record[field]:
                        raise ApprovalBlocked("reviewed destination identity changed")
                if (current["record_origin"] != "verified_external" or current["verification_status"] != "verified"
                        or current["is_synthetic"] is not False or current["status"] not in {"needs_review", "active"}
                        or current["source_count"] != 1 or current["latitude"] is None or current["longitude"] is None
                        or abs(float(current["latitude"]) - record["latitude"]) > 0.0000001
                        or abs(float(current["longitude"]) - record["longitude"]) > 0.0000001
                        or abs(float(current["stored_latitude"]) - record["latitude"]) > 0.0000001
                        or abs(float(current["stored_longitude"]) - record["longitude"]) > 0.0000001):
                    raise ApprovalBlocked("canonical destination or current geographic source is not eligible")
                connection.execute(
                    """INSERT INTO operations.private_pilot_geo_authorizations
                         (destination_key, decision_sha256, marker_sha256, canonical_name,
                          destination_type, province_name, city_name, latitude, longitude,
                          coordinate_role, source_url, reviewer, approval_reference, reviewed_at, expires_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::timestamptz,now()+interval '30 minutes')""",
                    (record["destination_key"], decision_hash, marker_hash, record["canonical_name"],
                     record["destination_type"], record["province_name"], record["city_name"],
                     record["latitude"], record["longitude"], record["coordinate_role"],
                     record["source_url"], packet["reviewer"], packet["approval_reference"],
                     packet["reviewed_at"]),
                )
        return {"status": "owner_signed_geo_authorization_provisioned", "records": len(records)}
    except ApprovalBlocked:
        raise
    except Exception:
        raise ApprovalBlocked("private pilot authorization provisioning failed") from None
    finally:
        if connection is not None:
            connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--target-authorization", type=Path, required=True)
    parser.add_argument("--provision-owner-authorization", action="store_true")
    args = parser.parse_args()
    try:
        packet_bytes = args.decisions.read_bytes()
        authorization_bytes = args.target_authorization.read_bytes()
        if len(packet_bytes) > 32_768 or len(authorization_bytes) > 32_768:
            raise ApprovalBlocked("review packet exceeds the size bound")
        packet = parse_unique_json(packet_bytes)
        authorization = parse_unique_json(authorization_bytes)
        if args.provision_owner_authorization is not True:
            raise ApprovalBlocked("explicit owner authorization provisioning flag is required")
        result = authorize_private(packet, packet_bytes, authorization)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ApprovalBlocked, OSError, ValueError, TypeError):
        print("BLOCKED: owner geographic authorization was not provisioned.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
