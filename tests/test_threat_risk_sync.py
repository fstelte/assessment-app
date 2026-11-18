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
