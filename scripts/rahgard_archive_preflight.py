#!/usr/bin/env python3
"""Read-only, standard-library preflight for nested tourism ZIP/CSV deliveries.

Never executes archive SQL, extracts files to disk, connects to PostgreSQL, or
declares candidate destinations published. Reports member content duplicates,
not real-world entity identity duplicates.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import PurePosixPath
from typing import Any

MAX_DEPTH = 3
MAX_MEMBER_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 256 * 1024 * 1024
MAX_FILES = 5000


class UnsafeArchive(ValueError):
    """Archive violates bounded, traversal-free inspection contract."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_path(name: str) -> str:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if (
        not normalized
        or normalized.startswith("/")
        or any(part in ("", ".", "..") for part in normalized.split("/"))
        or ":" in normalized.split("/")[0]
        or "\x00" in normalized
    ):
        raise UnsafeArchive("unsafe archive member path")
    return path.as_posix()


def _open_zip(data: bytes) -> zipfile.ZipFile:
    try:
        return zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError) as exc:
        raise UnsafeArchive("invalid nested ZIP") from exc


def inspect(data: bytes) -> dict[str, Any]:
    """Return deterministic, no-database inspection manifest."""
    if len(data) > MAX_TOTAL_BYTES:
        raise UnsafeArchive("input archive exceeds byte budget")
    members: list[dict[str, Any]] = []
    csv_rows: list[dict[str, Any]] = []
    total = 0
    file_count = 0

    def visit(payload: bytes, prefix: str, depth: int) -> None:
        nonlocal total, file_count
        if depth > MAX_DEPTH:
            raise UnsafeArchive("nested ZIP depth exceeded")
        with _open_zip(payload) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    continue
                name = safe_path(info.filename)
                if info.flag_bits & 1:
                    raise UnsafeArchive("encrypted member unsupported")
                file_count += 1
                if file_count > MAX_FILES or info.file_size > MAX_MEMBER_BYTES:
                    raise UnsafeArchive("archive member count/size exceeded")
                total += info.file_size
                if total > MAX_TOTAL_BYTES:
                    raise UnsafeArchive("expanded archive exceeds byte budget")
                # ZIP symlinks are not ordinary data files.
                mode = (info.external_attr >> 16) & 0o170000
                if mode == 0o120000:
                    raise UnsafeArchive("symbolic links prohibited")
                try:
                    body = archive.read(info)
                except (RuntimeError, zipfile.BadZipFile, OSError) as exc:
                    raise UnsafeArchive("unreadable ZIP member") from exc
                if len(body) != info.file_size:
                    raise UnsafeArchive("ZIP member size mismatch")
                location = f"{prefix}!{name}" if prefix else name
                digest = sha256(body)
                kind = name.lower().rsplit(".", 1)[-1] if "." in name else ""
                members.append({"location": location, "format": kind, "bytes": len(body), "sha256": digest})
                if kind == "zip":
                    visit(body, location, depth + 1)
                elif kind == "csv":
                    try:
                        text = body.decode("utf-8-sig", errors="strict")
                        reader = csv.DictReader(io.StringIO(text, newline=""))
                        if not reader.fieldnames or None in reader.fieldnames:
                            raise ValueError("invalid csv headers")
                        headers = list(reader.fieldnames)
                        count = 0
                        keys: set[str] = set()
                        duplicate_keys = 0
                        for row in reader:
                            if None in row:
                                raise ValueError("invalid csv field count")
                            count += 1
                            key = (row.get("destination_key") or "").strip()
                            if key:
                                if key in keys:
                                    duplicate_keys += 1
                                keys.add(key)
                    except (UnicodeError, csv.Error, ValueError) as exc:
                        raise UnsafeArchive(f"invalid CSV at {location}") from exc
                    csv_rows.append({
                        "location": location, "sha256": digest, "row_count": count,
                        "headers": headers, "unique_destination_keys": len(keys),
                        "repeated_destination_keys_in_file": duplicate_keys,
                    })

    visit(data, "", 0)
    by_hash: dict[str, list[str]] = defaultdict(list)
    for row in members:
        if row["format"] == "csv":
            by_hash[row["sha256"]].append(row["location"])
    duplicates = [
        {"sha256": digest, "deliveries": sorted(paths)}
        for digest, paths in sorted(by_hash.items())
        if len(paths) > 1
    ]
    return {
        "contract_version": "rahgard-archive-preflight.v1",
        "archive_sha256": sha256(data),
        "member_count": len(members),
        "csv_file_count": len(csv_rows),
        "csv_row_total_including_duplicate_deliveries": sum(x["row_count"] for x in csv_rows),
        "distinct_csv_content_count": len(by_hash),
        "duplicate_csv_content_groups": duplicates,
        "members": members,
        "csv": csv_rows,
        "publication_approved": False,
        "database_modified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="input ZIP path (read only)")
    parser.add_argument("--output", help="optional path for deterministic JSON report")
    args = parser.parse_args(argv)
    try:
        with open(args.archive, "rb") as handle:
            report = inspect(handle.read())
    except (UnsafeArchive, OSError) as exc:
        print(f"preflight failed: {exc}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(rendered)
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
