"""Service functions for Incident Response used by routes."""

from ...apps.bia.models import Component
from ...extensions import db


def get_bia_requirements(component_id: int) -> dict[str, str]:
    """
    Fetch the effective RTO and RPO from the BIA app for a given component:
    the tier goal when the tier defines one, otherwise the stored text.
    Returns a dictionary with 'rto' and 'rpo' keys.
    """
    component = db.session.get(Component, component_id)
    if component is None:
        return {"rto": "", "rpo": ""}
    return {"rto": component.effective_rto or "", "rpo": component.effective_rpo or ""}
