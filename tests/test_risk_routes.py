from __future__ import annotations

from datetime import date

import pytest

from scaffold.apps.bia.models import Component, ContextScope
from scaffold.apps.csa.models import Control
from scaffold.apps.identity.models import ROLE_ADMIN, Role, User, UserStatus
from scaffold.apps.risk.models import (
    Risk,
    RiskChance,
    RiskImpact,
    RiskImpactArea,
    RiskImpactAreaLink,
    RiskSeverity,
    RiskSeverityThreshold,
    RiskTreatmentOption,
)
from scaffold.extensions import db

_PASSWORD = "Password123!"


@pytest.fixture
def admin_user(app):
    with app.app_context():
        role = Role.query.filter_by(name=ROLE_ADMIN).first()
        if role is None:
            role = Role()
            role.name = ROLE_ADMIN
            db.session.add(role)
        user = User()
        user.email = "risk-admin@example.com"
        user.status = UserStatus.ACTIVE
        user.set_password(_PASSWORD)
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        return user


def _login(client, email: str, password: str = _PASSWORD) -> None:
    response = client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )
    assert response.status_code == 200


def _seed_component(app) -> int:
    with app.app_context():
        scope = ContextScope(name="Core Service", risk_assessment_human=True)
        component = Component(name="Payroll Portal", context_scope=scope)
        db.session.add(scope)
        db.session.add(component)
        db.session.commit()
        return component.id


def _seed_control(app) -> int:
    with app.app_context():
        control = Control()
        control.domain = "ISO-27002-5.7"
        control.section = "5"
        control.description = "Encrypt backups"
        db.session.add(control)
        db.session.commit()
        return control.id


def _seed_thresholds(app) -> dict[RiskSeverity, RiskSeverityThreshold]:
    ranges = [
        (RiskSeverity.LOW, 1, 5),
        (RiskSeverity.MODERATE, 6, 10),
        (RiskSeverity.HIGH, 11, 15),
        (RiskSeverity.CRITICAL, 16, 25),
    ]
    with app.app_context():
        results: dict[RiskSeverity, RiskSeverityThreshold] = {}
        for severity, minimum, maximum in ranges:
            threshold = RiskSeverityThreshold(severity=severity, min_score=minimum, max_score=maximum)
            db.session.add(threshold)
            results[severity] = threshold
        db.session.commit()
        return results


def test_risk_dashboard_displays_existing_risk(client, app, admin_user):
    component_id = _seed_component(app)
    control_id = _seed_control(app)
    _seed_thresholds(app)

    with app.app_context():
        owner = db.session.get(User, admin_user.id)
        component = db.session.get(Component, component_id)
        control = db.session.get(Control, control_id)
        risk = Risk(
            title="Payroll data exposure",
            description="Sensitive payroll data could leak via unsecured buckets.",
            discovered_on=date.today(),
            impact=RiskImpact.MAJOR,
            chance=RiskChance.LIKELY,
            treatment=RiskTreatmentOption.MITIGATE,
            treatment_plan="Enable encryption and access reviews",
            treatment_due_date=date.today(),
            treatment_owner=owner,
        )
        risk.components.append(component)
        risk.controls.append(control)
        risk.impact_area_links = [RiskImpactAreaLink(area=RiskImpactArea.PRIVACY)]
        db.session.add(risk)
        db.session.commit()
        component_name = component.name

    _login(client, admin_user.email)

    response = client.get("/risk/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Payroll data exposure" in html
    assert "Critical" in html  # severity badge text
    assert component_name in html


def test_risk_create_requires_csa_control_for_mitigate(client, app, admin_user):
    component_id = _seed_component(app)
    _seed_thresholds(app)
    _login(client, admin_user.email)

    payload = {
        "title": "Mitigation without control",
        "description": "Attempt to mitigate without linking a CSA control.",
        "discovered_on": date.today().isoformat(),
        "impact": RiskImpact.MAJOR.value,
        "chance": RiskChance.LIKELY.value,
        "impact_areas": [RiskImpactArea.PRIVACY.value],
        "component_ids": [str(component_id)],
        "treatment": RiskTreatmentOption.MITIGATE.value,
        "treatment_plan": "Document missing control",
        "treatment_due_date": date.today().isoformat(),
        "treatment_owner_id": str(admin_user.id),
        "csa_control_ids": [],
    }

    response = client.post("/risk/new", data=payload)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Select at least one CSA control when the treatment strategy is Mitigate." in html

    with app.app_context():
        assert Risk.query.count() == 0


def test_admin_can_update_risk_threshold(client, app, admin_user):
    thresholds = _seed_thresholds(app)
    low_threshold = thresholds[RiskSeverity.LOW]
    _login(client, admin_user.email)

    prefix = f"threshold-{low_threshold.id}-"
    payload = {
        f"{prefix}severity": RiskSeverity.LOW.value,
        f"{prefix}min_score": str(low_threshold.min_score),
        f"{prefix}max_score": str(low_threshold.max_score + 1),
        f"{prefix}submit": "Save range",
    }

    response = client.post("/admin/risk-thresholds", data=payload, follow_redirects=True)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Severity range for Low updated." in html

    with app.app_context():
        updated = db.session.get(RiskSeverityThreshold, low_threshold.id)
        assert updated.max_score == low_threshold.max_score + 1


def test_risk_threshold_overlap_validation_blocks_update(client, app, admin_user):
    thresholds = _seed_thresholds(app)
    low_threshold = thresholds[RiskSeverity.LOW]
    moderate_threshold = thresholds[RiskSeverity.MODERATE]
    _login(client, admin_user.email)

    prefix = f"threshold-{low_threshold.id}-"
    payload = {
        f"{prefix}severity": RiskSeverity.LOW.value,
        f"{prefix}min_score": str(low_threshold.min_score),
        f"{prefix}max_score": str(moderate_threshold.min_score),
        f"{prefix}submit": "Save range",
    }

    response = client.post("/admin/risk-thresholds", data=payload)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Thresholds cannot overlap. Adjust the ranges and try again." in html

    with app.app_context():
        current = db.session.get(RiskSeverityThreshold, low_threshold.id)
        assert current.max_score == low_threshold.max_score
