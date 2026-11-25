"""Compare a read-only VPS ledger with immutable Git migration blobs."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

BASE_NUMBERS = (*range(14), *range(16, 22))
TARGET_NUMBERS = (22, 23)
CURRENT_BASE_NUMBERS = (*range(14), *range(16, 24))
CURRENT_TARGET_NUMBERS = (24, 25, 26)
REPO = Path(__file__).resolve().parents[2]


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=REPO)


def _migration_blobs(sha: str, numbers: tuple[int, ...]) -> dict[int, tuple[str, bytes]]:
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or git("rev-parse", sha).decode().strip() != sha:
        raise ValueError("Expected an immutable full Git commit SHA")
    folders = ("engineering/database-prep/sql", "engineering/pilot/sql")
    paths = git("ls-tree", "-r", "--name-only", sha, "--", *folders).decode().splitlines()
    migrations = {0: ("0000_legacy_tourism_points_baseline", git("show", f"{sha}:database/tourism_points.sql"))}
    for number in numbers:
        folder = folders[0 if number <= 12 else 1]
        matches = [path for path in paths if path.startswith(f"{folder}/{number:03d}_") and path.endswith(".sql")]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one migration source for {number:04d}")
        path = matches[0]
        migrations[number] = ("0" + Path(path).stem, git("show", f"{sha}:{path}"))
    return migrations


def migration_blobs(sha: str) -> dict[int, tuple[str, bytes]]:
    """Legacy 0021-baseline map retained for the historical 0022/0023 rehearsal."""
    return _migration_blobs(sha, (*BASE_NUMBERS[1:], *TARGET_NUMBERS))


def current_migration_blobs(sha: str) -> dict[int, tuple[str, bytes]]:
    """Exact production-current 0023 baseline plus proposed 0024–0026."""
    return _migration_blobs(sha, (*CURRENT_BASE_NUMBERS[1:], *CURRENT_TARGET_NUMBERS))


def check_current_snapshot(manifest: dict, sha: str) -> dict:
    """Validate the sanitized, read-only 0023 VPS snapshot against Git SQL blobs."""
    vps = manifest["vps"]
    database = vps["database"]
    if not (
        database["name"] == "rahgard_pilot_vps_staging"
        and database["volume"] == "rahgard_staging_pgdata"
        and database["marker_matches_protected_host_state"] is True
        and database["postgresql"].split(".")[0] == "17"
        and vps["api_image"] == "rahgard-api:9b5b07d0786578abdfac56848baf3c6d1260832e"
        and vps["web_image"] == "rahgard-web:9b5b07d0786578abdfac56848baf3c6d1260832e"
        and vps["legacy_release_marker"] == "5e2664fb51e18f52549aa37a8b5793e12ace09b2"
    ):
        raise ValueError("Current 0023 snapshot identity or topology differs from the verified read-only target")

    migrations = current_migration_blobs(sha)
    ledger = database["migration_ledger"]
    expected_numbers = CURRENT_BASE_NUMBERS
    required_counts = {"users", "sessions", "trips", "conversations", "itineraries", "organizations",
                       "published_destinations"}
    counts = database["aggregate_counts"]
    if set(counts) != required_counts or any(type(value) is not int or value < 0 for value in counts.values()):
        raise ValueError("Current VPS aggregate snapshot is incomplete or invalid")
    if [row["migration_id"] for row in ledger] != [migrations[n][0] for n in expected_numbers]:
        raise ValueError("Current VPS ledger is not the exact known 0023 baseline (including intentional 0014/0015 omissions)")
    historical_crlf = []
    for number, row in zip(expected_numbers, ledger, strict=True):
        migration_id, source = migrations[number]
        if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
            raise ValueError(f"Invalid migration checksum format for {migration_id}")
        lf = source.replace(b"\r\n", b"\n")
        if b"\r" in lf:
            raise ValueError(f"Unsupported SQL line endings for {migration_id}")
        if row["sha256"] == hashlib.sha256(source).hexdigest():
            continue
        if row["sha256"] != hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest():
            raise ValueError(f"Current ledger checksum differs for {migration_id}")
        historical_crlf.append(migration_id)
    pending = []
    for number in CURRENT_TARGET_NUMBERS:
        migration_id, source = migrations[number]
        pending.append({"id": migration_id, "sha256": hashlib.sha256(source).hexdigest()})
    return {"source_sha": sha, "verified_base_entries": len(ledger),
            "historical_crlf_entries": historical_crlf, "pending": pending}


def check(manifest: dict, sha: str) -> dict:
    database = manifest["vps"]["database"]
    if not (
        database["marker_matches"] is True
        and database["volume"] == "rahgard_staging_pgdata"
        and database["postgresql"].split(".")[0] == "17"
        and database["share_and_response_tables_present"] is False
    ):
        raise ValueError("Unexpected marker, volume, PostgreSQL version or V2 schema objects")

    migrations = migration_blobs(sha)
    ledger = database["migration_ledger"]
    if [row["migration_id"] for row in ledger] != [migrations[n][0] for n in BASE_NUMBERS]:
        raise ValueError("Expected the complete, ordered migration ledger through 0021")
    historical_crlf = []
    for number, row in zip(BASE_NUMBERS, ledger, strict=True):
        migration_id, source = migrations[number]
        lf = source.replace(b"\r\n", b"\n")
        if b"\r" in lf:
            raise ValueError(f"Unsupported SQL line endings for {migration_id}")
        if row["sha256"] == hashlib.sha256(source).hexdigest():
            continue
        if row["sha256"] != hashlib.sha256(lf.replace(b"\n", b"\r\n")).hexdigest():
            raise ValueError(f"Existing migration checksum differs for {migration_id}")
        historical_crlf.append(migration_id)

    return {
        "source_sha": sha,
        "verified_base_entries": len(ledger),
        "historical_crlf_entries": historical_crlf,
        "pending": [
            {"id": migrations[n][0], "sha256": hashlib.sha256(migrations[n][1]).hexdigest()}
            for n in TARGET_NUMBERS
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("source_sha")
    arguments = parser.parse_args()
    try:
        manifest = json.loads(arguments.manifest.read_text(encoding="utf-8"))
        print(json.dumps(check(manifest, arguments.source_sha), indent=2))
    except (ValueError, KeyError, TypeError, AttributeError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"BLOCKED: {error}\n")


if __name__ == "__main__":
    main()
