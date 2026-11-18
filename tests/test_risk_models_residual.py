"""Actual vs residual risk scoring on the Risk model (decision 20261118-0800)."""

from __future__ import annotations

from datetime import UTC, datetime

from scaffold.apps.risk.models import (
    Risk,
    RiskChance,
    RiskImpact,
    RiskSeverity,
    RiskSeverityThreshold,
)


def _risk(**kwargs) -> Risk:
    return Risk(
        title="R",
        description="R",
        impact=RiskImpact.MAJOR,  # 4
        chance=RiskChance.LIKELY,  # 4
        **kwargs,
    )


def test_not_mitigated_uses_initial_score():
    risk = _risk(residual_impact=RiskImpact.MINOR, residual_chance=RiskChance.POSSIBLE)

    assert not risk.is_mitigated
    assert risk.actual_score() == risk.score() == 16
    assert (risk.actual_chance, risk.actual_impact) == (RiskChance.LIKELY, RiskImpact.MAJOR)


def test_mitigated_with_residual_uses_residual_score():
    risk = _risk(
        mitigated_at=datetime.now(UTC),
        residual_impact=RiskImpact.MINOR,  # 2
        residual_chance=RiskChance.POSSIBLE,  # 3
    )

    assert risk.is_mitigated
    assert risk.residual_score() == 6
    assert risk.actual_score() == 6
    assert (risk.actual_chance, risk.actual_impact) == (RiskChance.POSSIBLE, RiskImpact.MINOR)


def test_mitigated_without_full_residual_falls_back_to_initial():
    risk = _risk(mitigated_at=datetime.now(UTC), residual_impact=RiskImpact.MINOR)

    assert risk.residual_score() is None
    assert risk.actual_score() == 16
    assert (risk.actual_chance, risk.actual_impact) == (RiskChance.LIKELY, RiskImpact.MAJOR)


def test_actual_severity_follows_actual_score():
    thresholds = [
        RiskSeverityThreshold(severity=RiskSeverity.LOW, min_score=1, max_score=5),
        RiskSeverityThreshold(severity=RiskSeverity.MODERATE, min_score=6, max_score=10),
        RiskSeverityThreshold(severity=RiskSeverity.HIGH, min_score=11, max_score=17),
    ]
    risk = _risk(
        mitigated_at=datetime.now(UTC),
        residual_impact=RiskImpact.MINOR,
        residual_chance=RiskChance.POSSIBLE,
    )

    assert risk.determine_severity(thresholds) is RiskSeverity.HIGH
    assert risk.determine_actual_severity(thresholds) is RiskSeverity.MODERATE
