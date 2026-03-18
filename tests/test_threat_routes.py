"""Tests for the threat modeling module."""

from __future__ import annotations

import pytest

from scaffold import create_app
from scaffold.apps.csa.models import Control
from scaffold.apps.identity.models import ROLE_ADMIN, Role, User, UserStatus
from scaffold.apps.threat.models import (
    RiskLevel,
    ScenarioStatus,
    StrideCategory,
    ThreatModel,
    ThreatModelAsset,
    ThreatScenario,
    AssetType,
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
