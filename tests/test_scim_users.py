"""Tests for SCIM User endpoints."""

from __future__ import annotations

import hashlib
import secrets

import pytest

from scaffold import create_app
from scaffold.config import Settings
from scaffold.extensions import db
from scaffold.apps.identity.models import User, UserStatus


_SCIM_MODULES = [
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
]


@pytest.fixture
def scim_app():
    settings = Settings(
        secret_key="test-secret",
        database_url="sqlite:///:memory:",
        session_cookie_secure=False,
        session_cookie_httponly=True,
        session_cookie_samesite="Lax",
        app_modules=_SCIM_MODULES,
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
def raw_token(scim_app):
    from scaffold.apps.scim.models import SCIMToken

    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    with scim_app.app_context():
        t = SCIMToken(token_hash=token_hash, is_active=True)
        db.session.add(t)
        db.session.commit()
    return raw


def _headers(token):
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Create user
# ---------------------------------------------------------------------------

def test_create_user(client, raw_token):
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
        "externalId": "oid-001",
        "userName": "jdoe@example.com",
        "name": {"givenName": "Jane", "familyName": "Doe"},
        "emails": [{"value": "jdoe@example.com", "primary": True}],
        "active": True,
    }
    resp = client.post("/scim/v2/Users", json=payload, headers=_headers(raw_token))
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["userName"] == "jdoe@example.com"
    assert data["active"] is True


def test_create_user_idempotent(client, raw_token):
    """POSTing the same externalId again updates and returns 200."""
    payload = {
        "externalId": "oid-002",
        "userName": "alice@example.com",
        "emails": [{"value": "alice@example.com", "primary": True}],
        "active": True,
    }
    client.post("/scim/v2/Users", json=payload, headers=_headers(raw_token))
    resp = client.post("/scim/v2/Users", json=payload, headers=_headers(raw_token))
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Get user
# ---------------------------------------------------------------------------

def test_get_user_by_oid(client, raw_token):
    payload = {
        "externalId": "oid-003",
        "userName": "bob@example.com",
        "emails": [{"value": "bob@example.com", "primary": True}],
        "active": True,
    }
    client.post("/scim/v2/Users", json=payload, headers=_headers(raw_token))
    resp = client.get("/scim/v2/Users/oid-003", headers=_headers(raw_token))
    assert resp.status_code == 200
    assert resp.get_json()["id"] == "oid-003"


def test_get_unknown_user_404(client, raw_token):
    resp = client.get("/scim/v2/Users/nonexistent", headers=_headers(raw_token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Filter users
# ---------------------------------------------------------------------------

def test_filter_by_username(client, raw_token):
    payload = {
        "externalId": "oid-004",
        "userName": "charlie@example.com",
        "emails": [{"value": "charlie@example.com", "primary": True}],
        "active": True,
    }
    client.post("/scim/v2/Users", json=payload, headers=_headers(raw_token))
    resp = client.get(
        '/scim/v2/Users?filter=userName eq "charlie@example.com"',
        headers=_headers(raw_token),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["totalResults"] == 1


def test_filter_by_external_id(client, raw_token):
    payload = {
        "externalId": "oid-005",
        "userName": "dave@example.com",
        "emails": [{"value": "dave@example.com", "primary": True}],
        "active": True,
    }
    client.post("/scim/v2/Users", json=payload, headers=_headers(raw_token))
    resp = client.get(
        '/scim/v2/Users?filter=externalId eq "oid-005"',
        headers=_headers(raw_token),
    )
    assert resp.status_code == 200
    assert resp.get_json()["totalResults"] == 1


# ---------------------------------------------------------------------------
# Disable user
# ---------------------------------------------------------------------------

def test_patch_user_disable(client, raw_token, scim_app):
    payload = {
        "externalId": "oid-006",
        "userName": "eve@example.com",
        "emails": [{"value": "eve@example.com", "primary": True}],
        "active": True,
    }
    client.post("/scim/v2/Users", json=payload, headers=_headers(raw_token))
    patch = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [{"op": "replace", "path": "active", "value": False}],
    }
    resp = client.patch("/scim/v2/Users/oid-006", json=patch, headers=_headers(raw_token))
    assert resp.status_code == 200
    assert resp.get_json()["active"] is False

    with scim_app.app_context():
        user = User.query.filter_by(azure_oid="oid-006").first()
        assert user.status == UserStatus.DISABLED


# ---------------------------------------------------------------------------
# Delete user
# ---------------------------------------------------------------------------

def test_delete_user(client, raw_token, scim_app):
    payload = {
        "externalId": "oid-007",
        "userName": "frank@example.com",
        "emails": [{"value": "frank@example.com", "primary": True}],
        "active": True,
    }
    client.post("/scim/v2/Users", json=payload, headers=_headers(raw_token))
    resp = client.delete("/scim/v2/Users/oid-007", headers=_headers(raw_token))
    assert resp.status_code == 204

    with scim_app.app_context():
        user = User.query.filter_by(azure_oid="oid-007").first()
        # Hard delete does NOT happen; row must still exist with DISABLED status
        assert user is not None
        assert user.status == UserStatus.DISABLED
