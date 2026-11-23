"""Read-only verifier for the live Rahgard V2 migration state.

This utility intentionally cannot apply DDL. Production already has migrations
0022 and 0023; this command must report ALREADY_APPLIED_NO_DDL for that state.
Earlier-state migration rehearsals belong in a disposable restored database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path("/opt/rahgard-staging")
DATABASE_CONTAINER = "rahgard-staging-db-1"
API_CONTAINER = "rahgard-staging-api-1"
WEB_CONTAINER = "rahgard-staging-web-1"
DATABASE = "rahgard_pilot_vps_staging"
DATABASE_OWNER = "ai_tourism_owner"
DATABASE_IMAGE = "rahgard-postgres:17-postgis36-vector087"
DATABASE_VOLUME = "rahgard_staging_pgdata"
LEGACY_CURRENT_SHA = "5e2664fb51e18f52549aa37a8b5793e12ace09b2"
APPROVED_RELEASE_SHA = "36625ecf269c2a3d5590528257d32af2b6f47dd0"
EXPECTED_LEDGER_SHA256 = "515809c472a735018f939d8777a0a864188d13c0e870db32d0af6aef0e12782a"
EXPECTED_IMAGE_IDS = {
    "database": "sha256:a30c041297b2306a8bb79cc6ed737f16bfca3078a3024324bb8115b302e83535",
    "api": "sha256:2c814062db391b3b484b8c45b622329e9f8519a1bf0cc1627828744b23ab497e",
    "web": "sha256:44fb963eea6b5fa0dbd2a876036906c15581eec8677e34f3111781229eabd375",
}
EXPECTED_TAIL = (
    ("0022_traveler_company_requests", "e6b7db49abc0ff76c2620b2cc8d5dded0f4255f8533efd20bd5b402a0ba57eda"),
    ("0023_partner_trip_responses", "deef8c5016f26aa646b9ff22346fad4ade3c6780ff447f701aa9e8a8e28571ac"),
)


class SafetyError(RuntimeError):
    """A live identity or migration invariant did not match."""


def run(command: list[str], *, data: bytes | None = None) -> bytes:
    result = subprocess.run(command, input=data, capture_output=True, timeout=45, check=False)
    if result.returncode:
        # Never echo commands that could contain credentials or query data.
        raise SafetyError(f"read-only probe failed ({Path(command[0]).name}, exit {result.returncode})")
    return result.stdout


def inspect_json(name: str) -> dict[str, Any]:
    raw = run(["docker", "inspect", name])
    try:
        return json.loads(raw)[0]
    except (ValueError, IndexError, TypeError) as exc:
        raise SafetyError(f"invalid Docker inspection for {name}") from exc


def readonly_query(sql: str) -> list[str]:
    command = (
        "export PGPASSWORD=\"$(cat /run/secrets/pg_owner_password)\"; "
        "exec psql -XqAt -F '|' -v ON_ERROR_STOP=1 -h 127.0.0.1 "
        f"-U {DATABASE_OWNER} -d {DATABASE}"
    )
    return run(["docker", "exec", "-i", DATABASE_CONTAINER, "sh", "-lc", command],
               data=sql.encode("utf-8")).decode("utf-8").splitlines()


def assert_sha(value: str, label: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise SafetyError(f"{label} must be a full lowercase commit SHA")


def verify(*, root: Path, expected_release_sha: str, expected_ledger_sha256: str,
           expected_volume: str, expected_owner: str) -> dict[str, Any]:
    assert_sha(expected_release_sha, "expected release SHA")
    if expected_release_sha != APPROVED_RELEASE_SHA:
        raise SafetyError("release SHA differs from the reviewed live image bundle")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_ledger_sha256):
        raise SafetyError("expected ledger digest must be a full SHA-256")
    if expected_volume != DATABASE_VOLUME or expected_owner != DATABASE_OWNER:
        raise SafetyError("requested database owner or protected volume differs from the fixed pilot identity")
    if expected_ledger_sha256 != EXPECTED_LEDGER_SHA256:
        raise SafetyError("expected ledger digest differs from the independently captured live PG17 ledger")

    release = root / "releases" / expected_release_sha / "RELEASE_COMMIT"
    if not release.is_file() or release.read_text(encoding="ascii").strip() != expected_release_sha:
        raise SafetyError("immutable release marker mismatch")
    current = root / "current" / "RELEASE_COMMIT"
    if not current.is_file() or current.read_text(encoding="ascii").strip() != LEGACY_CURRENT_SHA:
        raise SafetyError("legacy current pointer changed; review writer topology before proceeding")
    env_path = root / ".env.v2"
    if not env_path.is_file() or env_path.is_symlink():
        raise SafetyError("isolated apex runtime configuration missing or symlinked")
    try:
        env_values: dict[str, list[str]] = {}
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line and not line.lstrip().startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_values.setdefault(key, []).append(value)
    except OSError as exc:
        raise SafetyError("isolated apex runtime configuration cannot be read") from exc
    env_expected = {
        "RAHGARD_PUBLIC_HOST": "hinaa.ir",
        "RAHGARD_RELEASE_SHA": expected_release_sha,
        "RAHGARD_WEB_BIND_PORT": "18081",
        "RAHGARD_COMPOSE_PROJECT": "rahgard-staging",
        "RAHGARD_PG_VOLUME": expected_volume,
        "RAHGARD_STAGING_EMAIL_SIGNUP_ENABLED": "true",
        "RAHGARD_BUILD_IMAGES": "false",
    }
    if any(env_values.get(key) != [value] for key, value in env_expected.items()):
        raise SafetyError("apex runtime host/release/volume configuration mismatch")
    if stat.S_IMODE(env_path.stat().st_mode) != 0o600:
        raise SafetyError("apex runtime configuration permissions must be exactly 0600")
    marker_path = root / "state" / "database-marker"
    if not marker_path.is_file():
        raise SafetyError("protected database marker is missing")
    marker = marker_path.read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[0-9a-fA-F]{48}", marker):
        raise SafetyError("protected database marker format mismatch")

    db = inspect_json(DATABASE_CONTAINER)
    mounts = db.get("Mounts", [])
    pg_mounts = [m for m in mounts if m.get("Destination") == "/var/lib/postgresql/data"]
    if (not db.get("State", {}).get("Running")
            or db.get("State", {}).get("Health", {}).get("Status") != "healthy"
            or db.get("Config", {}).get("Image") != DATABASE_IMAGE
            or db.get("Image") != EXPECTED_IMAGE_IDS["database"]
            or len(pg_mounts) != 1
            or pg_mounts[0].get("Type") != "volume"
            or pg_mounts[0].get("Name") != expected_volume):
        raise SafetyError("PG17 health, image, or persistent volume identity mismatch")

    runtime_images: dict[str, str] = {}
    for name, service in ((API_CONTAINER, "api"), (WEB_CONTAINER, "web")):
        container = inspect_json(name)
        image = container.get("Config", {}).get("Image", "")
        if (not container.get("State", {}).get("Running")
                or container.get("State", {}).get("Health", {}).get("Status") != "healthy"
                or image != f"rahgard-{service}:{expected_release_sha}"
                or container.get("Image") != EXPECTED_IMAGE_IDS[service]):
            raise SafetyError(f"running {service} container does not match the immutable release")
        runtime_images[service] = image

    sql = (
        "BEGIN READ ONLY;\n"
        "SELECT 'identity|' || current_database() || '|' || current_user || '|' || current_setting('server_version_num') || '|' || "
        "(SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database());\n"
        f"SELECT 'marker|' || count(*) FROM public.rahgard_private_pilot_marker WHERE marker_value='{marker}';\n"
        "SELECT 'ledger|' || migration_id || '|' || rtrim(sha256) FROM system.schema_migrations ORDER BY migration_id;\n"
        "COMMIT;\n"
    )
    rows = readonly_query(sql)
    if not rows or not rows[0].startswith("identity|"):
        raise SafetyError("database identity query returned an unexpected shape")
    identity = rows[0].split("|")
    if (len(identity) != 5 or identity[1] != DATABASE or identity[2] != expected_owner
            or not identity[3].isdigit() or not 170000 <= int(identity[3]) < 180000
            or identity[4] != expected_owner):
        raise SafetyError("database name, owner, or PostgreSQL 17 identity mismatch")
    if len(rows) < 2 or rows[1] != "marker|1":
        raise SafetyError("private pilot database marker is missing or ambiguous")
    ledger = [row.removeprefix("ledger|") for row in rows[2:] if row.startswith("ledger|")]
    ledger_sha = hashlib.sha256(("\n".join(ledger) + "\n").encode()).hexdigest()
    if len(ledger) != 22 or ledger_sha != expected_ledger_sha256:
        raise SafetyError("ledger count or caller-attested full-ledger digest mismatch")
    tail = [tuple(line.split("|", 1)) for line in ledger[-2:]]
    if tuple(tail) != EXPECTED_TAIL:
        raise SafetyError("migrations 0022/0023 are not present with the reviewed checksums")

    # Defensive assertion: the implementation is intentionally incapable of
    # loading or executing migration SQL. No output from this function claims DDL.
    return {
        "status": "ALREADY_APPLIED_NO_DDL",
        "database": DATABASE,
        "database_owner": expected_owner,
        "postgres_major": 17,
        "volume": expected_volume,
        "migration_count": len(ledger),
        "ledger_sha256": ledger_sha,
        "latest_migrations": [list(item) for item in EXPECTED_TAIL],
        "release_sha": expected_release_sha,
        "runtime_images": runtime_images,
        "ddl_executed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--expected-release-sha", required=True)
    parser.add_argument("--expected-ledger-sha256", required=True)
    parser.add_argument("--expected-volume", required=True)
    parser.add_argument("--expected-owner", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(verify(root=args.root, expected_release_sha=args.expected_release_sha,
                                expected_ledger_sha256=args.expected_ledger_sha256,
                                expected_volume=args.expected_volume, expected_owner=args.expected_owner),
                         sort_keys=True))
    except SafetyError as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "ddl_executed": False}, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
