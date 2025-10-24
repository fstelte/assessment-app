"""Routes for unauthenticated public pages."""

from __future__ import annotations

from flask import render_template
from flask_login import current_user

from ...models import Assessment, AssessmentStatus

from . import bp


@bp.get("/")
def index() -> str:
    """Placeholder landing page."""
    pending_reviews: list[Assessment] = []
    open_assignments = []
    if current_user.is_authenticated and (current_user.has_role("admin") or current_user.has_role("manager")):
        pending_reviews = (
            Assessment.query.filter(Assessment.status == AssessmentStatus.SUBMITTED)
            .order_by(Assessment.submitted_at.desc())
            .all()
        )

    if current_user.is_authenticated:
        open_statuses = {AssessmentStatus.ASSIGNED, AssessmentStatus.IN_PROGRESS}
        open_assignments = [
            assignment
            for assignment in current_user.assignments
            if getattr(assignment, "assessment", None)
            and assignment.assessment.status in open_statuses
        ]

    return render_template(
        "public_index.html",
        pending_reviews=pending_reviews,
        open_assignments=open_assignments,
    )
