"""Private pilot publication must fail before contacting any database without authority."""
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import json
import sys

import pytest

from scripts import rahgard_geo_visibility as geo
from scripts import rahgard_private_geo_authorize as authorizer
from scripts import rahgard_private_geo_publication as pilot
from scripts import rahgard_sign_pilot_geo_authorization as signer

OWNER_KEY = b"test-only-owner-authorization-key-32-bytes"
PILOT_MARKER = "a" * 48


def sign(auth):
    unsigned = {key: value for key, value in auth.items() if key != "signature_sha256"}
    canonical = json.dumps(unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    auth["signature_sha256"] = hmac.new(OWNER_KEY, canonical, hashlib.sha256).hexdigest()


def test_duplicate_json_fields_are_rejected():
    with pytest.raises(ValueError, match="duplicate"):
        pilot.parse_unique_json('{"decision":"defer","decision":"approve_approximate_display"}')


def reviewed():
    packet = geo.template()
    packet.update(reviewer="Owner", reviewed_at=datetime.now(UTC).isoformat(),
                  approval_reference="owner-private-pilot-001")
    packet["records"][0]["decision"] = geo.APPROVE
    raw = json.dumps(packet, ensure_ascii=False).encode()
    auth = {"schema": pilot.AUTH_SCHEMA, "host": "pilot.example.org", "port": 5432,
            "database": "rahgard_pilot_fars", "decision_sha256": hashlib.sha256(raw).hexdigest(),
            "marker_sha256": hashlib.sha256(PILOT_MARKER.encode()).hexdigest(),
            "issued_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
            "expires_at": (datetime.now(UTC) + timedelta(minutes=29)).isoformat(),
            "reviewer": packet["reviewer"], "approval_reference": packet["approval_reference"]}
    sign(auth)
    return packet, raw, auth


def test_authorization_is_bound_to_exact_target_and_reviewed_bytes():
    packet, raw, auth = reviewed()
    assert len(pilot.validate_authorization(packet, raw, auth, "pilot.example.org", 5432, "rahgard_pilot_fars", PILOT_MARKER, OWNER_KEY)) == 1
    with pytest.raises(geo.ApprovalBlocked):
        pilot.validate_authorization(packet, raw + b" ", auth, "pilot.example.org", 5432, "rahgard_pilot_fars", PILOT_MARKER, OWNER_KEY)
    altered = dict(packet)
    altered["reviewer"] = "Other reviewer"
    with pytest.raises(geo.ApprovalBlocked, match="differs"):
        pilot.validate_authorization(altered, raw, auth, "pilot.example.org", 5432, "rahgard_pilot_fars", PILOT_MARKER, OWNER_KEY)
    with pytest.raises(geo.ApprovalBlocked):
        pilot.validate_authorization(packet, raw, auth, "other.example.org", 5432, "rahgard_pilot_fars", PILOT_MARKER, OWNER_KEY)
    with pytest.raises(geo.ApprovalBlocked, match="signature"):
        pilot.validate_authorization(packet, raw, auth, "pilot.example.org", 5432, "rahgard_pilot_fars", PILOT_MARKER, b"x" * 32)
    with pytest.raises(geo.ApprovalBlocked):
        pilot.validate_authorization(packet, raw, auth, "pilot.example.org", 5432, "rahgard_pilot_fars", "b" * 48, OWNER_KEY)


def test_qa_authorization_is_rejected():
    packet, raw, auth = reviewed()
    packet["approval_reference"] = "QA_ONLY"
    raw = json.dumps(packet, ensure_ascii=False).encode()
    auth.update(approval_reference="QA_ONLY", decision_sha256=hashlib.sha256(raw).hexdigest())
    sign(auth)
    with pytest.raises(geo.ApprovalBlocked, match="QA authorization"):
        pilot.validate_authorization(packet, raw, auth, "pilot.example.org", 5432, "rahgard_pilot_fars", PILOT_MARKER, OWNER_KEY)


def test_expired_signed_target_authorization_is_rejected():
    packet, raw, auth = reviewed()
    auth["issued_at"] = (datetime.now(UTC) - timedelta(minutes=45)).isoformat()
    auth["expires_at"] = (datetime.now(UTC) - timedelta(minutes=15)).isoformat()
    sign(auth)
    with pytest.raises(geo.ApprovalBlocked, match="expired"):
        pilot.validate_authorization(packet, raw, auth, "pilot.example.org", 5432,
                                     "rahgard_pilot_fars", PILOT_MARKER, OWNER_KEY)


def test_missing_explicit_action_never_connects(monkeypatch):
    packet, raw, auth = reviewed()
    monkeypatch.setattr(pilot.psycopg, "connect", lambda **kwargs: pytest.fail("must not connect"))
    with pytest.raises(geo.ApprovalBlocked, match="explicit"):
        pilot.publish_private(packet, raw, auth, explicitly_authorized=False)


def test_authorization_provisioning_fails_closed_without_marked_target(monkeypatch):
    packet, raw, auth = reviewed()
    monkeypatch.setattr(authorizer.psycopg, "connect", lambda **kwargs: pytest.fail("must not connect"))
    with pytest.raises(geo.ApprovalBlocked, match="port is invalid|guard is incomplete"):
        authorizer.authorize_private(packet, raw, auth)


@pytest.mark.parametrize("host", ["/tmp/socket", "good.example,bad.example", " bad.example"])
def test_socket_and_multi_host_targets_fail_before_connection(monkeypatch, host):
    packet, raw, auth = reviewed()
    for name, value in {
        "RAHGARD_PILOT_PGHOST": host, "RAHGARD_PILOT_PGPORT": "5432",
        "RAHGARD_PILOT_DATABASE": "rahgard_pilot_fars", "RAHGARD_PILOT_DATABASE_MARKER": PILOT_MARKER,
        "RAHGARD_PILOT_GEO_PUBLISHER_PASSWORD": "test-only", "PGSSLROOTCERT": "ca.pem",
        "RAHGARD_PILOT_OWNER_AUTHORIZATION_KEY": OWNER_KEY.decode(),
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(pilot.Path, "is_file", lambda self: True)
    monkeypatch.setattr(pilot.psycopg, "connect", lambda **kwargs: pytest.fail("must not connect"))
    with pytest.raises(geo.ApprovalBlocked, match="guard"):
        pilot.publish_private(packet, raw, auth, explicitly_authorized=True)


def test_marked_pilot_identity_is_checked_before_any_promotion(monkeypatch):
    packet, raw, auth = reviewed()
    for name, value in {
        "RAHGARD_PILOT_PGHOST": "pilot.example.org", "RAHGARD_PILOT_PGPORT": "5432",
        "RAHGARD_PILOT_DATABASE": "rahgard_pilot_fars", "RAHGARD_PILOT_DATABASE_MARKER": "a" * 48,
        "RAHGARD_PILOT_GEO_PUBLISHER_PASSWORD": "test-only", "PGSSLROOTCERT": "ca.pem",
        "RAHGARD_PILOT_OWNER_AUTHORIZATION_KEY": OWNER_KEY.decode(),
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(pilot.Path, "is_file", lambda self: True)

    class Cursor:
        def fetchone(self):
            return {"name": "rahgard_pilot_fars", "role": pilot.ROLE, "session_role": pilot.ROLE, "version": 170000,
                    "privileged": False, "privileged_memberships": 0, "mutable_audit": False,
                    "owns_audit": False, "owns_destinations": False, "shared_audit_access": False,
                    "excessive_destination_privileges": False,
                    "function_allowed": True, "function_boundary": True,
                    "migration_hash": hashlib.sha256(pilot.MIGRATION_FILE.read_bytes()).hexdigest(),
                    "pilot_migration_hash": hashlib.sha256(pilot.PILOT_MIGRATION_FILE.read_bytes()).hexdigest(),
                    "marker_count": 1, "marker": "b" * 48}

    class Connection:
        def transaction(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, *args):
            return Cursor()

        def close(self):
            pass

    def connect(**kwargs):
        assert kwargs["sslmode"] == "verify-full"
        assert kwargs["user"] == pilot.ROLE
        return Connection()

    monkeypatch.setattr(pilot.psycopg, "connect", connect)
    with pytest.raises(geo.ApprovalBlocked, match="identity or marker"):
        pilot.publish_private(packet, raw, auth, explicitly_authorized=True)


def test_owner_signer_writes_target_bound_authorization_without_database(monkeypatch, tmp_path):
    packet, raw, _ = reviewed()
    decisions = tmp_path / "decisions.json"
    output = tmp_path / "authority.json"
    decisions.write_bytes(raw)
    monkeypatch.setenv("RAHGARD_PILOT_OWNER_AUTHORIZATION_KEY", OWNER_KEY.decode())
    monkeypatch.setenv("RAHGARD_PILOT_DATABASE_MARKER", PILOT_MARKER)
    monkeypatch.setattr(pilot.psycopg, "connect", lambda **kwargs: pytest.fail("must not connect"))
    monkeypatch.setattr(sys, "argv", ["sign", "--decisions", str(decisions), "--host", "pilot.example.org",
                                     "--port", "5432", "--database", "rahgard_pilot_fars",
                                     "--output", str(output), "--owner-authorizes-target"])
    assert signer.main() == 0
    authority = json.loads(output.read_text(encoding="utf-8"))
    assert len(pilot.validate_authorization(packet, raw, authority, "pilot.example.org", 5432,
                                            "rahgard_pilot_fars", PILOT_MARKER, OWNER_KEY)) == 1
    assert signer.main() == 2  # no overwrite of an existing authorization


@pytest.mark.parametrize(("changed", "mismatch"), [(True, False), (False, False), (True, True)])
def test_publication_delegates_to_database_and_verifies_visible_coordinates(monkeypatch, changed, mismatch):
    packet, raw, auth = reviewed()
    for name, value in {
        "RAHGARD_PILOT_PGHOST": "pilot.example.org", "RAHGARD_PILOT_PGPORT": "5432",
        "RAHGARD_PILOT_DATABASE": "rahgard_pilot_fars", "RAHGARD_PILOT_DATABASE_MARKER": PILOT_MARKER,
        "RAHGARD_PILOT_GEO_PUBLISHER_PASSWORD": "test-only", "PGSSLROOTCERT": "ca.pem",
        "RAHGARD_PILOT_OWNER_AUTHORIZATION_KEY": OWNER_KEY.decode(),
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(pilot.Path, "is_file", lambda self: True)

    class Cursor:
        def __init__(self, one=None, rows=None):
            self.one, self.rows = one, rows

        def fetchone(self):
            return self.one

        def fetchall(self):
            return self.rows

    class Connection:
        def __init__(self):
            self.calls = 0
            self.closed = False
            self.rolled_back = False

        def transaction(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.rolled_back = args[0] is not None
            return False

        def execute(self, query, *args):
            if "current_database()" in query:
                return Cursor(one={"name": "rahgard_pilot_fars", "role": pilot.ROLE, "session_role": pilot.ROLE, "version": 170000,
                                   "privileged": False, "privileged_memberships": 0, "mutable_audit": False,
                                   "owns_audit": False, "owns_destinations": False,
                                   "shared_audit_access": False,
                                   "excessive_destination_privileges": False, "function_allowed": True,
                                   "function_boundary": True,
                                   "migration_hash": hashlib.sha256(pilot.MIGRATION_FILE.read_bytes()).hexdigest(),
                                   "pilot_migration_hash": hashlib.sha256(pilot.PILOT_MIGRATION_FILE.read_bytes()).hexdigest(),
                                   "marker_count": 1, "marker": PILOT_MARKER})
            if "operations.apply_private_geo_approval" in query:
                self.calls += 1
                return Cursor(one={"activated": changed})
            if "production_destinations" in query:
                record = packet["records"][0]
                return Cursor(rows=[{"destination_key": record["destination_key"],
                                     "latitude": record["latitude"] + int(mismatch),
                                     "longitude": record["longitude"],
                                     "coordinate_role": record["coordinate_role"]}])
            pytest.fail("unexpected SQL")

        def close(self):
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(pilot.psycopg, "connect", lambda **kwargs: connection)
    if mismatch:
        with pytest.raises(geo.ApprovalBlocked, match="differs"):
            pilot.publish_private(packet, raw, auth, explicitly_authorized=True)
    else:
        result = pilot.publish_private(packet, raw, auth, explicitly_authorized=True)
        assert result["activated"] == int(changed)
    assert connection.calls == 1
    assert connection.rolled_back is mismatch
    assert connection.closed
