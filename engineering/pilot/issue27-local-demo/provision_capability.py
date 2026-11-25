"""Interactive operator-only grant helper for the isolated local demo.

It reads account email only in this terminal and retrieves only user UUIDs.
The owner DB password is read from the protected demo secret directory into
process memory; it is never printed or placed in an argument list.
"""
from __future__ import annotations

import os
from argparse import Namespace
from pathlib import Path
import sys

import psycopg
from psycopg.conninfo import make_conninfo

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from backend.scripts.provision_platform_capability import CAPABILITIES, run  # noqa: E402

DATA = Path(os.environ.get("LOCALAPPDATA", "")) / "Rahgard" / "Issue27OwnerDemo"
SECRET = DATA / "secrets" / "pg_owner_password"
MARKER_FILE = DATA / "state" / "database-marker"
if not SECRET.is_file() or not MARKER_FILE.is_file():
    raise SystemExit("BLOCKED: local demo secret or marker is unavailable")

print("Rahgard local-only audited capability provisioning. No API or public grant endpoint is used.")
action = input("Action (grant/revoke): ").strip().lower()
if action not in {"grant", "revoke"}:
    raise SystemExit("BLOCKED: action_invalid")
capability = input("Capability: ").strip()
if capability not in CAPABILITIES:
    raise SystemExit("BLOCKED: capability_invalid")
target_email = input("Target account email (created through local signup): ").strip().lower()
operator_email = input("Independent operator account email: ").strip().lower()
if not target_email or not operator_email or target_email == operator_email:
    raise SystemExit("BLOCKED: target_and_operator_must_be_distinct")
reason = input("Non-secret audit reason: ").strip()
if len(reason) < 10 or len(reason) > 1000:
    raise SystemExit("BLOCKED: reason_invalid")
confirmation = input("Type APPLY_LOCAL_CAPABILITY to continue, anything else cancels: ").strip()
if confirmation != "APPLY_LOCAL_CAPABILITY":
    raise SystemExit("CANCELLED")

password = SECRET.read_text(encoding="utf-8").strip()
dsn = make_conninfo(host="127.0.0.1", port=18543, dbname="rahgard_pilot_vps_staging",
                    user="ai_tourism_owner", password=password, connect_timeout=5,
                    application_name="rahgard_issue27_local_operator")
with psycopg.connect(dsn) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT user_id FROM identity.users WHERE lower(email)=lower(%s) AND is_synthetic=FALSE", (target_email,))
        target = cur.fetchall()
        cur.execute("SELECT user_id FROM identity.users WHERE lower(email)=lower(%s) AND is_synthetic=FALSE", (operator_email,))
        operator = cur.fetchall()
if len(target) != 1 or len(operator) != 1:
    raise SystemExit("BLOCKED: target_or_operator_account_not_unique")

os.environ["RAHGARD_OPERATOR_DATABASE_URL"] = dsn
os.environ["RAHGARD_PILOT_DATABASE_MARKER"] = MARKER_FILE.read_text(encoding="ascii").strip()
os.environ["RAHGARD_OPERATOR_GRANT_CONFIRM"] = "APPLY_APPROVED_PLATFORM_GRANT"
args = Namespace(target_user=target[0][0], operator_user=operator[0][0], capability=capability,
                 action=action, reason=reason, apply=True)
try:
    print(run(args))
except Exception as exc:
    # Print only stable provisioning codes, never driver text or connection info.
    from backend.scripts.provision_platform_capability import ProvisioningError
    code = str(exc) if isinstance(exc, ProvisioningError) else "database_operation_failed"
    raise SystemExit(f"BLOCKED code={code}") from None
finally:
    os.environ.pop("RAHGARD_OPERATOR_DATABASE_URL", None)
    os.environ.pop("RAHGARD_PILOT_DATABASE_MARKER", None)
    os.environ.pop("RAHGARD_OPERATOR_GRANT_CONFIRM", None)
