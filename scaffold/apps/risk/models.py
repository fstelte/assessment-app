"""Risk management domain models."""

from __future__ import annotations

import enum
import hashlib
from datetime import date
from typing import Sequence

import sqlalchemy as sa

from ...extensions import db
from ..identity.models import TimestampMixin, User


def _enum_column(enum_cls: type[enum.Enum], *, name: str) -> sa.Enum:
    """Return a SQLAlchemy Enum storing lowercase enum values."""

    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=False,
        values_callable=lambda members: [member.value for member in members],
    )


class RiskImpact(enum.Enum):
    """Scale describing the business impact when a risk materialises."""

    INSIGNIFICANT = "insignificant"
    MINOR = "minor"
    MODERATE = "moderate"
    MAJOR = "major"
    CATASTROPHIC = "catastrophic"


class RiskChance(enum.Enum):
    """Likelihood that a risk occurs within the assessed timeframe."""

    RARE = "rare"
    UNLIKELY = "unlikely"
    POSSIBLE = "possible"
    LIKELY = "likely"
    ALMOST_CERTAIN = "almost_certain"


class RiskImpactArea(enum.Enum):
    """Business areas affected when the risk materialises."""

    OPERATIONAL = "operational"
    FINANCIAL = "financial"
    REGULATORY = "regulatory"
    HUMAN_SAFETY = "human_safety"
    PRIVACY = "privacy"


class RiskTreatmentOption(enum.Enum):
    """Available treatment strategies."""

    ACCEPT = "accept"
    AVOID = "avoid"
    MITIGATE = "mitigate"
    TRANSFER = "transfer"


class RiskApprovalStatus(enum.Enum):
    """Owner decision on a risk. NULL in the column means awaiting approval."""

    APPROVED = "approved"
    REJECTED = "rejected"


# Fields whose change invalidates an owner decision (decisions 20261118-1039,
# -1057). The mitigated flag (mitigated_at set or not) also counts.
APPROVAL_MATERIAL_FIELDS = (
    "chance",
    "impact",
    "treatment",
    "residual_chance",
    "residual_impact",
    "treatment_owner_id",
)


class RiskSeverity(enum.Enum):
    """Categorisation derived from the weighted score."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


IMPACT_WEIGHTS = {
    RiskImpact.INSIGNIFICANT: 1,
    RiskImpact.MINOR: 2,
    RiskImpact.MODERATE: 3,
    RiskImpact.MAJOR: 4,
    RiskImpact.CATASTROPHIC: 5,
}

CHANCE_WEIGHTS = {
    RiskChance.RARE: 1,
    RiskChance.UNLIKELY: 2,
    RiskChance.POSSIBLE: 3,
    RiskChance.LIKELY: 4,
    RiskChance.ALMOST_CERTAIN: 5,
}


risk_component_links = db.Table(
    "risk_component_links",
    db.metadata,
    db.Column("risk_id", db.Integer, db.ForeignKey("risk_items.id", ondelete="CASCADE"), primary_key=True),
    db.Column("component_id", db.Integer, db.ForeignKey("bia_components.id", ondelete="CASCADE"), primary_key=True),
    sa.UniqueConstraint("risk_id", "component_id", name="uq_risk_component_link"),
)

risk_control_links = db.Table(
    "risk_control_links",
    db.metadata,
    db.Column("risk_id", db.Integer, db.ForeignKey("risk_items.id", ondelete="CASCADE"), primary_key=True),
    db.Column("control_id", db.Integer, db.ForeignKey("csa_controls.id", ondelete="CASCADE"), primary_key=True),
    sa.UniqueConstraint("risk_id", "control_id", name="uq_risk_control_link"),
)


class Risk(TimestampMixin, db.Model):
    """Identified risk tied to one or more components."""

    __tablename__ = "risk_items"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    discovered_on = db.Column(db.Date, default=date.today, nullable=False)
    impact = db.Column(_enum_column(RiskImpact, name="risk_impact"), nullable=False)
    chance = db.Column(_enum_column(RiskChance, name="risk_chance"), nullable=False)
    treatment = db.Column(
        _enum_column(RiskTreatmentOption, name="risk_treatment"),
        nullable=False,
        default=RiskTreatmentOption.MITIGATE,
    )
    treatment_plan = db.Column(db.Text)
    treatment_due_date = db.Column(db.Date)
    treatment_owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    ticket_url = db.Column(db.String(500))
    closed_at = db.Column(sa.DateTime(timezone=True))
    # Residual assessment (decision 20261118-0800). Only used for the actual
    # score when the risk is mitigated and both residual values are set.
    mitigated_at = db.Column(sa.DateTime(timezone=True))
    residual_impact = db.Column(_enum_column(RiskImpact, name="risk_impact"))
    residual_chance = db.Column(_enum_column(RiskChance, name="risk_chance"))
    # Owner approval (decision 20261118-1045). All NULL means awaiting approval.
    approval_status = db.Column(_enum_column(RiskApprovalStatus, name="risk_approval_status"))
    approval_decided_at = db.Column(sa.DateTime(timezone=True))
    approval_decided_by_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    approval_comment = db.Column(db.Text)

    treatment_owner =db.relationship(User, foreign_keys=[treatment_owner_id])
    approval_decided_by = db.relationship(User, foreign_keys=[approval_decided_by_id])
    components = db.relationship(
        "Component",
        secondary="risk_component_links",
        back_populates="risks",
    )
    controls = db.relationship(
        "Control",
        secondary="risk_control_links",
        backref="risks",
    )
    impact_area_links = db.relationship(
        "RiskImpactAreaLink",
        cascade="all, delete-orphan",
        back_populates="risk",
    )
    ticket_links = db.relationship(
        "RiskTicketLink",
        cascade="all, delete-orphan",
        back_populates="risk",
        order_by="RiskTicketLink.sort_order",
    )

    def score(self) -> int:
        """Return the numeric score derived from impact * chance."""

        return IMPACT_WEIGHTS[self.impact] * CHANCE_WEIGHTS[self.chance]

    def determine_severity(
        self,
        thresholds: Sequence["RiskSeverityThreshold"] | None = None,
    ) -> RiskSeverity | None:
        """Return the configured severity that matches the initial score."""

        return self._severity_for(self.score(), thresholds)

    def determine_actual_severity(
        self,
        thresholds: Sequence["RiskSeverityThreshold"] | None = None,
    ) -> RiskSeverity | None:
        """Return the configured severity that matches the actual score."""

        return self._severity_for(self.actual_score(), thresholds)

    @staticmethod
    def _severity_for(
        score: int,
        thresholds: Sequence["RiskSeverityThreshold"] | None,
    ) -> RiskSeverity | None:
        if thresholds is None:
            thresholds = RiskSeverityThreshold.query.order_by(RiskSeverityThreshold.min_score).all()
        for threshold in thresholds:
            if threshold.min_score <= score <= threshold.max_score:
                return threshold.severity
        return None

    @property
    def is_closed(self) -> bool:
        """Return True when the risk has been archived."""

        return self.closed_at is not None

    @property
    def is_mitigated(self) -> bool:
        """Return True when the risk has been marked as mitigated."""

        return self.mitigated_at is not None

    def residual_score(self) -> int | None:
        """Return residual impact * chance, or None when either value is missing."""

        if self.residual_impact is None or self.residual_chance is None:
            return None
        return IMPACT_WEIGHTS[self.residual_impact] * CHANCE_WEIGHTS[self.residual_chance]

    @property
    def _uses_residual(self) -> bool:
        return self.is_mitigated and self.residual_score() is not None

    @property
    def actual_impact(self) -> RiskImpact:
        """Residual impact when mitigated with residual values, otherwise initial."""

        return self.residual_impact if self._uses_residual else self.impact

    @property
    def actual_chance(self) -> RiskChance:
        """Residual chance when mitigated with residual values, otherwise initial."""

        return self.residual_chance if self._uses_residual else self.chance

    def actual_score(self) -> int:
        """Return the residual score when mitigated, otherwise the initial score."""

        return IMPACT_WEIGHTS[self.actual_impact] * CHANCE_WEIGHTS[self.actual_chance]

    @property
    def approval_state(self) -> str:
        """Return "no_owner", "awaiting", "approved" or "rejected"."""

        if self.treatment_owner_id is None:
            return "no_owner"
        if self.approval_status is None:
            return "awaiting"
        return self.approval_status.value

    def approval_fingerprint(self) -> str:
        """Short hash of the material fields, used to refuse decisions on a stale view."""

        parts = [getattr(self, name) for name in APPROVAL_MATERIAL_FIELDS]
        parts.append(self.is_mitigated)
        raw = "|".join(str(part.value if isinstance(part, enum.Enum) else part) for part in parts)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


class RiskImpactAreaLink(db.Model):
    """Association table storing selected impact areas per risk."""

    __tablename__ = "risk_impact_areas"
    __table_args__ = (
        sa.UniqueConstraint("risk_id", "area", name="uq_risk_impact_area"),
    )

    id = db.Column(db.Integer, primary_key=True)
    risk_id = db.Column(db.Integer, db.ForeignKey("risk_items.id", ondelete="CASCADE"), nullable=False)
    area = db.Column(_enum_column(RiskImpactArea, name="risk_impact_area"), nullable=False)

    risk = db.relationship(Risk, back_populates="impact_area_links")


class RiskTicketLink(db.Model):
    """Child row representing one external remediation or tracking reference for a risk."""

    __tablename__ = "risk_ticket_links"
    __table_args__ = (
        sa.UniqueConstraint("risk_id", "label", "url", name="uq_risk_ticket_link"),
    )

    id = db.Column(db.Integer, primary_key=True)
    risk_id = db.Column(db.Integer, db.ForeignKey("risk_items.id", ondelete="CASCADE"), nullable=False)
    label = db.Column(db.String(80), nullable=False)
    url = db.Column(db.String(500), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    risk = db.relationship(Risk, back_populates="ticket_links")


class RiskSeverityThreshold(TimestampMixin, db.Model):
    """Administrator managed ranges that translate scores to severities."""

    __tablename__ = "risk_severity_thresholds"
    __table_args__ = (
        sa.UniqueConstraint("severity", name="uq_risk_threshold_severity"),
        sa.CheckConstraint("min_score >= 0", name="ck_risk_threshold_min_non_negative"),
        sa.CheckConstraint("max_score >= min_score", name="ck_risk_threshold_bounds"),
    )

    id = db.Column(db.Integer, primary_key=True)
    severity = db.Column(_enum_column(RiskSeverity, name="risk_severity"), nullable=False)
    min_score = db.Column(db.Integer, nullable=False)
    max_score = db.Column(db.Integer, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RiskSeverityThreshold severity={self.severity.value} "
            f"min={self.min_score} max={self.max_score}>"
        )
