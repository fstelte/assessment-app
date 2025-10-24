from __future__ import annotations

from scaffold.apps.bia.models import Component, Consequences, ContextScope
from scaffold.apps.identity.models import User
from scaffold.extensions import db


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
