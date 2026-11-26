from uuid import UUID

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.auth import authenticated_user
from app.core.config import Settings, get_settings
from app.main import app
from app.modules.identity.auth_service import AuthenticatedUser


class Cursor:
    def __init__(self, *, company=False, catalogue=False, overview=False):
        self.company, self.catalogue, self.overview = company, catalogue, overview
        self.row = None
        self.rows = []
        self.queries = []

    def execute(self, query, params=()):
        sql = " ".join(query.split())
        self.queries.append(sql)
        if "partner.has_platform_capability" in sql:
            self.row = {"company_review": self.company, "service_review": False,
                        "offer_review": False, "admin_overview": self.overview}
        elif "identity.has_catalogue_review_capability" in sql:
            self.row = {"candidate_review": self.catalogue, "source_review": False,
                        "catalogue_publish": False}
        elif "identity.has_ai_provider_admin_capability" in sql:
            self.row = {"ai_provider_admin": False}
        elif "current_setting('server_version_num')" in sql:
            self.row = {"api": "responding", "server_version_num": 170004, "migration_count": 27,
                        "latest_migration": "0026_platform_reviewer_mfa"}
        elif "FROM identity.users" in sql:
            self.row = {"count": 14}
        elif "FROM partner.organizations" in sql and "share_eligible_organizations" not in sql:
            self.row = {"total": 3, "awaiting_application": 1, "awaiting_verification": 1}
        elif "FROM partner.share_eligible_organizations" in sql:
            self.row = {"count": 0}
        elif "FROM knowledge.production_destinations" in sql:
            self.row = {"count": 0}
        elif "partner.admin_grant_counts" in sql:
            self.rows = [{"grant_domain": "partner", "capability": "organization_review", "active_grant_count": 2}]
        else:
            self.row = None
        return self

    def fetchone(self):
        return self.row

    def fetchall(self):
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class Connection:
    def __init__(self, cursor): self._cursor = cursor
    def cursor(self): return self._cursor
    def __enter__(self): return self
    def __exit__(self, *_): return False


def settings():
    return Settings(_env_file=None, database_password="test-only", database_user="ai_tourism_app")


def client(monkeypatch, cursor):
    user = AuthenticatedUser(UUID(int=7), None, UUID(int=8), "staging_invite")
    app.dependency_overrides[authenticated_user] = lambda: user
    app.dependency_overrides[get_settings] = settings
    monkeypatch.setattr("app.api.admin._connection", lambda _settings: Connection(cursor))
    return TestClient(app)


def test_unauthenticated_control_center_request_is_401():
    app.dependency_overrides.clear()
    def unauthenticated():
        raise HTTPException(status_code=401, detail="unauthenticated")
    app.dependency_overrides[authenticated_user] = unauthenticated
    try:
        with TestClient(app) as http:
            assert http.get("/api/v1/admin/capabilities").status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_company_reviewer_sees_only_company_governance(monkeypatch):
    cursor = Cursor(company=True)
    http = client(monkeypatch, cursor)
    try:
        response = http.get("/api/v1/admin/capabilities")
        assert response.status_code == 200
        body = response.json()
        assert body["sections"] == {"companies": True, "destinations": False, "users": False, "system": False, "ai_providers": False}
        assert body["ai_admin"] == {"authorized": False, "available": False, "scope": "server_not_configured"}
        assert body["privileged_writes_available"] is True
        assert all("identity.users" not in query for query in cursor.queries)
    finally:
        app.dependency_overrides.clear()


def test_public_staging_reports_privileged_writes_unavailable(monkeypatch):
    cursor = Cursor(company=True)
    http = client(monkeypatch, cursor)
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, app_env="staging", database_password="test-only",
        database_user="ai_tourism_app",
    )
    try:
        response = http.get("/api/v1/admin/capabilities")
        assert response.status_code == 200
        assert response.json()["privileged_writes_available"] is False
        assert response.json()["privileged_step_up"] == {
            "available": False, "required": True, "enrolled": False, "step_up_expires_at": None,
        }
    finally:
        app.dependency_overrides.clear()


def test_catalogue_reviewer_sees_destination_but_not_company_or_identity_data(monkeypatch):
    cursor = Cursor(catalogue=True)
    http = client(monkeypatch, cursor)
    try:
        response = http.get("/api/v1/admin/capabilities")
        assert response.status_code == 200
        body = response.json()
        assert body["sections"]["destinations"] is True
        assert body["sections"]["users"] is False
        assert body["sections"]["companies"] is False
        assert "identity.users" not in " ".join(cursor.queries)
    finally:
        app.dependency_overrides.clear()


def test_unprivileged_traveler_is_denied_and_grant_mutation_route_does_not_exist(monkeypatch):
    cursor = Cursor()
    http = client(monkeypatch, cursor)
    try:
        assert http.get("/api/v1/admin/capabilities").status_code == 403
        assert http.post("/api/v1/admin/grants", json={}).status_code == 404
        assert not any("INSERT INTO" in query or "UPDATE " in query for query in cursor.queries)
    finally:
        app.dependency_overrides.clear()


def test_owner_overview_is_aggregate_only_and_reports_unknown_backup_evidence(monkeypatch):
    cursor = Cursor(company=True, catalogue=True, overview=True)
    http = client(monkeypatch, cursor)
    try:
        response = http.get("/api/v1/admin/overview")
        assert response.status_code == 200
        body = response.json()
        assert body["users"] == {"account_count": 14}
        assert body["system"]["database"] == "connected"
        assert body["system"]["api"] == "responding"
        assert body["system"]["postgres_major"] == 17
        assert body["system"]["latest_migration"] == "0026_platform_reviewer_mfa"
        assert body["system"]["backup_evidence"] == "not_available_from_application"
        assert body["companies"]["share_eligible_count"] == 0
        assert "email" not in str(body).lower()
        assert "password" not in str(body).lower()
    finally:
        app.dependency_overrides.clear()


def test_owner_overview_is_not_available_to_company_reviewer(monkeypatch):
    cursor = Cursor(company=True)
    http = client(monkeypatch, cursor)
    try:
        response = http.get("/api/v1/admin/overview")
        assert response.status_code == 200
        body = response.json()
        assert "users" not in body and "system" not in body
        assert all("identity.users" not in query for query in cursor.queries)
    finally:
        app.dependency_overrides.clear()
