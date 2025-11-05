"""Business Impact Analysis domain models."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Enum, Text, event, inspect

from ....extensions import db
from ...identity.models import User


class ContextScope(db.Model):
    """Represents the scope of a BIA context."""

    __tablename__ = "bia_context_scope"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(Text, nullable=False)
    responsible = db.Column(Text)
    coordinator = db.Column(Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    last_update = db.Column(db.Date, default=date.today)
    service_description = db.Column(Text)
    knowledge = db.Column(Text)
    interfaces = db.Column(Text)
    mission_critical = db.Column(Text)
    support_contracts = db.Column(Text)
    security_supplier = db.Column(Text)
    user_amount = db.Column(db.Integer)
    scope_description = db.Column(Text)

    risk_assessment_human = db.Column(db.Boolean, default=False)
    risk_assessment_process = db.Column(db.Boolean, default=False)
    risk_assessment_technological = db.Column(db.Boolean, default=False)
    ai_model = db.Column(db.Boolean, default=False)

    project_leader = db.Column(Text)
    risk_owner = db.Column(Text)
    product_owner = db.Column(Text)
    technical_administrator = db.Column(Text)
    security_manager = db.Column(Text)
    incident_contact = db.Column(Text)

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    author = db.relationship(User, back_populates="bia_contexts")
    components = db.relationship(
        "Component",
        back_populates="context_scope",
        cascade="all, delete-orphan",
    )
    summary = db.relationship(
        "Summary",
        uselist=False,
        back_populates="context_scope",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ContextScope {self.name}>"


class Component(db.Model):
    """Component linked to a BIA context."""

    __tablename__ = "bia_components"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(Text, nullable=False)
    info_type = db.Column(Text)
    info_owner = db.Column(Text)
    user_type = db.Column(Text)
    process_dependencies = db.Column(Text)
    description = db.Column(Text)
    context_scope_id = db.Column(db.Integer, db.ForeignKey("bia_context_scope.id"), nullable=False)

    context_scope = db.relationship("ContextScope", back_populates="components")
    consequences = db.relationship(
        "Consequences",
        back_populates="component",
        cascade="all, delete-orphan",
    )
    availability_requirement = db.relationship(
        "AvailabilityRequirements",
        back_populates="component",
        uselist=False,
        cascade="all, delete-orphan",
    )
    ai_identificaties = db.relationship(
        "AIIdentificatie",
        back_populates="component",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Component {self.name}>"


class Consequences(db.Model):
    """CIA consequence records per component."""

    __tablename__ = "bia_consequences"

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey("bia_components.id"), nullable=False)
    consequence_category = db.Column(Text)
    security_property = db.Column(Text)
    consequence_worstcase = db.Column(Text)
    justification_worstcase = db.Column(Text)
    consequence_realisticcase = db.Column(Text)
    justification_realisticcase = db.Column(Text)

    component = db.relationship("Component", back_populates="consequences")

    def get_categories(self) -> list[str]:
        if not self.consequence_category:
            return []
        return [category.strip() for category in self.consequence_category.split(",") if category.strip()]


class AvailabilityRequirements(db.Model):
    """Captures availability targets associated with a component."""

    __tablename__ = "bia_availability_requirements"

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey("bia_components.id"), nullable=False)
    mtd = db.Column(Text)
    rto = db.Column(Text)
    rpo = db.Column(Text)
    masl = db.Column(Text)

    component = db.relationship("Component", back_populates="availability_requirement")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AvailabilityRequirements component_id={self.component_id}>"


class AIIdentificatie(db.Model):
    """AI risk classification for a component."""

    __tablename__ = "bia_ai_identificatie"

    id = db.Column(db.Integer, primary_key=True)
    component_id = db.Column(db.Integer, db.ForeignKey("bia_components.id"), nullable=False)
    category = db.Column(
        Enum(
            "No AI",
            "Unacceptable risk",
            "High risk",
            "Limited risk",
            "Minimal risk",
            name="bia_ai_category",
        ),
        default="No AI",
    )
    motivatie = db.Column(Text)

    component = db.relationship("Component", back_populates="ai_identificaties")


class Summary(db.Model):
    """Summary report attached to a context scope."""

    __tablename__ = "bia_summary"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(Text)
    context_scope_id = db.Column(db.Integer, db.ForeignKey("bia_context_scope.id"), unique=True)

    context_scope = db.relationship("ContextScope", back_populates="summary")


_TRACKED_MODELS = [ContextScope, Component, Consequences, AvailabilityRequirements, AIIdentificatie, Summary]


def _update_last_modified(mapper, connection, target) -> None:
    """Keep the context scope `last_update` in sync when related records change."""

    context_scope: ContextScope | None = None

    if isinstance(target, ContextScope):
        if getattr(target, "_suppress_last_update", False):
            target.__dict__.pop("_suppress_last_update", None)
            return
        state = inspect(target)
        changed_attrs = {attr.key for attr in state.attrs if attr.history.has_changes()}
        ignored_attrs = {"author_id", "author", "last_update"}

        if not (changed_attrs - ignored_attrs):
            return

        context_scope = target
    elif isinstance(target, Component):
        context_scope = target.context_scope
    elif isinstance(target, (Consequences, AvailabilityRequirements, AIIdentificatie)):
        component = getattr(target, "component", None)
        if component is not None:
            context_scope = component.context_scope
    elif isinstance(target, Summary):
        context_scope = target.context_scope

    if context_scope is not None:
        context_scope.last_update = date.today()


def configure_listeners() -> None:
    """Attach SQLAlchemy event listeners for automatic timestamp updates."""

    event.listen(ContextScope, "before_update", _update_last_modified)

    for model in _TRACKED_MODELS:
        event.listen(model, "after_insert", _update_last_modified)
        event.listen(model, "after_update", _update_last_modified)
        event.listen(model, "after_delete", _update_last_modified)


configure_listeners()
