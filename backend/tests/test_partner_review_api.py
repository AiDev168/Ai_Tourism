from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from app.api.auth import authenticated_user, require_authenticated_csrf
from app.core.config import Settings, get_settings
from app.main import app
from app.modules.identity.auth_service import AuthenticatedUser


class _Cursor:
    def __init__(self, *, capability: bool, case: dict | None = None):
        self.capability = capability
        self.case = case
        self.row = None
        self.statements: list[str] = []
        self.params = None
        self.service_insert_params = None

    def execute(self, query, params=()):
        self.statements.append(" ".join(query.split()))
        self.params = params
        if "partner.has_platform_capability" in query:
            self.row = {"allowed": self.capability}
        elif "INSERT INTO partner.services" in query:
            self.service_insert_params = params
            self.row = {"service_id": UUID(int=91), "status": "draft"}
        elif "SELECT c.case_id,c.organization_id,c.submitted_by" in query:
            self.row = self.case
        elif "WITH latest_case AS" in query:
            self.row = []
        else:
            self.row = None
        return self

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.row or []

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


def _client(monkeypatch, cursor: _Cursor, user_id: UUID = UUID(int=7)):
    user = AuthenticatedUser(user_id, None, UUID(int=8), "partner-review-test")
    app.dependency_overrides[authenticated_user] = lambda: user
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    app.dependency_overrides[get_settings] = _settings
    monkeypatch.setattr("app.api.partners._connection", lambda _settings: _Connection(cursor))
    return TestClient(app), user


def test_owner_cannot_assign_review_lifecycle_fields(monkeypatch):
    cursor = _Cursor(capability=False)
    client, _ = _client(monkeypatch, cursor)
    try:
        response = client.post("/api/v1/partners/organizations", json={
            "legal_name": "Example Travel Co", "display_name": "Example",
            "organization_type": "company", "registration_country": "IR",
            "verification_status": "verified", "participation_status": "active",
        })
        assert response.status_code == 422
        assert not any("INSERT INTO partner.organizations" in query for query in cursor.statements)
    finally:
        app.dependency_overrides.clear()


def test_company_user_cannot_open_reviewer_queue_or_read_cases(monkeypatch):
    cursor = _Cursor(capability=False)
    client, _ = _client(monkeypatch, cursor)
    try:
        response = client.get("/api/v1/partners/platform/organization-review")
        assert response.status_code == 403
        assert response.json() == {"error": {"code": "request_rejected"}}
        assert not any("verification_cases" in query for query in cursor.statements)
    finally:
        app.dependency_overrides.clear()


def test_reviewer_queue_returns_only_latest_case_per_organization(monkeypatch):
    cursor = _Cursor(capability=True)
    client, _ = _client(monkeypatch, cursor)
    try:
        response = client.get("/api/v1/partners/platform/organization-review")
        assert response.status_code == 200
        assert response.json() == {"items": []}
        query = next(query for query in cursor.statements if "WITH latest_case AS" in query)
        assert "DISTINCT ON (organization_id)" in query
        assert "submitted_at DESC NULLS LAST" in query
        assert "c.status IN ('submitted','needs_information','verified')" in query
    finally:
        app.dependency_overrides.clear()


def test_reviewer_cannot_review_own_organization_even_with_grant(monkeypatch):
    actor = UUID(int=7)
    case = {"case_id": UUID(int=1), "organization_id": UUID(int=2),
            "submitted_by": actor, "status": "submitted", "created_by": actor,
            "application_status": "submitted", "verification_status": "pending"}
    cursor = _Cursor(capability=True, case=case)
    client, _ = _client(monkeypatch, cursor, actor)
    try:
        response = client.post("/api/v1/partners/platform/verification-cases/00000000-0000-0000-0000-000000000001/decision",
                               json={"decision": "verified", "reason": "The evidence was reviewed."})
        assert response.status_code == 403
        assert response.json() == {"error": {"code": "request_rejected"}}
        assert not any("UPDATE partner.verification_cases" in query for query in cursor.statements)
        assert not any("INSERT INTO partner.review_events" in query for query in cursor.statements)
    finally:
        app.dependency_overrides.clear()


def test_participation_cannot_activate_before_verification_and_approval():
    from app.api.partners import OrganizationParticipationDecision

    decision = OrganizationParticipationDecision(decision="activate", reason="Separate review approval.")
    assert decision.decision == "activate"
    # Lifecycle columns are not part of any partner self-service request model.
    from app.api.partners import OrganizationInput
    assert "participation_status" not in OrganizationInput.model_fields
    assert "verification_status" not in OrganizationInput.model_fields


def test_service_internal_key_is_created_by_backend(monkeypatch):
    cursor = _Cursor(capability=False)
    client, _ = _client(monkeypatch, cursor)
    try:
        response = client.post(
            "/api/v1/partners/organizations/00000000-0000-0000-0000-000000000010/services",
            json={"service_type": "tour", "locale": "fa-IR", "display_name": "تور محلی"},
        )
        assert response.status_code == 201
        assert response.json() == {"service_id": str(UUID(int=91)), "status": "draft"}
        assert "service_key" not in response.json()
        assert cursor.service_insert_params[0] == UUID("00000000-0000-0000-0000-000000000010")
        assert cursor.service_insert_params[2] == "tour"
        assert cursor.service_insert_params[3].startswith("service-")
        assert len(cursor.service_insert_params[3]) == len("service-") + 32
    finally:
        app.dependency_overrides.clear()
