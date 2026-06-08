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


class Methodology(enum.Enum):
    STRIDE = "STRIDE"
    PASTA = "PASTA"
    LINDDUN = "LINDDUN"
    OWASP = "OWASP"


# Canonical PASTA stage codes in ordered sequence
PASTA_STAGE_CODES: list[str] = [
    "define_objectives",
    "define_technical_scope",
    "decompose_application",
    "analyze_threats",
    "vulnerability_analysis",
    "attack_analysis",
    "risk_impact_analysis",
]

# Human-readable labels keyed by stage code (used for display/localization lookup)
PASTA_STAGE_LABELS: dict[str, str] = {
    "define_objectives": "Define Objectives",
    "define_technical_scope": "Define Technical Scope",
    "decompose_application": "Decompose Application",
    "analyze_threats": "Analyze Threats",
    "vulnerability_analysis": "Vulnerability Analysis",
    "attack_analysis": "Attack Analysis",
    "risk_impact_analysis": "Risk & Impact Analysis",
}

# Minimum content required to advance past each stage gate (FR-003B)
PASTA_STAGE_GATE_RULES: dict[str, dict] = {
    "define_objectives": {"min_findings": 1, "requires_scope": True},
    "define_technical_scope": {"min_findings": 1, "requires_notes": True},
    "decompose_application": {"min_findings": 1, "requires_notes": False},
    "analyze_threats": {"min_findings": 1, "requires_notes": False},
    "vulnerability_analysis": {"min_findings": 1, "requires_notes": False},
    "attack_analysis": {"min_findings": 1, "requires_notes": False},
    "risk_impact_analysis": {"min_findings": 1, "requires_notes": False},
}


class PastaStageStatus(enum.Enum):
    LOCKED = "locked"
    AVAILABLE = "available"
    COMPLETED = "completed"
    NEEDS_REVALIDATION = "needs_revalidation"


class PastaFindingType(enum.Enum):
    OBJECTIVE = "objective"
    SCOPE_ITEM = "scope_item"
    DECOMPOSITION_ITEM = "decomposition_item"
    THREAT = "threat"
    VULNERABILITY = "vulnerability"
    ATTACK_PATH = "attack_path"
    RISK_CONCLUSION = "risk_conclusion"


# Which finding types are eligible for downstream scenario generation (FR-016A)
PASTA_THREAT_FINDING_TYPES: frozenset[str] = frozenset(
    [
        PastaFindingType.THREAT.value,
        PastaFindingType.VULNERABILITY.value,
        PastaFindingType.ATTACK_PATH.value,
        PastaFindingType.RISK_CONCLUSION.value,
    ]
)

# Default finding type per stage
PASTA_STAGE_DEFAULT_FINDING_TYPE: dict[str, str] = {
    "define_objectives": PastaFindingType.OBJECTIVE.value,
    "define_technical_scope": PastaFindingType.SCOPE_ITEM.value,
    "decompose_application": PastaFindingType.DECOMPOSITION_ITEM.value,
    "analyze_threats": PastaFindingType.THREAT.value,
    "vulnerability_analysis": PastaFindingType.VULNERABILITY.value,
    "attack_analysis": PastaFindingType.ATTACK_PATH.value,
    "risk_impact_analysis": PastaFindingType.RISK_CONCLUSION.value,
}


class PastaFindingStatus(enum.Enum):
    DRAFT = "draft"
    CURRENT = "current"
    NEEDS_REVALIDATION = "needs_revalidation"
    ARCHIVED = "archived"


# Revalidation trigger: stages that become needs_revalidation when an earlier
# stage with significant content changes. Index = stage position (1-based).
# Editing stage N marks stages N+1 through 7 as needs_revalidation (FR-018B).
PASTA_REVALIDATION_TRIGGER_FIELDS: frozenset[str] = frozenset(
    [
        "define_objectives",       # changes trigger all later stages
        "define_technical_scope",  # changes trigger stages 3-7
        "decompose_application",   # changes trigger stages 4-7
        "analyze_threats",         # changes trigger stages 5-7
    ]
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

# M2M: ThreatScenario <-> ThreatModelAsset (plural assignment)
threat_scenario_assets = db.Table(
    "threat_scenario_assets",
    db.metadata,
    db.Column(
        "scenario_id",
        db.Integer,
        db.ForeignKey("threat_scenarios.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "asset_id",
        db.Integer,
        db.ForeignKey("threat_model_assets.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    sa.UniqueConstraint("scenario_id", "asset_id", name="uq_threat_scenario_asset"),
)


class ThreatScenarioStrideCategory(db.Model):
    """Association row connecting one threat scenario to one STRIDE-LM category."""

    __tablename__ = "threat_scenario_stride_categories"
    __table_args__ = (
        sa.UniqueConstraint("scenario_id", "stride_category", name="uq_threat_scenario_stride"),
    )

    scenario_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_scenarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    stride_category = db.Column(db.String(50), nullable=False, primary_key=True)


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
    # PASTA workflow extension fields
    methodology = db.Column(db.String(20), nullable=False, default=Methodology.STRIDE.value)
    bootstrap_source_model_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_models.id", ondelete="SET NULL"),
        nullable=True,
    )
    bootstrap_source = db.relationship(
        "ThreatModel",
        foreign_keys="[ThreatModel.bootstrap_source_model_id]",
        primaryjoin="ThreatModel.bootstrap_source_model_id == ThreatModel.id",
        remote_side="ThreatModel.id",
        uselist=False,
    )
    pasta_stages = db.relationship(
        "PastaStageRecord",
        back_populates="threat_model",
        cascade="all, delete-orphan",
        order_by="PastaStageRecord.display_order",
    )

    @property
    def is_pasta(self) -> bool:
        return self.methodology == Methodology.PASTA.value


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
    # Plural asset assignments (US1)
    assigned_assets = db.relationship(
        "ThreatModelAsset",
        secondary="threat_scenario_assets",
        backref=db.backref("assigned_scenarios", lazy="dynamic"),
    )
    # Plural STRIDE-LM category assignments (US2)
    stride_category_links = db.relationship(
        "ThreatScenarioStrideCategory",
        cascade="all, delete-orphan",
        backref="scenario",
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
    risk_id = db.Column(
        db.Integer,
        db.ForeignKey("risk_items.id", ondelete="SET NULL"),
        nullable=True,
    )
    linked_risk = db.relationship("Risk", foreign_keys=[risk_id])


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


# ---------------------------------------------------------------------------
# PASTA workflow models (model-level workflow extension)
# ---------------------------------------------------------------------------


class PastaStageRecord(TimestampMixin, db.Model):
    """One of the seven ordered PASTA stages for a PASTA ThreatModel."""

    __tablename__ = "pasta_stage_records"
    __table_args__ = (
        sa.UniqueConstraint("threat_model_id", "stage_code", name="uq_pasta_stage_model_code"),
    )

    id = db.Column(db.Integer, primary_key=True)
    threat_model_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_models.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage_code = db.Column(db.String(60), nullable=False)
    display_order = db.Column(db.Integer, nullable=False)
    status = db.Column(
        _enum_column(PastaStageStatus, name="pasta_stage_status_enum"),
        nullable=False,
        default=PastaStageStatus.LOCKED,
    )
    summary = db.Column(db.Text)
    completion_notes = db.Column(db.Text)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    completed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    last_revalidated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    threat_model = db.relationship("ThreatModel", back_populates="pasta_stages")
    completed_by = db.relationship("User", foreign_keys=[completed_by_id])
    findings = db.relationship(
        "PastaFinding",
        back_populates="stage_record",
        cascade="all, delete-orphan",
        order_by="PastaFinding.id",
    )

    @property
    def label(self) -> str:
        from .models import PASTA_STAGE_LABELS
        return PASTA_STAGE_LABELS.get(self.stage_code, self.stage_code)


class PastaFinding(TimestampMixin, db.Model):
    """A reviewable finding captured within one PASTA stage."""

    __tablename__ = "pasta_findings"

    id = db.Column(db.Integer, primary_key=True)
    stage_record_id = db.Column(
        db.Integer,
        db.ForeignKey("pasta_stage_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    finding_type = db.Column(
        _enum_column(PastaFindingType, name="pasta_finding_type_enum"),
        nullable=False,
    )
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    evidence = db.Column(db.Text)
    priority = db.Column(db.String(20), nullable=True)
    status = db.Column(
        _enum_column(PastaFindingStatus, name="pasta_finding_status_enum"),
        nullable=False,
        default=PastaFindingStatus.CURRENT,
    )
    source_library_entry_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_library_entries.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    stage_record = db.relationship("PastaStageRecord", back_populates="findings")
    source_library_entry = db.relationship("ThreatLibraryEntry", foreign_keys=[source_library_entry_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    updated_by = db.relationship("User", foreign_keys=[updated_by_id])
    asset_links = db.relationship(
        "PastaFindingAssetLink",
        back_populates="finding",
        cascade="all, delete-orphan",
    )
    stride_links = db.relationship(
        "PastaFindingStrideCategoryLink",
        back_populates="finding",
        cascade="all, delete-orphan",
    )
    scenario_links = db.relationship(
        "PastaFindingThreatScenarioLink",
        back_populates="finding",
        cascade="all, delete-orphan",
    )

    @property
    def is_threat_oriented(self) -> bool:
        from .models import PASTA_THREAT_FINDING_TYPES
        return self.finding_type.value in PASTA_THREAT_FINDING_TYPES


class PastaFindingAssetLink(db.Model):
    """M2M: PastaFinding <-> ThreatModelAsset."""

    __tablename__ = "pasta_finding_asset_links"
    __table_args__ = (
        sa.UniqueConstraint("finding_id", "asset_id", name="uq_pasta_finding_asset"),
    )

    finding_id = db.Column(
        db.Integer,
        db.ForeignKey("pasta_findings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    asset_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_model_assets.id", ondelete="CASCADE"),
        primary_key=True,
    )

    finding = db.relationship("PastaFinding", back_populates="asset_links")
    asset = db.relationship("ThreatModelAsset")


class PastaFindingStrideCategoryLink(db.Model):
    """Optional STRIDE-LM category mapping for a PASTA finding."""

    __tablename__ = "pasta_finding_stride_links"
    __table_args__ = (
        sa.UniqueConstraint("finding_id", "stride_category", name="uq_pasta_finding_stride"),
    )

    finding_id = db.Column(
        db.Integer,
        db.ForeignKey("pasta_findings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    stride_category = db.Column(db.String(50), nullable=False, primary_key=True)

    finding = db.relationship("PastaFinding", back_populates="stride_links")


class PastaFindingThreatScenarioLink(db.Model):
    """Traceability link: PastaFinding -> ThreatScenario (generated or linked)."""

    __tablename__ = "pasta_finding_scenario_links"
    __table_args__ = (
        sa.UniqueConstraint("finding_id", "scenario_id", name="uq_pasta_finding_scenario"),
    )

    finding_id = db.Column(
        db.Integer,
        db.ForeignKey("pasta_findings.id", ondelete="CASCADE"),
        primary_key=True,
    )
    scenario_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_scenarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    link_type = db.Column(db.String(20), nullable=False, default="linked")  # "generated" | "linked"

    finding = db.relationship("PastaFinding", back_populates="scenario_links")
    scenario = db.relationship("ThreatScenario")


# ---------------------------------------------------------------------------
# PASTA stage guidance metadata (FR-002, FR-004, FR-005)
# ---------------------------------------------------------------------------

#: Per-stage guidance shown to the user: purpose, expected inputs, downstream outputs.
PASTA_STAGE_GUIDANCE: dict[str, dict[str, str]] = {
    "define_objectives": {
        "purpose": "pasta.stage.define_objectives.purpose",
        "inputs": "pasta.stage.define_objectives.inputs",
        "outputs": "pasta.stage.define_objectives.outputs",
    },
    "define_technical_scope": {
        "purpose": "pasta.stage.define_technical_scope.purpose",
        "inputs": "pasta.stage.define_technical_scope.inputs",
        "outputs": "pasta.stage.define_technical_scope.outputs",
    },
    "decompose_application": {
        "purpose": "pasta.stage.decompose_application.purpose",
        "inputs": "pasta.stage.decompose_application.inputs",
        "outputs": "pasta.stage.decompose_application.outputs",
    },
    "analyze_threats": {
        "purpose": "pasta.stage.analyze_threats.purpose",
        "inputs": "pasta.stage.analyze_threats.inputs",
        "outputs": "pasta.stage.analyze_threats.outputs",
    },
    "vulnerability_analysis": {
        "purpose": "pasta.stage.vulnerability_analysis.purpose",
        "inputs": "pasta.stage.vulnerability_analysis.inputs",
        "outputs": "pasta.stage.vulnerability_analysis.outputs",
    },
    "attack_analysis": {
        "purpose": "pasta.stage.attack_analysis.purpose",
        "inputs": "pasta.stage.attack_analysis.inputs",
        "outputs": "pasta.stage.attack_analysis.outputs",
    },
    "risk_impact_analysis": {
        "purpose": "pasta.stage.risk_impact_analysis.purpose",
        "inputs": "pasta.stage.risk_impact_analysis.inputs",
        "outputs": "pasta.stage.risk_impact_analysis.outputs",
    },
}


class PastaPublicationState(enum.Enum):
    """Publication state for a PastaRiskConclusion."""

    NOT_PUBLISHED = "not_published"
    PUBLISHED = "published"
    NEEDS_REVALIDATION = "needs_revalidation"


# ---------------------------------------------------------------------------
# PastaRiskConclusion – structured stage-seven scoring and publication state
# ---------------------------------------------------------------------------


class PastaRiskConclusion(TimestampMixin, db.Model):
    """Structured stage-seven scoring and publication state for one risk_conclusion finding.

    One-to-one with PastaFinding (finding_type=risk_conclusion).
    Optional link to a published Risk row in the risk workspace.
    """

    __tablename__ = "pasta_risk_conclusions"

    id = db.Column(db.Integer, primary_key=True)
    finding_id = db.Column(
        db.Integer,
        db.ForeignKey("pasta_findings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    likelihood_score = db.Column(db.Integer, nullable=True)
    impact_score = db.Column(db.Integer, nullable=True)
    overall_score = db.Column(db.Integer, nullable=True)
    treatment = db.Column(db.String(20), nullable=True, default="mitigate")
    publication_state = db.Column(
        _enum_column(PastaPublicationState, name="pasta_publication_state_enum"),
        nullable=False,
        default=PastaPublicationState.NOT_PUBLISHED,
    )
    published_risk_id = db.Column(
        db.Integer,
        db.ForeignKey("risk_items.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    last_published_at = db.Column(db.DateTime(timezone=True), nullable=True)
    last_published_by_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    publication_notes = db.Column(db.Text, nullable=True)

    finding = db.relationship(
        "PastaFinding",
        backref=db.backref("risk_conclusion", uselist=False, cascade="all, delete-orphan"),
    )
    published_risk = db.relationship("Risk", foreign_keys=[published_risk_id])
    last_published_by = db.relationship("User", foreign_keys=[last_published_by_id])

    @property
    def is_publishable(self) -> bool:
        """Return True when the conclusion meets all publication gates (FR-011A)."""
        if not (self.likelihood_score and self.impact_score and self.overall_score):
            return False
        if not (self.finding and self.finding.description and self.finding.description.strip()):
            return False
        if self.finding.status.value == PastaFindingStatus.NEEDS_REVALIDATION.value:
            return False
        # Check owning stage revalidation state
        stage = self.finding.stage_record if self.finding else None
        if stage and stage.status.value == PastaStageStatus.NEEDS_REVALIDATION.value:
            return False
        return True

    @property
    def blocked_reasons(self) -> list[str]:
        """Return a list of i18n keys explaining why publication is blocked."""
        reasons: list[str] = []
        if not (self.likelihood_score and self.impact_score):
            reasons.append("pasta.risk_conclusion.blocked.missing_scores")
        if not self.overall_score:
            reasons.append("pasta.risk_conclusion.blocked.missing_overall_score")
        if not (self.finding and self.finding.description and self.finding.description.strip()):
            reasons.append("pasta.risk_conclusion.blocked.missing_narrative")
        if self.finding and self.finding.status.value == PastaFindingStatus.NEEDS_REVALIDATION.value:
            reasons.append("pasta.risk_conclusion.blocked.finding_needs_revalidation")
        stage = self.finding.stage_record if self.finding else None
        if stage and stage.status.value == PastaStageStatus.NEEDS_REVALIDATION.value:
            reasons.append("pasta.risk_conclusion.blocked.stage_needs_revalidation")
        return reasons
