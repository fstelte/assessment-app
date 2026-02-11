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


@unique
class AssessmentStatus(IntEnum):
    """Workflow status for Maturity Assessments."""

    UNASSESSED = 1
    BEING_ASSESSED = 2
    ASSESSED = 3
    SUBMITTED = 4
    APPROVED = 5



class MaturityAssessment(TimestampMixin, db.Model):
    """Maturity assessment instance for a specific Control."""

    __tablename__ = "maturity_assessments"

    id = db.Column(db.Integer, primary_key=True)
    control_id = db.Column(
        db.Integer, db.ForeignKey("csa_controls.id"), nullable=False, index=True
    )

    # Workflow tracking
    status = db.Column(
        db.Enum(AssessmentStatus), default=AssessmentStatus.UNASSESSED, nullable=False
    )
    last_updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

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
    last_updated_by = db.relationship("User", foreign_keys=[last_updated_by_id])
    submitted_by = db.relationship("User", foreign_keys=[submitted_by_id])

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


class MaturityAssessmentVersion(db.Model):
    """Snapshot of an approved maturity assessment."""

    __tablename__ = "maturity_assessment_versions"

    id = db.Column(db.Integer, primary_key=True)
    control_id = db.Column(
        db.Integer, db.ForeignKey("csa_controls.id"), nullable=False, index=True
    )
    approved_at = db.Column(db.DateTime, default=db.func.now(), nullable=False)
    approved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    maturity_level = db.Column(db.Enum(MaturityLevel), nullable=False)
    data = db.Column(db.JSON)
    notes = db.Column(db.Text)

    # Relationships
    control = db.relationship(
        "Control",
        backref=db.backref("maturity_versions", cascade="all, delete-orphan", lazy=True),
    )
    approved_by = db.relationship("User", foreign_keys=[approved_by_id])
