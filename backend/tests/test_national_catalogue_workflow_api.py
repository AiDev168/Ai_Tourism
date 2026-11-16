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
