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

    for component in context.components:
        # --- Controls from Risk items linked to this component ---
        for risk in component.risks:
            for control in risk.controls:
                _add_entry(control, ControlSource.RISK)

        # --- Controls from ThreatScenarios via DPIA link ---
        from ..threat.models import ThreatModel, ThreatScenario
        from ..dpia.models import DPIAAssessment

        # Find all DPIAs for this component
        dpia_ids = [
            d.id for d in DPIAAssessment.query.filter_by(component_id=component.id).all()
        ]
        if dpia_ids:
            threat_models = ThreatModel.query.filter(
                ThreatModel.dpia_id.in_(dpia_ids)
            ).all()
            for tm in threat_models:
                for scenario in tm.scenarios:
                    for control in scenario.controls:
                        _add_entry(control, ControlSource.THREAT)


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
