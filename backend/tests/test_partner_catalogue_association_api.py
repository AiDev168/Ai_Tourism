from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from app.api.auth import authenticated_user, require_authenticated_csrf
from app.core.config import Settings, get_settings
from app.main import app
from app.modules.identity.auth_service import AuthenticatedUser


class _Cursor:
    def __init__(self, *, published: bool):
        self.published = published
        self.row = None
        self.statements: list[str] = []

    def execute(self, query, params=()):
        self.statements.append(query)
        if "knowledge.production_destinations" in query:
            self.row = {"destination_id": params[0]} if self.published else None
        elif "INSERT INTO partner.service_destinations" in query:
            self.row = {
                "service_id": params[1],
                "destination_id": params[2],
                "relation_type": params[3],
                "status": "draft",
            }

    def fetchone(self):
        return self.row

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class _Connection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def _settings():
    return Settings(_env_file=None, database_password="test-only", database_user="ai_tourism_app")


def _client(monkeypatch, *, published: bool):
    user = AuthenticatedUser(UUID(int=7), None, UUID(int=8), "partner-test")
    cursor = _Cursor(published=published)
    app.dependency_overrides[authenticated_user] = lambda: user
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    app.dependency_overrides[get_settings] = _settings
    monkeypatch.setattr("app.api.partners._connection", lambda _settings: _Connection(cursor))
    return TestClient(app), cursor, user


def test_partner_cannot_link_unpublished_destination(monkeypatch):
    client, cursor, _ = _client(monkeypatch, published=False)
    try:
        response = client.post(
            "/api/v1/partners/organizations/00000000-0000-0000-0000-000000000010/services/00000000-0000-0000-0000-000000000011/destinations",
            json={"destination_id": 92, "relation_type": "at"},
        )
        assert response.status_code == 422
        assert not any("INSERT INTO partner.service_destinations" in query for query in cursor.statements)
    finally:
        app.dependency_overrides.clear()


def test_partner_destination_association_stays_draft_and_uses_published_identity(monkeypatch):
    client, cursor, _ = _client(monkeypatch, published=True)
    service_id = "00000000-0000-0000-0000-000000000011"
    organization_id = "00000000-0000-0000-0000-000000000010"
    try:
        response = client.post(
            f"/api/v1/partners/organizations/{organization_id}/services/{service_id}/destinations",
            json={"destination_id": 92, "relation_type": "serves", "evidence_note": "service area"},
        )
        assert response.status_code == 201
        assert response.json() == {
            "service_id": service_id,
            "destination_id": 92,
            "relation_type": "serves",
            "status": "draft",
        }
        assert any("knowledge.production_destinations" in query for query in cursor.statements)
        assert any("INSERT INTO partner.service_destinations" in query for query in cursor.statements)
    finally:
        app.dependency_overrides.clear()
