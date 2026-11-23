"""Compare a read-only VPS ledger with immutable Git migration blobs."""

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

BASE_NUMBERS = (*range(14), *range(16, 22))
TARGET_NUMBERS = (22, 23)
REPO = Path(__file__).resolve().parents[2]


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=REPO)


def migration_blobs(sha: str) -> dict[int, tuple[str, bytes]]:
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or git("rev-parse", sha).decode().strip() != sha:
        raise ValueError("Expected an immutable full Git commit SHA")
    folders = ("engineering/database-prep/sql", "engineering/pilot/sql")
    paths = git("ls-tree", "-r", "--name-only", sha, "--", *folders).decode().splitlines()
    migrations = {0: ("0000_legacy_tourism_points_baseline", git("show", f"{sha}:database/tourism_points.sql"))}
    for number in (*BASE_NUMBERS[1:], *TARGET_NUMBERS):
        folder = folders[0 if number <= 12 else 1]
        matches = [path for path in paths if path.startswith(f"{folder}/{number:03d}_") and path.endswith(".sql")]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one migration source for {number:04d}")
        path = matches[0]
        migrations[number] = ("0" + Path(path).stem, git("show", f"{sha}:{path}"))
    return migrations


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
