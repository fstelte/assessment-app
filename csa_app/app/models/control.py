"""Control catalogue and assessment template models."""

from __future__ import annotations

import copy
from typing import Any, Dict

from ..extensions import db
from . import TimestampMixin


DEFAULT_QUESTION_SET: Dict[str, Any] = {
    "design": {
        "label": "Ontwerp van de Beheersmaatregel",
        "questions": [
            "Is de beheersmaatregel duidelijk en ondubbelzinnig gedocumenteerd in een vastgesteld beleidsdocument of procedure?",
            "Is er een duidelijke 'control owner' toegewezen die eindverantwoordelijk is voor deze maatregel?",
            "Zijn de rollen en verantwoordelijkheden voor de uitvoering van de maatregel duidelijk beschreven en toegewezen?",
        ],
    },
    "operation": {
        "label": "Werking van de Beheersmaatregel (bestaan)",
        "questions": [
            "Is de beheersmaatregel in de afgelopen periode consequent uitgevoerd zoals beschreven?",
            "Kunt u bewijs overleggen waaruit de consistente uitvoering van de maatregel blijkt (bv. logs, rapportages, screenshots)?",
            "Zijn eventuele afwijkingen of uitzonderingen op de procedure gedocumenteerd en geautoriseerd?",
        ],
    },
    "monitoring_improvement": {
        "label": "Monitoring en Verbetering",
        "questions": [
            "Wordt de effectiviteit van deze maatregel periodiek gemonitord en gerapporteerd aan de 'control owner'?",
            "Is de maatregel in het afgelopen jaar geëvalueerd om te bepalen of deze nog steeds effectief en efficiënt is?",
            "Zijn er verbeteracties geïdentificeerd en geïmplementeerd op basis van de evaluatie of geïdentificeerde afwijkingen?",
        ],
    },
}


class Control(TimestampMixin, db.Model):
    """Control metadata sourced from ISO 27002 or similar catalogues."""

    __tablename__ = "controls"

    id = db.Column(db.Integer, primary_key=True)
    section = db.Column(db.String(120), nullable=True)
    domain = db.Column(db.String(255), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)

    templates = db.relationship(
        "AssessmentTemplate",
        back_populates="control",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover - diagnostic helper
        return f"<Control domain={self.domain!r} section={self.section!r}>"


class AssessmentTemplate(TimestampMixin, db.Model):
    """Template describing the questions and scoring rules for a control."""

    __tablename__ = "assessment_templates"

    id = db.Column(db.Integer, primary_key=True)
    control_id = db.Column(
        db.Integer,
        db.ForeignKey("controls.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(255), nullable=False)
    version = db.Column(db.String(50), default="1.0", nullable=False)
    question_set = db.Column(db.JSON, nullable=False, default=lambda: copy.deepcopy(DEFAULT_QUESTION_SET))
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    control = db.relationship("Control", back_populates="templates")
    assessments = db.relationship("Assessment", back_populates="template")

    __table_args__ = (
        db.UniqueConstraint("control_id", "version", name="uq_template_control_version"),
    )

    @staticmethod
    def default_question_set() -> Dict[str, Any]:
        """Return a deep copy of the standard question set."""
        return copy.deepcopy(DEFAULT_QUESTION_SET)

    def __repr__(self) -> str:  # pragma: no cover - diagnostic helper
        return f"<AssessmentTemplate control={self.control_id} version={self.version}>"
