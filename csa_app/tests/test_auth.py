"""Basic smoke tests for authentication routes."""

from __future__ import annotations

from app.extensions import db
from app.models import MFASetting, UserStatus
from tests.factories import create_user


def test_register_page(client):
    response = client.get("/auth/register")
    assert response.status_code == 200


def test_login_requires_activation(client):
    create_user("pending@example.com", "Password123", status=UserStatus.PENDING)
    response = client.post(
        "/auth/login",
        data={"email": "pending@example.com", "password": "Password123"},
        follow_redirects=True,
    )
    assert b"nog niet geactiveerd" in response.data


def test_login_with_mfa_redirects_to_verification(client):
    user = create_user("mfa@example.com", "Password123")
    mfa = MFASetting(user=user, secret="JBSWY3DPEHPK3PXP", enabled=True)
    db.session.add(mfa)
    db.session.commit()

    response = client.post(
        "/auth/login",
        data={"email": "mfa@example.com", "password": "Password123"},
    )
    assert response.status_code == 302
    assert "/auth/mfa/enroll" in response.headers["Location"]


def test_registration_rejects_short_password(client):
    response = client.post(
        "/auth/register",
        data={
            "email": "short@example.com",
            "password": "short",
            "confirm_password": "short",
        },
        follow_redirects=True,
    )
    assert b"Wachtwoord moet minimaal 8 tekens lang zijn." in response.data