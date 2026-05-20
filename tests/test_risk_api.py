from __future__ import annotations

from datetime import date

from scaffold.apps.bia.models import Component, ContextScope
from scaffold.apps.csa.models import Control
from scaffold.apps.identity.models import Role, User, UserStatus
from scaffold.extensions import db


def _provision_admin(app) -> User:
    with app.app_context():
        role = Role()
        role.name = "admin"
        db.session.add(role)
        db.session.commit()

        admin = User()
        admin.email = "admin@example.com"
        admin.status = UserStatus.ACTIVE
        admin.set_password("Password123!")
        admin.roles.append(role)
        db.session.add(admin)
        db.session.commit()
        return admin


def _provision_component(app) -> dict[str, object]:
    with app.app_context():
        scope = ContextScope(name="Core Service", risk_assessment_human=True)
        component = Component(name="Payroll", context_scope=scope)
        db.session.add(scope)
        db.session.add(component)
        db.session.commit()
        return {
            "id": component.id,
            "name": component.name,
            "context": scope.name,
        }


def _provision_control(app) -> Control:
    with app.app_context():
        control = Control()
        control.domain = "ISO-27002-5.7"
        control.section = "5"
        control.description = "Ensure backups are encrypted"
        db.session.add(control)
        db.session.commit()
        return control


def _login(client, admin: User) -> None:
    response = client.post(
        "/auth/login",
        data={"email": admin.email, "password": "Password123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200


def test_risk_api_create_and_list(client, app):
    admin = _provision_admin(app)
    component = _provision_component(app)
    control = _provision_control(app)
    _login(client, admin)

    payload = {
        "title": "Payroll data breach",
        "description": "Sensitive payroll data could be exposed via misconfigured storage.",
        "impact": 4,
        "chance": "likely",
        "impact_areas": ["privacy", "operational"],
        "component_ids": [component["id"]],
        "treatment": "mitigate",
        "treatment_plan": "Roll out strict access controls",
        "treatment_due_date": date.today().isoformat(),
        "treatment_owner_id": admin.id,
        "discovered_on": date.today().isoformat(),
        "csa_control_ids": [control.id],
    }

    response = client.post("/api/risks", json=payload)
    assert response.status_code == 201
    body = response.get_json()
    assert body["success"] is True
    data = body["data"]
    assert data["score"] == 16
    assert data["impact"]["weight"] == 4
    assert data["chance"]["weight"] == 4
    assert data["components"][0]["name"] == component["name"]
    assert data["components"][0]["context"] == component["context"]
    assert data["component_ids"] == [component["id"]]
    assert data["treatment_owner"]["email"] == admin.email
    assert data["controls"][0]["domain"] == control.domain
    assert data["control_ids"] == [control.id]
    assert "privacy" in data["impact_areas"]

    list_response = client.get("/api/risks")
    assert list_response.status_code == 200
    list_body = list_response.get_json()
    assert list_body["success"] is True
    assert len(list_body["data"]) == 1
    assert list_body["data"][0]["title"] == "Payroll data breach"


def test_risk_api_requires_control_for_mitigate(client, app):
    admin = _provision_admin(app)
    component = _provision_component(app)
    _login(client, admin)

    payload = {
        "title": "Missing CSA control",
        "description": "Mitigation without control should fail",
        "impact": 3,
        "chance": 2,
        "impact_areas": ["operational"],
        "component_ids": [component["id"]],
        "treatment": "mitigate",
    }

    response = client.post("/api/risks", json=payload)
    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    assert "csa_control_ids" in body["errors"]


def test_risk_api_enforces_impact_range(client, app):
    admin = _provision_admin(app)
    component = _provision_component(app)
    _login(client, admin)

    payload = {
        "title": "Out of range impact",
        "description": "Impact weights must stay within 1-5",
        "impact": 9,
        "chance": 2,
        "impact_areas": ["regulatory"],
        "component_ids": [component["id"]],
        "treatment": "accept",
    }

    response = client.post("/api/risks", json=payload)
    assert response.status_code == 400
    body = response.get_json()
    assert body["success"] is False
    assert "impact" in body["errors"]


# ---------------------------------------------------------------------------
# T023: US4 – API ticket_links field and compatibility alias
# ---------------------------------------------------------------------------


def test_risk_api_create_with_ticket_links(client, app):
    """POST /api/risks with ticket_links persists both links."""
    admin = _provision_admin(app)
    component = _provision_component(app)
    control = _provision_control(app)
    _login(client, admin)

    payload = {
        "title": "Ticket links API risk",
        "description": "Testing plural ticket links via API.",
        "impact": 3,
        "chance": "possible",
        "impact_areas": ["operational"],
        "component_ids": [component["id"]],
        "treatment": "mitigate",
        "csa_control_ids": [control.id],
        "ticket_links": [
            {"label": "JIRA-300", "url": "https://jira.example.com/browse/JIRA-300"},
            {"label": "GH-99", "url": "https://github.com/org/repo/issues/99"},
        ],
    }

    resp = client.post("/api/risks", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()["data"]
    assert len(data["ticket_links"]) == 2
    labels = {tl["label"] for tl in data["ticket_links"]}
    assert "JIRA-300" in labels
    assert "GH-99" in labels
    # Compat alias points to first link
    assert data["ticket_url"] == "https://jira.example.com/browse/JIRA-300"


def test_risk_api_ticket_url_compat_alias(client, app):
    """POST /api/risks with legacy ticket_url creates one link labeled 'Ticket'."""
    admin = _provision_admin(app)
    component = _provision_component(app)
    control = _provision_control(app)
    _login(client, admin)

    payload = {
        "title": "Legacy ticket url risk",
        "description": "Backward compat test.",
        "impact": 2,
        "chance": "unlikely",
        "impact_areas": ["financial"],
        "component_ids": [component["id"]],
        "treatment": "mitigate",
        "csa_control_ids": [control.id],
        "ticket_url": "https://legacy.example.com/ticket/42",
    }

    resp = client.post("/api/risks", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()["data"]
    # One ticket_links entry created from ticket_url
    assert len(data["ticket_links"]) == 1
    assert data["ticket_links"][0]["url"] == "https://legacy.example.com/ticket/42"
    assert data["ticket_links"][0]["label"] == "Ticket"
    assert data["ticket_url"] == "https://legacy.example.com/ticket/42"


def test_risk_api_ticket_link_label_too_long(client, app):
    """ticket_links with label > 80 chars should return 400."""
    admin = _provision_admin(app)
    component = _provision_component(app)
    control = _provision_control(app)
    _login(client, admin)

    payload = {
        "title": "Long label via API",
        "description": "Should fail validation.",
        "impact": 2,
        "chance": "unlikely",
        "impact_areas": ["operational"],
        "component_ids": [component["id"]],
        "treatment": "mitigate",
        "csa_control_ids": [control.id],
        "ticket_links": [
            {"label": "X" * 81, "url": "https://example.com/ticket/1"},
        ],
    }

    resp = client.post("/api/risks", json=payload)
    assert resp.status_code == 400
    body = resp.get_json()
    assert "ticket_links" in body["errors"]
