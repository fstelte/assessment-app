from __future__ import annotations

from scaffold.extensions import db
from scaffold.models import AuditLog
from scaffold.apps.identity.models import User, UserStatus


def _create_user(email: str = "listener@example.com") -> User:
    user = User()
    user.email = email
    user.status = UserStatus.ACTIVE
    user.set_password("Password123!")
    db.session.add(user)
    return user


def test_auto_audit_logs_user_creation(app):
    with app.app_context():
        _create_user()
        db.session.commit()

        event = AuditLog.query.filter_by(event_type="user.created").one()
        payload = event.payload or {}
        changes = payload.get("changes", {})
        assert changes.get("email", {}).get("new") == "listener@example.com"
        assert changes.get("status", {}).get("new") == "active"
        assert payload.get("operation") == "insert"


def test_auto_audit_logs_user_update(app):
    with app.app_context():
        user = _create_user("update-listener@example.com")
        db.session.commit()

        user.status = UserStatus.DISABLED
        db.session.commit()

        event = (
            AuditLog.query.filter_by(event_type="user.updated")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert event is not None
        changes = (event.payload or {}).get("changes", {})
        status_change = changes.get("status")
        assert status_change == {"old": "active", "new": "disabled"}
        assert (event.payload or {}).get("operation") == "update"


def test_auto_audit_logs_user_deletion(app):
    with app.app_context():
        user = _create_user("delete-listener@example.com")
        db.session.commit()
        db.session.delete(user)
        db.session.commit()

        event = (
            AuditLog.query.filter_by(event_type="user.deleted")
            .order_by(AuditLog.id.desc())
            .first()
        )
        assert event is not None
        payload = event.payload or {}
        changes = payload.get("changes", {})
        assert changes.get("email", {}).get("old") == "delete-listener@example.com"
        assert payload.get("operation") == "delete"
