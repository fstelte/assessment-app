"""Business logic for threat modeling workflows."""

from __future__ import annotations

import csv
import io

from ..identity.models import User
from .models import RiskLevel, ScenarioStatus, StrideCategory, ThreatScenario


RISK_LEVEL_MATRIX: dict[tuple[str, str], str] = {
    ("low", "low"): "low",
    ("low", "medium"): "low",
    ("low", "high"): "medium",
    ("medium", "low"): "low",
    ("medium", "medium"): "medium",
    ("medium", "high"): "high",
    ("high", "low"): "medium",
    ("high", "medium"): "high",
    ("high", "high"): "critical",
}


def _band(value: int) -> str:
    if value <= 2:
        return "low"
    if value == 3:
        return "medium"
    return "high"


def compute_risk_score(likelihood: int, impact: int) -> tuple[int, str]:
    """Return (score, level_string) for the given likelihood and impact (1-5 each)."""

    score = likelihood * impact
    level = RISK_LEVEL_MATRIX[(_band(likelihood), _band(impact))]
    return score, level


def apply_risk_score(scenario: ThreatScenario) -> None:
    """Recalculate and persist risk_score/risk_level on the given scenario."""

    score, level_str = compute_risk_score(scenario.likelihood, scenario.impact_score)
    scenario.risk_score = score
    scenario.risk_level = RiskLevel(level_str)


def apply_residual_risk_score(scenario: ThreatScenario) -> None:
    """Recalculate residual_risk_score/level if both inputs are set."""

    if scenario.residual_likelihood and scenario.residual_impact:
        score, level_str = compute_risk_score(scenario.residual_likelihood, scenario.residual_impact)
        scenario.residual_risk_score = score
        scenario.residual_risk_level = RiskLevel(level_str)
    else:
        scenario.residual_risk_score = None
        scenario.residual_risk_level = None


def user_choices(include_blank: bool = True) -> list[tuple[str, str]]:
    """Build SelectField choices from all users."""

    choices = []
    if include_blank:
        choices.append(("", "— unassigned —"))
    for user in User.query.order_by(User.email).all():
        choices.append((str(user.id), user.email))
    return choices


def stride_choices() -> list[tuple[str, str]]:
    return [(c.value, c.value.replace("_", " ").title()) for c in StrideCategory]


def status_choices() -> list[tuple[str, str]]:
    return [(s.value, s.value.replace("_", " ").title()) for s in ScenarioStatus]


def export_scenarios_csv(scenarios: list[ThreatScenario]) -> str:
    """Return a UTF-8 CSV string for the given list of ThreatScenario objects."""

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "title",
            "stride_category",
            "asset",
            "likelihood",
            "impact_score",
            "risk_score",
            "risk_level",
            "treatment",
            "status",
            "mitigation",
            "owner",
        ]
    )
    for s in scenarios:
        writer.writerow(
            [
                s.id,
                s.title,
                s.stride_category.value if s.stride_category else "",
                s.asset.name if s.asset else "",
                s.likelihood,
                s.impact_score,
                s.risk_score,
                s.risk_level.value if s.risk_level else "",
                s.treatment.value if s.treatment else "",
                s.status.value if s.status else "",
                s.mitigation or "",
                s.owner.email if s.owner else "",
            ]
        )
    return output.getvalue()
