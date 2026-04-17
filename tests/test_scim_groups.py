"""Tests for SCIM Group endpoints and role assignment."""

from __future__ import annotations

import hashlib
import secrets

import pytest

from scaffold import create_app
from scaffold.config import Settings
from scaffold.extensions import db
from scaffold.apps.identity.models import AADGroupMapping, Role, User, UserStatus


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


def _create_user(scim_app, oid: str, email: str) -> User:
    with scim_app.app_context():
        user = User(
            email=email,
            password_hash=secrets.token_hex(16),
            azure_oid=oid,
            aad_upn=email,
            status=UserStatus.ACTIVE,
        )
        db.session.add(user)
        db.session.commit()
    return user


def _create_role_and_mapping(scim_app, group_oid: str, role_name: str) -> None:
    with scim_app.app_context():
        role = Role.query.filter_by(name=role_name).first()
        if role is None:
            role = Role(name=role_name, description=role_name)
            db.session.add(role)
            db.session.flush()
        mapping = AADGroupMapping(group_object_id=group_oid, role_id=role.id)
        db.session.add(mapping)
        db.session.commit()


# ---------------------------------------------------------------------------
# Create group
# ---------------------------------------------------------------------------

def test_create_group(client, raw_token):
    payload = {
        "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
        "id": "grp-001",
        "displayName": "Managers",
    }
    resp = client.post("/scim/v2/Groups", json=payload, headers=_headers(raw_token))
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["id"] == "grp-001"
    assert data["displayName"] == "Managers"


def test_create_group_idempotent(client, raw_token):
    payload = {
        "id": "grp-002",
        "displayName": "Owners",
    }
    client.post("/scim/v2/Groups", json=payload, headers=_headers(raw_token))
    resp = client.post("/scim/v2/Groups", json=payload, headers=_headers(raw_token))
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Add member → role assigned
# ---------------------------------------------------------------------------

def test_patch_add_member_assigns_role(client, raw_token, scim_app):
    _create_user(scim_app, "user-oid-1", "member@example.com")
    _create_role_and_mapping(scim_app, "grp-003", "manager")

    patch = {
        "schemas": ["urn:ietf:params:scim:api:messages:2.0:PatchOp"],
        "Operations": [
            {"op": "add", "path": "members", "value": [{"value": "user-oid-1"}]}
        ],
    }
    resp = client.patch("/scim/v2/Groups/grp-003", json=patch, headers=_headers(raw_token))
    assert resp.status_code == 200

    with scim_app.app_context():
        user = User.query.filter_by(azure_oid="user-oid-1").first()
        assert user.has_role("manager")


# ---------------------------------------------------------------------------
# Remove member → role revoked
# ---------------------------------------------------------------------------

def test_patch_remove_member_revokes_role(client, raw_token, scim_app):
    _create_user(scim_app, "user-oid-2", "to-remove@example.com")
    _create_role_and_mapping(scim_app, "grp-004", "manager")

    # First add the member
    add_patch = {
        "Operations": [
            {"op": "add", "path": "members", "value": [{"value": "user-oid-2"}]}
        ]
    }
    client.patch("/scim/v2/Groups/grp-004", json=add_patch, headers=_headers(raw_token))

    # Now remove them using the Entra path filter syntax
    remove_patch = {
        "Operations": [
            {"op": "remove", "path": 'members[value eq "user-oid-2"]'}
        ]
    }
    resp = client.patch("/scim/v2/Groups/grp-004", json=remove_patch, headers=_headers(raw_token))
    assert resp.status_code == 200

    with scim_app.app_context():
        user = User.query.filter_by(azure_oid="user-oid-2").first()
        assert not user.has_role("manager")


# ---------------------------------------------------------------------------
# Delete group
# ---------------------------------------------------------------------------

def test_delete_group(client, raw_token, scim_app):
    _create_role_and_mapping(scim_app, "grp-005", "manager")

    resp = client.delete("/scim/v2/Groups/grp-005", headers=_headers(raw_token))
    assert resp.status_code == 204

    with scim_app.app_context():
        mapping = AADGroupMapping.query.filter_by(group_object_id="grp-005").first()
        assert mapping is None


def test_delete_unknown_group_404(client, raw_token):
    resp = client.delete("/scim/v2/Groups/nonexistent", headers=_headers(raw_token))
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Filter groups
# ---------------------------------------------------------------------------

def test_filter_groups_by_external_id(client, raw_token):
    payload = {"id": "grp-006", "displayName": "Auditors"}
    client.post("/scim/v2/Groups", json=payload, headers=_headers(raw_token))
    resp = client.get(
        '/scim/v2/Groups?filter=externalId eq "grp-006"',
        headers=_headers(raw_token),
    )
    assert resp.status_code == 200
    assert resp.get_json()["totalResults"] == 1
