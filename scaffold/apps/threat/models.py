"""Threat modeling domain models."""

from __future__ import annotations

import enum
import json

import sqlalchemy as sa

from ...extensions import db
from ..identity.models import TimestampMixin, utc_now


def _enum_column(enum_cls: type[enum.Enum], *, name: str) -> sa.Enum:
    """Return a SQLAlchemy Enum storing lowercase enum values."""

    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=False,
        values_callable=lambda members: [member.value for member in members],
    )


class AssetType(enum.Enum):
    COMPONENT = "component"
    DATA_FLOW = "data_flow"
    TRUST_BOUNDARY = "trust_boundary"
    EXTERNAL_ENTITY = "external_entity"
    DATA_STORE = "data_store"


class StrideCategory(enum.Enum):
    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFORMATION_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SERVICE = "denial_of_service"
    ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"
    LATERAL_MOVEMENT = "lateral_movement"


class TreatmentOption(enum.Enum):
    ACCEPT = "accept"
    MITIGATE = "mitigate"
    TRANSFER = "transfer"
    AVOID = "avoid"


class ScenarioStatus(enum.Enum):
    IDENTIFIED = "identified"
    ANALYSED = "analysed"
    MITIGATED = "mitigated"
    ACCEPTED = "accepted"
    CLOSED = "closed"


class RiskLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# M2M: ThreatScenario <-> CSA Control
threat_scenario_controls = db.Table(
    "threat_scenario_controls",
    db.metadata,
    db.Column(
        "scenario_id",
        db.Integer,
        db.ForeignKey("threat_scenarios.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "control_id",
        db.Integer,
        db.ForeignKey("csa_controls.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.UniqueConstraint("scenario_id", "control_id", name="uq_threat_scenario_control"),
)


class ThreatModel(TimestampMixin, db.Model):
    """Top-level container grouping related threat scenarios."""

    __tablename__ = "threat_models"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    scope = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    archived_at = db.Column(db.DateTime(timezone=True), nullable=True)
    product_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_products.id", ondelete="SET NULL"),
        nullable=True,
    )
    suggested_frameworks = db.Column(db.Text, nullable=True)  # JSON array e.g. '["STRIDE","LINDDUN"]'
    dpia_id = db.Column(
        db.Integer,
        db.ForeignKey("dpia_assessments.id", ondelete="SET NULL"),
        nullable=True,
    )
    context_scope_id = db.Column(
        db.Integer,
        db.ForeignKey("bia_context_scope.id", ondelete="SET NULL"),
        nullable=True,
    )

    owner = db.relationship("User", foreign_keys=[owner_id])
    product = db.relationship("ThreatProduct", back_populates="models", foreign_keys=[product_id])
    context_scope = db.relationship("ContextScope", foreign_keys=[context_scope_id])
    assets = db.relationship(
        "ThreatModelAsset",
        back_populates="threat_model",
        cascade="all, delete-orphan",
        order_by="ThreatModelAsset.order",
    )
    scenarios = db.relationship(
        "ThreatScenario",
        back_populates="threat_model",
        cascade="all, delete-orphan",
    )


class ThreatModelAsset(TimestampMixin, db.Model):
    """An asset (component, data flow, trust boundary, etc.) within a ThreatModel."""

    __tablename__ = "threat_model_assets"

    id = db.Column(db.Integer, primary_key=True)
    threat_model_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_models.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(255), nullable=False)
    asset_type = db.Column(_enum_column(AssetType, name="asset_type_enum"), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0, nullable=False)

    threat_model = db.relationship("ThreatModel", back_populates="assets")
    scenarios = db.relationship(
        "ThreatScenario",
        back_populates="asset",
        foreign_keys="ThreatScenario.asset_id",
    )


class ThreatScenario(TimestampMixin, db.Model):
    """A single identified threat scenario within a ThreatModel."""

    __tablename__ = "threat_scenarios"

    id = db.Column(db.Integer, primary_key=True)
    threat_model_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_models.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_model_assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    stride_category = db.Column(
        _enum_column(StrideCategory, name="stride_category_enum"),
        nullable=False,
    )
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    threat_actor = db.Column(db.String(255))
    attack_vector = db.Column(db.Text)
    preconditions = db.Column(db.Text)
    impact_description = db.Column(db.Text)
    affected_cia = db.Column(db.String(3))
    likelihood = db.Column(db.Integer, nullable=False, default=1)
    impact_score = db.Column(db.Integer, nullable=False, default=1)
    risk_score = db.Column(db.Integer, nullable=False, default=1)
    risk_level = db.Column(
        _enum_column(RiskLevel, name="risk_level_enum"),
        nullable=False,
        default=RiskLevel.LOW,
    )
    treatment = db.Column(
        _enum_column(TreatmentOption, name="treatment_option_enum"),
        nullable=True,
    )
    mitigation = db.Column(db.Text)
    residual_likelihood = db.Column(db.Integer, nullable=True)
    residual_impact = db.Column(db.Integer, nullable=True)
    residual_risk_score = db.Column(db.Integer, nullable=True)
    residual_risk_level = db.Column(
        _enum_column(RiskLevel, name="residual_risk_level_enum"),
        nullable=True,
    )
    status = db.Column(
        _enum_column(ScenarioStatus, name="scenario_status_enum"),
        nullable=False,
        default=ScenarioStatus.IDENTIFIED,
    )
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)

    threat_model = db.relationship("ThreatModel", back_populates="scenarios")
    asset = db.relationship(
        "ThreatModelAsset",
        back_populates="scenarios",
        foreign_keys=[asset_id],
    )
    owner = db.relationship("User", foreign_keys=[owner_id])
    controls = db.relationship(
        "Control",
        secondary="threat_scenario_controls",
        backref="threat_scenarios",
    )
    library_entry_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_library_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    library_entry = db.relationship("ThreatLibraryEntry", foreign_keys=[library_entry_id])
    methodology = db.Column(db.String(50), default="STRIDE", nullable=False)
    pasta_stage = db.Column(db.String(100), nullable=True)
    mitigation_actions = db.relationship(
        "ThreatMitigationAction",
        back_populates="scenario",
        cascade="all, delete-orphan",
    )


class ThreatFramework(TimestampMixin, db.Model):
    """A named threat-modeling framework (STRIDE, OWASP Top 10, PASTA, LINDDUN, …)."""

    __tablename__ = "threat_frameworks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    is_builtin = db.Column(db.Boolean, default=True, nullable=False)

    entries = db.relationship(
        "ThreatLibraryEntry",
        back_populates="framework",
        cascade="all, delete-orphan",
    )


class ThreatLibraryEntry(TimestampMixin, db.Model):
    """A reusable threat / mitigation entry from a knowledge-base framework."""

    __tablename__ = "threat_library_entries"

    id = db.Column(db.Integer, primary_key=True)
    framework_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_frameworks.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))
    suggested_mitigation = db.Column(db.Text)
    stride_hint = db.Column(db.String(50), nullable=True)
    is_custom = db.Column(db.Boolean, default=False, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    framework = db.relationship("ThreatFramework", back_populates="entries")
    created_by = db.relationship("User", foreign_keys=[created_by_id])


class ThreatProduct(TimestampMixin, db.Model):
    """Optional product-level grouping of multiple ThreatModels."""

    __tablename__ = "threat_products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_archived = db.Column(db.Boolean, default=False, nullable=False)

    owner = db.relationship("User", foreign_keys=[owner_id])
    models = db.relationship("ThreatModel", back_populates="product")


class MitigationStatus(enum.Enum):
    PROPOSED = "proposed"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"


class ThreatMitigationAction(TimestampMixin, db.Model):
    """Structured mitigation action, optionally linked to a library entry."""

    __tablename__ = "threat_mitigation_actions"

    id = db.Column(db.Integer, primary_key=True)
    scenario_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_scenarios.id", ondelete="CASCADE"),
        nullable=False,
    )
    library_entry_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_library_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(
        _enum_column(MitigationStatus, name="mitigation_status_enum"),
        default=MitigationStatus.PROPOSED,
        nullable=False,
    )
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    due_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text)

    scenario = db.relationship("ThreatScenario", back_populates="mitigation_actions")
    library_entry = db.relationship("ThreatLibraryEntry", foreign_keys=[library_entry_id])
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
