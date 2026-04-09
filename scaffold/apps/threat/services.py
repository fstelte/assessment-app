"""Business logic for threat modeling workflows."""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime

from ..identity.models import User
from .models import RiskLevel, ScenarioStatus, StrideCategory, ThreatScenario, TreatmentOption


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


# ---------------------------------------------------------------------------
# Risk workspace synchronisation
# ---------------------------------------------------------------------------

_EXCLUDED_STATUSES = {ScenarioStatus.MITIGATED, ScenarioStatus.ACCEPTED, ScenarioStatus.CLOSED}

_CHANCE_MAP = {
    1: "rare",
    2: "unlikely",
    3: "possible",
    4: "likely",
    5: "almost_certain",
}

_IMPACT_MAP = {
    1: "insignificant",
    2: "minor",
    3: "moderate",
    4: "major",
    5: "catastrophic",
}

_TREATMENT_MAP = {
    TreatmentOption.ACCEPT: "accept",
    TreatmentOption.MITIGATE: "mitigate",
    TreatmentOption.TRANSFER: "transfer",
    TreatmentOption.AVOID: "avoid",
}


def _components_for_scenario(scenario: ThreatScenario) -> list:
    """Return BIA components to link when syncing to the risk workspace.

    Resolves the single BIA component whose name matches the scenario's linked
    asset.  Falls back to all eligible components in the threat model's context
    scope only when no asset is linked to the scenario or no name match is found.
    """
    from ..bia.models import Component
    from ..risk.services import eligible_component_query

    context_scope_id = (
        scenario.threat_model.context_scope_id
        if scenario.threat_model
        else None
    )
    if not context_scope_id:
        return []

    # Use the asset that is directly linked to this specific scenario.
    asset_name = scenario.asset.name if scenario.asset else None
    if asset_name:
        matched = (
            eligible_component_query()
            .filter(
                Component.context_scope_id == context_scope_id,
                Component.name == asset_name,
            )
            .all()
        )
        if matched:
            return matched

        # Try without the eligibility filter so ineligible components are also accepted.
        matched_all = (
            Component.query
            .filter(
                Component.context_scope_id == context_scope_id,
                Component.name == asset_name,
            )
            .all()
        )
        if matched_all:
            return matched_all

    # Fallback: all eligible components in the scope (no asset linked to the scenario).
    eligible = (
        eligible_component_query()
        .filter(Component.context_scope_id == context_scope_id)
        .all()
    )
    if eligible:
        return eligible

    return Component.query.filter_by(context_scope_id=context_scope_id).all()


def sync_scenario_to_risk(scenario: ThreatScenario) -> None:
    """Create, update, or close the linked Risk entry based on the scenario state.

    When the scenario status is mitigated, accepted, or closed the linked risk
    (if any) is closed.  For all other statuses the risk is created or kept in
    sync with the scenario's inherent risk fields.
    """
    from ...extensions import db
    from ..risk.models import Risk, RiskChance, RiskImpact, RiskTreatmentOption

    if scenario.status in _EXCLUDED_STATUSES or scenario.treatment is not TreatmentOption.MITIGATE:
        if scenario.risk_id:
            risk = db.session.get(Risk, scenario.risk_id)
            if risk and not risk.is_closed:
                risk.closed_at = datetime.now(UTC)
        return

    likelihood = max(1, min(5, scenario.likelihood or 1))
    impact = max(1, min(5, scenario.impact_score or 1))
    treatment_str = _TREATMENT_MAP.get(scenario.treatment, "mitigate") if scenario.treatment else "mitigate"

    fields: dict = {
        "title": scenario.title,
        "description": scenario.description or scenario.title,
        "chance": RiskChance(str(_CHANCE_MAP[likelihood])),
        "impact": RiskImpact(str(_IMPACT_MAP[impact])),
        "treatment": RiskTreatmentOption(treatment_str),
    }

    if scenario.risk_id is None:
        risk = Risk(discovered_on=date.today(), **fields)
        risk.components = _components_for_scenario(scenario)
        db.session.add(risk)
        db.session.flush()
        scenario.risk_id = risk.id
    else:
        risk = db.session.get(Risk, scenario.risk_id)
        if risk:
            for key, value in fields.items():
                setattr(risk, key, value)
            if risk.is_closed:
                risk.closed_at = None
            # Always keep components in sync with the threat model's assets.
            risk.components = _components_for_scenario(scenario)

