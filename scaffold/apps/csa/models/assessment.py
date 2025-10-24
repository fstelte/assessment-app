"""Assessment workflow data models."""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from ....extensions import db
from ...identity.models import TimestampMixin, User, utc_now


class AssessmentStatus(enum.Enum):
    """Workflow status for a self-assessment."""

    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    REVIEWED = "reviewed"


class AssessmentResult(enum.Enum):
    """High-level outcome used for colour coding."""

    GREEN = "green"
    AMBER = "amber"
    RED = "red"


class AssessmentDimension(enum.Enum):
    """Dimensions evaluated during an assessment."""

    DESIGN = "design"
    OPERATION = "operation"
    MONITORING_IMPROVEMENT = "monitoring_improvement"


class Assessment(TimestampMixin, db.Model):
    """Self-assessment instance tied to a template."""

    __tablename__ = "csa_assessments"

    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer,
        db.ForeignKey("csa_assessment_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    status = db.Column(
        db.Enum(AssessmentStatus, name="csa_assessment_status"),
        default=AssessmentStatus.ASSIGNED,
        nullable=False,
    )
    due_date = db.Column(db.Date)
    started_at = db.Column(db.DateTime(timezone=True))
    submitted_at = db.Column(db.DateTime(timezone=True))
    reviewed_at = db.Column(db.DateTime(timezone=True))
    design_rating = db.Column(db.Enum(AssessmentResult, name="csa_assessment_result"))
    operation_rating = db.Column(db.Enum(AssessmentResult, name="csa_assessment_result"))
    monitoring_rating = db.Column(db.Enum(AssessmentResult, name="csa_assessment_result"))
    overall_comment = db.Column(db.Text)
    review_comment = db.Column(db.Text)

    template = db.relationship("AssessmentTemplate", back_populates="assessments")
    created_by = db.relationship(User, back_populates="created_assessments")
    assignments = db.relationship(
        "AssessmentAssignment",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentAssignment.assigned_at",
    )
    responses = db.relationship(
        "AssessmentResponse",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )

    def mark_started(self) -> None:
        if self.started_at is None:
            self.started_at = datetime.now(UTC)
            self.status = AssessmentStatus.IN_PROGRESS

    def mark_submitted(self) -> None:
        self.submitted_at = datetime.now(UTC)
        self.status = AssessmentStatus.SUBMITTED

    def mark_reviewed(self) -> None:
        self.reviewed_at = datetime.now(UTC)
        self.status = AssessmentStatus.REVIEWED

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Assessment id={self.id} status={self.status.value}>"


class AssessmentAssignment(TimestampMixin, db.Model):
    """Assignment of a self-assessment to a user."""

    __tablename__ = "csa_assessment_assignments"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(
        db.Integer,
        db.ForeignKey("csa_assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    assignee_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    assigned_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    is_primary = db.Column(db.Boolean, default=True, nullable=False)

    assessment = db.relationship("Assessment", back_populates="assignments")
    assignee = db.relationship(User, back_populates="assignments", foreign_keys=[assignee_id])
    assigned_by = db.relationship(User, foreign_keys=[assigned_by_id])

    __table_args__ = (
        db.UniqueConstraint(
            "assessment_id",
            "assignee_id",
            name="uq_csa_assignment_assessment_assignee",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AssessmentAssignment assessment={self.assessment_id} assignee={self.assignee_id}>"


class AssessmentResponse(TimestampMixin, db.Model):
    """Response captured for each question within an assessment."""

    __tablename__ = "csa_assessment_responses"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(
        db.Integer,
        db.ForeignKey("csa_assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    dimension = db.Column(
        db.Enum(AssessmentDimension, name="csa_assessment_dimension"),
        nullable=False,
    )
    question_text = db.Column(db.Text, nullable=False)
    answer_text = db.Column(db.Text)
    rating = db.Column(db.Enum(AssessmentResult, name="csa_assessment_result"))
    evidence_uri = db.Column(db.String(255))
    comment = db.Column(db.Text)
    responder_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    responded_at = db.Column(db.DateTime(timezone=True), default=utc_now)

    assessment = db.relationship("Assessment", back_populates="responses")
    responder = db.relationship(User)

    __table_args__ = (
        db.Index(
            "ix_csa_responses_assessment_dimension",
            "assessment_id",
            "dimension",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AssessmentResponse assessment={self.assessment_id} dimension={self.dimension.value}>"
