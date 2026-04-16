"""Tests for SCIM bearer token authentication."""

from __future__ import annotations

import hashlib
import secrets

import pytest

from scaffold import create_app
from scaffold.config import Settings
from scaffold.extensions import db
from scaffold.apps.identity.models import User, UserStatus


@pytest.fixture
def scim_app():
    settings = Settings(
        secret_key="test-secret",
        database_url="sqlite:///:memory:",
        session_cookie_secure=False,
        session_cookie_httponly=True,
        session_cookie_samesite="Lax",
        app_modules=[
            "scaffold.apps.auth.routes",
            "scaffold.apps.admin",
            "scaffold.apps.bia",
            "scaffold.apps.csa",
            "scaffold.apps.dpia",
            "scaffold.apps.risk.api",
            "scaffold.apps.risk.routes",
            "scaffold.apps.template",
            "scaffold.apps.ssp",
            "scaffold.apps.scim",
        ],
        password_login_enabled=False,
    )
    app = create_app(settings)
    app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(scim_app):
    return scim_app.test_client()


@pytest.fixture
def token(scim_app):
    from scaffold.apps.scim.models import SCIMToken

    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    with scim_app.app_context():
        t = SCIMToken(token_hash=token_hash, description="test", is_active=True)
        db.session.add(t)
        db.session.commit()
    return raw


def _auth_headers(raw_token: str) -> dict:
    return {"Authorization": f"Bearer {raw_token}"}


def test_no_auth_returns_401(client):
    resp = client.get("/scim/v2/ServiceProviderConfig")
    assert resp.status_code == 401


def test_wrong_token_returns_401(client, token):
    resp = client.get(
        "/scim/v2/ServiceProviderConfig",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert resp.status_code == 401


def test_valid_token_returns_200(client, token):
    resp = client.get(
        "/scim/v2/ServiceProviderConfig",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["patch"]["supported"] is True


def test_revoked_token_returns_401(scim_app, client, token):
    from scaffold.apps.scim.models import SCIMToken

    with scim_app.app_context():
        t = SCIMToken.query.first()
        t.is_active = False
        db.session.commit()

    resp = client.get(
        "/scim/v2/ServiceProviderConfig",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 401
