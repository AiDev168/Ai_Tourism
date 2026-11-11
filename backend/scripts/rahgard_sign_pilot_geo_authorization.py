"""Create an owner-controlled target authorization without connecting to a DB."""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.rahgard_geo_visibility import ApprovalBlocked, validate_packet  # noqa: E402
from scripts.rahgard_private_geo_publication import AUTH_SCHEMA, HOST, MARKER, PILOT_NAME, parse_unique_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--owner-authorizes-target", action="store_true")
    args = parser.parse_args()
    try:
        key = os.environ.get("RAHGARD_PILOT_OWNER_AUTHORIZATION_KEY", "").encode("utf-8")
        marker = os.environ.get("RAHGARD_PILOT_DATABASE_MARKER", "")
        if (not args.owner_authorizes_target or len(key) < 32 or not HOST.fullmatch(args.host)
                or not MARKER.fullmatch(marker)
                or not PILOT_NAME.fullmatch(args.database) or not 1024 <= args.port <= 65535
                or args.port == 55433):
            raise ApprovalBlocked("owner authorization or target is missing")
        # Read once to bind the signature to exactly the validated file bytes.
        raw = args.decisions.read_bytes()
        if len(raw) > 32768:
            raise ApprovalBlocked("decision batch is too large")
        packet = parse_unique_json(raw)
        if not validate_packet(packet):
            raise ApprovalBlocked("no approved geographic points")
        now = datetime.now(UTC)
        auth = {"schema": AUTH_SCHEMA, "host": args.host, "port": args.port,
                "database": args.database, "decision_sha256": hashlib.sha256(raw).hexdigest(),
                "marker_sha256": hashlib.sha256(marker.encode("ascii")).hexdigest(),
                "issued_at": now.isoformat(), "expires_at": (now + timedelta(minutes=30)).isoformat(),
                "reviewer": packet["reviewer"], "approval_reference": packet["approval_reference"]}
        canonical = json.dumps(auth, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        auth["signature_sha256"] = hmac.new(key, canonical, hashlib.sha256).hexdigest()
        with args.output.open("x", encoding="utf-8") as output:
            json.dump(auth, output, ensure_ascii=False, sort_keys=True, indent=2)
            output.write("\n")
        print("Owner target authorization written; no database connection was made.")
        return 0
    except (ApprovalBlocked, OSError, ValueError, TypeError):
        print("BLOCKED: target authorization was not written.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
