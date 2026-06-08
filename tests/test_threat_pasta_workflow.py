"""Stage gating and revalidation tests for the PASTA threat modeling feature.

T012 — stage gating and revalidation tests
"""

from __future__ import annotations

import pytest

from scaffold import create_app
from scaffold.apps.identity.models import ROLE_ADMIN, Role, User, UserStatus
from scaffold.apps.threat.models import (
    Methodology,
    PastaFinding,
    PastaFindingStatus,
    PastaFindingType,
    PastaStageStatus,
    PASTA_STAGE_CODES,
    ThreatModel,
)
from scaffold.apps.threat.services import initialize_pasta_stages, evaluate_stage_progression, trigger_revalidation_for_stage
from scaffold.config import Settings
from scaffold.extensions import db

_PASSWORD = "Password123!"


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
        user.email = "gate-admin@example.com"
        user.status = UserStatus.ACTIVE
        user.azure_oid = "test-oid-gate-admin"  # bypass MFA enforcement
        user.set_password(_PASSWORD)
        user.roles.append(role)
        db.session.add(user)
        db.session.commit()
        email = user.email
    return {"email": email}


def _login(client, email: str):
    return client.post(
        "/auth/login",
        data={"email": email, "password": _PASSWORD},
        follow_redirects=True,
    )


def _create_pasta_model(app) -> int:
    with app.app_context():
        model = ThreatModel(title="Gate Test Model", methodology=Methodology.PASTA.value)
        db.session.add(model)
        db.session.flush()
        initialize_pasta_stages(model)
        db.session.commit()
        return model.id


# ---------------------------------------------------------------------------
# Stage gating
# ---------------------------------------------------------------------------


def test_stage_without_findings_stays_available(app):
    """A stage with no findings and no summary must stay AVAILABLE (not progress)."""
    with app.app_context():
        model_id = _create_pasta_model(app)
        model = db.session.get(ThreatModel, model_id)
        evaluate_stage_progression(model)
        stage1 = next(s for s in model.pasta_stages if s.display_order == 1)
        assert stage1.status == PastaStageStatus.AVAILABLE


def test_stage_with_finding_but_no_summary_gate(app):
    """Stage 1 gate requires summary (requires_scope=True) — finding alone is
    insufficient until summary is also provided."""
    with app.app_context():
        model_id = _create_pasta_model(app)
        model = db.session.get(ThreatModel, model_id)
        stage1 = next(s for s in model.pasta_stages if s.display_order == 1)
        # Add a finding but no summary
        finding = PastaFinding(
            stage_record_id=stage1.id,
            finding_type=PastaFindingType.OBJECTIVE,
            title="Some objective",
            status=PastaFindingStatus.CURRENT,
        )
        db.session.add(finding)
        db.session.flush()
        evaluate_stage_progression(model)
        # Stage 1 gate requires summary too — should not be COMPLETED yet
        assert stage1.status == PastaStageStatus.AVAILABLE


def test_stage_gate_passes_with_finding_and_summary(app):
    """Stage 1 gate must pass when both a finding and a summary are present."""
    with app.app_context():
        model_id = _create_pasta_model(app)
        model = db.session.get(ThreatModel, model_id)
        stage1 = next(s for s in model.pasta_stages if s.display_order == 1)
        stage1.summary = "Protect user data."
        finding = PastaFinding(
            stage_record_id=stage1.id,
            finding_type=PastaFindingType.OBJECTIVE,
            title="Goal 1",
            status=PastaFindingStatus.CURRENT,
        )
        db.session.add(finding)
        db.session.flush()
        evaluate_stage_progression(model)
        assert stage1.status == PastaStageStatus.COMPLETED


def test_stage_locked_until_predecessor_completed(app):
    """Stage 2 must remain LOCKED until stage 1 is COMPLETED."""
    with app.app_context():
        model_id = _create_pasta_model(app)
        model = db.session.get(ThreatModel, model_id)
        stage2 = next(s for s in model.pasta_stages if s.display_order == 2)
        assert stage2.status == PastaStageStatus.LOCKED


def test_later_stages_locked_until_chain_completes(app):
    """Stages 3-7 must stay LOCKED until stage 2 is completed."""
    with app.app_context():
        model_id = _create_pasta_model(app)
        model = db.session.get(ThreatModel, model_id)
        for stage in model.pasta_stages:
            if stage.display_order > 2:
                assert stage.status == PastaStageStatus.LOCKED


def test_stage_gate_unlocks_next_in_chain(app):
    """Completing stages 1 and 2 must unlock stage 3."""
    with app.app_context():
        model_id = _create_pasta_model(app)
        model = db.session.get(ThreatModel, model_id)

        for code in PASTA_STAGE_CODES[:2]:
            stage = next(s for s in model.pasta_stages if s.stage_code == code)
            stage.status = PastaStageStatus.COMPLETED

        # Manually call progression for stage 2 being complete
        stage3 = next(s for s in model.pasta_stages if s.display_order == 3)
        assert stage3.status == PastaStageStatus.LOCKED
        evaluate_stage_progression(model)
        assert stage3.status == PastaStageStatus.AVAILABLE


# ---------------------------------------------------------------------------
# Revalidation
# ---------------------------------------------------------------------------


def test_editing_stage1_marks_completed_stage2_as_needs_revalidation(app):
    """After stage 1 content changes, completed stages after it become needs_revalidation."""
    with app.app_context():
        model_id = _create_pasta_model(app)
        model = db.session.get(ThreatModel, model_id)
        # Simulate completed stages 1, 2, 3
        for stage in model.pasta_stages:
            if stage.display_order <= 3:
                stage.status = PastaStageStatus.COMPLETED
        db.session.commit()

        model = db.session.get(ThreatModel, model_id)
        trigger_revalidation_for_stage(model, "define_objectives")
        db.session.commit()

        model = db.session.get(ThreatModel, model_id)
        for stage in model.pasta_stages:
            if stage.display_order in (2, 3):
                assert stage.status == PastaStageStatus.NEEDS_REVALIDATION


def test_revalidation_doesnt_affect_locked_stages(app):
    """LOCKED stages must not become needs_revalidation — they have no content to revalidate."""
    with app.app_context():
        model_id = _create_pasta_model(app)
        model = db.session.get(ThreatModel, model_id)
        # Stage 1 = COMPLETED, stages 2-7 stay LOCKED
        for stage in model.pasta_stages:
            if stage.display_order == 1:
                stage.status = PastaStageStatus.COMPLETED
        db.session.commit()

        model = db.session.get(ThreatModel, model_id)
        trigger_revalidation_for_stage(model, "define_objectives")
        db.session.commit()

        model = db.session.get(ThreatModel, model_id)
        for stage in model.pasta_stages:
            if stage.display_order > 1:
                assert stage.status == PastaStageStatus.LOCKED


def test_revalidation_via_stage_edit_route(client, app, admin_user):
    """Editing stage 1 content via the HTTP route must trigger revalidation for
    completed later stages."""
    _login(client, admin_user["email"])
    model_id = _create_pasta_model(app)

    # Set stages 1 and 2 as completed
    with app.app_context():
        model = db.session.get(ThreatModel, model_id)
        for stage in model.pasta_stages:
            if stage.display_order <= 2:
                stage.status = PastaStageStatus.COMPLETED
        db.session.commit()

    # Edit stage 1 with new summary content
    client.post(
        f"/threat/{model_id}/pasta/stages/{PASTA_STAGE_CODES[0]}",
        data={"summary": "Updated scope — triggers revalidation", "completion_notes": ""},
    )

    with app.app_context():
        model = db.session.get(ThreatModel, model_id)
        stage2 = next(s for s in model.pasta_stages if s.display_order == 2)
        assert stage2.status == PastaStageStatus.NEEDS_REVALIDATION


def test_finding_added_to_earlier_stage_triggers_revalidation(client, app, admin_user):
    """Adding a finding to stage 1 (a revalidation trigger stage) marks later completed stages."""
    _login(client, admin_user["email"])
    model_id = _create_pasta_model(app)

    with app.app_context():
        model = db.session.get(ThreatModel, model_id)
        for stage in model.pasta_stages:
            if stage.display_order <= 3:
                stage.status = PastaStageStatus.COMPLETED
        db.session.commit()

    client.post(
        f"/threat/{model_id}/pasta/stages/{PASTA_STAGE_CODES[0]}/findings",
        data={"finding_type": "objective", "title": "New late objective"},
    )

    with app.app_context():
        model = db.session.get(ThreatModel, model_id)
        stage2 = next(s for s in model.pasta_stages if s.display_order == 2)
        assert stage2.status == PastaStageStatus.NEEDS_REVALIDATION
