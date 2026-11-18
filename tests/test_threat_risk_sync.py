"""Threat scenario → risk workspace synchronisation tests.

Feature 20261118-074624-risk-workspace-sync-bia-filter.
"""

from __future__ import annotations

import pytest

from scaffold import create_app
from scaffold.apps.bia.models import Component, ContextScope
from scaffold.apps.threat.models import (
    StrideCategory,
    AssetType,
    ThreatModel,
    ThreatModelAsset,
    ThreatScenario,
)
from scaffold.apps.threat.services import _components_for_scenario
from scaffold.config import Settings
from scaffold.extensions import db


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
