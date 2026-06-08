"""Route and workflow tests for the PASTA threat modeling feature.

T011 — create/progress/reopen workflow tests
T013 — authorization and audit regression tests
"""

from __future__ import annotations

import pytest

from scaffold import create_app
from scaffold.apps.identity.models import ROLE_ADMIN, ROLE_ASSESSMENT_MANAGER, Role, User, UserStatus
from scaffold.apps.threat.models import (
    Methodology,
    PastaFinding,
    PastaFindingStatus,
    PastaFindingType,
    PastaStageStatus,
    PASTA_STAGE_CODES,
    ThreatModel,
)
from scaffold.apps.threat.services import initialize_pasta_stages
from scaffold.config import Settings
from scaffold.extensions import db

_PASSWORD = "Password123!"


# ---------------------------------------------------------------------------
# App and user fixtures
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
        user.email = "pasta-admin@example.com"
        user.status = UserStatus.ACTIVE
        user.azure_oid = "test-oid-admin"  # bypass MFA enforcement
        user.set_password(_PASSWORD)
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        email = user.email
    # Return a simple dict so the email is accessible outside the session
    return {"email": email}


@pytest.fixture
def manager_user(app):
    with app.app_context():
        role = Role.query.filter_by(name=ROLE_ASSESSMENT_MANAGER).first()
        if role is None:
            role = Role(name=ROLE_ASSESSMENT_MANAGER)
            db.session.add(role)
        user = User()
        user.email = "pasta-manager@example.com"
        user.status = UserStatus.ACTIVE
        user.azure_oid = "test-oid-manager"  # bypass MFA enforcement
        user.set_password(_PASSWORD)
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        email = user.email
    return {"email": email}


@pytest.fixture
def viewer_user(app):
    """A regular authenticated user with no admin or manager role."""
    with app.app_context():
        user = User()
        user.email = "pasta-viewer@example.com"
        user.status = UserStatus.ACTIVE
        user.azure_oid = "test-oid-viewer"  # bypass MFA enforcement
        user.set_password(_PASSWORD)
        db.session.add(user)
        db.session.commit()
        email = user.email
    return {"email": email}


def _login(client, email: str, password: str = _PASSWORD):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def _pasta_model_id(app) -> int:
    """Create a PASTA model and return its ID."""
    with app.app_context():
        model = ThreatModel(
            title="PASTA Workflow Test",
            methodology=Methodology.PASTA.value,
        )
        db.session.add(model)
        db.session.flush()
        initialize_pasta_stages(model)
        db.session.commit()
        return model.id


# ---------------------------------------------------------------------------
# T011 — Create / progress / reopen workflow tests
# ---------------------------------------------------------------------------


def test_create_pasta_model_via_form(client, app, admin_user):
    """POST /threat/new with methodology=PASTA creates a PASTA model with 7 stages."""
    _login(client, admin_user["email"])
    resp = client.post(
        "/threat/new",
        data={
            "title": "My PASTA Model",
            "methodology": "PASTA",
            "description": "",
            "scope": "",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (301, 302)

    with app.app_context():
        model = ThreatModel.query.filter_by(title="My PASTA Model").first()
        assert model is not None
        assert model.methodology == "PASTA"
        assert model.is_pasta is True
        assert len(model.pasta_stages) == 7


def test_pasta_model_detail_shows_stages(client, app, admin_user):
    """GET /threat/<id> for a PASTA model renders the stage list."""
    model_id = _pasta_model_id(app)
    _login(client, admin_user["email"])
    resp = client.get(f"/threat/{model_id}")
    assert resp.status_code == 200
    body = resp.data.decode()
    # Stage 1 must be shown as available
    assert "Define Objectives" in body


def test_stage1_available_stage2_locked_on_initial_detail(client, app, admin_user):
    """Stage 1 must show Available, stage 2 must show Locked on initial load."""
    model_id = _pasta_model_id(app)
    _login(client, admin_user["email"])
    resp = client.get(f"/threat/{model_id}")
    body = resp.data.decode()
    assert "Available" in body
    assert "Locked" in body


def test_edit_stage1_saves_summary(client, app, admin_user):
    """POST to stage edit saves stage summary."""
    model_id = _pasta_model_id(app)
    _login(client, admin_user["email"])
    stage_code = PASTA_STAGE_CODES[0]
    resp = client.post(
        f"/threat/{model_id}/pasta/stages/{stage_code}",
        data={"summary": "Protect customer data", "completion_notes": ""},
        follow_redirects=False,
    )
    assert resp.status_code in (301, 302)

    with app.app_context():
        model = db.session.get(ThreatModel, model_id)
        stage = next(s for s in model.pasta_stages if s.stage_code == stage_code)
        assert stage.summary == "Protect customer data"


def test_adding_finding_to_stage1_and_gate_progression(client, app, admin_user):
    """Adding a finding + summary to stage 1 should progress it to COMPLETED
    and unlock stage 2 to AVAILABLE."""
    model_id = _pasta_model_id(app)
    _login(client, admin_user["email"])
    stage_code = PASTA_STAGE_CODES[0]

    # First set the summary (required by gate rule)
    client.post(
        f"/threat/{model_id}/pasta/stages/{stage_code}",
        data={"summary": "Secure customer PII", "completion_notes": ""},
    )
    # Then add a finding
    client.post(
        f"/threat/{model_id}/pasta/stages/{stage_code}/findings",
        data={
            "finding_type": "objective",
            "title": "Protect PII at rest",
            "description": "Encrypt all PII in storage",
        },
    )

    with app.app_context():
        model = db.session.get(ThreatModel, model_id)
        stage1 = next(s for s in model.pasta_stages if s.display_order == 1)
        stage2 = next(s for s in model.pasta_stages if s.display_order == 2)
        assert stage1.status == PastaStageStatus.COMPLETED
        assert stage2.status == PastaStageStatus.AVAILABLE


def test_model_detail_reopen_shows_stage_content(client, app, admin_user):
    """Reopening a PASTA model after saving shows the saved summary."""
    model_id = _pasta_model_id(app)
    _login(client, admin_user["email"])
    stage_code = PASTA_STAGE_CODES[0]
    client.post(
        f"/threat/{model_id}/pasta/stages/{stage_code}",
        data={"summary": "Resumed from saved state", "completion_notes": ""},
    )
    resp = client.get(f"/threat/{model_id}")
    body = resp.data.decode()
    assert "Resumed from saved state" in body


def test_edit_locked_stage_redirects(client, app, admin_user):
    """Attempting to edit a LOCKED stage should redirect (not render the form)."""
    model_id = _pasta_model_id(app)
    _login(client, admin_user["email"])
    # Stage 2 starts LOCKED
    locked_code = PASTA_STAGE_CODES[1]
    resp = client.post(
        f"/threat/{model_id}/pasta/stages/{locked_code}",
        data={"summary": "Should not save", "completion_notes": ""},
        follow_redirects=False,
    )
    # Should redirect back to model detail (locked guard)
    assert resp.status_code in (301, 302)

    with app.app_context():
        model = db.session.get(ThreatModel, model_id)
        stage2 = next(s for s in model.pasta_stages if s.stage_code == locked_code)
        assert stage2.summary is None or stage2.summary == ""


# ---------------------------------------------------------------------------
# T013 — Authorization and audit regression tests
# ---------------------------------------------------------------------------


def test_unauthenticated_user_cannot_create_pasta_model(client):
    """Unauthenticated POST to /threat/new must return 302/403."""
    resp = client.post(
        "/threat/new",
        data={"title": "Unauth", "methodology": "PASTA"},
        follow_redirects=False,
    )
    # Should redirect to login or return 403
    assert resp.status_code in (302, 403)


def test_viewer_cannot_create_pasta_model(client, app, viewer_user):
    """Viewer user (no admin/manager role) must receive 403 on mutation routes."""
    _login(client, viewer_user["email"])
    resp = client.post(
        "/threat/new",
        data={"title": "Viewer Created", "methodology": "PASTA"},
        follow_redirects=False,
    )
    assert resp.status_code == 403


def test_viewer_cannot_edit_stage(client, app, viewer_user):
    model_id = _pasta_model_id(app)
    _login(client, viewer_user["email"])
    resp = client.post(
        f"/threat/{model_id}/pasta/stages/{PASTA_STAGE_CODES[0]}",
        data={"summary": "Viewer edit", "completion_notes": ""},
        follow_redirects=False,
    )
    assert resp.status_code == 403


def test_viewer_cannot_create_finding(client, app, viewer_user):
    model_id = _pasta_model_id(app)
    _login(client, viewer_user["email"])
    resp = client.post(
        f"/threat/{model_id}/pasta/stages/{PASTA_STAGE_CODES[0]}/findings",
        data={"finding_type": "objective", "title": "Sneaky"},
        follow_redirects=False,
    )
    assert resp.status_code == 403


def test_manager_can_create_pasta_model(client, app, manager_user):
    """Assessment manager must be allowed to create a PASTA model."""
    _login(client, manager_user["email"])
    resp = client.post(
        "/threat/new",
        data={
            "title": "Manager PASTA Model",
            "methodology": "PASTA",
            "description": "",
            "scope": "",
        },
        follow_redirects=False,
    )
    assert resp.status_code in (301, 302)
    with app.app_context():
        model = ThreatModel.query.filter_by(title="Manager PASTA Model").first()
        assert model is not None
        assert model.is_pasta is True


def test_viewer_can_read_pasta_model_detail(client, app, viewer_user):
    """Viewer must be able to GET the PASTA model detail (read-only)."""
    model_id = _pasta_model_id(app)
    _login(client, viewer_user["email"])
    resp = client.get(f"/threat/{model_id}")
    assert resp.status_code == 200


def test_create_pasta_model_audit_event_logged(client, app, admin_user):
    """Creating a PASTA model should log a threat_model_created audit event."""

    _login(client, admin_user["email"])
    client.post(
        "/threat/new",
        data={
            "title": "Audit Pasta",
            "methodology": "PASTA",
            "description": "",
            "scope": "",
        },
        follow_redirects=True,
    )
    with app.app_context():
        from scaffold.models import AuditLog
        model = ThreatModel.query.filter_by(title="Audit Pasta").first()
        assert model is not None
        event = AuditLog.query.filter_by(
            event_type="threat_model_created",
            target_type="threat_model",
            target_id=str(model.id),
        ).first()
        assert event is not None


# ---------------------------------------------------------------------------
# US2 — Risk scoring form (T019) and publish route (T020)
# ---------------------------------------------------------------------------

from scaffold.apps.threat.models import (
    PastaFindingType,
    PastaPublicationState,
    PastaRiskConclusion,
    PastaStageStatus,
)


def _stage7_finding_id(app, model_id):
    """Helper: add a risk_conclusion finding to stage 7 and return its id."""
    with app.app_context():
        model = db.session.get(ThreatModel, model_id)
        stage7 = next(s for s in model.pasta_stages if s.stage_code == "risk_impact_analysis")
        finding = PastaFinding(
            stage_record_id=stage7.id,
            finding_type=PastaFindingType.RISK_CONCLUSION,
            title="Auth bypass risk",
            description="Session tokens can be forged.",
            status=PastaFindingStatus.CURRENT,
        )
        db.session.add(finding)
        db.session.commit()
        return finding.id


def test_risk_conclusion_form_get_returns_200(client, app, admin_user):
    """GET pasta_risk_conclusion_edit must return 200 for a valid finding."""
    model_id = _pasta_model_id(app)
    finding_id = _stage7_finding_id(app, model_id)
    _login(client, admin_user["email"])
    resp = client.get(f"/threat/{model_id}/pasta/findings/{finding_id}/risk")
    assert resp.status_code == 200


def test_risk_conclusion_form_post_saves_scores(client, app, admin_user):
    """POST to pasta_risk_conclusion_edit must persist likelihood and impact scores."""
    model_id = _pasta_model_id(app)
    finding_id = _stage7_finding_id(app, model_id)
    _login(client, admin_user["email"])
    resp = client.post(
        f"/threat/{model_id}/pasta/findings/{finding_id}/risk",
        data={
            "likelihood_score": "3",
            "impact_score": "4",
            "treatment": "mitigate",
            "publication_notes": "",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        finding = db.session.get(PastaFinding, finding_id)
        assert finding.risk_conclusion is not None
        assert finding.risk_conclusion.likelihood_score == 3
        assert finding.risk_conclusion.impact_score == 4
        assert finding.risk_conclusion.overall_score is not None


def test_risk_conclusion_form_unauthenticated_redirects(client, app):
    """Unauthenticated request to scoring form must redirect to login."""
    model_id = _pasta_model_id(app)
    finding_id = _stage7_finding_id(app, model_id)
    resp = client.get(f"/threat/{model_id}/pasta/findings/{finding_id}/risk")
    assert resp.status_code in (302, 401)


def test_risk_conclusion_publish_route_publishes(client, app, admin_user):
    """POST to pasta_publish_risk with publishable conclusion must set state=PUBLISHED."""
    model_id = _pasta_model_id(app)
    finding_id = _stage7_finding_id(app, model_id)
    # First save scores
    _login(client, admin_user["email"])
    client.post(
        f"/threat/{model_id}/pasta/findings/{finding_id}/risk",
        data={
            "likelihood_score": "2",
            "impact_score": "3",
            "treatment": "mitigate",
            "publication_notes": "",
        },
        follow_redirects=True,
    )
    # Then publish
    resp = client.post(
        f"/threat/{model_id}/pasta/findings/{finding_id}/publish-risk",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        finding = db.session.get(PastaFinding, finding_id)
        assert finding.risk_conclusion.publication_state == PastaPublicationState.PUBLISHED
        assert finding.risk_conclusion.published_risk_id is not None


def test_risk_conclusion_publish_blocked_without_scores(client, app, admin_user):
    """Publishing without scores must NOT change state and must flash a blocked message."""
    model_id = _pasta_model_id(app)
    finding_id = _stage7_finding_id(app, model_id)
    _login(client, admin_user["email"])
    # Do NOT post scores first
    resp = client.post(
        f"/threat/{model_id}/pasta/findings/{finding_id}/publish-risk",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    with app.app_context():
        finding = db.session.get(PastaFinding, finding_id)
        # Either no conclusion at all, or state is NOT_PUBLISHED
        if finding.risk_conclusion:
            assert finding.risk_conclusion.publication_state != PastaPublicationState.PUBLISHED


def test_risk_conclusion_publish_audit_event_logged(client, app, admin_user):
    """Publishing a conclusion must log a pasta_risk_conclusion_published audit event."""
    model_id = _pasta_model_id(app)
    finding_id = _stage7_finding_id(app, model_id)
    _login(client, admin_user["email"])
    client.post(
        f"/threat/{model_id}/pasta/findings/{finding_id}/risk",
        data={"likelihood_score": "4", "impact_score": "3", "treatment": "mitigate", "publication_notes": ""},
        follow_redirects=True,
    )
    client.post(
        f"/threat/{model_id}/pasta/findings/{finding_id}/publish-risk",
        follow_redirects=True,
    )
    with app.app_context():
        from scaffold.models import AuditLog
        event = AuditLog.query.filter_by(
            event_type="pasta_risk_conclusion_published",
        ).first()
        assert event is not None
