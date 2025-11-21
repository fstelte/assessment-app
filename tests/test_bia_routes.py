from __future__ import annotations

from scaffold.apps.bia.models import Component, Consequences, ContextScope
from scaffold.apps.identity.models import ROLE_ADMIN, User, UserStatus, ensure_default_roles
from scaffold.extensions import db
from scaffold.models import AuditLog


def test_bia_detail_shows_component_summary(app, client, login):
    with app.app_context():
        user = User.find_by_email("user@example.com")
        context = ContextScope(name="Disaster Recovery", author=user)
        component = Component(
            name="Backup Platform",
            info_owner="Operations",
            user_type="Internal",
            context_scope=context,
        )
        consequence = Consequences(
            component=component,
            consequence_category="Operational",
            security_property="confidentiality",
            consequence_worstcase="major",
            justification_worstcase="High exposure",
            consequence_realisticcase="major",
            justification_realisticcase="Backups contain secrets",
        )
        db.session.add(context)
        db.session.add(component)
        db.session.add(consequence)
        db.session.commit()
        context_id = context.id

    response = client.get(f"/bia/{context_id}")
    assert response.status_code == 200
    body = response.data.decode()
    assert "Backup Platform" in body
    assert "Major" in body
    assert "Components" in body


def test_assigning_bia_owner_records_audit_event(app, client, login):
    with app.app_context():
        ensure_default_roles()
        admin = User.find_by_email("user@example.com")
        assert admin is not None
        admin.ensure_role(ROLE_ADMIN)

        target = User(
            email="owner@example.com",
            first_name="Case",
            last_name="Worker",
            status=UserStatus.ACTIVE,
        )
        target.set_password("Password123!")
        context = ContextScope(name="Continuity Plan")
        db.session.add_all([admin, target, context])
        db.session.commit()

        context_id = context.id
        admin_id = admin.id
        target_id = target.id
        target_name = target.full_name

    response = client.post(
        f"/bia/item/{context_id}/owner",
        data={"owner_id": str(target_id)},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        events = AuditLog.query.filter_by(target_type="bia.context_scope").all()
        assert len(events) == 1
        event = events[0]
        assert event.event_type == "bia.context_scope.owner_updated"
        assert event.target_id == str(context_id)
        assert event.actor_id == admin_id
        payload = event.payload or {}
        changes = payload.get("changes") or {}
        assert changes.get("author_id", {}).get("new") == target_id
        assert changes.get("author_name", {}).get("new") == target_name
