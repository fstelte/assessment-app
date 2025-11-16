"""Database models for DPIA / FRIA assessments integrated with BIA components."""

from __future__ import annotations

import enum
from datetime import UTC, datetime

from ...extensions import db


def utc_now() -> datetime:
    """Return timezone-aware timestamps for default values."""

    return datetime.now(UTC)


class TimestampMixin:
    """Provide created/updated timestamps for DPIA entities."""

    created_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class DPIAAssessmentStatus(enum.Enum):
    """Workflow states for a DPIA assessment."""

    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    FINISHED = "finished"
    ABANDONED = "abandoned"


class DPIAAssessment(TimestampMixin, db.Model):
    """Root entity that links a DPIA/FRIA to a BIA component."""

    __tablename__ = "dpia_assessments"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    project_lead = db.Column(db.String(255))
    responsible_name = db.Column(db.String(255))
    status = db.Column(
        db.Enum(
            DPIAAssessmentStatus,
            name="dpia_assessment_status",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=DPIAAssessmentStatus.IN_PROGRESS,
    )
    started_at = db.Column(db.DateTime(timezone=True), default=utc_now, nullable=False)
    submitted_at = db.Column(db.DateTime(timezone=True))

    component_id = db.Column(
        db.Integer,
        db.ForeignKey("bia_components.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
    )

    component = db.relationship("Component", back_populates="dpia_assessments")
    created_by = db.relationship("User")
    answers = db.relationship("DPIAAnswer", back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True)
    risks = db.relationship("DPIARisk", back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True)
    measures = db.relationship("DPIAMeasure", back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True)

    def needs_fria(self) -> bool:
        """Return True if any answer or risk indicates FRIA requirements."""

        return any(risk.risk_type == "FRIA" for risk in self.risks)


class DPIAQuestion(TimestampMixin, db.Model):
    """Canonical DPIA questions shown in the assessment wizard."""

    __tablename__ = "dpia_questions"

    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    text_key = db.Column(db.String(255), unique=True)
    category = db.Column(db.String(100), nullable=False)
    help_text = db.Column(db.Text)
    help_key = db.Column(db.String(255))
    question_type = db.Column(db.String(50), default="text", nullable=False)
    sort_order = db.Column(db.Integer)

    answers = db.relationship("DPIAAnswer", back_populates="question", cascade="all, delete-orphan", passive_deletes=True)


class DPIAAnswer(TimestampMixin, db.Model):
    """Stores user responses for each question."""

    __tablename__ = "dpia_answers"

    id = db.Column(db.Integer, primary_key=True)
    answer_text = db.Column(db.Text)
    assessment_id = db.Column(
        db.Integer,
        db.ForeignKey("dpia_assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("dpia_questions.id", ondelete="CASCADE"),
        nullable=False,
    )

    assessment = db.relationship("DPIAAssessment", back_populates="answers")
    question = db.relationship("DPIAQuestion", back_populates="answers")


class DPIARisk(TimestampMixin, db.Model):
    """Risk entries tied to a DPIA assessment."""

    __tablename__ = "dpia_risks"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    risk_type = db.Column(db.String(50), nullable=False)
    likelihood = db.Column(db.Integer, nullable=False, default=1)
    impact = db.Column(db.Integer, nullable=False, default=1)
    assessment_id = db.Column(
        db.Integer,
        db.ForeignKey("dpia_assessments.id", ondelete="CASCADE"),
        nullable=False,
    )

    assessment = db.relationship("DPIAAssessment", back_populates="risks")
    measures = db.relationship("DPIAMeasure", back_populates="risk", cascade="all, delete-orphan", passive_deletes=True)

    @property
    def residual_likelihood(self) -> int:
        total_effect = sum(measure.effect_likelihood for measure in self.measures)
        return max(1, self.likelihood + total_effect)

    @property
    def residual_impact(self) -> int:
        total_effect = sum(measure.effect_impact for measure in self.measures)
        return max(1, self.impact + total_effect)


class DPIAMeasure(TimestampMixin, db.Model):
    """Mitigating measures linked to risks or the overall assessment."""

    __tablename__ = "dpia_measures"

    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    effect_likelihood = db.Column(db.Integer, nullable=False, default=0)
    effect_impact = db.Column(db.Integer, nullable=False, default=0)
    assessment_id = db.Column(
        db.Integer,
        db.ForeignKey("dpia_assessments.id", ondelete="CASCADE"),
        nullable=False,
    )
    risk_id = db.Column(
        db.Integer,
        db.ForeignKey("dpia_risks.id", ondelete="SET NULL"),
    )

    assessment = db.relationship("DPIAAssessment", back_populates="measures")
    risk = db.relationship("DPIARisk", back_populates="measures")
