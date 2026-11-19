"""Threat scenario → risk workspace synchronisation tests.

Feature 20261118-074624-risk-workspace-sync-bia-filter.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from flask import g, request_started

from scaffold import create_app
from scaffold.apps.bia.models import Component, ContextScope
from scaffold.apps.risk.models import Risk, RiskChance, RiskImpact
from scaffold.apps.threat.models import (
    AssetType,
    ScenarioStatus,
    StrideCategory,
    ThreatModel,
    ThreatModelAsset,
    ThreatScenario,
    TreatmentOption,
)
from scaffold.apps.threat.services import _components_for_scenario, sync_scenario_to_risk
from scaffold.config import Settings
from scaffold.extensions import db
from scaffold.models.audit import AuditLog


@pytest.fixture
def app():
    settings = Settings(
        secret_key="test-secret",
        database_url="sqlite:///:memory:",
        session_cookie_secure=False,
        session_cookie_httponly=True,
        session_cookie_samesite="Lax",
        audit_log_retention_days=0,
        app_modules=[
            "scaffold.apps.auth.routes",
            "scaffold.apps.admin",
            "scaffold.apps.bia",
            "scaffold.apps.csa",
            "scaffold.apps.risk",
            "scaffold.apps.ssp",
            "scaffold.apps.template",
            "scaffold.apps.threat",
        ],
        password_login_enabled=True,
    )
    flask_app = create_app(settings)
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)

    # Same as conftest: drop Flask-Login's cached user (audit hooks cache an
    # anonymous one during setup) so each request resolves the session user.
    def _reset_login_cache(sender, **extra):
        g.pop("_login_user", None)

    request_started.connect(_reset_login_cache, flask_app)
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()


def _bia(name: str, component_names: list[str]) -> tuple[ContextScope, list[Component]]:
    scope = ContextScope(name=name)
    db.session.add(scope)
    db.session.flush()
    components = [Component(name=n, context_scope_id=scope.id) for n in component_names]
    db.session.add_all(components)
    db.session.flush()
    return scope, components


def _model(scope: ContextScope | None, asset_names: list[str]) -> tuple[ThreatModel, list[ThreatModelAsset]]:
    model = ThreatModel(title="TM", context_scope_id=scope.id if scope else None)
    db.session.add(model)
    db.session.flush()
    assets = [
        ThreatModelAsset(threat_model_id=model.id, name=n, asset_type=AssetType.COMPONENT, order=i)
        for i, n in enumerate(asset_names)
    ]
    db.session.add_all(assets)
    db.session.flush()
    return model, assets


def _scenario(model: ThreatModel, assigned=(), legacy=None) -> ThreatScenario:
    scenario = ThreatScenario(
        threat_model_id=model.id,
        title="S",
        stride_category=StrideCategory.SPOOFING,
        asset_id=legacy.id if legacy else None,
    )
    scenario.assigned_assets = list(assigned)
    db.session.add(scenario)
    db.session.flush()
    return scenario


def _names(components) -> set[str]:
    return {c.name for c in components}


def test_only_assigned_assets_are_linked(app):
    scope, _ = _bia("BIA", ["App", "DB", "Queue", "Cache"])
    model, assets = _model(scope, ["App", "DB", "Queue", "Cache"])
    scenario = _scenario(model, assigned=assets[:2])

    assert _names(_components_for_scenario(scenario)) == {"App", "DB"}


def test_legacy_asset_used_when_no_assigned_assets(app):
    scope, _ = _bia("BIA", ["App", "DB"])
    model, assets = _model(scope, ["App", "DB"])
    scenario = _scenario(model, legacy=assets[1])

    assert _names(_components_for_scenario(scenario)) == {"DB"}


def test_no_assets_links_nothing(app):
    scope, _ = _bia("BIA", ["App", "DB"])
    model, _ = _model(scope, ["App", "DB"])
    scenario = _scenario(model)

    assert _components_for_scenario(scenario) == []


def test_no_name_match_links_nothing(app):
    scope, _ = _bia("BIA", ["App"])
    model, assets = _model(scope, ["Data flow X"])
    scenario = _scenario(model, assigned=assets)

    assert _components_for_scenario(scenario) == []


def test_threat_model_without_bia_links_nothing(app):
    _bia("BIA", ["App"])
    model, assets = _model(None, ["App"])
    scenario = _scenario(model, assigned=assets)

    assert _components_for_scenario(scenario) == []


def test_same_name_in_other_bia_is_not_linked(app):
    scope, own = _bia("BIA", ["App"])
    _bia("Other BIA", ["App"])
    model, assets = _model(scope, ["App"])
    scenario = _scenario(model, assigned=assets)

    assert [c.id for c in _components_for_scenario(scenario)] == [own[0].id]


def test_match_ignores_case_and_whitespace(app):
    scope, _ = _bia("BIA", ["Payment API"])
    model, assets = _model(scope, ["  payment api "])
    scenario = _scenario(model, assigned=assets)

    assert _names(_components_for_scenario(scenario)) == {"Payment API"}


def test_duplicate_component_names_are_all_linked(app):
    scope, comps = _bia("BIA", ["App", "App"])
    model, assets = _model(scope, ["App"])
    scenario = _scenario(model, assigned=assets)

    assert [c.id for c in _components_for_scenario(scenario)] == [comps[0].id, comps[1].id]


# ---------------------------------------------------------------------------
# Mitigated state, residual values and audit (Task 3)
# ---------------------------------------------------------------------------


def _synced_scenario(status=ScenarioStatus.ANALYSED, treatment=TreatmentOption.MITIGATE, **kwargs):
    scope, _ = _bia("BIA", ["App"])
    model, assets = _model(scope, ["App"])
    scenario = _scenario(model, assigned=assets)
    scenario.status = status
    scenario.treatment = treatment
    scenario.likelihood = kwargs.get("likelihood", 4)
    scenario.impact_score = kwargs.get("impact_score", 4)
    scenario.residual_likelihood = kwargs.get("residual_likelihood")
    scenario.residual_impact = kwargs.get("residual_impact")
    sync_scenario_to_risk(scenario)
    db.session.flush()
    return scenario, db.session.get(Risk, scenario.risk_id) if scenario.risk_id else None


def _sync_events(risk):
    return AuditLog.query.filter_by(event_type="risk_synced_from_threat", target_id=str(risk.id)).all()


def test_mitigated_scenario_keeps_risk_open_with_residual(app):
    scenario, risk = _synced_scenario()
    scenario.status = ScenarioStatus.MITIGATED
    scenario.residual_likelihood = 3
    scenario.residual_impact = 2
    sync_scenario_to_risk(scenario)

    assert not risk.is_closed
    assert risk.is_mitigated
    assert (risk.residual_chance, risk.residual_impact) == (RiskChance.POSSIBLE, RiskImpact.MINOR)
    assert risk.actual_score() == 6


def test_resync_keeps_original_mitigated_at(app):
    scenario, risk = _synced_scenario(status=ScenarioStatus.MITIGATED)
    original = datetime(2026, 1, 1, tzinfo=UTC)
    risk.mitigated_at = original
    sync_scenario_to_risk(scenario)

    assert risk.mitigated_at == original


def test_back_to_open_clears_mitigated_and_remitigation_is_new(app):
    scenario, risk = _synced_scenario(status=ScenarioStatus.MITIGATED)
    first = datetime.now(UTC) - timedelta(days=30)
    risk.mitigated_at = first

    scenario.status = ScenarioStatus.ANALYSED
    sync_scenario_to_risk(scenario)
    assert risk.mitigated_at is None

    scenario.status = ScenarioStatus.MITIGATED
    sync_scenario_to_risk(scenario)
    assert risk.mitigated_at is not None and risk.mitigated_at != first


@pytest.mark.parametrize(
    ("status", "treatment"),
    [
        (ScenarioStatus.ACCEPTED, TreatmentOption.MITIGATE),
        (ScenarioStatus.CLOSED, TreatmentOption.MITIGATE),
        (ScenarioStatus.MITIGATED, TreatmentOption.ACCEPT),
    ],
)
def test_closing_status_or_non_mitigate_treatment_closes_risk(app, status, treatment):
    scenario, risk = _synced_scenario()
    scenario.status = status
    scenario.treatment = treatment
    sync_scenario_to_risk(scenario)

    assert risk.is_closed


def test_archived_risk_of_mitigated_scenario_reopens(app):
    scenario, risk = _synced_scenario(status=ScenarioStatus.MITIGATED)
    risk.closed_at = datetime.now(UTC)  # archived by the old sync behaviour
    sync_scenario_to_risk(scenario)

    assert not risk.is_closed


def test_new_risk_logs_creation_event(app):
    scenario, risk = _synced_scenario()

    event = AuditLog.query.filter_by(event_type="risk_created_from_threat").one()
    assert event.target_id == str(risk.id)
    assert event.payload["scenario_id"] == scenario.id


def test_noop_resync_logs_nothing_and_change_logs_only_changed_fields(app):
    scenario, risk = _synced_scenario()
    sync_scenario_to_risk(scenario)
    assert _sync_events(risk) == []

    scenario.status = ScenarioStatus.MITIGATED
    scenario.residual_likelihood = 3
    scenario.residual_impact = 2
    sync_scenario_to_risk(scenario)

    (event,) = _sync_events(risk)
    assert event.payload["scenario_id"] == scenario.id
    assert set(event.payload["changes"]) == {"mitigated", "residual_chance", "residual_impact"}
    assert event.payload["changes"]["mitigated"] == {"before": False, "after": True}


def test_bulk_sync_includes_mitigated_scenarios(app, client, login):
    scope, _ = _bia("BIA", ["App"])
    model, assets = _model(scope, ["App"])
    scenario = _scenario(model, assigned=assets)
    scenario.status = ScenarioStatus.MITIGATED
    scenario.treatment = TreatmentOption.MITIGATE
    db.session.commit()

    response = client.post("/risk/sync-from-threats")

    assert response.status_code == 302
    assert "/risk/" in response.headers["Location"]
    db.session.expire_all()  # the request used its own session
    assert db.session.get(ThreatScenario, scenario.id).risk_id is not None


# ---------------------------------------------------------------------------
# Risk edit form for threat-linked risks (Task 4)
# ---------------------------------------------------------------------------


def _linked_risk_without_components():
    scope, _ = _bia("BIA", ["App"])
    model, assets = _model(scope, ["Unmatched asset"])
    scenario = _scenario(model, assigned=assets)
    scenario.status = ScenarioStatus.ANALYSED
    scenario.treatment = TreatmentOption.MITIGATE
    scenario.likelihood = 4
    scenario.impact_score = 4
    sync_scenario_to_risk(scenario)
    db.session.commit()
    return scenario, db.session.get(Risk, scenario.risk_id)


def test_linked_risk_without_components_saves_editable_fields(app, client, login):
    _, risk = _linked_risk_without_components()
    assert risk.components == []

    response = client.post(
        f"/risk/{risk.id}/edit",
        data={"impact_areas": ["operational"], "treatment_plan": "Patch monthly"},
    )

    assert response.status_code == 302
    db.session.expire_all()
    assert db.session.get(Risk, risk.id).treatment_plan == "Patch monthly"


def test_linked_risk_ignores_posted_sync_owned_fields(app, client, login):
    _, risk = _linked_risk_without_components()

    response = client.post(
        f"/risk/{risk.id}/edit",
        data={
            "impact_areas": ["operational"],
            "title": "Changed title",
            "chance": "rare",
            "mitigated": "y",
            "residual_impact": "minor",
            "residual_chance": "rare",
        },
    )

    assert response.status_code == 302  # saved, not rejected
    db.session.expire_all()
    stored = db.session.get(Risk, risk.id)
    assert stored.title == "S"
    assert stored.chance is RiskChance.LIKELY
    assert not stored.is_mitigated
    assert stored.residual_impact is None


def test_linked_risk_form_renders_sync_fields_disabled(app, client, login):
    _, risk = _linked_risk_without_components()

    page = client.get(f"/risk/{risk.id}/edit").get_data(as_text=True)

    assert "managed by a threat scenario" in page
    for field_id in ("title", "chance", "mitigated", "residual_impact", "component_ids"):
        tag = page[page.index(f'id="{field_id}"') - 300 : page.index(f'id="{field_id}"') + 300]
        assert "disabled" in tag, field_id


# ---------------------------------------------------------------------------
# Admin risk register and SSP summary use the actual score (Task 8)
# ---------------------------------------------------------------------------


def _capture(client, url: str, template_name: str) -> dict:
    from flask import template_rendered

    captured: dict = {}

    def _record(sender, template, context, **extra):
        if template.name == template_name:
            captured.update(context)

    template_rendered.connect(_record)
    try:
        client.get(url)
    finally:
        template_rendered.disconnect(_record)
    return captured


def _seed_scope_risks():
    from scaffold.apps.risk.models import RiskSeverity, RiskSeverityThreshold

    for severity, low, high in (
        (RiskSeverity.LOW, 1, 5),
        (RiskSeverity.MODERATE, 6, 10),
        (RiskSeverity.HIGH, 11, 15),
        (RiskSeverity.CRITICAL, 16, 25),
    ):
        db.session.add(RiskSeverityThreshold(severity=severity, min_score=low, max_score=high))
    scope, (component,) = _bia("SSP BIA", ["App"])
    mitigated = Risk(
        title="Mitigated", description="d", impact=RiskImpact.MAJOR, chance=RiskChance.LIKELY,
        mitigated_at=datetime.now(UTC), residual_impact=RiskImpact.MINOR, residual_chance=RiskChance.POSSIBLE,
    )
    closed = Risk(
        title="Closed", description="d", impact=RiskImpact.MAJOR, chance=RiskChance.LIKELY,
        closed_at=datetime.now(UTC),
    )
    mitigated.components = [component]
    closed.components = [component]
    db.session.add_all([mitigated, closed])
    db.session.commit()
    return scope, mitigated


def test_admin_risk_register_shows_actual_score(app, client, login):
    from scaffold.apps.identity.models import ROLE_ADMIN, Role

    login.roles.append(Role.query.filter_by(name=ROLE_ADMIN).first() or Role(name=ROLE_ADMIN))
    db.session.commit()
    _, mitigated = _seed_scope_risks()

    context = _capture(client, "/admin/risks", "admin/risks.html")

    scores = {risk.id: risk.inherent_risk_score for risk in context["pagination"].items}
    assert scores[mitigated.id] == 6


@pytest.mark.parametrize("suffix, template", [("", "ssp/view.html"), ("/export/pdf", "ssp/print.html")])
def test_ssp_risk_summary_uses_actual_severity(app, client, login, suffix, template):
    from scaffold.apps.ssp.models import SSPlan

    scope, _ = _seed_scope_risks()
    ssp = SSPlan(context_scope_id=scope.id)
    db.session.add(ssp)
    db.session.commit()

    context = _capture(client, f"/ssp/{ssp.id}{suffix}", template)

    # Mitigated 16 -> 6 counts as moderate; the closed risk is excluded.
    assert context["risk_summary"] == {"moderate": 1}


# --- Owner approval reset through the sync (decisions 20261118-1057, -1058) ---


def _approve(risk, scenario):
    """Approve *risk* by its owner; the owner comes from the scenario (decision 20261118-1545)."""
    from scaffold.apps.identity.models import User, UserStatus
    from scaffold.apps.risk.models import RiskApprovalStatus

    owner = User()
    owner.email = "owner@example.com"
    owner.status = UserStatus.ACTIVE
    owner.set_password("Password123!")
    db.session.add(owner)
    db.session.flush()
    scenario.owner_id = owner.id
    risk.treatment_owner_id = owner.id
    risk.approval_status = RiskApprovalStatus.APPROVED
    risk.approval_decided_by_id = owner.id
    risk.approval_decided_at = datetime.now(UTC)
    db.session.commit()


def test_sync_material_change_resets_approval_and_says_so(app):
    scenario, risk = _synced_scenario()
    _approve(risk, scenario)

    scenario.likelihood = 1
    sync_scenario_to_risk(scenario)
    db.session.commit()

    db.session.refresh(risk)
    assert risk.approval_status is None
    (event,) = _sync_events(risk)
    assert event.payload["approval_reset"] is True


def test_noop_resync_keeps_approval(app):
    scenario, risk = _synced_scenario()
    _approve(risk, scenario)

    sync_scenario_to_risk(scenario)
    db.session.commit()

    db.session.refresh(risk)
    assert risk.approval_state == "approved"
    assert _sync_events(risk) == []


# --- Risk owner from threat owner (decision 20261118-1545) -------------------


def _user(email):
    from scaffold.apps.identity.models import User, UserStatus

    user = User()
    user.email = email
    user.status = UserStatus.ACTIVE
    user.set_password("Password123!")
    db.session.add(user)
    db.session.flush()
    return user


def _owned_scenario(scenario_owner=None, model_owner=None):
    scope, _ = _bia("BIA", ["App"])
    model, assets = _model(scope, ["App"])
    model.owner_id = model_owner.id if model_owner else None
    scenario = _scenario(model, assigned=assets)
    scenario.owner_id = scenario_owner.id if scenario_owner else None
    scenario.status = ScenarioStatus.ANALYSED
    scenario.treatment = TreatmentOption.MITIGATE
    scenario.likelihood = 4
    scenario.impact_score = 4
    sync_scenario_to_risk(scenario)
    db.session.flush()
    return scenario, db.session.get(Risk, scenario.risk_id)


def test_scenario_owner_becomes_risk_owner(app):
    alice, bob = _user("alice@example.com"), _user("bob@example.com")
    _scenario_obj, risk = _owned_scenario(scenario_owner=alice, model_owner=bob)

    assert risk.treatment_owner_id == alice.id


def test_model_owner_used_when_scenario_has_no_owner(app):
    bob = _user("bob@example.com")
    _scenario_obj, risk = _owned_scenario(model_owner=bob)

    assert risk.treatment_owner_id == bob.id


def test_risk_owner_cleared_when_threat_has_no_owner(app):
    alice = _user("alice@example.com")
    scenario, risk = _owned_scenario(scenario_owner=alice)

    scenario.owner_id = None
    sync_scenario_to_risk(scenario)

    assert risk.treatment_owner_id is None


def test_manual_owner_change_is_overwritten_by_next_sync(app):
    alice, carol = _user("alice@example.com"), _user("carol@example.com")
    scenario, risk = _owned_scenario(scenario_owner=alice)

    risk.treatment_owner_id = carol.id
    db.session.flush()
    sync_scenario_to_risk(scenario)

    assert risk.treatment_owner_id == alice.id


def test_owner_change_by_sync_is_audited_and_resets_approval(app):
    from scaffold.apps.risk.models import RiskApprovalStatus

    alice, dave = _user("alice@example.com"), _user("dave@example.com")
    scenario, risk = _owned_scenario(scenario_owner=alice)
    risk.approval_status = RiskApprovalStatus.APPROVED
    risk.approval_decided_by_id = alice.id
    risk.approval_decided_at = datetime.now(UTC)
    db.session.commit()

    scenario.owner_id = dave.id
    sync_scenario_to_risk(scenario)
    db.session.commit()

    db.session.refresh(risk)
    assert risk.treatment_owner_id == dave.id
    assert risk.approval_state == "awaiting"
    (event,) = _sync_events(risk)
    assert event.payload["changes"]["treatment_owner_id"] == {"before": alice.id, "after": dave.id}
    assert event.payload["approval_reset"] is True


def test_pasta_published_risk_gets_threat_model_owner(app):
    from types import SimpleNamespace

    from scaffold.apps.threat.services import publish_pasta_conclusion_to_risk

    bob = _user("bob@example.com")
    model = SimpleNamespace(owner_id=bob.id)
    conclusion = SimpleNamespace(
        is_publishable=True,
        likelihood_score=3,
        impact_score=3,
        treatment="mitigate",
        finding=SimpleNamespace(title="PASTA risk", description="d", stage_record=SimpleNamespace(threat_model=model)),
        published_risk_id=None,
        publication_state=None,
        last_published_at=None,
        last_published_by_id=None,
    )

    publish_pasta_conclusion_to_risk(conclusion, None)

    risk = db.session.get(Risk, conclusion.published_risk_id)
    assert risk.treatment_owner_id == bob.id


def test_owner_hint_only_shown_for_threat_linked_risks(app, client, login):
    _scenario_obj, linked = _owned_scenario(scenario_owner=login)
    manual = Risk(
        title="Manual",
        description="Manual risk",
        chance=RiskChance.POSSIBLE,
        impact=RiskImpact.MODERATE,
    )
    db.session.add(manual)
    db.session.commit()
    hint = b"Set from the threat owner; the next threat sync overwrites this."

    assert hint in client.get(f"/risk/{linked.id}/edit").data
    assert hint not in client.get(f"/risk/{manual.id}/edit").data


# --- Feature 20261119-073747: affected assets list with add overlay ---------


def _make_admin(user) -> None:
    from scaffold.apps.identity.models import ROLE_ADMIN, Role

    role = Role.query.filter_by(name=ROLE_ADMIN).first() or Role(name=ROLE_ADMIN)
    user.roles.append(role)
    db.session.commit()


_SCENARIO_POST = {
    "stride_category": "spoofing",
    "title": "Renamed",
    "likelihood": "2",
    "impact_score": "2",
    "status": "identified",
}


def test_scenario_edit_shows_asset_picker(app, client, login):
    """Edit lists the threatened assets with an "Add asset" overlay; new keeps the select (0740)."""
    _make_admin(login)
    model, (front, back) = _model(None, ["Frontend", "Backend"])
    scenario = _scenario(model, assigned=[front])
    db.session.commit()

    html = client.get(f"/threat/{model.id}/scenarios/{scenario.id}/edit").get_data(as_text=True)
    assert "data-asset-picker" in html
    assert f'data-value="{front.id}"' in html
    assert f'data-value="{back.id}"' not in html  # an option in the select, not a listed row
    assert "Add asset" in html
    new_html = client.get(f"/threat/{model.id}/scenarios/new").get_data(as_text=True)
    assert "data-asset-picker" not in new_html


def test_scenario_edit_requires_an_asset(app, client, login):
    """Removing every threatened asset is rejected and nothing is saved (0800)."""
    _make_admin(login)
    model, (front,) = _model(None, ["Frontend"])
    scenario = _scenario(model, assigned=[front])
    db.session.commit()

    response = client.post(f"/threat/{model.id}/scenarios/{scenario.id}/edit", data=_SCENARIO_POST)

    assert response.status_code == 200
    assert "Select at least one threatened asset." in response.get_data(as_text=True)
    db.session.expire_all()
    saved = db.session.get(ThreatScenario, scenario.id)
    assert saved.title == "S"
    assert [a.id for a in saved.assigned_assets] == [front.id]


def test_legacy_scenario_saves_without_assets(app, client, login):
    """A legacy scalar-asset scenario keeps its silent backfill (0800 legacy exemption)."""
    _make_admin(login)
    model, (legacy,) = _model(None, ["Legacy"])
    scenario = _scenario(model, legacy=legacy)
    db.session.commit()

    response = client.post(f"/threat/{model.id}/scenarios/{scenario.id}/edit", data=_SCENARIO_POST)

    assert response.status_code == 302
    db.session.expire_all()
    saved = db.session.get(ThreatScenario, scenario.id)
    assert saved.title == "Renamed"
    assert [a.id for a in saved.assigned_assets] == [legacy.id]


def test_scenario_edit_saves_posted_assets(app, client, login):
    """The hidden select is still what gets submitted: posted ids replace the assignment."""
    _make_admin(login)
    model, (front, back) = _model(None, ["Frontend", "Backend"])
    scenario = _scenario(model, assigned=[front])
    db.session.commit()

    response = client.post(
        f"/threat/{model.id}/scenarios/{scenario.id}/edit",
        data={**_SCENARIO_POST, "asset_ids": [str(back.id)]},
    )

    assert response.status_code == 302
    db.session.expire_all()
    assert [a.id for a in db.session.get(ThreatScenario, scenario.id).assigned_assets] == [back.id]


def _linked_risk_with_component():
    scope, (app_component,) = _bia("BIA", ["App"])
    model, assets = _model(scope, ["App"])
    scenario = _scenario(model, assigned=assets)
    scenario.status = ScenarioStatus.ANALYSED
    scenario.treatment = TreatmentOption.MITIGATE
    scenario.likelihood = 4
    scenario.impact_score = 4
    sync_scenario_to_risk(scenario)
    db.session.commit()
    return scenario, db.session.get(Risk, scenario.risk_id), app_component


def test_linked_risk_edit_shows_read_only_component_list(app, client, login):
    """Threat-linked risk: listed components, no add/remove, note links to scenario detail (0741, 0800)."""
    scenario, risk, component = _linked_risk_with_component()

    html = client.get(f"/risk/{risk.id}/edit").get_data(as_text=True)

    assert "data-asset-picker" in html
    assert f'data-value="{component.id}"' in html
    assert "data-asset-picker-add" not in html
    assert "data-asset-picker-remove" not in html
    assert "These components come from the threatened assets" in html
    assert f'href="/threat/{scenario.threat_model_id}/scenarios/{scenario.id}"' in html
    assert "Linked components" not in html  # old summary block is gone


def test_linked_risk_read_only_list_survives_failed_post(app, client, login):
    """The disabled select is not posted; a re-rendered page still lists the components."""
    _, risk, component = _linked_risk_with_component()

    response = client.post(f"/risk/{risk.id}/edit", data={"impact_areas": ["not-an-area"]})

    assert response.status_code == 200
    assert f'data-value="{component.id}"' in response.get_data(as_text=True)


def test_manual_risk_edit_has_add_component_picker(app, client, login):
    """Manual risk edit gets the editable picker; the create page keeps the select (0740)."""
    _, (component,) = _bia("BIA", ["App"])
    manual = Risk(
        title="Manual",
        description="Manual risk",
        chance=RiskChance.POSSIBLE,
        impact=RiskImpact.MODERATE,
    )
    manual.components = [component]
    db.session.add(manual)
    db.session.commit()

    html = client.get(f"/risk/{manual.id}/edit").get_data(as_text=True)
    assert "data-asset-picker-add" in html
    assert "Add component" in html
    assert f'data-value="{component.id}"' in html
    assert "data-asset-picker" not in client.get("/risk/new").get_data(as_text=True)
