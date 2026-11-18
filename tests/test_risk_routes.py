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


# ---------------------------------------------------------------------------
# T032/T033: Auth regression – role-aware access to risk ticket links
# ---------------------------------------------------------------------------


def test_unauthenticated_risk_create_redirects(client, app):
    """Unauthenticated POST to create risk should redirect to login."""
    resp = client.post("/risk/new", data={}, follow_redirects=False)
    assert resp.status_code in (302, 403)


# ---------------------------------------------------------------------------
# T023: US4 – multiple labeled ticket links on a risk
# ---------------------------------------------------------------------------


def _build_risk_payload(component_id: int, control_id: int, user_id: int) -> dict:
    return {
        "title": "Ticket link risk",
        "description": "Test multiple ticket links.",
        "discovered_on": date.today().isoformat(),
        "impact": RiskImpact.MODERATE.value,
        "chance": RiskChance.POSSIBLE.value,
        "impact_areas": [RiskImpactArea.OPERATIONAL.value],
        "component_ids": [str(component_id)],
        "treatment": RiskTreatmentOption.MITIGATE.value,
        "treatment_plan": "Fix it",
        "treatment_due_date": date.today().isoformat(),
        "treatment_owner_id": str(user_id),
        "csa_control_ids": [str(control_id)],
    }


def test_risk_create_with_two_ticket_links(client, app, admin_user):
    """Creating a risk with two ticket links persists both."""
    from scaffold.apps.risk.models import RiskTicketLink

    component_id = _seed_component(app)
    control_id = _seed_control(app)
    _seed_thresholds(app)
    _login(client, admin_user.email)

    payload = _build_risk_payload(component_id, control_id, admin_user.id)
    payload.update({
        "ticket_label_0": "JIRA-101",
        "ticket_url_0": "https://jira.example.com/browse/JIRA-101",
        "ticket_label_1": "GH-55",
        "ticket_url_1": "https://github.com/org/repo/issues/55",
    })

    resp = client.post("/risk/new", data=payload, follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        risk = Risk.query.filter_by(title="Ticket link risk").first()
        assert risk is not None
        links = sorted(risk.ticket_links, key=lambda t: t.sort_order)
        assert len(links) == 2
        assert links[0].label == "JIRA-101"
        assert links[0].url == "https://jira.example.com/browse/JIRA-101"
        assert links[1].label == "GH-55"


def test_risk_edit_page_renders_existing_ticket_links(client, app, admin_user):
    """Edit page renders existing ticket links without template errors."""
    component_id = _seed_component(app)
    control_id = _seed_control(app)
    _seed_thresholds(app)
    _login(client, admin_user.email)

    payload = _build_risk_payload(component_id, control_id, admin_user.id)
    payload.update({
        "title": "Render edit risk",
        "ticket_label_0": "JIRA-150",
        "ticket_url_0": "https://jira.example.com/browse/JIRA-150",
    })
    client.post("/risk/new", data=payload, follow_redirects=False)

    with app.app_context():
        risk = Risk.query.filter_by(title="Render edit risk").first()
        assert risk is not None
        risk_id = risk.id

    response = client.get(f"/risk/{risk_id}/edit")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "JIRA-150" in html
    assert "https://jira.example.com/browse/JIRA-150" in html


def test_risk_edit_replaces_ticket_links(client, app, admin_user):
    """Editing a risk replaces ticket links with the submitted set."""
    from scaffold.apps.risk.models import RiskTicketLink

    component_id = _seed_component(app)
    control_id = _seed_control(app)
    _seed_thresholds(app)
    _login(client, admin_user.email)

    # Create with one link
    payload = _build_risk_payload(component_id, control_id, admin_user.id)
    payload.update({
        "title": "Edit link risk",
        "ticket_label_0": "JIRA-200",
        "ticket_url_0": "https://jira.example.com/browse/JIRA-200",
    })
    client.post("/risk/new", data=payload, follow_redirects=False)

    with app.app_context():
        risk = Risk.query.filter_by(title="Edit link risk").first()
        assert risk is not None
        risk_id = risk.id

    # Edit with two links
    payload["ticket_label_0"] = "JIRA-200"
    payload["ticket_url_0"] = "https://jira.example.com/browse/JIRA-200"
    payload["ticket_label_1"] = "JIRA-201"
    payload["ticket_url_1"] = "https://jira.example.com/browse/JIRA-201"
    client.post(f"/risk/{risk_id}/edit", data=payload, follow_redirects=False)

    with app.app_context():
        risk = db.session.get(Risk, risk_id)
        assert len(risk.ticket_links) == 2


def test_risk_create_with_no_ticket_links(client, app, admin_user):
    """Creating a risk with no ticket links is valid."""
    component_id = _seed_component(app)
    control_id = _seed_control(app)
    _seed_thresholds(app)
    _login(client, admin_user.email)

    payload = _build_risk_payload(component_id, control_id, admin_user.id)
    payload["title"] = "No ticket links risk"
    resp = client.post("/risk/new", data=payload, follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        risk = Risk.query.filter_by(title="No ticket links risk").first()
        assert risk is not None
        assert len(risk.ticket_links) == 0


def test_ticket_link_label_max_length_validation(client, app, admin_user):
    """A label exceeding 80 characters should be rejected."""
    component_id = _seed_component(app)
    control_id = _seed_control(app)
    _seed_thresholds(app)
    _login(client, admin_user.email)

    payload = _build_risk_payload(component_id, control_id, admin_user.id)
    payload["title"] = "Long label risk"
    payload["ticket_label_0"] = "X" * 81
    payload["ticket_url_0"] = "https://jira.example.com/browse/LONG"

    resp = client.post("/risk/new", data=payload, follow_redirects=False)
    # Should re-render form with error, not redirect
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "80" in html or "label" in html.lower()


# ---------------------------------------------------------------------------
# Mitigated marker and residual assessment on the manual form (Task 4)
# ---------------------------------------------------------------------------


def _manual_form(component_id: int, **overrides) -> dict:
    data = {
        "title": "Backup leak",
        "description": "Backups stored unencrypted",
        "impact": RiskImpact.MAJOR.value,  # 4
        "chance": RiskChance.LIKELY.value,  # 4
        "impact_areas": [RiskImpactArea.OPERATIONAL.value],
        "component_ids": [str(component_id)],
        "treatment": RiskTreatmentOption.ACCEPT.value,
        "mitigated": "y",
        "residual_impact": RiskImpact.MINOR.value,  # 2
        "residual_chance": RiskChance.POSSIBLE.value,  # 3
    }
    data.update(overrides)
    return {key: value for key, value in data.items() if value is not None}


def test_manual_risk_can_be_mitigated_with_residual(client, app, login):
    component_id = _seed_component(app)
    _seed_thresholds(app)

    response = client.post("/risk/new", data=_manual_form(component_id))
    assert response.status_code == 302

    risk = Risk.query.one()
    assert risk.is_mitigated
    assert (risk.residual_impact, risk.residual_chance) == (RiskImpact.MINOR, RiskChance.POSSIBLE)

    page = client.get(f"/risk/{risk.id}/edit").get_data(as_text=True)
    assert "Initial: 16 → Residual: 6" in page


def test_unchecking_mitigated_clears_marker(client, app, login):
    component_id = _seed_component(app)
    client.post("/risk/new", data=_manual_form(component_id))
    risk_id = Risk.query.one().id
    assert Risk.query.one().is_mitigated

    response = client.post(f"/risk/{risk_id}/edit", data=_manual_form(component_id, mitigated=None))

    assert response.status_code == 302
    db.session.expire_all()
    assert db.session.get(Risk, risk_id).mitigated_at is None


def test_manual_risk_without_components_is_rejected(client, app, login):
    component_id = _seed_component(app)
    client.post("/risk/new", data=_manual_form(component_id))
    risk_id = Risk.query.one().id

    response = client.post(f"/risk/{risk_id}/edit", data=_manual_form(component_id, component_ids=[]))

    assert response.status_code == 200  # re-rendered with errors
    db.session.expire_all()
    assert [c.id for c in db.session.get(Risk, risk_id).components] == [component_id]


# ---------------------------------------------------------------------------
# Dashboard shows the actual score (Task 5)
# ---------------------------------------------------------------------------


def _seed_mitigated_and_open_risk(app) -> tuple[Risk, Risk]:
    from datetime import UTC, datetime

    component = db.session.get(Component, _seed_component(app))
    mitigated = Risk(
        title="Mitigated leak",
        description="d",
        impact=RiskImpact.MAJOR,  # 4
        chance=RiskChance.LIKELY,  # 4
        treatment=RiskTreatmentOption.MITIGATE,
        mitigated_at=datetime.now(UTC),
        residual_impact=RiskImpact.MINOR,  # 2
        residual_chance=RiskChance.POSSIBLE,  # 3
    )
    open_risk = Risk(
        title="Open leak",
        description="d",
        impact=RiskImpact.MAJOR,
        chance=RiskChance.LIKELY,
        treatment=RiskTreatmentOption.ACCEPT,
    )
    mitigated.components = [component]
    open_risk.components = [component]
    db.session.add_all([mitigated, open_risk])
    db.session.commit()
    return mitigated, open_risk


def test_dashboard_cards_matrix_and_metrics_use_actual_score(app):
    from scaffold.apps.risk.routes import _build_dashboard_cards, _build_risk_matrix, _dashboard_metrics
    from scaffold.apps.risk.services import load_thresholds

    _seed_thresholds(app)
    mitigated, open_risk = _seed_mitigated_and_open_risk(app)
    thresholds = load_thresholds()

    with app.test_request_context():
        cards = {card["id"]: card for card in _build_dashboard_cards([mitigated, open_risk], thresholds)}
        matrix = _build_risk_matrix([mitigated, open_risk], thresholds)

    assert cards[mitigated.id]["score"] == 6
    assert cards[mitigated.id]["severity"] is RiskSeverity.MODERATE
    assert (cards[mitigated.id]["initial_score"], cards[mitigated.id]["residual_score"]) == (16, 6)
    assert cards[open_risk.id]["score"] == 16
    assert cards[open_risk.id]["severity"] is RiskSeverity.CRITICAL
    assert _dashboard_metrics(list(cards.values()))["high"] == 1

    placed = {
        (row["chance"], cell["impact"]): [entry["id"] for entry in cell["risks"]]
        for row in matrix["rows"]
        for cell in row["cells"]
    }
    assert placed[(RiskChance.POSSIBLE, RiskImpact.MINOR)] == [mitigated.id]
    assert placed[(RiskChance.LIKELY, RiskImpact.MAJOR)] == [open_risk.id]


def test_dashboard_card_shows_mitigated_pill_and_initial_hint(client, app, login):
    _seed_thresholds(app)
    _seed_mitigated_and_open_risk(app)

    page = client.get("/risk/").get_data(as_text=True)

    assert "Initial: 16 → Residual: 6" in page
    assert "Treatment: mitigate" in page
    assert page.count('risk-pill risk-pill--low">Mitigated<') == 1


# ---------------------------------------------------------------------------
# BIA multi-filter on the dashboard (Task 7)
# ---------------------------------------------------------------------------


def _seed_bia_risks(app) -> dict[str, object]:
    scopes, risks = {}, {}
    for name in ("Alpha BIA", "Beta BIA", "Gamma BIA"):
        scope = ContextScope(name=name, risk_assessment_human=True)
        db.session.add(scope)
        scopes[name] = scope
    a1 = Component(name="A1", context_scope=scopes["Alpha BIA"])
    a2 = Component(name="A2", context_scope=scopes["Alpha BIA"])
    b1 = Component(name="B1", context_scope=scopes["Beta BIA"])
    g1 = Component(name="G1", context_scope=scopes["Gamma BIA"])
    db.session.add_all([a1, a2, b1, g1])
    for title, components in (
        ("Alpha risk", [a1, a2]),
        ("Beta risk", [b1]),
        ("Gamma risk", [g1]),
        ("Shared risk", [a1, g1]),
        ("Orphan risk", []),
    ):
        risk = Risk(title=title, description="d", impact=RiskImpact.MINOR, chance=RiskChance.RARE)
        risk.components = components
        db.session.add(risk)
        risks[title] = risk
    db.session.commit()
    return {"scopes": scopes, "risks": risks}


def _dashboard_context(client, query: str = "") -> dict:
    from flask import template_rendered

    captured: dict = {}

    def _record(sender, template, context, **extra):
        if template.name == "risk/dashboard.html":
            captured.update(context)

    template_rendered.connect(_record)
    try:
        assert client.get(f"/risk/{query}").status_code == 200
    finally:
        template_rendered.disconnect(_record)
    return captured


def _titles(context) -> set[str]:
    return {card["title"] for card in context["risk_cards"]}


def test_bia_filter_single_shows_only_matching_risks(client, app, login):
    seed = _seed_bia_risks(app)
    alpha = seed["scopes"]["Alpha BIA"].id

    context = _dashboard_context(client, f"?bia={alpha}")

    assert _titles(context) == {"Alpha risk", "Shared risk"}
    assert context["selected_bia_ids"] == [alpha]


def test_bia_filter_multiple_shows_union(client, app, login):
    seed = _seed_bia_risks(app)
    alpha, beta = seed["scopes"]["Alpha BIA"].id, seed["scopes"]["Beta BIA"].id

    context = _dashboard_context(client, f"?bia={alpha}&bia={beta}")

    assert _titles(context) == {"Alpha risk", "Beta risk", "Shared risk"}


@pytest.mark.parametrize("query", ["", "?bia=x", "?bia=999", "?bia="])
def test_no_or_invalid_bia_filter_shows_all_risks(client, app, login, query):
    _seed_bia_risks(app)

    context = _dashboard_context(client, query)

    assert _titles(context) == {"Alpha risk", "Beta risk", "Gamma risk", "Shared risk", "Orphan risk"}
    assert context["selected_bia_ids"] == []


def test_bia_filter_scopes_metrics_matrix_and_component_count(client, app, login):
    seed = _seed_bia_risks(app)
    alpha = seed["scopes"]["Alpha BIA"].id

    context = _dashboard_context(client, f"?bia={alpha}")

    visible = len(context["risk_cards"])
    matrix_count = sum(len(cell["risks"]) for row in context["risk_matrix"]["rows"] for cell in row["cells"])
    assert context["metrics"]["total"] == visible == matrix_count == 2
    # Shared risk also links G1 (Gamma), which must not count under the Alpha filter.
    assert context["metrics"]["components"] == 2


def test_bia_filter_options_and_active_summary_render(client, app, login):
    seed = _seed_bia_risks(app)
    beta = seed["scopes"]["Beta BIA"].id

    page = client.get(f"/risk/?bia={beta}").get_data(as_text=True)

    assert f'<option value="{beta}" selected>Beta BIA</option>' in page
    assert "Showing risks for: Beta BIA" in page
    assert "Clear filter" in page


def _seed_open_and_closed_risks(app) -> dict[str, Risk]:
    """A manual open risk, a manual closed risk and a threat-closed risk, all in Alpha BIA."""

    from datetime import UTC, datetime

    scope = ContextScope(name="Alpha BIA", risk_assessment_human=True)
    component = Component(name="A1", context_scope=scope)
    risks = {}
    for title, closed in (("Open risk", False), ("Closed manual risk", True), ("Threat closed risk", True)):
        risk = Risk(
            title=title,
            description="d",
            impact=RiskImpact.CATASTROPHIC,
            chance=RiskChance.ALMOST_CERTAIN,
            closed_at=datetime.now(UTC) if closed else None,
        )
        risk.components = [component]
        risks[title] = risk
    db.session.add_all([scope, component, *risks.values()])
    db.session.commit()
    return risks


def test_workspace_hides_closed_risks_from_cards_metrics_and_matrix(client, app, login):
    _seed_thresholds(app)
    _seed_open_and_closed_risks(app)

    context = _dashboard_context(client)

    assert _titles(context) == {"Open risk"}
    matrix_count = sum(len(cell["risks"]) for row in context["risk_matrix"]["rows"] for cell in row["cells"])
    assert context["metrics"]["total"] == matrix_count == 1
    assert context["metrics"]["high"] == 1


def test_workspace_bia_filter_still_hides_closed_risks(client, app, login):
    _seed_open_and_closed_risks(app)
    scope_id = ContextScope.query.filter_by(name="Alpha BIA").one().id

    context = _dashboard_context(client, f"?bia={scope_id}")

    assert _titles(context) == {"Open risk"}


def test_threat_closed_risk_leaves_the_workspace(client, app, login):
    from scaffold.apps.threat.models import (
        AssetType,
        ScenarioStatus,
        StrideCategory,
        ThreatModel,
        ThreatModelAsset,
        ThreatScenario,
        TreatmentOption,
    )
    from scaffold.apps.threat.services import sync_scenario_to_risk

    scope = ContextScope(name="Threat BIA")
    db.session.add(scope)
    db.session.flush()
    db.session.add(Component(name="App", context_scope_id=scope.id))
    model = ThreatModel(title="TM", context_scope_id=scope.id)
    db.session.add(model)
    db.session.flush()
    asset = ThreatModelAsset(threat_model_id=model.id, name="App", asset_type=AssetType.COMPONENT, order=0)
    db.session.add(asset)
    db.session.flush()
    scenario = ThreatScenario(
        threat_model_id=model.id,
        title="Spoofed login",
        stride_category=StrideCategory.SPOOFING,
        status=ScenarioStatus.ANALYSED,
        treatment=TreatmentOption.MITIGATE,
        likelihood=4,
        impact_score=4,
    )
    scenario.assigned_assets = [asset]
    db.session.add(scenario)
    db.session.flush()
    sync_scenario_to_risk(scenario)
    db.session.commit()
    risk_title = db.session.get(Risk, scenario.risk_id).title
    assert risk_title in _titles(_dashboard_context(client))

    scenario.status = ScenarioStatus.ACCEPTED
    sync_scenario_to_risk(scenario)
    db.session.commit()

    assert db.session.get(Risk, scenario.risk_id).is_closed
    assert risk_title not in _titles(_dashboard_context(client))


def test_workspace_has_no_reopen_button(client, app, login):
    _seed_open_and_closed_risks(app)

    page = client.get("/risk/").get_data(as_text=True)

    assert "Reopen risk" not in page
    assert "Close &amp; archive" in page


def test_workspace_with_only_closed_risks_shows_no_open_risks(client, app, login):
    from datetime import UTC, datetime

    for risk in _seed_open_and_closed_risks(app).values():
        risk.closed_at = risk.closed_at or datetime.now(UTC)
    db.session.commit()

    page = client.get("/risk/").get_data(as_text=True)

    assert "data-no-open-risks" in page
    assert "No open risks." in page
    assert "No risks recorded yet." not in page


def test_empty_workspace_still_shows_first_risk_prompt(client, app, login):
    page = client.get("/risk/").get_data(as_text=True)

    assert "No risks recorded yet." in page
    assert "data-no-open-risks" not in page
