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


def scenario_asset_names(scenario: ThreatScenario) -> list[str]:
    """Return display names for all assets assigned to a scenario.

    Prefers the plural ``assigned_assets`` relationship.  Falls back to the
    legacy scalar ``asset`` when the plural collection is empty (e.g. on
    objects that pre-date backfill or during form preview).
    """

    if scenario.assigned_assets:
        return [a.name for a in scenario.assigned_assets]
    if scenario.asset:
        return [scenario.asset.name]
    return []


def scenario_stride_values(scenario: ThreatScenario) -> list[str]:
    """Return STRIDE-LM values for all categories assigned to a scenario.

    Prefers the plural ``stride_category_links`` relationship.  Falls back to
    the legacy scalar ``stride_category`` for STRIDE scenarios.
    """

    if scenario.stride_category_links:
        return [link.stride_category for link in scenario.stride_category_links]
    if scenario.stride_category:
        return [scenario.stride_category.value]
    return []


def set_scenario_assets(scenario: ThreatScenario, asset_ids: list[int], model_assets: list) -> None:
    """Replace the plural asset assignments on a scenario.

    Preserves any assets that are no longer in *model_assets* (historical/
    unavailable) as read-only entries so existing records are not silently
    lost on re-save.

    :param scenario: the scenario being edited
    :param asset_ids: IDs selected by the user from the form
    :param model_assets: current assets available in the threat model
    """

    available_ids = {a.id for a in model_assets}
    requested_ids = set(asset_ids)

    # IDs that were previously assigned but are no longer available
    current_ids = {a.id for a in scenario.assigned_assets}
    unavailable_preserved = current_ids - available_ids

    desired_ids = requested_ids | unavailable_preserved
    asset_map = {a.id: a for a in model_assets}

    # Also keep a lookup for already-assigned unavailable assets
    for a in scenario.assigned_assets:
        if a.id not in asset_map:
            asset_map[a.id] = a

    new_assets = [asset_map[aid] for aid in desired_ids if aid in asset_map]
    scenario.assigned_assets = new_assets


def set_scenario_stride_categories(
    scenario: ThreatScenario,
    category_values: list[str],
) -> None:
    """Replace the plural STRIDE-LM category assignments on a scenario.

    Preserves categories that are no longer valid enum members (historical)
    as read-only entries.

    :param scenario: the scenario being edited
    :param category_values: string values selected by the user
    """
    from .models import ThreatScenarioStrideCategory

    valid_values = {c.value for c in StrideCategory}
    requested = set(category_values) & valid_values

    # Keep historical unavailable categories
    current_values = {link.stride_category for link in scenario.stride_category_links}
    unavailable_preserved = current_values - valid_values
    desired = requested | unavailable_preserved

    # Compute diff
    to_remove = [
        link for link in scenario.stride_category_links
        if link.stride_category not in desired
    ]
    to_add = desired - current_values

    for link in to_remove:
        scenario.stride_category_links.remove(link)
    for value in to_add:
        scenario.stride_category_links.append(
            ThreatScenarioStrideCategory(stride_category=value)
        )


def export_scenarios_csv(scenarios: list[ThreatScenario]) -> str:
    """Return a UTF-8 CSV string for the given list of ThreatScenario objects.

    Plural columns ``assets`` and ``stride_categories`` contain semicolon-
    separated values.  Compatibility alias columns ``asset`` and
    ``stride_category`` are preserved for one release cycle.
    """

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "title",
            # plural columns (new)
            "assets",
            "stride_categories",
            # compatibility aliases (deprecated – one release cycle)
            "stride_category",
            "asset",
            # remaining columns
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
        asset_names = scenario_asset_names(s)
        stride_values = scenario_stride_values(s)
        writer.writerow(
            [
                s.id,
                s.title,
                "; ".join(asset_names),
                "; ".join(stride_values),
                stride_values[0] if stride_values else "",
                asset_names[0] if asset_names else "",
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
        risk.controls = list(scenario.controls)
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
            # Keep controls in sync with the linked threat scenario.
            risk.controls = list(scenario.controls)


# ---------------------------------------------------------------------------
# PASTA workflow services
# ---------------------------------------------------------------------------


def initialize_pasta_stages(threat_model) -> None:
    """Create the seven canonical PastaStageRecord rows for a new PASTA model.

    Stage 1 is set to AVAILABLE; all others start LOCKED.
    """
    from .models import (
        PASTA_STAGE_CODES,
        PastaStageRecord,
        PastaStageStatus,
    )
    from ...extensions import db

    for idx, code in enumerate(PASTA_STAGE_CODES, start=1):
        status = PastaStageStatus.AVAILABLE if idx == 1 else PastaStageStatus.LOCKED
        stage = PastaStageRecord(
            threat_model_id=threat_model.id,
            stage_code=code,
            display_order=idx,
            status=status,
        )
        db.session.add(stage)


def _stage_meets_gate(stage_record) -> bool:
    """Return True if the stage satisfies its minimum content gate (FR-003B)."""
    from .models import PASTA_STAGE_GATE_RULES, PastaFindingStatus

    rules = PASTA_STAGE_GATE_RULES.get(stage_record.stage_code, {})
    active_findings = [
        f for f in stage_record.findings
        if f.status.value != PastaFindingStatus.ARCHIVED.value
    ]
    if len(active_findings) < rules.get("min_findings", 1):
        return False
    if rules.get("requires_scope") and not (stage_record.summary or "").strip():
        return False
    if rules.get("requires_notes") and not (stage_record.completion_notes or "").strip():
        # notes not strictly required for gate unlock — only summary counts
        pass
    return True


def evaluate_stage_progression(threat_model) -> None:
    """After saving a stage, unlock the next stage if the gate is satisfied.

    Raises no exceptions; silently does nothing for non-PASTA models.
    """
    from .models import (
        PASTA_STAGE_CODES,
        PastaStageStatus,
    )

    if not threat_model.is_pasta:
        return

    stages: dict[str, object] = {s.stage_code: s for s in threat_model.pasta_stages}
    for idx, code in enumerate(PASTA_STAGE_CODES):
        stage = stages.get(code)
        if stage is None:
            continue
        if stage.status in (PastaStageStatus.COMPLETED, PastaStageStatus.NEEDS_REVALIDATION):
            # Already completed — check if the next stage should be unlocked
            next_codes = PASTA_STAGE_CODES[idx + 1 :]
            if next_codes:
                next_stage = stages.get(next_codes[0])
                if next_stage and next_stage.status == PastaStageStatus.LOCKED:
                    next_stage.status = PastaStageStatus.AVAILABLE
        elif stage.status == PastaStageStatus.AVAILABLE:
            if _stage_meets_gate(stage):
                # Mark current stage completed and unlock next
                from datetime import UTC, datetime
                from flask_login import current_user

                stage.status = PastaStageStatus.COMPLETED
                stage.completed_at = datetime.now(UTC)
                if current_user and current_user.is_authenticated:
                    stage.completed_by_id = current_user.id
                next_codes = PASTA_STAGE_CODES[idx + 1 :]
                if next_codes:
                    next_stage = stages.get(next_codes[0])
                    if next_stage and next_stage.status == PastaStageStatus.LOCKED:
                        next_stage.status = PastaStageStatus.AVAILABLE


def trigger_revalidation_for_stage(threat_model, edited_stage_code: str) -> None:
    """Mark all stages after the edited stage as needs_revalidation (FR-018B).

    Only stages that are COMPLETED or already NEEDS_REVALIDATION are changed
    (LOCKED and AVAILABLE stages are unaffected — no content to revalidate).
    """
    from .models import (
        PASTA_STAGE_CODES,
        PASTA_REVALIDATION_TRIGGER_FIELDS,
        PastaStageStatus,
    )

    if edited_stage_code not in PASTA_REVALIDATION_TRIGGER_FIELDS:
        return

    edited_idx = PASTA_STAGE_CODES.index(edited_stage_code)
    later_codes = set(PASTA_STAGE_CODES[edited_idx + 1 :])
    for stage in threat_model.pasta_stages:
        if stage.stage_code in later_codes and stage.status in (
            PastaStageStatus.COMPLETED,
            PastaStageStatus.NEEDS_REVALIDATION,
        ):
            stage.status = PastaStageStatus.NEEDS_REVALIDATION


def bootstrap_pasta_from_stride(source_model, current_user_obj, title: str | None = None):
    """Create a new PASTA ThreatModel bootstrapped from an existing STRIDE-LM model.

    Copies metadata, assets (by reference/name), and records the source model
    traceability.  Does NOT mutate the source model.

    Returns the newly created ThreatModel (not yet committed to the session).
    """
    from .models import Methodology, ThreatModel, ThreatModelAsset
    from ...extensions import db

    new_model = ThreatModel(
        title=title or f"{source_model.title} (PASTA)",
        description=source_model.description,
        scope=source_model.scope,
        owner_id=current_user_obj.id if current_user_obj else None,
        methodology=Methodology.PASTA.value,
        bootstrap_source_model_id=source_model.id,
        product_id=source_model.product_id,
        dpia_id=source_model.dpia_id,
        context_scope_id=source_model.context_scope_id,
    )
    db.session.add(new_model)
    db.session.flush()  # get new_model.id

    # Copy assets (new rows, same names/types)
    for asset in source_model.assets:
        db.session.add(
            ThreatModelAsset(
                threat_model_id=new_model.id,
                name=asset.name,
                asset_type=asset.asset_type,
                description=asset.description,
                order=asset.order,
            )
        )

    # Initialize PASTA stage records
    initialize_pasta_stages(new_model)
    return new_model


def export_pasta_findings_csv(threat_model) -> str:
    """Return CSV string of all PASTA findings across all stages.

    One row per finding.  Headers: stage, finding_type, title, description,
    evidence, priority, stride_mappings, linked_scenarios.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "stage",
            "finding_type",
            "title",
            "description",
            "evidence",
            "priority",
            "stride_mappings",
            "linked_scenarios",
        ]
    )
    for stage in threat_model.pasta_stages:
        for finding in stage.findings:
            stride_vals = "; ".join(link.stride_category for link in finding.stride_links)
            scenario_ids = "; ".join(
                str(link.scenario_id) for link in finding.scenario_links
            )
            writer.writerow(
                [
                    stage.stage_code,
                    finding.finding_type.value,
                    finding.title,
                    finding.description or "",
                    finding.evidence or "",
                    finding.priority or "",
                    stride_vals,
                    scenario_ids,
                ]
            )
    return output.getvalue()


# ---------------------------------------------------------------------------
# PASTA risk-conclusion scoring and publication helpers (T007)
# ---------------------------------------------------------------------------


def compute_pasta_overall_score(likelihood: int, impact: int) -> tuple[int, str]:
    """Return (overall_score, risk_level_string) for a PASTA risk conclusion.

    Delegates to the same matrix used by STRIDE scenarios for comparability (FR-008).
    """
    return compute_risk_score(likelihood, impact)


def apply_pasta_conclusion_scores(conclusion) -> None:
    """Recalculate and persist likelihood/impact/overall_score on a PastaRiskConclusion."""
    if conclusion.likelihood_score and conclusion.impact_score:
        score, _ = compute_pasta_overall_score(conclusion.likelihood_score, conclusion.impact_score)
        conclusion.overall_score = score


def publish_pasta_conclusion_to_risk(conclusion, published_by_user) -> None:
    """Create or refresh the linked Risk workspace record from a PastaRiskConclusion.

    - First publish: creates a new Risk row and stores the link on the conclusion.
    - Republish: refreshes the existing linked Risk row in-place (no duplicate).
    - PASTA remains the source of truth; the Risk row is a projection.

    Raises ValueError if the conclusion is not publishable (FR-011A).
    """
    import datetime as _dt
    from datetime import UTC, datetime

    from ...extensions import db
    from ..risk.models import Risk, RiskChance, RiskImpact, RiskTreatmentOption
    from .models import PastaPublicationState

    if not conclusion.is_publishable:
        raise ValueError("pasta.risk_conclusion.error.not_publishable")

    likelihood = max(1, min(5, conclusion.likelihood_score or 1))
    impact = max(1, min(5, conclusion.impact_score or 1))

    treatment_str = conclusion.treatment or "mitigate"
    try:
        treatment = RiskTreatmentOption(treatment_str)
    except ValueError:
        treatment = RiskTreatmentOption.MITIGATE

    finding = conclusion.finding
    title = finding.title if finding else "PASTA Risk Conclusion"
    description = (finding.description or title).strip()

    fields = {
        "title": title,
        "description": description,
        "chance": RiskChance(_CHANCE_MAP[likelihood]),
        "impact": RiskImpact(_IMPACT_MAP[impact]),
        "treatment": treatment,
    }

    if conclusion.published_risk_id is None:
        risk = Risk(discovered_on=_dt.date.today(), **fields)
        db.session.add(risk)
        db.session.flush()
        conclusion.published_risk_id = risk.id
    else:
        risk = db.session.get(Risk, conclusion.published_risk_id)
        if risk:
            for key, value in fields.items():
                setattr(risk, key, value)
            if risk.closed_at:
                risk.closed_at = None

    conclusion.publication_state = PastaPublicationState.PUBLISHED
    conclusion.last_published_at = datetime.now(UTC)
    if published_by_user and getattr(published_by_user, "id", None):
        conclusion.last_published_by_id = published_by_user.id


def export_pasta_findings_csv_with_scores(threat_model) -> str:
    """Return CSV with stage-seven score columns added (T028).

    Extends the base CSV with: likelihood_score, impact_score, overall_score,
    risk_priority, publication_state, published_risk_id.
    Non-stage-seven rows leave those columns blank.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "stage",
            "finding_type",
            "title",
            "description",
            "evidence",
            "priority",
            "stride_mappings",
            "linked_scenarios",
            "likelihood_score",
            "impact_score",
            "overall_score",
            "risk_priority",
            "publication_state",
            "published_risk_id",
        ]
    )
    for stage in threat_model.pasta_stages:
        for finding in stage.findings:
            stride_vals = "; ".join(link.stride_category for link in finding.stride_links)
            scenario_ids = "; ".join(str(link.scenario_id) for link in finding.scenario_links)
            rc = getattr(finding, "risk_conclusion", None)
            if rc:
                _, risk_level = compute_pasta_overall_score(
                    rc.likelihood_score or 1, rc.impact_score or 1
                )
                writer.writerow(
                    [
                        stage.stage_code,
                        finding.finding_type.value,
                        finding.title,
                        finding.description or "",
                        finding.evidence or "",
                        finding.priority or "",
                        stride_vals,
                        scenario_ids,
                        rc.likelihood_score or "",
                        rc.impact_score or "",
                        rc.overall_score or "",
                        risk_level if rc.overall_score else "",
                        rc.publication_state.value if rc.publication_state else "",
                        rc.published_risk_id or "",
                    ]
                )
            else:
                writer.writerow(
                    [
                        stage.stage_code,
                        finding.finding_type.value,
                        finding.title,
                        finding.description or "",
                        finding.evidence or "",
                        finding.priority or "",
                        stride_vals,
                        scenario_ids,
                        "", "", "", "", "", "",
                    ]
                )
    return output.getvalue()
