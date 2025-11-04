"""Control catalogue and assessment template models."""

from __future__ import annotations

import copy
from typing import Any, Dict

from ....extensions import db
from ...identity.models import TimestampMixin


DEFAULT_QUESTION_SET: Dict[str, Any] = {
    "design": {
        "label_key": "csa.assessments.questions.design.label",
        "questions": [
            {"text_key": "csa.assessments.questions.design.q1"},
            {"text_key": "csa.assessments.questions.design.q2"},
            {"text_key": "csa.assessments.questions.design.q3"},
        ],
    },
    "operation": {
        "label_key": "csa.assessments.questions.operation.label",
        "questions": [
            {"text_key": "csa.assessments.questions.operation.q1"},
            {"text_key": "csa.assessments.questions.operation.q2"},
            {"text_key": "csa.assessments.questions.operation.q3"},
        ],
    },
    "monitoring_improvement": {
        "label_key": "csa.assessments.questions.monitoring.label",
        "questions": [
            {"text_key": "csa.assessments.questions.monitoring.q1"},
            {"text_key": "csa.assessments.questions.monitoring.q2"},
            {"text_key": "csa.assessments.questions.monitoring.q3"},
        ],
    },
}


class Control(TimestampMixin, db.Model):
    """Control metadata sourced from ISO 27002 or similar catalogues."""

    __tablename__ = "csa_controls"

    id = db.Column(db.Integer, primary_key=True)
    section = db.Column(db.String(120), nullable=True)
    domain = db.Column(db.String(255), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)

    templates = db.relationship(
        "AssessmentTemplate",
        back_populates="control",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Control domain={self.domain!r} section={self.section!r}>"


class AssessmentTemplate(TimestampMixin, db.Model):
    """Template describing the questions and scoring rules for a control."""

    __tablename__ = "csa_assessment_templates"

    id = db.Column(db.Integer, primary_key=True)
    control_id = db.Column(
        db.Integer,
        db.ForeignKey("csa_controls.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(50), default="1.0", nullable=False)
    question_set = db.Column(db.JSON, nullable=False, default=lambda: copy.deepcopy(DEFAULT_QUESTION_SET))
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    control = db.relationship("Control", back_populates="templates")
    assessments = db.relationship("Assessment", back_populates="template")

    __table_args__ = (
        db.UniqueConstraint("control_id", "version", name="uq_csa_template_control_version"),
    )

    @staticmethod
    def default_question_set() -> Dict[str, Any]:
        """Return a deep copy of the standard question set."""

        return copy.deepcopy(DEFAULT_QUESTION_SET)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AssessmentTemplate control={self.control_id} version={self.version}>"
