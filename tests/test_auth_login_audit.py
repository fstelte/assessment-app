from __future__ import annotations

from flask import session
from flask_login import logout_user

from scaffold.apps.auth.flow import finalise_login
from scaffold.apps.identity.models import User, UserStatus
from scaffold.extensions import db
from scaffold.models import AuditLog


def _make_user(email: str) -> User:
    user = User()
    user.email = email
    user.status = UserStatus.ACTIVE
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


def test_password_login_records_audit_entry(app, client):
    with app.app_context():
        user = _make_user("login-audit@example.com")

    response = client.post(
        "/auth/login",
        data={"email": "login-audit@example.com", "password": "Password123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        record = (
            AuditLog.query.filter_by(event_type="auth.login.success")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert record is not None
        assert record.actor_id == user.id
        assert record.actor_ip == "127.0.0.1"
        assert record.payload.get("method") == "password"
        assert record.payload.get("remember") is False
        assert record.payload.get("status") == "success"
        assert record.payload.get("mfa_enrolled") is False
        assert "login_time" in record.payload


def test_finalise_login_includes_request_metadata(app):
    with app.app_context():
        user = _make_user("saml-audit@example.com")

        with app.test_request_context(
            "/auth/saml/callback",
            environ_base={"REMOTE_ADDR": "10.1.2.3"},
            headers={"User-Agent": "pytest-agent"},
        ):
            finalise_login(
                user,
                remember=True,
                method="saml",
                metadata={"provider": "saml", "custom": "value"},
            )

            record = (
                AuditLog.query.filter_by(event_type="auth.login.success")
                .order_by(AuditLog.id.desc())
                .first()
            )
            assert record is not None
            assert record.actor_id == user.id
            assert record.actor_ip == "10.1.2.3"
            assert record.actor_user_agent == "pytest-agent"
            payload = record.payload or {}
            assert payload.get("method") == "saml"
            assert payload.get("remember") is True
            assert payload.get("provider") == "saml"
            assert payload.get("custom") == "value"
            assert payload.get("status") == "success"
            assert payload.get("mfa_enrolled") is False
            assert "login_time" in payload

            assert session["session_fingerprint"]
            assert session["login_time"]
            assert session["last_activity"]

            logout_user()
*** End File