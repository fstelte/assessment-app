"""Services for the System Security Plan module."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ...extensions import db

if TYPE_CHECKING:
    from ..bia.models import ContextScope
    from .models import SSPlan


# ---------------------------------------------------------------------------
# FIPS 199 rating derivation
# ---------------------------------------------------------------------------

_SCALE_TO_FIPS = {
    "negligible": "low",
    "very low": "low",
    "low": "low",
    "minor": "low",
    "moderate": "moderate",
    "significant": "high",
    "severe": "high",
    "catastrophic": "high",
    "very high": "high",
    "critical": "high",
    "high": "high",
}

_FIPS_ORDER = {"low": 0, "moderate": 1, "high": 2}


def _upgrade(current: str | None, candidate: str) -> str:
    """Return whichever FIPS rating is higher."""
    if current is None:
        return candidate
    if _FIPS_ORDER.get(candidate, -1) > _FIPS_ORDER.get(current, -1):
        return candidate
    return current


def derive_fips_rating(consequences: list) -> dict[str, str]:
    """Map BIA Consequences records to a C/I/A rating dict.

    Returns a dict with keys 'confidentiality', 'integrity', 'availability',
    each containing 'low', 'moderate', or 'high'.  Defaults to 'low' when no
    relevant consequence is found.
    """
    conf: str | None = None
    integ: str | None = None
    avail: str | None = None

    for c in consequences:
        raw = (c.consequence_worstcase or "").lower().strip()
        rating = _SCALE_TO_FIPS.get(raw)
        if rating is None:
            continue
        prop = (c.security_property or "").lower()
        if "confid" in prop:
            conf = _upgrade(conf, rating)
        elif "integr" in prop:
            integ = _upgrade(integ, rating)
        elif "availab" in prop:
            avail = _upgrade(avail, rating)

    return {
        "confidentiality": conf or "low",
        "integrity": integ or "low",
        "availability": avail or "low",
    }


# ---------------------------------------------------------------------------
# Seed interconnections from ContextScope.interfaces free-text
# ---------------------------------------------------------------------------

def seed_interconnections(ssp: "SSPlan") -> None:
    """Parse ContextScope.interfaces into SSPInterconnection rows."""
    from .models import SSPInterconnection

    raw = (ssp.context_scope.interfaces or "").strip()
    if not raw:
        return

    # Split on newlines or semicolons
    entries = [e.strip() for e in re.split(r"[\n;]+", raw) if e.strip()]
    for idx, entry in enumerate(entries):
        interconnection = SSPInterconnection(
            ssp_id=ssp.id,
            system_name=entry[:255],
            sort_order=idx,
        )
        db.session.add(interconnection)


# ---------------------------------------------------------------------------
# Seed control entries from Risk and Threat models
# ---------------------------------------------------------------------------

def seed_controls(ssp: "SSPlan") -> None:
    """Gather Control objects linked to the scope's components and create SSPControlEntry rows."""
    from .models import SSPControlEntry, ControlSource
    from ..csa.models import Control

    seen_control_ids: set[int] = set()

    def _add_entry(control: "Control", source: "ControlSource") -> None:
        if control.id in seen_control_ids:
            return
        seen_control_ids.add(control.id)
        entry = SSPControlEntry(
            ssp_id=ssp.id,
            control_id=control.id,
            source=source,
        )
        db.session.add(entry)

    context = ssp.context_scope

    from ..threat.models import ThreatModel
    from ..dpia.models import DPIAAssessment

    # --- ThreatScenario controls: path 1 — ThreatModel.context_scope_id (direct link) ---
    direct_threat_models = ThreatModel.query.filter_by(context_scope_id=context.id).all()
    for tm in direct_threat_models:
        for scenario in tm.scenarios:
            for control in scenario.controls:
                _add_entry(control, ControlSource.THREAT)

    # --- ThreatScenario controls: path 2 — via DPIA linked to components ---
    dpia_ids = [
        d.id
        for component in context.components
        for d in DPIAAssessment.query.filter_by(component_id=component.id).all()
    ]
    seen_direct_ids = {tm.id for tm in direct_threat_models}
    if dpia_ids:
        via_dpia_models = ThreatModel.query.filter(
            ThreatModel.dpia_id.in_(dpia_ids),
            ~ThreatModel.id.in_(seen_direct_ids) if seen_direct_ids else True,
        ).all()
        for tm in via_dpia_models:
            for scenario in tm.scenarios:
                for control in scenario.controls:
                    _add_entry(control, ControlSource.THREAT)

    for component in context.components:
        # --- Controls from Risk items linked to this component ---
        for risk in component.risks:
            for control in risk.controls:
                _add_entry(control, ControlSource.RISK)


# ---------------------------------------------------------------------------
# Sync threat scenario controls to SSP minimum security controls
# ---------------------------------------------------------------------------

def sync_scenario_controls_to_ssp(scenario: object) -> None:
    """Add controls from a ThreatScenario to the linked SSP as minimum security controls.

    Resolves the SSP via the scenario's ThreatModel → ContextScope → SSPlan chain.
    Only adds entries that do not already exist; never removes existing entries.
    """
    from .models import SSPControlEntry, ControlSource

    threat_model = scenario.threat_model
    if threat_model is None:
        return

    context_scope = threat_model.context_scope

    # Fall back to DPIA → ContextScope when the direct FK is absent
    if context_scope is None and threat_model.dpia_id is not None:
        from ..dpia.models import DPIAAssessment

        dpia = DPIAAssessment.query.get(threat_model.dpia_id)
        if dpia is not None:
            from ..bia.models import ContextScope as CS

            context_scope = CS.query.filter_by(id=dpia.component.context_scope_id).first() if hasattr(dpia, "component") and dpia.component else None

    if context_scope is None:
        return

    ssp = context_scope.ssp
    if ssp is None:
        return

    existing_control_ids: set[int] = {
        e.control_id
        for e in SSPControlEntry.query.filter_by(ssp_id=ssp.id).with_entities(SSPControlEntry.control_id).all()
    }

    for control in scenario.controls:
        if control.id not in existing_control_ids:
            entry = SSPControlEntry(
                ssp_id=ssp.id,
                control_id=control.id,
                source=ControlSource.THREAT,
            )
            db.session.add(entry)
            existing_control_ids.add(control.id)


# ---------------------------------------------------------------------------
# Build environment summary from component dependency fields
# ---------------------------------------------------------------------------

_DEP_FIELDS = [
    ("it_systems_applications", "dependencies_it_systems_applications"),
    ("equipment", "dependencies_equipment"),
    ("suppliers", "dependencies_suppliers"),
    ("people", "dependencies_people"),
    ("facilities", "dependencies_facilities"),
    ("others", "dependencies_others"),
]


def build_environment_summary(context_scope: "ContextScope") -> list[dict]:
    """Aggregate Component dependency fields into a structured list."""
    rows: list[dict] = []

    for component in context_scope.components:
        for category_key, attr in _DEP_FIELDS:
            value = getattr(component, attr, None)
            if not value or not value.strip():
                continue
            items = [i.strip() for i in re.split(r"[\n,;]+", value) if i.strip()]
            if items:
                rows.append({
                    "component": component.name,
                    "category": category_key,
                    "items": items,
                })

    return rows


# ---------------------------------------------------------------------------
# Sync a ThreatMitigationAction to the SSP POA&M
# ---------------------------------------------------------------------------

_MITIGATION_TO_POAM_STATUS = {
    "proposed": "open",
    "in_progress": "in_progress",
    "implemented": "completed",
    "verified": "completed",
}


def sync_mitigation_to_poam(action: object) -> None:
    """Create or update a POA&M item in the SSP linked to a ThreatMitigationAction.

    Resolves the SSP via action → scenario → ThreatModel → ContextScope → SSPlan.
    Does nothing when no SSP is found for the associated context scope.
    """
    from .models import POAMItem, POAMStatus

    scenario = action.scenario
    if scenario is None:
        return

    threat_model = scenario.threat_model
    if threat_model is None:
        return

    context_scope = threat_model.context_scope

    # Fall back to DPIA → ContextScope when the direct FK is absent
    if context_scope is None and threat_model.dpia_id is not None:
        from ..dpia.models import DPIAAssessment

        dpia = DPIAAssessment.query.get(threat_model.dpia_id)
        if dpia is not None and hasattr(dpia, "component") and dpia.component:
            from ..bia.models import ContextScope as CS

            context_scope = CS.query.filter_by(id=dpia.component.context_scope_id).first()

    if context_scope is None:
        return

    ssp = context_scope.ssp
    if ssp is None:
        return

    # Map MitigationStatus → POAMStatus
    status_value = _MITIGATION_TO_POAM_STATUS.get(
        action.status.value if hasattr(action.status, "value") else str(action.status),
        "open",
    )
    poam_status = POAMStatus(status_value)

    # Resolve point of contact from assigned user
    poc: str | None = None
    if action.assigned_to is not None:
        user = action.assigned_to
        poc = getattr(user, "display_name", None) or getattr(user, "username", None) or getattr(user, "email", None)

    # Build weakness description combining title and optional description
    weakness = action.title
    if action.description:
        weakness = f"{action.title}\n\n{action.description}"

    # Look for an existing POA&M item linked to this mitigation action
    existing = POAMItem.query.filter_by(source_threat_mitigation_id=action.id).first()

    if existing is not None:
        existing.weakness_description = weakness
        existing.point_of_contact = poc
        existing.scheduled_completion = action.due_date
        existing.resources_required = action.notes
        existing.status = poam_status
    else:
        item = POAMItem(
            ssp_id=ssp.id,
            source_threat_mitigation_id=action.id,
            weakness_description=weakness,
            point_of_contact=poc,
            scheduled_completion=action.due_date,
            resources_required=action.notes,
            status=poam_status,
        )
        db.session.add(item)
