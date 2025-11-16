"""Helper routines to bootstrap DPIA assessments from BIA components."""

from __future__ import annotations

from scaffold.apps.bia.models import Component
from scaffold.apps.identity.models import User
from scaffold.apps.dpia.models import DPIAAssessment, DPIAAssessmentStatus


def bootstrap_assessment(*, component: Component, creator: User, title: str, project_lead: str | None, responsible: str | None) -> DPIAAssessment:
    """Create a DPIA assessment instance with sensible defaults."""

    project_lead_value = project_lead
    if not project_lead_value and component.context_scope:
        project_lead_value = component.context_scope.project_leader

    responsible_value = responsible or component.info_owner

    assessment = DPIAAssessment(
        title=title,
        project_lead=project_lead_value,
        responsible_name=responsible_value,
        component=component,
        created_by=creator,
        status=DPIAAssessmentStatus.IN_PROGRESS,
    )
    return assessment
