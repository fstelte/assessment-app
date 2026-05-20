"""Tests for the threat modeling module."""

from __future__ import annotations

import pytest

from scaffold import create_app
from scaffold.apps.csa.models import Control
from scaffold.apps.identity.models import ROLE_ADMIN, ROLE_ASSESSMENT_MANAGER, Role, User, UserStatus
from scaffold.apps.threat.models import (
    AssetType,
    RiskLevel,
    ScenarioStatus,
    StrideCategory,
    ThreatModel,
    ThreatModelAsset,
    ThreatScenario,
    ThreatScenarioStrideCategory,
)
from scaffold.apps.threat.services import compute_risk_score
from scaffold.config import Settings
from scaffold.extensions import db

_PASSWORD = "Password123!"


# ---------------------------------------------------------------------------
# App fixture — includes the threat module
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    settings = Settings(
        secret_key="test-secret",
        database_url="sqlite:///:memory:",
        session_cookie_secure=False,
        session_cookie_httponly=True,
        session_cookie_samesite="Lax",
        app_modules=[
            "scaffold.apps.auth.routes",
            "scaffold.apps.admin",
            "scaffold.apps.bia",
            "scaffold.apps.csa",
            "scaffold.apps.risk",
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


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    with app.app_context():
        role = Role.query.filter_by(name=ROLE_ADMIN).first()
        if role is None:
            role = Role(name=ROLE_ADMIN)
            db.session.add(role)
        user = User()
        user.email = "threat-admin@example.com"
        user.status = UserStatus.ACTIVE
        user.set_password(_PASSWORD)
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        return user


def _login(client, email: str, password: str = _PASSWORD) -> None:
    resp = client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )
    assert resp.status_code == 200


def _seed_model(app, owner_id: int) -> int:
    with app.app_context():
        model = ThreatModel(
            title="Test Model",
            description="A test threat model",
            scope="All internal services",
            owner_id=owner_id,
        )
        db.session.add(model)
        db.session.commit()
        return model.id


def _seed_scenario(app, model_id: int) -> int:
    with app.app_context():
        scenario = ThreatScenario(
            threat_model_id=model_id,
            stride_category=StrideCategory.SPOOFING,
            title="Fake identity scenario",
            likelihood=3,
            impact_score=4,
            risk_score=12,
            risk_level=RiskLevel.HIGH,
            status=ScenarioStatus.IDENTIFIED,
        )
        db.session.add(scenario)
        db.session.commit()
        return scenario.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_dashboard_requires_login(client):
    """Unauthenticated request should redirect to login."""
    resp = client.get("/threat/")
    assert resp.status_code in (302, 403)
    if resp.status_code == 302:
        assert "/auth/login" in resp.headers["Location"]


def test_create_threat_model(client, app, admin_user):
    """POST valid form creates model and redirects."""
    _login(client, admin_user.email)
    resp = client.post(
        "/threat/new",
        data={"title": "My Threat Model", "description": "desc", "scope": "scope"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        model = ThreatModel.query.filter_by(title="My Threat Model").first()
        assert model is not None
        assert model.scope == "scope"


def test_create_asset(client, app, admin_user):
    """POST asset form creates asset under the model."""
    model_id = _seed_model(app, admin_user.id)
    _login(client, admin_user.email)
    resp = client.post(
        f"/threat/{model_id}/assets/new",
        data={"name": "API Gateway", "asset_type": "component", "description": "", "order": 0},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        asset = ThreatModelAsset.query.filter_by(name="API Gateway").first()
        assert asset is not None
        assert asset.threat_model_id == model_id


def test_create_scenario_spoofing(client, app, admin_user):
    """Can create a scenario with SPOOFING category."""
    model_id = _seed_model(app, admin_user.id)
    _login(client, admin_user.email)
    resp = client.post(
        f"/threat/{model_id}/scenarios/new",
        data={
            "stride_category": "spoofing",
            "title": "Spoofing attack",
            "likelihood": "3",
            "impact_score": "3",
            "status": "identified",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        scenario = ThreatScenario.query.filter_by(title="Spoofing attack").first()
        assert scenario is not None
        assert scenario.stride_category == StrideCategory.SPOOFING


def test_create_scenario_lateral_movement(client, app, admin_user):
    """Can create a scenario with LATERAL_MOVEMENT (LM) category."""
    model_id = _seed_model(app, admin_user.id)
    _login(client, admin_user.email)
    resp = client.post(
        f"/threat/{model_id}/scenarios/new",
        data={
            "stride_category": "lateral_movement",
            "title": "Pivot through internal network",
            "likelihood": "4",
            "impact_score": "5",
            "status": "identified",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        scenario = ThreatScenario.query.filter_by(title="Pivot through internal network").first()
        assert scenario is not None
        assert scenario.stride_category == StrideCategory.LATERAL_MOVEMENT
        assert scenario.risk_level == RiskLevel.CRITICAL


def test_risk_score_computation():
    """Unit test the risk scoring matrix."""
    # Low × Low = low, score 1
    score, level = compute_risk_score(1, 1)
    assert score == 1
    assert level == "low"

    # Medium × Medium = medium, score 9
    score, level = compute_risk_score(3, 3)
    assert score == 9
    assert level == "medium"

    # High × High = critical, score 25
    score, level = compute_risk_score(5, 5)
    assert score == 25
    assert level == "critical"

    # Low likelihood × High impact = medium
    score, level = compute_risk_score(2, 5)
    assert level == "medium"

    # High likelihood × Low impact = medium
    score, level = compute_risk_score(5, 2)
    assert level == "medium"


def test_export_csv(client, app, admin_user):
    """Authenticated GET to /export/csv returns CSV content."""
    model_id = _seed_model(app, admin_user.id)
    _seed_scenario(app, model_id)
    _login(client, admin_user.email)
    resp = client.get(f"/threat/{model_id}/export/csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.content_type
    data = resp.data.decode("utf-8")
    assert "title" in data  # header row
    assert "Fake identity scenario" in data


def test_export_html(client, app, admin_user):
    """Authenticated GET to /export/html returns HTML content."""
    model_id = _seed_model(app, admin_user.id)
    _login(client, admin_user.email)
    resp = client.get(f"/threat/{model_id}/export/html")
    assert resp.status_code == 200
    assert "text/html" in resp.content_type


def test_archive_model(client, app, admin_user):
    """POST archive toggles is_archived to True."""
    model_id = _seed_model(app, admin_user.id)
    _login(client, admin_user.email)
    resp = client.post(f"/threat/{model_id}/archive", follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        model = db.session.get(ThreatModel, model_id)
        assert model.is_archived is True


def test_delete_scenario(client, app, admin_user):
    """POST delete removes the scenario from the database."""
    model_id = _seed_model(app, admin_user.id)
    scenario_id = _seed_scenario(app, model_id)
    _login(client, admin_user.email)
    resp = client.post(
        f"/threat/{model_id}/scenarios/{scenario_id}/delete",
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        scenario = db.session.get(ThreatScenario, scenario_id)
        assert scenario is None


def test_model_detail_shows_scenarios(client, app, admin_user):
    """GET model detail page renders all scenario titles."""
    model_id = _seed_model(app, admin_user.id)
    _seed_scenario(app, model_id)
    _login(client, admin_user.email)
    resp = client.get(f"/threat/{model_id}")
    assert resp.status_code == 200
    assert b"Fake identity scenario" in resp.data


# ---------------------------------------------------------------------------
# T032: Auth regression – role-aware view/edit access
# ---------------------------------------------------------------------------


@pytest.fixture
def readonly_user(app):
    """A user with no special roles – read access only."""
    with app.app_context():
        user = User()
        user.email = "readonly@example.com"
        user.status = UserStatus.ACTIVE
        user.set_password(_PASSWORD)
        db.session.add(user)
        db.session.commit()
        return user


def test_unauthenticated_scenario_edit_rejected(client, app, admin_user):
    """Unauthenticated access to scenario edit form is rejected."""
    model_id = _seed_model(app, admin_user.id)
    scenario_id = _seed_scenario(app, model_id)
    resp = client.get(f"/threat/{model_id}/scenarios/{scenario_id}/edit")
    assert resp.status_code in (302, 403)


def test_authenticated_user_can_view_scenario(client, app, admin_user, readonly_user):
    """Any authenticated user can view scenario detail."""
    model_id = _seed_model(app, admin_user.id)
    scenario_id = _seed_scenario(app, model_id)
    _login(client, readonly_user.email)
    resp = client.get(f"/threat/{model_id}/scenarios/{scenario_id}")
    assert resp.status_code == 200


def test_admin_can_edit_scenario(client, app, admin_user):
    """Admin can GET the scenario edit form."""
    model_id = _seed_model(app, admin_user.id)
    scenario_id = _seed_scenario(app, model_id)
    _login(client, admin_user.email)
    resp = client.get(f"/threat/{model_id}/scenarios/{scenario_id}/edit")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# T008: US1 – multi-asset scenario persistence
# ---------------------------------------------------------------------------


def _seed_asset(app, model_id: int, name: str = "API Gateway") -> int:
    with app.app_context():
        asset = ThreatModelAsset(
            threat_model_id=model_id,
            name=name,
            asset_type=AssetType.COMPONENT,
        )
        db.session.add(asset)
        db.session.commit()
        return asset.id


def test_create_scenario_with_multiple_assets(client, app, admin_user):
    """Creating a scenario with two asset IDs persists both in assigned_assets."""
    model_id = _seed_model(app, admin_user.id)
    asset1_id = _seed_asset(app, model_id, "API Gateway")
    asset2_id = _seed_asset(app, model_id, "Database")
    _login(client, admin_user.email)
    resp = client.post(
        f"/threat/{model_id}/scenarios/new",
        data={
            "stride_category": "spoofing",
            "asset_ids": [str(asset1_id), str(asset2_id)],
            "title": "Multi-asset scenario",
            "likelihood": "3",
            "impact_score": "3",
            "status": "identified",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        scenario = ThreatScenario.query.filter_by(title="Multi-asset scenario").first()
        assert scenario is not None
        assigned_ids = {a.id for a in scenario.assigned_assets}
        assert asset1_id in assigned_ids
        assert asset2_id in assigned_ids


def test_edit_scenario_preserves_assets(client, app, admin_user):
    """Editing a scenario preserves previously assigned assets."""
    model_id = _seed_model(app, admin_user.id)
    asset1_id = _seed_asset(app, model_id, "Frontend")
    asset2_id = _seed_asset(app, model_id, "Backend")
    _login(client, admin_user.email)
    # Create with two assets
    client.post(
        f"/threat/{model_id}/scenarios/new",
        data={
            "stride_category": "tampering",
            "asset_ids": [str(asset1_id), str(asset2_id)],
            "title": "Preserve test",
            "likelihood": "2",
            "impact_score": "2",
            "status": "identified",
        },
        follow_redirects=False,
    )
    with app.app_context():
        scenario = ThreatScenario.query.filter_by(title="Preserve test").first()
        scenario_id = scenario.id
    # Edit submitting only one asset – second should be removed
    client.post(
        f"/threat/{model_id}/scenarios/{scenario_id}/edit",
        data={
            "stride_category": "tampering",
            "asset_ids": [str(asset1_id)],
            "title": "Preserve test",
            "likelihood": "2",
            "impact_score": "2",
            "status": "identified",
        },
        follow_redirects=False,
    )
    with app.app_context():
        scenario = db.session.get(ThreatScenario, scenario_id)
        assigned_ids = {a.id for a in scenario.assigned_assets}
        assert asset1_id in assigned_ids
        # asset2 was deselected – it is available so it should be removed
        assert asset2_id not in assigned_ids


def test_legacy_single_asset_scenario_saves_without_reassignment(client, app, admin_user):
    """A legacy scenario with only asset_id can be edited without re-selecting assets."""
    model_id = _seed_model(app, admin_user.id)
    asset_id = _seed_asset(app, model_id, "Legacy Asset")
    # Seed scenario the old way (only scalar asset_id, no plural assignments)
    with app.app_context():
        scenario = ThreatScenario(
            threat_model_id=model_id,
            stride_category=StrideCategory.REPUDIATION,
            asset_id=asset_id,
            title="Legacy scenario",
            likelihood=2,
            impact_score=2,
            risk_score=4,
            risk_level=RiskLevel.LOW,
            status=ScenarioStatus.IDENTIFIED,
        )
        db.session.add(scenario)
        db.session.commit()
        scenario_id = scenario.id
    _login(client, admin_user.email)
    # Edit without submitting asset_ids – should succeed (no forced reassignment)
    resp = client.post(
        f"/threat/{model_id}/scenarios/{scenario_id}/edit",
        data={
            "stride_category": "repudiation",
            "title": "Legacy scenario edited",
            "likelihood": "2",
            "impact_score": "2",
            "status": "identified",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        scenario = db.session.get(ThreatScenario, scenario_id)
        assert scenario.title == "Legacy scenario edited"


# ---------------------------------------------------------------------------
# T013: US2 – multi-category STRIDE scenario persistence
# ---------------------------------------------------------------------------


def test_create_stride_scenario_with_multiple_categories(client, app, admin_user):
    """Creating a STRIDE scenario with two categories persists both."""
    model_id = _seed_model(app, admin_user.id)
    _login(client, admin_user.email)
    resp = client.post(
        f"/threat/{model_id}/scenarios/new",
        data={
            "stride_category": "spoofing",  # legacy compat field
            "stride_category_ids": ["spoofing", "tampering"],
            "title": "Multi-cat STRIDE",
            "likelihood": "3",
            "impact_score": "3",
            "status": "identified",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        scenario = ThreatScenario.query.filter_by(title="Multi-cat STRIDE").first()
        assert scenario is not None
        values = {link.stride_category for link in scenario.stride_category_links}
        assert "spoofing" in values
        assert "tampering" in values


def test_non_stride_scenario_skips_multi_category(client, app, admin_user):
    """A PASTA scenario should not have stride_category_links set."""
    model_id = _seed_model(app, admin_user.id)
    _login(client, admin_user.email)
    resp = client.post(
        f"/threat/{model_id}/scenarios/new",
        data={
            "methodology": "PASTA",
            "stride_category": "spoofing",
            "title": "PASTA scenario",
            "likelihood": "2",
            "impact_score": "2",
            "status": "identified",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        scenario = ThreatScenario.query.filter_by(title="PASTA scenario").first()
        assert scenario is not None
        # Non-STRIDE scenarios should not gain multi-category links
        assert len(scenario.stride_category_links) == 0


# ---------------------------------------------------------------------------
# T018: US3 – review surfaces include all assigned assets/categories
# ---------------------------------------------------------------------------


def _seed_multi_scenario(app, model_id: int, asset1_id: int, asset2_id: int) -> int:
    """Seed a scenario with two assets and two categories."""
    with app.app_context():
        scenario = ThreatScenario(
            threat_model_id=model_id,
            stride_category=StrideCategory.SPOOFING,
            title="Multi-assigned scenario",
            likelihood=3,
            impact_score=3,
            risk_score=9,
            risk_level=RiskLevel.MEDIUM,
            status=ScenarioStatus.IDENTIFIED,
        )
        db.session.add(scenario)
        db.session.flush()
        asset1 = db.session.get(ThreatModelAsset, asset1_id)
        asset2 = db.session.get(ThreatModelAsset, asset2_id)
        scenario.assigned_assets = [asset1, asset2]
        scenario.stride_category_links = [
            ThreatScenarioStrideCategory(stride_category="spoofing"),
            ThreatScenarioStrideCategory(stride_category="tampering"),
        ]
        db.session.commit()
        return scenario.id


def test_scenario_detail_shows_all_assets(client, app, admin_user):
    """Scenario detail page renders all assigned asset names."""
    model_id = _seed_model(app, admin_user.id)
    asset1_id = _seed_asset(app, model_id, "Asset Alpha")
    asset2_id = _seed_asset(app, model_id, "Asset Beta")
    _seed_multi_scenario(app, model_id, asset1_id, asset2_id)
    _login(client, admin_user.email)
    with app.app_context():
        scenario = ThreatScenario.query.filter_by(title="Multi-assigned scenario").first()
        scenario_id = scenario.id
    resp = client.get(f"/threat/{model_id}/scenarios/{scenario_id}")
    assert resp.status_code == 200
    assert b"Asset Alpha" in resp.data
    assert b"Asset Beta" in resp.data


def test_csv_export_includes_plural_columns(client, app, admin_user):
    """CSV export includes assets and stride_categories columns."""
    model_id = _seed_model(app, admin_user.id)
    asset1_id = _seed_asset(app, model_id, "Export Asset A")
    asset2_id = _seed_asset(app, model_id, "Export Asset B")
    _seed_multi_scenario(app, model_id, asset1_id, asset2_id)
    _login(client, admin_user.email)
    resp = client.get(f"/threat/{model_id}/export/csv")
    assert resp.status_code == 200
    csv_text = resp.data.decode("utf-8")
    assert "assets" in csv_text
    assert "stride_categories" in csv_text
    assert "Export Asset A" in csv_text
