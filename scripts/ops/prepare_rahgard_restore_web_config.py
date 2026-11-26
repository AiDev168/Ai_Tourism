"""Create the isolated restore-only Nginx config for the archived Web image.

The normal Web image resolves ``api`` through Compose DNS. During a portable
restore check, API and Web share an isolated container network namespace with
the PostgreSQL test target, so the only permitted upstream is API loopback.
This helper accepts only the repository's expected single upstream directive
and writes the derived config to a caller-owned private temporary path.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


SOURCE = "proxy_pass http://api:8000;"
TARGET = "proxy_pass http://127.0.0.1:8000;"


def prepare(source: Path, destination: Path) -> None:
    content = source.read_text(encoding="utf-8")
    if content.count(SOURCE) != 1:
        raise ValueError("web_proxy_upstream_contract_mismatch")
    directives = re.findall(r"^\s*proxy_pass\s+[^;]+;\s*$", content, re.MULTILINE)
    if len(directives) != 1 or directives[0].strip() != SOURCE:
        raise ValueError("web_proxy_upstream_contract_mismatch")
    if destination.exists() or destination.is_symlink():
        raise ValueError("web_config_destination_exists")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content.replace(SOURCE, TARGET), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        prepare(args.source, args.destination)
    except (OSError, ValueError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2
    print("PASS: isolated restore proxy config targets only API loopback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
