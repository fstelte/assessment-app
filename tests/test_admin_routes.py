from __future__ import annotations

from datetime import UTC, datetime, timedelta

from scaffold.models import AuditLog
from scaffold.apps.identity.models import Role, User, UserStatus
from scaffold.core.audit import log_change_event, log_login_event
from scaffold.extensions import db


def test_admin_mfa_routes_use_shared_helpers(app, client):
    with app.app_context():
        admin_role = Role()
        admin_role.name = "admin"
        db.session.add(admin_role)
        db.session.commit()

        admin = User()
        admin.email = "admin@example.com"
        admin.status = UserStatus.ACTIVE
        admin.set_password("Password123!")
        admin.roles.append(admin_role)
        db.session.add(admin)
        db.session.commit()

    response = client.post(
        "/auth/login",
        data={"email": "admin@example.com", "password": "Password123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        target_user = User()
        target_user.email = "target@example.com"
        target_user.status = UserStatus.ACTIVE
        target_user.set_password("Password123!")
        db.session.add(target_user)
        db.session.commit()
        target_id = target_user.id

    manage_resp = client.get(f"/admin/users/{target_id}/mfa")
    assert manage_resp.status_code == 200
    assert "Manage MFA" in manage_resp.get_data(as_text=True)

    reset_resp = client.post(f"/admin/users/{target_id}/mfa/reset", follow_redirects=True)
    assert reset_resp.status_code == 200
    page = reset_resp.get_data(as_text=True)
    assert "MFA secret regenerated" in page

    with app.app_context():
        refreshed_user = db.session.get(User, target_id)
        assert refreshed_user.mfa_setting is not None
        assert refreshed_user.mfa_setting.enabled is True


def _provision_admin() -> tuple[Role, User]:
    admin_role = Role()
    admin_role.name = "admin"
    db.session.add(admin_role)
    db.session.commit()

    admin = User()
    admin.email = "admin@example.com"
    admin.status = UserStatus.ACTIVE
    admin.set_password("Password123!")
    admin.roles.append(admin_role)
    db.session.add(admin)
    db.session.commit()
    return admin_role, admin


def test_log_change_event_persists_audit_record(app):
    with app.app_context():
        _, admin = _provision_admin()

        event = log_change_event(
            action="update",
            entity_type="unit",
            entity_id="123",
            changes={"example": {"old": 1, "new": 2}},
            user=admin,
            ip_address="127.0.0.1",
            user_agent="pytest",
            commit=True,
        )

        assert event is not None
        stored = AuditLog.query.filter_by(event_type="unit.update").one()
        assert stored.event_type == "unit.update"
        assert stored.target_type == "unit"
        assert stored.target_id == "123"
        assert stored.payload == {"changes": {"example": {"old": 1, "new": 2}}}
        assert stored.actor_ip == "127.0.0.1"
        assert stored.actor_user_agent == "pytest"
        assert stored.actor_id == admin.id


def test_log_login_event_records_metadata(app):
    with app.app_context():
        _, admin = _provision_admin()

        event = log_login_event(
            "success",
            user=admin,
            ip_address="192.168.1.10",
            user_agent="pytest-client",
            metadata={"method": "password"},
            commit=True,
        )

        assert event is not None
        stored = AuditLog.query.filter_by(event_type="auth.login.success").one()
        assert stored.actor_id == admin.id
        assert stored.actor_ip == "192.168.1.10"
        assert stored.payload.get("status") == "success"
        assert stored.payload.get("method") == "password"


def test_admin_audit_trail_listing(app, client):
    with app.app_context():
        _, admin = _provision_admin()

    response = client.post(
        "/auth/login",
        data={"email": "admin@example.com", "password": "Password123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200

    with app.app_context():
        log_login_event(
            "success",
            user=admin,
            ip_address="10.0.0.1",
            user_agent="pytest-client",
            commit=True,
        )

    today = datetime.now(UTC).date().isoformat()
    page = client.get(
        f"/admin/audit-trail?event_type=auth.login.success&actor=admin@example.com&start_date={today}"
    )
    assert page.status_code == 200
    content = page.get_data(as_text=True)
    assert "auth.login.success" in content
    assert "pytest-client" in content


def test_admin_audit_trail_date_filter_excludes_old_events(app, client):
    with app.app_context():
        _, admin = _provision_admin()

    client.post(
        "/auth/login",
        data={"email": "admin@example.com", "password": "Password123!"},
        follow_redirects=True,
    )

    with app.app_context():
        old_event = log_login_event(
            "success",
            user=admin,
            metadata={"marker": "old"},
            commit=True,
        )
        old_event.created_at = datetime.now(UTC) - timedelta(days=5)
        log_login_event(
            "success",
            user=admin,
            metadata={"marker": "recent"},
            commit=True,
        )
        db.session.commit()

    today = datetime.now(UTC).date().isoformat()
    page = client.get(f"/admin/audit-trail?start_date={today}&event_type=auth.login.success")
    assert page.status_code == 200
    body = page.get_data(as_text=True)
    assert '"recent"' in body
    assert '"old"' not in body


def test_non_admin_cannot_access_audit_trail(app, client):
    with app.app_context():
        user = User()
        user.email = "member@example.com"
        user.status = UserStatus.ACTIVE
        user.set_password("Password123!")
        db.session.add(user)
        db.session.commit()

    client.post(
        "/auth/login",
        data={"email": "member@example.com", "password": "Password123!"},
        follow_redirects=True,
    )

    resp = client.get("/admin/audit-trail")
    assert resp.status_code == 403


def test_user_activation_records_audit_event(app, client):
    with app.app_context():
        _, admin = _provision_admin()
        target = User()
        target.email = "target@example.com"
        target.status = UserStatus.PENDING
        target.set_password("Password123!")
        db.session.add(target)
        db.session.commit()
        target_id = target.id

    client.post(
        "/auth/login",
        data={"email": "admin@example.com", "password": "Password123!"},
        follow_redirects=True,
    )

    resp = client.post(f"/admin/users/{target_id}/activate", follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        events = AuditLog.query.filter_by(event_type="user_activated").all()
        assert events
        assert any(event.entity_id == str(target_id) for event in events)


def test_role_assignment_records_audit_event(app, client):
    with app.app_context():
        _, admin = _provision_admin()
        auditor_role = Role()
        auditor_role.name = "auditor"
        db.session.add(auditor_role)
        target = User()
        target.email = "subject@example.com"
        target.status = UserStatus.ACTIVE
        target.set_password("Password123!")
        db.session.add(target)
        db.session.commit()
        target_id = target.id

    client.post(
        "/auth/login",
        data={"email": "admin@example.com", "password": "Password123!"},
        follow_redirects=True,
    )

    resp = client.post(
        f"/admin/users/{target_id}/roles",
        data={"role": "auditor"},
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        events = AuditLog.query.filter_by(event_type="user_role_assigned").all()
        assert events
        assert any(event.details.get("role") == "auditor" and event.entity_id == str(target_id) for event in events)
