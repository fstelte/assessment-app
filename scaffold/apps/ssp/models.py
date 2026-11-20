"""System Security Plan domain models."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

import sqlalchemy as sa

from ...extensions import db
from ..identity.models import TimestampMixin


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _enum_col(enum_cls: type[enum.Enum], *, name: str) -> sa.Enum:
    return sa.Enum(
        enum_cls,
        name=name,
        native_enum=False,
        values_callable=lambda members: [m.value for m in members],
    )


class FipsRating(enum.Enum):
    NOT_SET = "not_set"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class AgreementType(enum.Enum):
    MOU = "mou"
    ISA = "isa"
    CONTRACT = "contract"
    INFORMAL = "informal"
    NONE = "none"


class DataDirection(enum.Enum):
    INCOMING = "incoming"
    OUTGOING = "outgoing"
    BIDIRECTIONAL = "bidirectional"


class ImplementationStatus(enum.Enum):
    PLANNED = "planned"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    IMPLEMENTED = "implemented"
    NOT_APPLICABLE = "not_applicable"


class ControlSource(enum.Enum):
    THREAT = "threat"
    RISK = "risk"
    MANUAL = "manual"


class POAMStatus(enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DELAYED = "delayed"


class InterconnectionSource(enum.Enum):
    """Where an interconnection's system name comes from (decision 20261118-1455)."""

    BIA = "bia"
    MANUAL = "manual"


class SSPOptionKind(enum.Enum):
    """Admin-managed SSP option lists (decision 20261118-1500)."""

    LAW_REGULATION = "law_regulation"
    MONITORING_FREQUENCY = "monitoring_frequency"


class ADRStatus(enum.Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class SSPOption(db.Model):
    """An admin-managed choice for an SSP list: a law/regulation/policy or a monitoring frequency."""

    __tablename__ = "ssp_options"
    __table_args__ = (sa.UniqueConstraint("kind", "name", name="uq_ssp_options_kind_name"),)

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(_enum_col(SSPOptionKind, name="ssp_option_kind"), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, server_default=sa.true())
    created_at = db.Column(db.DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SSPOption {self.kind.value}:{self.name!r}>"


# M2M: SSPlan <-> SSPOption (kind = law_regulation)
ssp_plan_laws = db.Table(
    "ssp_plan_laws",
    db.metadata,
    db.Column("ssp_id", db.Integer, db.ForeignKey("ssp_plans.id", ondelete="CASCADE"), primary_key=True),
    db.Column("option_id", db.Integer, db.ForeignKey("ssp_options.id", ondelete="CASCADE"), primary_key=True),
)


class SSPlan(db.Model):
    """System Security Plan — one per ContextScope."""

    __tablename__ = "ssp_plans"

    id = db.Column(db.Integer, primary_key=True)
    context_scope_id = db.Column(
        db.Integer,
        db.ForeignKey("bia_context_scope.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    laws_regulations = db.Column(db.Text, nullable=True)
    authorization_boundary = db.Column(db.Text, nullable=True)
    fips_confidentiality = db.Column(
        _enum_col(FipsRating, name="ssp_fips_conf"),
        nullable=False,
        default=FipsRating.NOT_SET,
        server_default="not_set",
    )
    fips_integrity = db.Column(
        _enum_col(FipsRating, name="ssp_fips_integ"),
        nullable=False,
        default=FipsRating.NOT_SET,
        server_default="not_set",
    )
    fips_availability = db.Column(
        _enum_col(FipsRating, name="ssp_fips_avail"),
        nullable=False,
        default=FipsRating.NOT_SET,
        server_default="not_set",
    )
    plan_completion_date = db.Column(db.Date, nullable=True)
    plan_approval_date = db.Column(db.Date, nullable=True)
    monitoring_kpis_kris = db.Column(db.Text, nullable=True)
    monitoring_what = db.Column(db.Text, nullable=True)
    monitoring_who = db.Column(db.Text, nullable=True)
    monitoring_tools = db.Column(db.Text, nullable=True)
    monitoring_frequency_id = db.Column(
        db.Integer,
        db.ForeignKey("ssp_options.id", ondelete="SET NULL"),
        nullable=True,
    )
    adr_register_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    context_scope = db.relationship(
        "ContextScope",
        back_populates="ssp",
    )
    created_by = db.relationship("User", foreign_keys=[created_by_id])
    monitoring_frequency_option = db.relationship("SSPOption", foreign_keys=[monitoring_frequency_id])
    laws_regulations_options = db.relationship(
        "SSPOption",
        secondary=ssp_plan_laws,
        order_by="SSPOption.name",
    )
    interconnections = db.relationship(
        "SSPInterconnection",
        back_populates="ssp",
        cascade="all, delete-orphan",
        order_by="SSPInterconnection.sort_order",
    )
    control_entries = db.relationship(
        "SSPControlEntry",
        back_populates="ssp",
        cascade="all, delete-orphan",
    )
    poam_items = db.relationship(
        "POAMItem",
        back_populates="ssp",
        cascade="all, delete-orphan",
        order_by="POAMItem.scheduled_completion",
    )
    adr_records = db.relationship(
        "ADRRecord",
        back_populates="ssp",
        cascade="all, delete-orphan",
    )
    architecture_overview_versions = db.relationship(
        "SSPArchitectureOverview",
        back_populates="ssp",
        cascade="all, delete-orphan",
        # Interim newest-first so the single-file view's [0] stays current;
        # Task 3 switches to oldest-first for the list display.
        order_by="[SSPArchitectureOverview.uploaded_at.desc(), SSPArchitectureOverview.id.desc()]",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SSPlan context_scope_id={self.context_scope_id}>"


class SSPInterconnection(db.Model):
    """An external system interconnection listed in an SSP."""

    __tablename__ = "ssp_interconnections"

    id = db.Column(db.Integer, primary_key=True)
    ssp_id = db.Column(
        db.Integer,
        db.ForeignKey("ssp_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    system_name = db.Column(db.String(255), nullable=False, default="")
    owning_organization = db.Column(db.String(255), nullable=True)
    agreement_type = db.Column(
        _enum_col(AgreementType, name="ssp_agreement_type"),
        nullable=False,
        default=AgreementType.NONE,
    )
    data_direction = db.Column(
        _enum_col(DataDirection, name="ssp_data_direction"),
        nullable=False,
        default=DataDirection.BIDIRECTIONAL,
    )
    security_contact = db.Column(db.String(255), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    source = db.Column(
        _enum_col(InterconnectionSource, name="ssp_interconnection_source"),
        nullable=False,
        default=InterconnectionSource.MANUAL,
        server_default="manual",
    )

    ssp = db.relationship("SSPlan", back_populates="interconnections")

    @property
    def in_bia(self) -> bool:
        """True when the BIA's ``interfaces`` still lists this system (normalised match)."""
        from .services import normalise_name, parse_interfaces

        scope = self.ssp.context_scope if self.ssp else None
        names = {normalise_name(n) for n in parse_interfaces(scope.interfaces if scope else None)}
        return normalise_name(self.system_name) in names

    @property
    def is_stale(self) -> bool:
        """A BIA-sourced row whose system was removed from the BIA (decision 20261118-1455)."""
        return self.source is InterconnectionSource.BIA and not self.in_bia

    @property
    def is_deletable(self) -> bool:
        """Live BIA rows cannot be deleted: reconcile would add them again (CHK003)."""
        return not (self.source is InterconnectionSource.BIA and self.in_bia)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SSPInterconnection {self.system_name!r}>"


class SSPControlEntry(db.Model):
    """Implementation statement for a control referenced in an SSP."""

    __tablename__ = "ssp_control_entries"
    __table_args__ = (
        sa.UniqueConstraint("ssp_id", "control_id", name="uq_ssp_control_entry"),
    )

    id = db.Column(db.Integer, primary_key=True)
    ssp_id = db.Column(
        db.Integer,
        db.ForeignKey("ssp_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    control_id = db.Column(
        db.Integer,
        db.ForeignKey("csa_controls.id", ondelete="CASCADE"),
        nullable=False,
    )
    implementation_status = db.Column(
        _enum_col(ImplementationStatus, name="ssp_impl_status"),
        nullable=False,
        default=ImplementationStatus.PLANNED,
        server_default="planned",
    )
    responsible_entity = db.Column(db.String(255), nullable=True)
    implementation_statement = db.Column(db.Text, nullable=True)
    source = db.Column(
        _enum_col(ControlSource, name="ssp_control_source"),
        nullable=False,
        default=ControlSource.MANUAL,
        server_default="manual",
    )

    ssp = db.relationship("SSPlan", back_populates="control_entries")
    control = db.relationship("Control")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SSPControlEntry ssp_id={self.ssp_id} control_id={self.control_id}>"


class POAMItem(db.Model):
    """Plan of Action and Milestones (POA&M) item linked to an SSP."""

    __tablename__ = "ssp_poam_items"

    id = db.Column(db.Integer, primary_key=True)
    ssp_id = db.Column(
        db.Integer,
        db.ForeignKey("ssp_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_threat_mitigation_id = db.Column(
        db.Integer,
        db.ForeignKey("threat_mitigation_actions.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
    )
    weakness_description = db.Column(db.Text, nullable=False)
    resources_required = db.Column(db.Text, nullable=True)
    point_of_contact = db.Column(db.String(255), nullable=True)
    scheduled_completion = db.Column(db.Date, nullable=True)
    estimated_cost = db.Column(db.String(100), nullable=True)
    jira_url = db.Column(db.String(500), nullable=True)
    status = db.Column(
        _enum_col(POAMStatus, name="ssp_poam_status"),
        nullable=False,
        default=POAMStatus.OPEN,
        server_default="open",
    )
    created_at = db.Column(db.DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    ssp = db.relationship("SSPlan", back_populates="poam_items")
    milestones = db.relationship(
        "POAMMilestone",
        back_populates="item",
        cascade="all, delete-orphan",
        order_by="POAMMilestone.scheduled_date",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<POAMItem ssp_id={self.ssp_id} status={self.status.value!r}>"


class POAMMilestone(db.Model):
    """A milestone within a POA&M item."""

    __tablename__ = "ssp_poam_milestones"

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(
        db.Integer,
        db.ForeignKey("ssp_poam_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    description = db.Column(db.Text, nullable=False)
    scheduled_date = db.Column(db.Date, nullable=True)
    completed_date = db.Column(db.Date, nullable=True)

    item = db.relationship("POAMItem", back_populates="milestones")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<POAMMilestone item_id={self.item_id}>"


class ArchitecturePrinciple(db.Model):
    """Admin-governed architecture principle that ADRs are anchored to."""

    __tablename__ = "architecture_principles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ArchitecturePrinciple {self.name!r}>"


# M2M: ADRRecord <-> ArchitecturePrinciple (secondary principles)
adr_secondary_principles = db.Table(
    "adr_secondary_principles",
    db.metadata,
    db.Column(
        "adr_id",
        db.Integer,
        db.ForeignKey("adr_records.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    db.Column(
        "principle_id",
        db.Integer,
        db.ForeignKey("architecture_principles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class ADRRecord(db.Model):
    """Architecture Decision Record (adr.github.io) attached to an SSP."""

    __tablename__ = "adr_records"

    id = db.Column(db.Integer, primary_key=True)
    ssp_id = db.Column(
        db.Integer,
        db.ForeignKey("ssp_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    title = db.Column(db.String(255), nullable=False)
    status = db.Column(
        _enum_col(ADRStatus, name="adr_status"),
        nullable=False,
        default=ADRStatus.PROPOSED,
        server_default="proposed",
    )
    # Either an external link, or both context and decision (decision 20261118-1515).
    context = db.Column(db.Text, nullable=True)
    decision = db.Column(db.Text, nullable=True)
    consequences = db.Column(db.Text, nullable=True)
    external_url = db.Column(db.String(500), nullable=True)
    # Status this ADR had when another ADR superseded it, restored if that
    # successor is deleted (decision 20261118-1530, CHK001).
    status_before_supersede = db.Column(
        _enum_col(ADRStatus, name="adr_status_before_supersede"),
        nullable=True,
    )
    primary_principle_id = db.Column(
        db.Integer,
        db.ForeignKey("architecture_principles.id"),
        nullable=False,
    )
    supersedes_id = db.Column(
        db.Integer,
        db.ForeignKey("adr_records.id"),
        nullable=True,
        unique=True,
    )
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decided_on = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=_utc_now, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=_utc_now, onupdate=_utc_now, nullable=False)

    ssp = db.relationship("SSPlan", back_populates="adr_records")
    primary_principle = db.relationship("ArchitecturePrinciple", foreign_keys=[primary_principle_id])
    secondary_principles = db.relationship(
        "ArchitecturePrinciple",
        secondary=adr_secondary_principles,
        backref="secondary_adrs",
    )
    author = db.relationship("User", foreign_keys=[author_id])
    supersedes = db.relationship(
        "ADRRecord",
        remote_side=[id],
        backref=db.backref("superseded_by", uselist=False),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ADRRecord ssp_id={self.ssp_id} title={self.title!r} status={self.status.value!r}>"


class SSPArchitectureOverview(db.Model):
    """An uploaded architecture overview file for an SSP (decision 20261119-1825).

    The table keeps its legacy ``..._versions`` name (decision 20261120-0900, CHK010).
    """

    __tablename__ = "ssp_architecture_overview_versions"

    id = db.Column(db.Integer, primary_key=True)
    ssp_id = db.Column(
        db.Integer,
        db.ForeignKey("ssp_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    image_data = db.Column(db.LargeBinary, nullable=False)
    mime_type = db.Column(db.String(20), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size_bytes = db.Column(db.Integer, nullable=False)
    uploaded_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    uploaded_at = db.Column(db.DateTime(timezone=True), default=_utc_now, nullable=False)

    ssp = db.relationship("SSPlan", back_populates="architecture_overview_versions")
    uploaded_by = db.relationship("User", foreign_keys=[uploaded_by_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SSPArchitectureOverview ssp_id={self.ssp_id} filename={self.original_filename!r}>"
