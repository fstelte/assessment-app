from enum import IntEnum, unique

from scaffold.apps.identity.models import TimestampMixin
from scaffold.extensions import db


@unique
class MaturityLevel(IntEnum):
    """CMMI Maturity Levels."""

    INITIAL = 1
    MANAGED = 2
    DEFINED = 3
    QUANTITATIVELY_MANAGED = 4
    OPTIMIZING = 5


class MaturityAssessment(TimestampMixin, db.Model):
    """Maturity assessment instance for a specific Control."""

    __tablename__ = "maturity_assessments"

    id = db.Column(db.Integer, primary_key=True)
    control_id = db.Column(
        db.Integer, db.ForeignKey("csa_controls.id"), nullable=False, index=True
    )
    assessor_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )

    current_level = db.Column(
        db.Enum(MaturityLevel), default=MaturityLevel.INITIAL, nullable=False
    )
    target_level = db.Column(db.Enum(MaturityLevel), nullable=True)
    notes = db.Column(db.Text)

    # Relationships
    control = db.relationship(
        "Control",
        backref=db.backref("maturity_assessments", cascade="all, delete-orphan", lazy=True),
    )
    assessor = db.relationship("User", backref=db.backref("maturity_assessments", lazy=True))
    answers = db.relationship(
        "MaturityAnswer",
        backref="assessment",
        cascade="all, delete-orphan",
        lazy=True,
    )


class MaturityAnswer(db.Model):
    """Specific evidence or compliance answer for a maturity requirement."""

    __tablename__ = "maturity_answers"

    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(
        db.Integer,
        db.ForeignKey("maturity_assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level = db.Column(db.Enum(MaturityLevel), nullable=False)
    requirement_key = db.Column(db.String(50), nullable=False)
    compliant = db.Column(db.Boolean, default=False, nullable=False)
    evidence = db.Column(db.Text)

    def __repr__(self):
        return (
            f"<MaturityAnswer id={self.id} level={self.level.name} "
            f"key={self.requirement_key} compliant={self.compliant}>"
        )
