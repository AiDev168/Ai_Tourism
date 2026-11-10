"""Operator-only, geographic-only publication of four existing Fars POIs.

No historical claim, RAG document, index, or source-text approval is implied.
The only write is an exact status transition on already-seeded canonical
destinations, and ONLY in the marker-validated disposable PostgreSQL 17 DB.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from scripts.rahgard_content_workflow import (  # noqa: E402
    ApprovalBlocked,
    _guarded_operator_connection,
)

SCHEMA = "rahgard.geo-visibility-batch.v1"
APPROVE = "approve_approximate_display"
DECISIONS = frozenset((APPROVE, "revise", "defer"))
# Values are REVIEW CANDIDATES, not approved places or verified entrances.
# Seeded canonical rows in migrations 0005/0007 already contain these points.
POINTS: dict[str, dict[str, Any]] = {
    "shiraz-hafezieh-v1": {
        "canonical_name": "آرامگاه حافظ (حافظیه)",
        "destination_type": "historic_memorial",
        "province_name": "فارس",
        "city_name": "شیراز",
        "latitude": 29.6254028,
        "longitude": 52.5583194,
        "coordinate_role": "representative_point",
        "source_url": "https://en.wikipedia.org/wiki/Tomb_of_Hafez",
    },
    "shiraz-eram-garden-v1": {
        "canonical_name": "باغ ارم",
        "destination_type": "historic_garden",
        "province_name": "فارس",
        "city_name": "شیراز",
        "latitude": 29.63583,
        "longitude": 52.52528,
        "coordinate_role": "representative_point",
        "source_url": "https://en.wikipedia.org/wiki/Eram_Garden",
    },
    "shiraz-vakil-bazaar-v1": {
        "canonical_name": "بازار وکیل",
        "destination_type": "historic_bazaar",
        "province_name": "فارس",
        "city_name": "شیراز",
        "latitude": 29.6149806,
        "longitude": 52.5467972,
        "coordinate_role": "representative_point",
        "source_url": "https://en.wikipedia.org/wiki/Vakil_Bazaar",
    },
    "unesco-persepolis-v1": {
        "canonical_name": "تخت جمشید",
        "destination_type": "archaeological_site",
        "province_name": "فارس",
        "city_name": None,
        "latitude": 29.93444,
        "longitude": 52.89028,
        "coordinate_role": "property_reference",
        "source_url": "https://whc.unesco.org/en/list/114/maps/",
    },
}
REVIEW_FIELDS = frozenset((
    "destination_key", "decision", "canonical_name", "destination_type",
    "province_name", "city_name", "latitude", "longitude",
    "coordinate_role", "source_url",
))
PACKET_FIELDS = frozenset((
    "schema", "scope", "reviewer", "reviewed_at", "approval_reference", "records",
))


def template() -> dict[str, Any]:
    """Create a non-authorizing, all-deferred four-record decision packet."""
    return {
        "schema": SCHEMA,
        "scope": "Shiraz/Fars orientation-only map display",
        "reviewer": None,
        "reviewed_at": None,
        "approval_reference": None,
        "records": [
            {"destination_key": key, "decision": "defer", **data}
            for key, data in POINTS.items()
        ],
    }


def validate_packet(payload: object) -> list[dict[str, Any]]:
    """Fail closed on altered POI identities, unreviewed fields and approvals.

    An approval authorizes an *approximate orientation marker*, never visitor
    entrance, turn-by-turn route, accessibility, opening hours or RAG claims.
    To change any candidate pin/source identity, first revise this versioned
    reference and repeat the owner's geographic review.
    """
    if not isinstance(payload, dict) or set(payload) != PACKET_FIELDS:
        raise ApprovalBlocked("geo review packet schema is incomplete or contains unknown fields")
    if payload["schema"] != SCHEMA or payload["scope"] != template()["scope"]:
        raise ApprovalBlocked("geo review scope/version mismatch")
    records = payload["records"]
    if not isinstance(records, list) or len(records) != len(POINTS):
        raise ApprovalBlocked("geo review must enumerate all four canonical identities")
    approved: list[dict[str, Any]] = []
    for (expected_key, reference), record in zip(POINTS.items(), records, strict=True):
        if not isinstance(record, dict) or set(record) != REVIEW_FIELDS:
            raise ApprovalBlocked("geo review record has missing or unknown fields")
        if record["destination_key"] != expected_key:
            raise ApprovalBlocked("geo review record order or canonical key changed")
        if record["decision"] not in DECISIONS:
            raise ApprovalBlocked("invalid geo-visibility decision")
        for field, expected in reference.items():
            received = record[field]
            if field in {"latitude", "longitude"}:
                if (
                    isinstance(received, bool)
                    or not isinstance(received, (int, float))
                    or not math.isfinite(received)
                    or received != expected
                ):
                    raise ApprovalBlocked("geo point differs from the reviewed seed coordinate")
            elif received != expected:
                raise ApprovalBlocked("geo identity, locality, role or source differs from reviewed seed")
        if record["decision"] == APPROVE:
            approved.append(record)

    if approved:
        if any(
            not isinstance(payload[field], str)
            or not payload[field].strip()
            or len(payload[field]) > 240
            for field in ("reviewer", "approval_reference", "reviewed_at")
        ):
            raise ApprovalBlocked("approved map pins require owner reviewer/date/reference")
        try:
            reviewed_at = datetime.fromisoformat(payload["reviewed_at"].replace("Z", "+00:00"))
        except ValueError:
            raise ApprovalBlocked("invalid geo review timestamp") from None
        if reviewed_at.tzinfo is None or reviewed_at.utcoffset() != UTC.utcoffset(None):
            raise ApprovalBlocked("geo review timestamp must be UTC")
        if reviewed_at > datetime.now(UTC):
            raise ApprovalBlocked("geo review cannot be in the future")
    return approved


def _read_decisions(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file() or path.stat().st_size > 32_768:
            raise ApprovalBlocked("geo decision file is missing or too large")
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError):
        raise ApprovalBlocked("geo decision file is missing or invalid") from None


def _promote_one(connection: Any, record: dict[str, Any]) -> bool:
    key = record["destination_key"]
    matches = connection.execute(
        """SELECT destination_id, destination_key, canonical_name,
                  destination_type, province_name, city_name,
                  latitude, longitude, coordinate_role, record_origin,
                  verification_status, status, is_synthetic,
                  ST_Y(location::geometry) AS stored_latitude,
                  ST_X(location::geometry) AS stored_longitude
           FROM knowledge.destinations WHERE destination_key=%s FOR UPDATE""",
        (key,),
    ).fetchall()
    if len(matches) != 1:
        raise ApprovalBlocked("approved destination canonical identity is missing or ambiguous")
    row = matches[0]
    for field in (
        "destination_key", "canonical_name", "destination_type",
        "province_name", "city_name", "coordinate_role",
    ):
        if row[field] != record[field]:
            raise ApprovalBlocked("approved destination identity or point role has drifted")
    if (
        row["latitude"] is None
        or row["longitude"] is None
        or abs(float(row["latitude"]) - record["latitude"]) > 0.0000001
        or abs(float(row["longitude"]) - record["longitude"]) > 0.0000001
        or row["stored_latitude"] is None
        or row["stored_longitude"] is None
        or abs(float(row["stored_latitude"]) - record["latitude"]) > 0.0000001
        or abs(float(row["stored_longitude"]) - record["longitude"]) > 0.0000001
        or row["record_origin"] != "verified_external"
        or row["verification_status"] != "verified"
        or row["is_synthetic"] is not False
        or row["status"] not in {"needs_review", "active"}
    ):
        raise ApprovalBlocked("approved destination is not a matching verified real geographic row")
    source_rows = connection.execute(
        """SELECT s.source_id
           FROM knowledge.destination_sources ds
           JOIN knowledge.knowledge_sources s ON s.source_id=ds.source_id
           WHERE ds.destination_id=%s AND s.url=%s
             AND s.verification_status='verified' AND s.is_synthetic=FALSE
             AND (ds.valid_from IS NULL OR ds.valid_from <= NOW())
             AND (ds.valid_until IS NULL OR ds.valid_until >= NOW())""",
        (row["destination_id"], record["source_url"]),
    ).fetchall()
    if len(source_rows) != 1:
        raise ApprovalBlocked("no unique, current verified geographic source link for POI")
    if row["status"] == "active":
        return False
    result = connection.execute(
        """UPDATE knowledge.destinations
           SET status='active', updated_at=NOW()
           WHERE destination_id=%s AND destination_key=%s
             AND status='needs_review' AND verification_status='verified'
             AND record_origin='verified_external' AND is_synthetic=FALSE
           RETURNING destination_id""",
        (row["destination_id"], key),
    ).fetchone()
    if result is None:
        raise ApprovalBlocked("geographic activation precondition changed")
    return True


def apply_geo_review(packet: dict[str, Any], *, explicitly_authorized: bool) -> dict[str, Any]:
    """Apply approved rows transactionally in the disposable DB, then verify view."""
    approved = validate_packet(packet)
    if not approved:
        return {"status": "held_for_owner_geo_review", "activated": 0, "unchanged": 0}
    if not explicitly_authorized:
        raise ApprovalBlocked("explicit --apply-approved-geo flag is required")
    connection = _guarded_operator_connection()
    try:
        with connection.transaction():
            activated = unchanged = 0
            for record in approved:
                if _promote_one(connection, record):
                    activated += 1
                else:
                    unchanged += 1
            exposed = connection.execute(
                """SELECT destination_key, latitude, longitude, coordinate_role
                   FROM knowledge.production_destinations
                   WHERE destination_key = ANY(%s::TEXT[])""",
                ([record["destination_key"] for record in approved],),
            ).fetchall()
            exposed_by_key = {row["destination_key"]: row for row in exposed}
            if len(exposed_by_key) != len(approved):
                raise ApprovalBlocked("approved POIs are not all visible in real production catalogue")
            for record in approved:
                row = exposed_by_key[record["destination_key"]]
                if (
                    row["coordinate_role"] != record["coordinate_role"]
                    or abs(float(row["latitude"]) - record["latitude"]) > 0.0000001
                    or abs(float(row["longitude"]) - record["longitude"]) > 0.0000001
                ):
                    raise ApprovalBlocked("approved published POI coordinate mismatch")
        return {
            "status": "isolated_geo_catalogue_published",
            "activated": activated,
            "unchanged": unchanged,
            "visible_approved": len(exposed_by_key),
            "public_deployment": False,
            "owner_rag_indexed": False,
        }
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    template_cmd = commands.add_parser("template", help="write default-deferred owner batch")
    template_cmd.add_argument("--output", type=Path, required=True)
    dry = commands.add_parser("dry-run", help="validate review without database access")
    dry.add_argument("--decisions", type=Path)
    publish = commands.add_parser("publish-approved", help="guarded disposable PG17 only")
    publish.add_argument("--decisions", type=Path, required=True)
    publish.add_argument("--apply-approved-geo", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "template":
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(template(), stream, ensure_ascii=False, indent=2)
                stream.write("\n")
            result = {"status": "deferred_template_written", "output": str(args.output)}
        elif args.command == "dry-run":
            payload = _read_decisions(args.decisions) if args.decisions else template()
            approved = validate_packet(payload)
            result = {
                "status": "ready_for_geo_review" if not approved else "owner_geo_approval_supplied",
                "candidate_records": len(POINTS),
                "approved_records": len(approved),
                "deferred_or_revise_records": len(POINTS) - len(approved),
                "published": False,
            }
        else:
            result = apply_geo_review(
                _read_decisions(args.decisions),
                explicitly_authorized=args.apply_approved_geo,
            )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (ApprovalBlocked, FileExistsError, OSError):
        print("BLOCKED: geo publication precondition failed; no unapproved record was promoted.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
