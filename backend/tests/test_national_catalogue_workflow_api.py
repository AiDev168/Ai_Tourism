from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.auth import authenticated_user, require_authenticated_csrf
from app.core.config import Settings, get_settings
from app.main import app
from app.modules.identity.auth_service import AuthenticatedUser


def _settings():
    return Settings(_env_file=None, database_password="test-only", database_user="ai_tourism_app")


def test_archive_upload_requires_authenticated_user(monkeypatch):
    app.dependency_overrides[authenticated_user] = lambda: (_ for _ in ()).throw(HTTPException(401))
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    try:
        result = TestClient(app).post(
            "/api/v1/catalogue-review/archives",
            content=b"not-read",
            headers={"X-Archive-Filename": "data.zip"},
        )
        assert result.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_archive_upload_stages_only_after_auth_and_never_claims_publication(monkeypatch):
    user = AuthenticatedUser(UUID(int=1), None, UUID(int=2), "test")
    app.dependency_overrides[authenticated_user] = lambda: user
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    app.dependency_overrides[get_settings] = _settings
    staged = []
    monkeypatch.setattr(
        "app.api.catalogue_review.stage_archive",
        lambda data, actor, settings: staged.append((data, actor.user_id))
        or {"rows_staged": 2, "archive_sha256": "a" * 64},
    )
    try:
        result = TestClient(app).post(
            "/api/v1/catalogue-review/archives",
            content=b"zip-bytes",
            headers={"X-Archive-Filename": "data.zip", "Content-Type": "application/zip"},
        )
        assert result.status_code == 202
        assert result.json()["publication_approved"] is False
        assert result.json()["status"] == "needs_review"
        assert staged == [(b"zip-bytes", user.user_id)]
    finally:
        app.dependency_overrides.clear()


def test_identity_review_rejects_ambiguous_target_contract_before_database(monkeypatch):
    user = AuthenticatedUser(UUID(int=1), None, UUID(int=2), "test")
    app.dependency_overrides[authenticated_user] = lambda: user
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    app.dependency_overrides[get_settings] = _settings
    try:
        result = TestClient(app).post(
            "/api/v1/catalogue-review/candidates/00000000-0000-0000-0000-000000000001/decision",
            json={
                "decision": "accept",
                "identity_relation": "same_entity",
                "reason": "same named site",
                "policy_version": "v1",
            },
        )
        assert result.status_code == 422
        assert "error" in result.json()
    finally:
        app.dependency_overrides.clear()


def test_unresolved_is_not_implicitly_approved_as_a_new_identity():
    user = AuthenticatedUser(UUID(int=1), None, UUID(int=2), "test")
    app.dependency_overrides[authenticated_user] = lambda: user
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    app.dependency_overrides[get_settings] = _settings
    try:
        response = TestClient(app).post(
            "/api/v1/catalogue-review/candidates/00000000-0000-0000-0000-000000000001/decision",
            json={
                "decision": "accept",
                "identity_relation": "unresolved",
                "reason": "not enough identity evidence",
                "evidence_refs": ["archive:row-1"],
            },
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_new_identity_approval_requires_explicit_evidence():
    user = AuthenticatedUser(UUID(int=1), None, UUID(int=2), "test")
    app.dependency_overrides[authenticated_user] = lambda: user
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    app.dependency_overrides[get_settings] = _settings
    try:
        response = TestClient(app).post(
            "/api/v1/catalogue-review/candidates/00000000-0000-0000-0000-000000000001/decision",
            json={
                "decision": "approve_new_identity",
                "identity_relation": "unresolved",
                "reason": "reviewer explicitly designates a new identity",
                "evidence_refs": [],
            },
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_source_registration_requires_review_evidence_before_database_access(monkeypatch):
    user = AuthenticatedUser(UUID(int=1), None, UUID(int=2), "test")
    app.dependency_overrides[authenticated_user] = lambda: user
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    app.dependency_overrides[get_settings] = _settings
    monkeypatch.setattr(
        "app.api.catalogue_review._connect",
        lambda _settings: (_ for _ in ()).throw(AssertionError("database should not be reached")),
    )
    try:
        response = TestClient(app).post(
            "/api/v1/catalogue-review/sources/00000000-0000-0000-0000-000000000001/decision",
            json={"decision": "register_pending", "reason": "reviewed archive record", "evidence_refs": []},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_public_runtime_reviewer_can_read_source_queue_without_write_step_up(monkeypatch):
    user = AuthenticatedUser(UUID(int=1), None, UUID(int=2), "test")
    app.dependency_overrides[authenticated_user] = lambda: user
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, database_password="test-only", database_user="ai_tourism_app", app_env="staging"
    )

    class Cursor:
        def __init__(self):
            self.query = ""

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def execute(self, query, _params=None):
            self.query = query
            return self

        def fetchone(self):
            return {"allowed": True}

        def fetchall(self):
            return []

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return Cursor()

    monkeypatch.setattr("app.api.catalogue_review._connect", lambda _settings: Connection())
    monkeypatch.setattr(
        "app.api.catalogue_review.require_privileged_admin_step_up",
        lambda _env: (_ for _ in ()).throw(AssertionError("read-only queue must not require write step-up")),
    )
    try:
        response = TestClient(app).get("/api/v1/catalogue-review/sources")
        assert response.status_code == 200
        assert response.json() == {"items": [], "next_cursor": None}
    finally:
        app.dependency_overrides.clear()


def test_identity_approval_rejects_archive_reference_instead_of_real_field_evidence(monkeypatch):
    user = AuthenticatedUser(UUID(int=1), None, UUID(int=2), "test")
    app.dependency_overrides[authenticated_user] = lambda: user
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    app.dependency_overrides[get_settings] = _settings
    monkeypatch.setattr(
        "app.api.catalogue_review._connect",
        lambda _settings: (_ for _ in ()).throw(AssertionError("opaque evidence must fail before DB")),
    )
    try:
        response = TestClient(app).post(
            "/api/v1/catalogue-review/candidates/00000000-0000-0000-0000-000000000001/decision",
            json={
                "decision": "approve_new_identity", "identity_relation": "unresolved",
                "reason": "archive name only, direct evidence missing", "evidence_refs": ["archive:row-1"],
            },
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_candidate_evidence_requires_short_source_excerpt_and_timestamp(monkeypatch):
    user = AuthenticatedUser(UUID(int=1), None, UUID(int=2), "test")
    app.dependency_overrides[authenticated_user] = lambda: user
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    app.dependency_overrides[get_settings] = _settings
    monkeypatch.setattr(
        "app.api.catalogue_review._connect",
        lambda _settings: (_ for _ in ()).throw(AssertionError("invalid source evidence must not reach DB")),
    )
    try:
        response = TestClient(app).post(
            "/api/v1/catalogue-review/candidates/00000000-0000-0000-0000-000000000001/evidence",
            json={
                "source_id": 1, "field_key": "identity", "claim_value": "A site",
                "evidence_excerpt": "one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen twenty one twenty two twenty three twenty four twenty five twenty six",
                "retrieved_at": "2026-11-16T10:00:00Z",
            },
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_publication_requires_safe_coordinate_role_before_database(monkeypatch):
    user = AuthenticatedUser(UUID(int=1), None, UUID(int=2), "test")
    app.dependency_overrides[authenticated_user] = lambda: user
    app.dependency_overrides[require_authenticated_csrf] = lambda: None
    app.dependency_overrides[get_settings] = _settings
    monkeypatch.setattr(
        "app.api.catalogue_review._connect",
        lambda _settings: (_ for _ in ()).throw(AssertionError("bad coordinate role must not reach DB")),
    )
    try:
        response = TestClient(app).post(
            "/api/v1/catalogue-review/candidates/00000000-0000-0000-0000-000000000001/publish",
            json={"destination_key": "unesco-1262-sample", "coordinate_role": "entrance"},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()
