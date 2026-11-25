"""Operator-only, audited provisioning for platform reviewer capabilities.

The command defaults to read-only. It intentionally accepts a database DSN
only through RAHGARD_OPERATOR_DATABASE_URL and never prints connection data.
It is not exposed through the traveler or company API.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
from pathlib import Path
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]
MIGRATION_024 = ROOT / "engineering/pilot/sql/024_partner_review_audit_actions.sql"
MIGRATION_025 = ROOT / "engineering/pilot/sql/025_owner_control_center.sql"
MIGRATION_026 = ROOT / "engineering/pilot/sql/026_platform_reviewer_mfa.sql"
CAPABILITIES = {
    "organization_review": "partner",
    "service_review": "partner",
    "offer_review": "partner",
    "admin_overview_read": "partner",
    "candidate_review": "catalogue",
    "source_review": "catalogue",
    "catalogue_publish": "catalogue",
}
DATABASE_NAME = "rahgard_pilot_vps_staging"
APP_ROLE = "ai_tourism_app"


class ProvisioningError(RuntimeError):
    pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-user", required=True, type=UUID)
    parser.add_argument("--operator-user", required=True, type=UUID)
    parser.add_argument("--capability", required=True, choices=sorted(CAPABILITIES))
    parser.add_argument("--action", required=True, choices=("grant", "revoke"))
    parser.add_argument("--reason", required=True)
    parser.add_argument("--apply", action="store_true", help="Apply after all guards pass; default is dry-run")
    return parser


def _verify(conn, marker: str) -> tuple[str, str]:
    if not re.fullmatch(r"[a-fA-F0-9]{32,128}", marker):
        raise ProvisioningError("pilot_marker_invalid")
    with conn.cursor() as cur:
        state = cur.execute(
            """SELECT current_database() AS database_name,
                      current_setting('server_version_num')::integer AS version_num,
                      COALESCE(inet_server_port(),0) AS server_port,
                      current_user AS database_role,
                      (SELECT count(*) FROM public.rahgard_private_pilot_marker) AS marker_count,
                      (SELECT min(marker_value) FROM public.rahgard_private_pilot_marker) AS marker_value,
                      (SELECT sha256 FROM system.schema_migrations WHERE migration_id='0024_partner_review_audit_actions') AS m24,
                      (SELECT sha256 FROM system.schema_migrations WHERE migration_id='0025_owner_control_center') AS m25,
                      (SELECT sha256 FROM system.schema_migrations WHERE migration_id='0026_platform_reviewer_mfa') AS m26,
                      (SELECT count(*) FROM system.schema_migrations) AS migration_count,
                      (SELECT max(migration_id) FROM system.schema_migrations) AS latest_migration"""
        ).fetchone()
    expected_024 = hashlib.sha256(MIGRATION_024.read_bytes()).hexdigest()
    expected_025 = hashlib.sha256(MIGRATION_025.read_bytes()).hexdigest()
    expected_026 = hashlib.sha256(MIGRATION_026.read_bytes()).hexdigest()
    if state["database_name"] != DATABASE_NAME:
        raise ProvisioningError("database_name_mismatch")
    if not 170000 <= state["version_num"] < 180000 or state["server_port"] == 55433:
        raise ProvisioningError("database_is_not_guarded_postgresql_17")
    if state["database_role"] in {"", APP_ROLE}:
        raise ProvisioningError("operator_database_role_is_not_privileged")
    if state["marker_count"] != 1 or state["marker_value"] != marker:
        raise ProvisioningError("pilot_marker_mismatch")
    if ((state["m24"] or "").strip() != expected_024
            or (state["m25"] or "").strip() != expected_025
            or (state["m26"] or "").strip() != expected_026):
        raise ProvisioningError("migration_checksum_mismatch")
    if state["migration_count"] not in (25, 27) or state["latest_migration"] != "0026_platform_reviewer_mfa":
        raise ProvisioningError("migration_ledger_mismatch")
    return str(state["database_name"]), str(state["database_role"])


def run(args: argparse.Namespace, *, environ: dict[str, str] | None = None) -> str:
    env = environ if environ is not None else os.environ
    # Reject an attempted self grant before reading credentials or connecting
    # to the database. This remains fail-closed even when operator setup is
    # incomplete, and makes the negative authorization path deterministic.
    if args.target_user == args.operator_user:
        raise ProvisioningError("self_provisioning_forbidden")
    marker = env.get("RAHGARD_PILOT_DATABASE_MARKER", "")
    dsn = env.get("RAHGARD_OPERATOR_DATABASE_URL", "")
    if not dsn:
        raise ProvisioningError("operator_database_dsn_unavailable")
    if len(args.reason.strip()) < 10 or len(args.reason) > 1000:
        raise ProvisioningError("reason_invalid")
    domain = CAPABILITIES[args.capability]
    with psycopg.connect(dsn, row_factory=dict_row, connect_timeout=5) as conn:
        database, _role = _verify(conn, marker)
        with conn.cursor() as cur:
            admin_exists = cur.execute(
                "SELECT EXISTS(SELECT 1 FROM partner.platform_grants WHERE capability='admin_overview_read' AND revoked_at IS NULL) AS active"
            ).fetchone()["active"]
            operator_is_admin = cur.execute(
                "SELECT EXISTS(SELECT 1 FROM partner.platform_grants WHERE user_id=%s AND capability='admin_overview_read' AND revoked_at IS NULL) AS active",
                (args.operator_user,),
            ).fetchone()["active"]
            bootstrap = not admin_exists and args.action == "grant" and args.capability == "admin_overview_read"
            if not bootstrap and not operator_is_admin:
                raise ProvisioningError("operator_admin_capability_required")
            if not cur.execute("SELECT EXISTS(SELECT 1 FROM identity.users WHERE user_id=%s) AS ok",
                                (args.target_user,)).fetchone()["ok"]:
                raise ProvisioningError("target_identity_not_found")
            if not cur.execute("SELECT EXISTS(SELECT 1 FROM identity.users WHERE user_id=%s) AS ok",
                                (args.operator_user,)).fetchone()["ok"]:
                raise ProvisioningError("operator_identity_not_found")
            if domain == "partner":
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM partner.platform_grants WHERE user_id=%s AND capability=%s AND revoked_at IS NULL) AS active",
                    (args.target_user, args.capability),
                )
            else:
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM identity.catalogue_review_grants WHERE user_id=%s AND capability=%s AND revoked_at IS NULL) AS active",
                    (args.target_user, args.capability),
                )
            active = bool(cur.fetchone()["active"])
            wanted_active = args.action == "grant"
            if active == wanted_active:
                return f"NO_CHANGE action={args.action} capability={args.capability} database={database}"
            if not args.apply:
                return f"DRY_RUN action={args.action} capability={args.capability} database={database}"
            if env.get("RAHGARD_OPERATOR_GRANT_CONFIRM") != "APPLY_APPROVED_PLATFORM_GRANT":
                raise ProvisioningError("explicit_operator_confirmation_missing")
            grant_table = "partner.platform_grants" if domain == "partner" else "identity.catalogue_review_grants"
            if wanted_active:
                cur.execute(
                    f"INSERT INTO {grant_table}(user_id,capability,granted_by,reason) VALUES (%s,%s,%s,%s)",
                    (args.target_user, args.capability, args.operator_user, args.reason.strip()),
                )
                event = "granted"
            else:
                cur.execute(
                    f"UPDATE {grant_table} SET revoked_at=now() WHERE user_id=%s AND capability=%s AND revoked_at IS NULL",
                    (args.target_user, args.capability),
                )
                event = "revoked"
                remaining_partner = cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM partner.platform_grants WHERE user_id=%s AND revoked_at IS NULL) AS ok",
                    (args.target_user,),
                ).fetchone()["ok"]
                remaining_catalogue = cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM identity.catalogue_review_grants WHERE user_id=%s AND revoked_at IS NULL) AS ok",
                    (args.target_user,),
                ).fetchone()["ok"]
                if not remaining_partner and not remaining_catalogue:
                    # Revoke encrypted MFA material and all dependent
                    # session-bound step-ups when the final platform grant is
                    # removed. The grant event remains in the audit ledger.
                    cur.execute("DELETE FROM identity.platform_admin_mfa WHERE user_id=%s", (args.target_user,))
            cur.execute(
                """INSERT INTO partner.platform_grant_events
                   (grant_domain,target_user_id,capability,action,actor_user_id,reason)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (domain, args.target_user, args.capability, event, args.operator_user, args.reason.strip()),
            )
        return f"APPLIED action={event} capability={args.capability} database={database}"


def main() -> int:
    args = _parser().parse_args()
    try:
        print(run(args))
    except (ProvisioningError, psycopg.Error, OSError) as exc:
        # Only stable error categories are emitted; driver messages may contain
        # host, database, role, query or deployment details.
        code = str(exc) if isinstance(exc, ProvisioningError) else "database_operation_failed"
        print(f"BLOCKED code={code}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
