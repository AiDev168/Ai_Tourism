"""Focused safety and pure-contract tests for the geo-only owner operator."""
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.modules.catalog.owner_content_approval import ApprovalBlocked
from scripts import rahgard_geo_visibility as geo


def _approved_packet(keys: tuple[str, ...] = ("unesco-persepolis-v1",)):
    packet = geo.template()
    packet.update({
        "reviewer": "Pilot geography reviewer",
        "reviewed_at": datetime.now(UTC).isoformat(),
        "approval_reference": "isolated-reviewed-pilot-batch",
    })
    for record in packet["records"]:
        if record["destination_key"] in keys:
            record["decision"] = geo.APPROVE
    return packet


def test_default_template_never_approves_any_pin():
    packet = geo.template()
    assert list(geo.POINTS) == [row["destination_key"] for row in packet["records"]]
    assert geo.validate_packet(packet) == []
    assert all(row["decision"] == "defer" for row in packet["records"])


def test_owner_scope_does_not_silently_authorize_geo_rows(monkeypatch):
    monkeypatch.setattr(
        geo,
        "_guarded_operator_connection",
        lambda: pytest.fail("DB must not be contacted for a deferred packet"),
    )
    assert geo.apply_geo_review(geo.template(), explicitly_authorized=False)["activated"] == 0


def test_per_row_approval_and_independent_review_information():
    packet = _approved_packet(("shiraz-eram-garden-v1",))
    rows = geo.validate_packet(packet)
    assert len(rows) == 1
    assert rows[0]["destination_key"] == "shiraz-eram-garden-v1"
    assert rows[0]["coordinate_role"] == "representative_point"
    assert all(row["decision"] == "defer" for row in packet["records"] if row not in rows)


@pytest.mark.parametrize(
    ("field", "tampered"),
    [
        ("latitude", True),
        ("latitude", 29.6259),
        ("longitude", float("nan")),
        ("coordinate_role", "visitor_entrance"),
        ("city_name", "Other city"),
        ("source_url", "https://example.org/other"),
        ("canonical_name", "Other monument"),
    ],
)
def test_tampered_map_coordinates_or_identity_are_rejected(field, tampered):
    packet = _approved_packet(("shiraz-hafezieh-v1",))
    packet["records"][0][field] = tampered
    with pytest.raises(ApprovalBlocked):
        geo.validate_packet(packet)


def test_review_requires_explicit_reviewer_and_utc_time():
    packet = _approved_packet()
    packet["reviewer"] = None
    with pytest.raises(ApprovalBlocked):
        geo.validate_packet(packet)
    packet["reviewer"] = "Geography reviewer"
    packet["reviewed_at"] = datetime.now().replace(tzinfo=None).isoformat()
    with pytest.raises(ApprovalBlocked):
        geo.validate_packet(packet)


def test_incomplete_or_duplicate_candidate_set_rejected():
    packet = _approved_packet()
    packet["records"] = packet["records"][:-1]
    with pytest.raises(ApprovalBlocked):
        geo.validate_packet(packet)
    packet = _approved_packet()
    packet["records"][1]["destination_key"] = packet["records"][0]["destination_key"]
    with pytest.raises(ApprovalBlocked):
        geo.validate_packet(packet)


def test_explicit_cli_switch_required_before_db_access(monkeypatch):
    packet = _approved_packet()
    monkeypatch.setattr(
        geo,
        "_guarded_operator_connection",
        lambda: pytest.fail("DB guard must not be reached without --apply-approved-geo"),
    )
    with pytest.raises(ApprovalBlocked, match="explicit"):
        geo.apply_geo_review(packet, explicitly_authorized=False)


class _Cursor:
    def __init__(self, *, rows=None, row=None):
        self._rows, self._row = rows, row

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._row


class _FakeConnection:
    """In-memory SQL contract check; NOT a substitute for real PostgreSQL."""

    def __init__(self, *, source_present=True):
        self.status = "needs_review"
        self.source_present = source_present
        self.closed = False
        self.updated = []

    def transaction(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def close(self):
        self.closed = True

    def execute(self, query, args):
        approved = geo.POINTS["unesco-persepolis-v1"]
        if "FROM knowledge.destinations WHERE destination_key=" in query:
            return _Cursor(rows=[{
                "destination_id": 17,
                "destination_key": "unesco-persepolis-v1",
                **{k: approved[k] for k in (
                    "canonical_name", "destination_type", "province_name",
                    "city_name", "latitude", "longitude", "coordinate_role",
                )},
                "stored_latitude": approved["latitude"],
                "stored_longitude": approved["longitude"],
                "status": self.status,
                "verification_status": "verified",
                "record_origin": "verified_external",
                "is_synthetic": False,
            }])
        if "FROM knowledge.destination_sources ds" in query:
            return _Cursor(rows=[{"source_id": 11}] if self.source_present else [])
        if "UPDATE knowledge.destinations" in query:
            self.updated.append(args)
            self.status = "active"
            return _Cursor(row={"destination_id": 17})
        if "FROM knowledge.production_destinations" in query:
            return _Cursor(rows=[{
                "destination_key": "unesco-persepolis-v1",
                "latitude": approved["latitude"],
                "longitude": approved["longitude"],
                "coordinate_role": approved["coordinate_role"],
            }])
        raise AssertionError(f"unexpected SQL: {query}")


def test_one_approved_record_activates_once_and_verifies_production_view(monkeypatch):
    connection = _FakeConnection()
    monkeypatch.setattr(geo, "_guarded_operator_connection", lambda: connection)
    packet = _approved_packet()
    outcome = geo.apply_geo_review(packet, explicitly_authorized=True)
    assert outcome["status"] == "isolated_geo_catalogue_published"
    assert outcome["visible_approved"] == 1
    assert outcome["activated"] == 1
    assert outcome["unchanged"] == 0
    assert len(connection.updated) == 1
    assert connection.closed


def test_missing_verified_source_never_activates(monkeypatch):
    connection = _FakeConnection(source_present=False)
    monkeypatch.setattr(geo, "_guarded_operator_connection", lambda: connection)
    with pytest.raises(ApprovalBlocked, match="source link"):
        geo.apply_geo_review(_approved_packet(), explicitly_authorized=True)
    assert connection.updated == []
    assert connection.closed
