"""Security-focused tests for admin MFA management."""

from __future__ import annotations

from app.extensions import db
from app.models import User
from tests.factories import create_user


def login(client, email: str, password: str):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def test_admin_mfa_requires_authentication(client):
    target = create_user("target@example.com", "Password123")
    response = client.get(f"/admin/users/{target.id}/mfa")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_admin_mfa_requires_admin_role(client):
    target = create_user("target2@example.com", "Password123")
    user = create_user("user@example.com", "Password123")

    login(client, "user@example.com", "Password123")
    response = client.get(f"/admin/users/{target.id}/mfa")
    assert response.status_code == 403


def test_admin_can_enable_mfa_for_user(client):
    target = create_user("target3@example.com", "Password123")
    admin = create_user("admin@example.com", "Password123", roles=["admin"])

    login(client, "admin@example.com", "Password123")
    response = client.post(
        f"/admin/users/{target.id}/mfa",
        data={"action": "enable"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Huidig secret" in response.data

    updated_user: User | None = db.session.get(User, target.id)
    assert updated_user is not None
    assert updated_user.mfa_setting is not None
    assert updated_user.mfa_setting.enabled is True
    assert updated_user.mfa_setting.secret is not None