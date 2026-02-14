from __future__ import annotations

from scaffold.apps.bia.models import (
    AuthenticationMethod,
    AvailabilityRequirements,
    Component,
    ComponentEnvironment,
    Consequences,
    ContextScope,
)
from scaffold.apps.identity.models import ROLE_ADMIN, User, UserStatus, ensure_default_roles
from scaffold.extensions import db
from scaffold.models import AuditLog
from werkzeug.datastructures import MultiDict


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


def test_updating_bia_owner_does_not_change_security_manager(app, client, login):
    with app.app_context():
        ensure_default_roles()
        admin = User.find_by_email("user@example.com")
        assert admin is not None
        admin.ensure_role(ROLE_ADMIN)

        target = User(
            email="owner2@example.com",
            first_name="Morgan",
            last_name="Lead",
            status=UserStatus.ACTIVE,
        )
        target.set_password("Password123!")
        context = ContextScope(
            name="Continuity Plan Two",
            security_manager="Existing Manager",
        )
        db.session.add_all([admin, target, context])
        db.session.commit()

        context_id = context.id
        target_id = target.id

    response = client.post(
        f"/bia/item/{context_id}/owner",
        data={"owner_id": str(target_id)},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        updated = ContextScope.query.get(context_id)
        assert updated is not None
        assert updated.responsible == target.full_name
        assert updated.security_manager == "Existing Manager"

    response = client.post(
        f"/bia/item/{context_id}/owner",
        data={"owner_id": ""},
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        cleared = ContextScope.query.get(context_id)
        assert cleared is not None
        assert cleared.responsible is None
        assert cleared.security_manager == "Existing Manager"


def test_export_authentication_overview_uses_environment_method(app, client, login):
    with app.app_context():
        method = AuthenticationMethod(slug="central-idp", label_en="Central IdP", label_nl="Centraal IdP")
        context = ContextScope(name="Continuity Plan Three")
        component = Component(name="Access Portal", context_scope=context)
        environment = ComponentEnvironment(
            environment_type="production",
            is_enabled=True,
            authentication_method=method,
        )
        component.environments.append(environment)
        db.session.add_all([method, context, component])
        db.session.commit()

    response = client.get("/bia/export_authentication_overview")
    assert response.status_code == 200
    body = response.data.decode()
    assert "Access Portal" in body
    assert "Central IdP" in body
    assert "All components have an authentication type assigned." in body


def test_components_page_exposes_action_buttons(app, client, login):
    with app.app_context():
        context = ContextScope(name="Continuity Plan Four")
        component = Component(name="Messaging Gateway", context_scope=context)
        db.session.add_all([context, component])
        db.session.commit()
        if "dpia.start_from_component" not in app.view_functions:
            app.add_url_rule(
                "/dpia/mock/start/<int:component_id>",
                "dpia.start_from_component",
                lambda component_id: "",
            )
        if "dpia.dashboard" not in app.view_functions:
            app.add_url_rule("/dpia/mock/dashboard", "dpia.dashboard", lambda: "")

    response = client.get("/bia/components")
    assert response.status_code == 200
    body = response.data.decode()
    assert f"/bia/component/{component.id}/availability?return_to=%2Fbia%2Fcomponents" in body
    assert f"/bia/component/{component.id}/consequences/new?return_to=%2Fbia%2Fcomponents" in body
    assert 'data-dpia-action="start"' in body
    assert 'id="component-query"' in body
    assert 'table-components' in body
    assert 'btn-icon' in body
    assert f"/bia/component/{component.id}/edit" in body


def test_edit_component_view_updates_component(app, client, login):
    with app.app_context():
        context = ContextScope(name="Continuity Plan Five")
        component = Component(name="Legacy Portal", context_scope=context)
        db.session.add_all([context, component])
        db.session.commit()
        component_id = component.id
        context_id = context.id

    response = client.get(f"/bia/component/{component_id}/edit")
    assert response.status_code == 200
    assert "Legacy Portal" in response.data.decode()

    data = {
        "bia_id": str(context_id),
        "name": "Modern Portal",
        "info_type": "PII",
        "info_owner": "Security",
        "user_type": "External",
        "dependencies_others": "CRM",
        "description": "Updated description",
    }
    environment_order = ("development", "test", "acceptance", "production")
    for idx, env in enumerate(environment_order):
        data[f"environments-{idx}-environment_type"] = env
        data[f"environments-{idx}-authentication_method"] = ""

    response = client.post(
        f"/bia/component/{component_id}/edit",
        data=data,
        follow_redirects=False,
    )
    assert response.status_code == 302

    with app.app_context():
        updated = Component.query.get(component_id)
        assert updated is not None
        assert updated.name == "Modern Portal"
        assert updated.description == "Updated description"


def test_manage_component_availability_updates_requirements(app, client, login):
    with app.app_context():
        context = ContextScope(name="Continuity Plan Six")
        component = Component(name="Batch Processor", context_scope=context)
        db.session.add_all([context, component])
        db.session.commit()
        component_id = component.id

    response = client.get(f"/bia/component/{component_id}/availability")
    assert response.status_code == 200
    assert "Save requirements" in response.data.decode()

    post_response = client.post(
        f"/bia/component/{component_id}/availability",
        data={
            "mtd": "24h",
            "rto": "8h",
            "rpo": "30m",
            "masl": "Minimal core services",
        },
        follow_redirects=False,
    )
    assert post_response.status_code == 302

    with app.app_context():
        availability = AvailabilityRequirements.query.filter_by(component_id=component_id).first()
        assert availability is not None
        assert availability.mtd == "24h"
        assert availability.rto == "8h"
        assert availability.rpo == "30m"
        assert availability.masl == "Minimal core services"


def test_manage_component_consequence_creates_multiple_entries(app, client, login):
    with app.app_context():
        context = ContextScope(name="Continuity Plan Seven")
        component = Component(name="Messaging Fabric", context_scope=context)
        db.session.add_all([context, component])
        db.session.commit()
        component_id = component.id

    response = client.get(f"/bia/component/{component_id}/consequences/new")
    assert response.status_code == 200
    assert "Add consequences" in response.data.decode()

    payload = MultiDict(
        [
            ("consequence_category", "financial"),
            ("consequence_category", "operational"),
            ("security_property", "confidentiality"),
            ("consequence_worstcase", "major"),
            ("justification_worstcase", "Critical vendor exposure"),
            ("consequence_realisticcase", "moderate"),
            ("justification_realisticcase", "Impacts day-to-day workflows"),
        ]
    )

    post_response = client.post(
        f"/bia/component/{component_id}/consequences/new",
        data=payload,
        follow_redirects=False,
    )
    assert post_response.status_code == 302
    assert post_response.headers["Location"].endswith(f"/bia/consequences/{component_id}")

    with app.app_context():
        stored = Consequences.query.filter_by(component_id=component_id).all()
        assert len(stored) == 2
        assert {row.consequence_category for row in stored} == {"financial", "operational"}
        for row in stored:
            assert row.security_property == "confidentiality"


def test_export_all_dependencies_returns_html(app, client, login):
    with app.app_context():
        context = ContextScope(name="Global Dependency Test")
        component = Component(
            name="Global Component",
            context_scope=context,
            dependencies_others="Global Dep 1\nGlobal Dep 2",
        )
        db.session.add_all([context, component])
        db.session.commit()

    response = client.get("/bia/export_all_dependencies")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/html")
    assert response.headers["Content-Disposition"].startswith("attachment; filename=BIA_Dependencies_")

    content = response.data.decode("utf-8")
    assert "Global Dependency Test" in content
    assert "Global Component" in content
    assert "Global Dep 1" in content
    assert "Global Dep 2" in content

