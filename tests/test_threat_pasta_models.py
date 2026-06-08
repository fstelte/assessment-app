"""Foundational tests for the PASTA threat modeling schema and model initialization.

T010 — schema and model initialization coverage.
"""

from __future__ import annotations

import pytest

from scaffold import create_app
from scaffold.config import Settings
from scaffold.extensions import db
from scaffold.apps.threat.models import (
    Methodology,
    PastaFinding,
    PastaFindingAssetLink,
    PastaFindingStrideCategoryLink,
    PastaFindingThreatScenarioLink,
    PastaFindingStatus,
    PastaFindingType,
    PastaStageRecord,
    PastaStageStatus,
    PASTA_STAGE_CODES,
    PASTA_STAGE_LABELS,
    PASTA_STAGE_GATE_RULES,
    PASTA_THREAT_FINDING_TYPES,
    ThreatModel,
)
from scaffold.apps.threat.services import (
    initialize_pasta_stages,
    evaluate_stage_progression,
    trigger_revalidation_for_stage,
)


# ---------------------------------------------------------------------------
# App fixture (includes threat module only)
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


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def pasta_model(app):
    """Return a freshly created PASTA ThreatModel with seven stage records."""
    with app.app_context():
        model = ThreatModel(
            title="Test PASTA Model",
            methodology=Methodology.PASTA.value,
        )
        db.session.add(model)
        db.session.flush()
        initialize_pasta_stages(model)
        db.session.commit()
        yield model


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_pasta_stage_codes_count():
    """Exactly seven canonical stage codes must be defined."""
    assert len(PASTA_STAGE_CODES) == 7


def test_pasta_stage_codes_values():
    """All expected canonical codes are present and ordered."""
    expected = [
        "define_objectives",
        "define_technical_scope",
        "decompose_application",
        "analyze_threats",
        "vulnerability_analysis",
        "attack_analysis",
        "risk_impact_analysis",
    ]
    assert PASTA_STAGE_CODES == expected


def test_pasta_stage_labels_cover_all_codes():
    """Every stage code must have a human-readable label."""
    for code in PASTA_STAGE_CODES:
        assert code in PASTA_STAGE_LABELS, f"Missing label for {code}"


def test_pasta_stage_gate_rules_cover_all_codes():
    """Gate rules must be defined for every stage code."""
    for code in PASTA_STAGE_CODES:
        assert code in PASTA_STAGE_GATE_RULES, f"Missing gate rule for {code}"
        assert PASTA_STAGE_GATE_RULES[code]["min_findings"] >= 1


def test_pasta_threat_finding_types_not_empty():
    """Threat-oriented finding types must be a non-empty frozenset."""
    assert len(PASTA_THREAT_FINDING_TYPES) >= 3


# ---------------------------------------------------------------------------
# Model initialization
# ---------------------------------------------------------------------------


def test_initialize_pasta_stages_creates_seven_records(app, pasta_model):
    """initialize_pasta_stages must produce exactly 7 PastaStageRecord rows."""
    with app.app_context():
        model = db.session.get(ThreatModel, pasta_model.id)
        assert len(model.pasta_stages) == 7


def test_initialize_pasta_stages_first_is_available(app, pasta_model):
    """Stage 1 must start as AVAILABLE."""
    with app.app_context():
        model = db.session.get(ThreatModel, pasta_model.id)
        stage1 = next(s for s in model.pasta_stages if s.display_order == 1)
        assert stage1.status == PastaStageStatus.AVAILABLE


def test_initialize_pasta_stages_rest_are_locked(app, pasta_model):
    """Stages 2-7 must start as LOCKED."""
    with app.app_context():
        model = db.session.get(ThreatModel, pasta_model.id)
        for stage in model.pasta_stages:
            if stage.display_order > 1:
                assert stage.status == PastaStageStatus.LOCKED, (
                    f"Stage {stage.display_order} ({stage.stage_code}) should be LOCKED"
                )


def test_initialize_pasta_stages_display_order(app, pasta_model):
    """Stage display_order values must match the canonical sequence."""
    with app.app_context():
        model = db.session.get(ThreatModel, pasta_model.id)
        codes_in_order = [s.stage_code for s in model.pasta_stages]
        assert codes_in_order == PASTA_STAGE_CODES


# ---------------------------------------------------------------------------
# ThreatModel.is_pasta
# ---------------------------------------------------------------------------


def test_is_pasta_true_for_pasta_methodology(app):
    with app.app_context():
        m = ThreatModel(title="P", methodology=Methodology.PASTA.value)
        assert m.is_pasta is True


def test_is_pasta_false_for_stride_methodology(app):
    with app.app_context():
        m = ThreatModel(title="S", methodology=Methodology.STRIDE.value)
        assert m.is_pasta is False


def test_is_pasta_false_for_default_model(app):
    with app.app_context():
        m = ThreatModel(title="Default")
        assert m.is_pasta is False


# ---------------------------------------------------------------------------
# Stage gating and progression
# ---------------------------------------------------------------------------


def test_evaluate_stage_progression_unlocks_stage2_after_stage1_complete(app, pasta_model):
    """Completing stage 1 with a finding should unlock stage 2."""
    with app.app_context():
        model = db.session.get(ThreatModel, pasta_model.id)
        stage1 = next(s for s in model.pasta_stages if s.display_order == 1)
        stage2 = next(s for s in model.pasta_stages if s.display_order == 2)

        # Add minimum content
        stage1.summary = "Protect user PII from unauthorised disclosure."
        finding = PastaFinding(
            stage_record_id=stage1.id,
            finding_type=PastaFindingType.OBJECTIVE,
            title="Protect PII",
            status=PastaFindingStatus.CURRENT,
        )
        db.session.add(finding)
        db.session.flush()

        evaluate_stage_progression(model)
        db.session.commit()

        model = db.session.get(ThreatModel, pasta_model.id)
        stage1_after = next(s for s in model.pasta_stages if s.display_order == 1)
        stage2_after = next(s for s in model.pasta_stages if s.display_order == 2)
        assert stage1_after.status == PastaStageStatus.COMPLETED
        assert stage2_after.status == PastaStageStatus.AVAILABLE


def test_evaluate_stage_progression_no_op_for_stride_model(app):
    """evaluate_stage_progression must be a no-op for non-PASTA models."""
    with app.app_context():
        model = ThreatModel(title="Stride", methodology=Methodology.STRIDE.value)
        db.session.add(model)
        db.session.commit()
        # Should not raise or create any stage records
        evaluate_stage_progression(model)
        assert model.pasta_stages == []


# ---------------------------------------------------------------------------
# Revalidation triggers
# ---------------------------------------------------------------------------


def test_trigger_revalidation_marks_later_stages(app, pasta_model):
    """Editing stage 1 should mark completed later stages as needs_revalidation."""
    with app.app_context():
        model = db.session.get(ThreatModel, pasta_model.id)
        # Manually set stages 1-3 to COMPLETED, 4-7 to LOCKED
        for stage in model.pasta_stages:
            if stage.display_order <= 3:
                stage.status = PastaStageStatus.COMPLETED
        db.session.commit()

        model = db.session.get(ThreatModel, pasta_model.id)
        trigger_revalidation_for_stage(model, "define_objectives")
        db.session.commit()

        model = db.session.get(ThreatModel, pasta_model.id)
        for stage in model.pasta_stages:
            if stage.display_order in (2, 3):
                assert stage.status == PastaStageStatus.NEEDS_REVALIDATION, (
                    f"Stage {stage.display_order} should be needs_revalidation"
                )
            elif stage.display_order > 3:
                # These were LOCKED, not COMPLETED, so they must stay LOCKED
                assert stage.status == PastaStageStatus.LOCKED


def test_trigger_revalidation_noop_for_non_trigger_stage(app, pasta_model):
    """Editing stage 5 (vulnerability_analysis) should NOT trigger revalidation for
    stages 6-7 because vulnerability_analysis is not in the revalidation trigger set."""
    with app.app_context():
        model = db.session.get(ThreatModel, pasta_model.id)
        for stage in model.pasta_stages:
            stage.status = PastaStageStatus.COMPLETED
        db.session.commit()

        model = db.session.get(ThreatModel, pasta_model.id)
        # vulnerability_analysis is NOT in PASTA_REVALIDATION_TRIGGER_FIELDS
        trigger_revalidation_for_stage(model, "vulnerability_analysis")
        db.session.commit()

        model = db.session.get(ThreatModel, pasta_model.id)
        # All stages should remain COMPLETED (no revalidation triggered)
        for stage in model.pasta_stages:
            assert stage.status == PastaStageStatus.COMPLETED, (
                f"Stage {stage.stage_code} should remain COMPLETED"
            )


# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------


def test_pasta_finding_is_threat_oriented_for_threat_type(app, pasta_model):
    """is_threat_oriented must be True for threat-type findings."""
    with app.app_context():
        model = db.session.get(ThreatModel, pasta_model.id)
        stage4 = next(s for s in model.pasta_stages if s.stage_code == "analyze_threats")
        f = PastaFinding(
            stage_record_id=stage4.id,
            finding_type=PastaFindingType.THREAT,
            title="SQL injection",
            status=PastaFindingStatus.CURRENT,
        )
        assert f.is_threat_oriented is True


def test_pasta_finding_is_not_threat_oriented_for_objective_type(app, pasta_model):
    with app.app_context():
        model = db.session.get(ThreatModel, pasta_model.id)
        stage1 = next(s for s in model.pasta_stages if s.stage_code == "define_objectives")
        f = PastaFinding(
            stage_record_id=stage1.id,
            finding_type=PastaFindingType.OBJECTIVE,
            title="Define goal",
            status=PastaFindingStatus.CURRENT,
        )
        assert f.is_threat_oriented is False


def test_pasta_stage_record_label(app, pasta_model):
    """PastaStageRecord.label must return the human-readable stage name."""
    with app.app_context():
        model = db.session.get(ThreatModel, pasta_model.id)
        stage1 = next(s for s in model.pasta_stages if s.display_order == 1)
        assert stage1.label == "Define Objectives"
