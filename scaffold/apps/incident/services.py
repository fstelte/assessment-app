"""Service functions for Incident Response used by routes."""

from ...apps.bia.models import Component, AvailabilityRequirements

def get_bia_requirements(component_id: int) -> dict[str, str]:
    """
    Fetch the current RTO and RPO from the BIA app for a given component.
    Returns a dictionary with 'rto' and 'rpo' keys.
    """
    requirements = AvailabilityRequirements.query.filter_by(component_id=component_id).first()
    
    result = {
        "rto": "",
        "rpo": ""
    }
    
    if requirements:
        result["rto"] = requirements.rto or ""
        result["rpo"] = requirements.rpo or ""
        
    return result
