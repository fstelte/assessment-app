"""Downstream scenario generation, linking, and audit-event tests for PASTA.

T027 — Scenario generation, linking, and traceability tests
"""

from __future__ import annotations

import pytest

from scaffold import create_app
from scaffold.apps.identity.models import ROLE_ADMIN, Role, User, UserStatus
from scaffold.apps.threat.models import (
    Methodology,
    PastaFinding,
    PastaFindingThreatScenarioLink,
    PastaFindingType,
    PASTA_STAGE_CODES,
    PASTA_THREAT_FINDING_TYPES,
    ScenarioStatus,
    StrideCategory,
    ThreatModel,
    ThreatScenario,
)
from scaffold.apps.threat.services import initialize_pasta_stages
from scaffold.config import Settings
from scaffold.extensions import db

_PASSWORD = "Password123!"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
        user.email = "scenario-admin@example.com"
        user.status = UserStatus.ACTIVE
        user.azure_oid = "test-oid-scenario-admin"  # bypass MFA enforcement
        user.set_password(_PASSWORD)
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        email = user.email
    return {"id": user_id, "email": email}


def _login(client, email: str, password: str = _PASSWORD):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def _pasta_model_with_threat_finding(app) -> tuple[int, int]:
    """Create a PASTA model with a THREAT-type finding and return (model_id, finding_id)."""
    with app.app_context():
        model = ThreatModel(
            title="Scenario Gen Test Model",
            methodology=Methodology.PASTA.value,
        )
        db.session.add(model)
        db.session.flush()
        initialize_pasta_stages(model)
        # Stage 4 = "threat_analysis" - use its code
        stage4_code = PASTA_STAGE_CODES[3]  # index 3 = stage 4
        stage4 = next(s for s in model.pasta_stages if s.stage_code == stage4_code)
        finding = PastaFinding(
            stage_record_id=stage4.id,
            finding_type=PastaFindingType.THREAT,
            title="SQL Injection Attack",
            description="Attacker injects malicious SQL via unescaped input",
        )
        db.session.add(finding)
        db.session.commit()
        return model.id, finding.id


def _pasta_model_with_non_threat_finding(app) -> tuple[int, int]:
    """Create a PASTA model with a non-threat finding (OBJECTIVE type)."""
    with app.app_context():
        model = ThreatModel(
            title="Non-Threat Finding Model",
            methodology=Methodology.PASTA.value,
        )
        db.session.add(model)
        db.session.flush()
        initialize_pasta_stages(model)
        stage = next(s for s in model.pasta_stages if s.stage_code == PASTA_STAGE_CODES[0])
        finding = PastaFinding(
            stage_record_id=stage.id,
            finding_type=PastaFindingType.OBJECTIVE,  # not threat-oriented
            title="Business Objective",
            description="Protect PII",
        )
        db.session.add(finding)
        db.session.commit()
        return model.id, finding.id


def _pasta_model_with_existing_scenario(app) -> tuple[int, int, int]:
    """Create a model with a threat finding and an independent scenario.
    Returns (model_id, finding_id, scenario_id).
    """
    with app.app_context():
        model = ThreatModel(
            title="Link Scenario Test Model",
            methodology=Methodology.PASTA.value,
        )
        db.session.add(model)
        db.session.flush()
        initialize_pasta_stages(model)
        stage4_code = PASTA_STAGE_CODES[3]
        stage4 = next(s for s in model.pasta_stages if s.stage_code == stage4_code)
        finding = PastaFinding(
            stage_record_id=stage4.id,
            finding_type=PastaFindingType.THREAT,
            title="Brute Force Login",
            description="Repeated failed login attempts",
        )
        db.session.add(finding)
        scenario = ThreatScenario(
            threat_model_id=model.id,
            stride_category=StrideCategory.DENIAL_OF_SERVICE,
            title="Rate Limiting Bypass",
            description="Scenario for brute-force",
            methodology="PASTA",
            status=ScenarioStatus.IDENTIFIED,
            likelihood=2,
            impact_score=3,
            risk_score=6,
        )
        db.session.add(scenario)
        db.session.commit()
        return model.id, finding.id, scenario.id


# ---------------------------------------------------------------------------
# is_threat_oriented property
# ---------------------------------------------------------------------------


class TestThreatOrientedProperty:
    def test_threat_type_is_threat_oriented(self, app):
        """THREAT finding type should be classified as threat-oriented."""
        _, finding_id = _pasta_model_with_threat_finding(app)
        with app.app_context():
            finding = PastaFinding.query.get(finding_id)
            assert finding.is_threat_oriented is True

    def test_objective_type_is_not_threat_oriented(self, app):
        _, finding_id = _pasta_model_with_non_threat_finding(app)
        with app.app_context():
            finding = PastaFinding.query.get(finding_id)
            assert finding.is_threat_oriented is False

    def test_vulnerability_type_is_threat_oriented(self, app):
        _, finding_id = _pasta_model_with_threat_finding(app)
        with app.app_context():
            # Patch the finding type to VULNERABILITY
            finding = PastaFinding.query.get(finding_id)
            finding.finding_type = PastaFindingType.VULNERABILITY
            db.session.commit()
            finding2 = PastaFinding.query.get(finding_id)
            assert finding2.is_threat_oriented is True


# ---------------------------------------------------------------------------
# Generate scenario route
# ---------------------------------------------------------------------------


class TestGenerateScenarioRoute:
    def test_generate_scenario_creates_threat_scenario(self, client, app, admin_user):
        model_id, finding_id = _pasta_model_with_threat_finding(app)
        _login(client, admin_user["email"])
        resp = client.post(
            f"/threat/{model_id}/pasta/findings/{finding_id}/generate-scenario",
            follow_redirects=False,
        )
        assert resp.status_code == 302
        with app.app_context():
            # A new ThreatScenario should have been created
            scenario = ThreatScenario.query.filter_by(
                threat_model_id=model_id
            ).first()
            assert scenario is not None

    def test_generate_scenario_uses_finding_title(self, client, app, admin_user):
        model_id, finding_id = _pasta_model_with_threat_finding(app)
        _login(client, admin_user["email"])
        client.post(
            f"/threat/{model_id}/pasta/findings/{finding_id}/generate-scenario",
            follow_redirects=True,
        )
        with app.app_context():
            scenario = ThreatScenario.query.filter_by(
                threat_model_id=model_id
            ).first()
            assert scenario is not None
            assert "SQL Injection" in scenario.title

    def test_generate_scenario_creates_link_record(self, client, app, admin_user):
        model_id, finding_id = _pasta_model_with_threat_finding(app)
        _login(client, admin_user["email"])
        client.post(
            f"/threat/{model_id}/pasta/findings/{finding_id}/generate-scenario",
            follow_redirects=True,
        )
        with app.app_context():
            link = PastaFindingThreatScenarioLink.query.filter_by(
                finding_id=finding_id,
                link_type="generated",
            ).first()
            assert link is not None

    def test_generate_scenario_for_non_threat_finding_returns_400(
        self, client, app, admin_user
    ):
        model_id, finding_id = _pasta_model_with_non_threat_finding(app)
        _login(client, admin_user["email"])
        resp = client.post(
            f"/threat/{model_id}/pasta/findings/{finding_id}/generate-scenario"
        )
        assert resp.status_code == 400

    def test_generate_scenario_logs_audit_event(self, client, app, admin_user):
        from scaffold.models import AuditLog
        model_id, finding_id = _pasta_model_with_threat_finding(app)
        _login(client, admin_user["email"])
        client.post(
            f"/threat/{model_id}/pasta/findings/{finding_id}/generate-scenario",
            follow_redirects=True,
        )
        with app.app_context():
            event = AuditLog.query.filter_by(
                event_type="pasta_scenario_generated",
            ).first()
            assert event is not None

    def test_generate_scenario_requires_login(self, client, app, admin_user):
        model_id, finding_id = _pasta_model_with_threat_finding(app)
        resp = client.post(
            f"/threat/{model_id}/pasta/findings/{finding_id}/generate-scenario"
        )
        assert resp.status_code == 302


# ---------------------------------------------------------------------------
# Link scenario route
# ---------------------------------------------------------------------------


class TestLinkScenarioRoute:
    def test_link_existing_scenario_creates_link_record(
        self, client, app, admin_user
    ):
        model_id, finding_id, scenario_id = _pasta_model_with_existing_scenario(app)
        _login(client, admin_user["email"])
        resp = client.post(
            f"/threat/{model_id}/pasta/findings/{finding_id}/link-scenario",
            data={"scenario_id": str(scenario_id)},
            follow_redirects=False,
        )
        assert resp.status_code == 302
        with app.app_context():
            link = PastaFindingThreatScenarioLink.query.filter_by(
                finding_id=finding_id,
                scenario_id=scenario_id,
            ).first()
            assert link is not None
            assert link.link_type == "linked"

    def test_link_scenario_is_idempotent(self, client, app, admin_user):
        """Linking the same scenario twice should not create duplicate records."""
        model_id, finding_id, scenario_id = _pasta_model_with_existing_scenario(app)
        _login(client, admin_user["email"])
        client.post(
            f"/threat/{model_id}/pasta/findings/{finding_id}/link-scenario",
            data={"scenario_id": str(scenario_id)},
            follow_redirects=True,
        )
        client.post(
            f"/threat/{model_id}/pasta/findings/{finding_id}/link-scenario",
            data={"scenario_id": str(scenario_id)},
            follow_redirects=True,
        )
        with app.app_context():
            count = PastaFindingThreatScenarioLink.query.filter_by(
                finding_id=finding_id,
                scenario_id=scenario_id,
            ).count()
            assert count == 1

    def test_link_non_threat_finding_returns_400(self, client, app, admin_user):
        model_id, finding_id = _pasta_model_with_non_threat_finding(app)
        with app.app_context():
            model = ThreatModel.query.get(model_id)
            scenario = ThreatScenario(
                threat_model_id=model.id,
                stride_category=StrideCategory.TAMPERING,
                title="Dummy Scenario",
                status=ScenarioStatus.IDENTIFIED,
                likelihood=1,
                impact_score=1,
                risk_score=1,
            )
            db.session.add(scenario)
            db.session.commit()
            scenario_id = scenario.id
        _login(client, admin_user["email"])
        resp = client.post(
            f"/threat/{model_id}/pasta/findings/{finding_id}/link-scenario",
            data={"scenario_id": str(scenario_id)},
        )
        assert resp.status_code == 400

    def test_link_scenario_requires_login(self, client, app, admin_user):
        model_id, finding_id, scenario_id = _pasta_model_with_existing_scenario(app)
        resp = client.post(
            f"/threat/{model_id}/pasta/findings/{finding_id}/link-scenario",
            data={"scenario_id": str(scenario_id)},
        )
        assert resp.status_code == 302

    def test_link_scenario_with_invalid_scenario_id_returns_400(
        self, client, app, admin_user
    ):
        model_id, finding_id = _pasta_model_with_threat_finding(app)
        _login(client, admin_user["email"])
        resp = client.post(
            f"/threat/{model_id}/pasta/findings/{finding_id}/link-scenario",
            data={"scenario_id": "not-a-number"},
        )
        assert resp.status_code == 400
