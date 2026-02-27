"""Forms for the Business Impact Analysis workflow."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, DateField, FieldList, FormField, HiddenField, IntegerField, PasswordField, SelectField, SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms.form import Form
from wtforms.validators import DataRequired, EqualTo, Length, Optional, NumberRange, ValidationError
import sqlalchemy as sa
from ...extensions import db
from .models import BiaTier
from scaffold.core.i18n import lazy_gettext as _l, get_locale


# Keep in sync with ENVIRONMENT_TYPES in .models.__init__
_COMPONENT_ENVIRONMENT_TYPES = ("development", "test", "acceptance", "production")

_AI_CATEGORY_CHOICES = (
    ("No AI", _l("bia.components.ai.options.no_ai")),
    ("Unacceptable risk", _l("bia.components.ai.options.unacceptable")),
    ("High risk", _l("bia.components.ai.options.high")),
    ("Limited risk", _l("bia.components.ai.options.limited")),
    ("Minimal risk", _l("bia.components.ai.options.minimal")),
)


def _optional_int(value: object) -> int | None:
    if value in (None, "", "None"):
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError("Not a valid integer value") from exc


class ContextScopeForm(FlaskForm):
    """Capture or update the core attributes of a BIA context."""

    name = StringField(
        _l("bia.context_form.fields.name.label"),
        validators=[DataRequired(), Length(max=255)],
        description=_l("bia.context_form.tooltips.name"),
    )
    tier = SelectField(
        _l("bia.context_form.fields.tier.label"),
        validators=[Optional()],
        coerce=_optional_int,
        description=_l("bia.context_form.tooltips.tier"),
    )
    responsible = StringField(
        _l("bia.context_form.fields.responsible.label"),
        validators=[Optional(), Length(max=255)],
        description=_l("bia.context_form.tooltips.responsible"),
    )
    coordinator = StringField(
        _l("bia.context_form.fields.coordinator.label"),
        validators=[Optional(), Length(max=255)],
        description=_l("bia.context_form.tooltips.coordinator"),
    )
    start_date = DateField(
        _l("bia.context_form.fields.start_date.label"),
        format="%Y-%m-%d",
        validators=[Optional()],
        description=_l("bia.context_form.tooltips.start_date"),
    )
    end_date = DateField(
        _l("bia.context_form.fields.end_date.label"),
        format="%Y-%m-%d",
        validators=[Optional()],
        description=_l("bia.context_form.tooltips.end_date"),
    )
    service_description = TextAreaField(
        _l("bia.context_form.fields.service_description.label"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.context_form.tooltips.service_description"),
    )
    knowledge = TextAreaField(
        _l("bia.context_form.fields.knowledge.label"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.context_form.tooltips.knowledge"),
    )
    interfaces = TextAreaField(
        _l("bia.context_form.fields.interfaces.label"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.context_form.tooltips.interfaces"),
    )
    mission_critical = TextAreaField(
        _l("bia.context_form.fields.mission_critical.label"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.context_form.tooltips.mission_critical"),
    )
    support_contracts = TextAreaField(
        _l("bia.context_form.fields.support_contracts.label"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.context_form.tooltips.support_contracts"),
    )
    security_supplier = TextAreaField(
        _l("bia.context_form.fields.security_supplier.label"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.context_form.tooltips.security_supplier"),
    )
    user_amount = IntegerField(
        _l("bia.context_form.fields.user_amount.label"),
        validators=[Optional(), NumberRange(min=0)],
        description=_l("bia.context_form.tooltips.user_amount"),
    )
    scope_description = TextAreaField(
        _l("bia.context_form.fields.scope_description.label"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.context_form.tooltips.scope_description"),
    )
    risk_assessment_human = BooleanField(
        _l("bia.context_form.fields.risk_assessment_human.label"),
        description=_l("bia.context_form.tooltips.risk_assessment_human"),
    )
    risk_assessment_process = BooleanField(
        _l("bia.context_form.fields.risk_assessment_process.label"),
        description=_l("bia.context_form.tooltips.risk_assessment_process"),
    )
    risk_assessment_technological = BooleanField(
        _l("bia.context_form.fields.risk_assessment_technological.label"),
        description=_l("bia.context_form.tooltips.risk_assessment_technological"),
    )
    ai_model = BooleanField(
        _l("bia.context_form.fields.ai_model.label"),
        description=_l("bia.context_form.tooltips.ai_model"),
    )
    project_leader = StringField(
        _l("bia.context_form.fields.project_leader.label"),
        validators=[Optional(), Length(max=255)],
        description=_l("bia.context_form.tooltips.project_leader"),
    )
    risk_owner = StringField(
        _l("bia.context_form.fields.risk_owner.label"),
        validators=[Optional(), Length(max=255)],
        description=_l("bia.context_form.tooltips.risk_owner"),
    )
    product_owner = StringField(
        _l("bia.context_form.fields.product_owner.label"),
        validators=[Optional(), Length(max=255)],
        description=_l("bia.context_form.tooltips.product_owner"),
    )
    technical_administrator = StringField(
        _l("bia.context_form.fields.technical_administrator.label"),
        validators=[Optional(), Length(max=255)],
        description=_l("bia.context_form.tooltips.technical_administrator"),
    )
    security_manager = StringField(
        _l("bia.context_form.fields.security_manager.label"),
        validators=[Optional(), Length(max=255)],
        description=_l("bia.context_form.tooltips.security_manager"),
    )
    incident_contact = StringField(
        _l("bia.context_form.fields.incident_contact.label"),
        validators=[Optional(), Length(max=255)],
        description=_l("bia.context_form.tooltips.incident_contact"),
    )
    submit = SubmitField("Save context")

    def validate_end_date(self, field):
        if self.start_date.data and field.data:
            if field.data < self.start_date.data:
                raise ValidationError(_l("bia.context_form.errors.end_date_before_start"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        locale = get_locale()
        tiers = db.session.scalars(sa.select(BiaTier).order_by(BiaTier.level)).all()
        self.tier.choices = [(t.id, t.get_label(locale)) for t in tiers]
        self.tier.choices.insert(0, (None, "-"))

class ComponentEnvironmentForm(Form):
    """Capture whether a component uses a specific environment."""

    environment_type = HiddenField(validators=[DataRequired()])
    is_enabled = BooleanField("Environment enabled")
    authentication_method = SelectField(
        "Environment authentication",
        validators=[Optional()],
        choices=[],
        coerce=_optional_int,
    )

    class Meta:
        csrf = False


class ComponentForm(FlaskForm):
    """Create or update a component linked to a BIA context."""

    name = StringField(
        _l("bia.components.labels.name"),
        validators=[DataRequired(), Length(max=255)],
        description=_l("bia.components.tooltips.name"),
    )
    info_type = StringField(
        _l("bia.components.labels.information_type"),
        validators=[Optional(), Length(max=255)],
        description=_l("bia.components.tooltips.info_type"),
    )
    info_owner = StringField(
        _l("bia.components.labels.owner"),
        validators=[Optional(), Length(max=255)],
        description=_l("bia.components.tooltips.info_owner"),
    )
    user_type = StringField(
        _l("bia.components.labels.user_type"),
        validators=[Optional(), Length(max=255)],
        description=_l("bia.components.tooltips.user_type"),
    )
    dependencies_it_systems_applications = TextAreaField(
        _l("bia.components.labels.dependencies_it_systems_applications"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.components.tooltips.dependencies_it_systems_applications"),
    )
    dependencies_equipment = TextAreaField(
        _l("bia.components.labels.dependencies_equipment"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.components.tooltips.dependencies_equipment"),
    )
    dependencies_suppliers = TextAreaField(
        _l("bia.components.labels.dependencies_suppliers"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.components.tooltips.dependencies_suppliers"),
    )
    dependencies_people = TextAreaField(
        _l("bia.components.labels.dependencies_people"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.components.tooltips.dependencies_people"),
    )
    dependencies_facilities = TextAreaField(
        _l("bia.components.labels.dependencies_facilities"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.components.tooltips.dependencies_facilities"),
    )
    dependencies_others = TextAreaField(
        _l("bia.components.labels.dependencies_others"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.components.tooltips.dependencies_others"),
    )
    description = TextAreaField(
        _l("bia.components.labels.description"),
        validators=[Optional(), Length(max=5000)],
        description=_l("bia.components.tooltips.description"),
    )
    environments = FieldList(
        FormField(ComponentEnvironmentForm),
        min_entries=len(_COMPONENT_ENVIRONMENT_TYPES),
        max_entries=len(_COMPONENT_ENVIRONMENT_TYPES),
    )
    ai_category = SelectField(
        _l("bia.components.modal.category"),
        choices=list(_AI_CATEGORY_CHOICES),
        validators=[Optional()],
        default="No AI",
    )
    ai_motivatie = TextAreaField(
        _l("bia.components.modal.motivation"),
        validators=[Optional()],
    )
    submit = SubmitField("Save component")


class ConsequenceForm(FlaskForm):
    """Capture CIA consequence data for a component."""

    consequence_category = SelectMultipleField(
        "Consequence category",
        choices=[
            ("financial", "Financial"),
            ("operational", "Operational"),
            ("reputation and trust", "Reputation and Trust"),
            ("regulatory", "Regulatory"),
            ("human and safety", "Human and Safety"),
            ("privacy", "Privacy"),
        ],
        validators=[DataRequired()],
    )
    security_property = SelectField(
        "Security property",
        choices=[
            ("confidentiality", "Confidentiality"),
            ("integrity", "Integrity"),
            ("availability", "Availability"),
        ],
        validators=[DataRequired()],
    )
    consequence_worstcase = SelectField(
        "Worst case consequence",
        choices=[
            ("catastrophic", "Catastrophic"),
            ("major", "Major"),
            ("moderate", "Moderate"),
            ("minor", "Minor"),
            ("insignificant", "Insignificant"),
        ],
        validators=[DataRequired()],
    )
    justification_worstcase = TextAreaField("Justification (worst case)", validators=[Optional()])
    consequence_realisticcase = SelectField(
        "Realistic consequence",
        choices=[
            ("catastrophic", "Catastrophic"),
            ("major", "Major"),
            ("moderate", "Moderate"),
            ("minor", "Minor"),
            ("insignificant", "Insignificant"),
        ],
        validators=[DataRequired()],
    )
    justification_realisticcase = TextAreaField("Justification (realistic)", validators=[Optional()])
    submit = SubmitField("Save consequence")


class AvailabilityForm(FlaskForm):
    """Capture availability requirement targets for a component."""

    mtd = StringField("Maximum tolerable downtime", validators=[Optional(), Length(max=255)])
    rto = StringField("Recovery time objective", validators=[Optional(), Length(max=255)])
    rpo = StringField("Recovery point objective", validators=[Optional(), Length(max=255)])
    masl = StringField("Minimum acceptable service level", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Save availability requirements")


class BIAAvailabilityForm(AvailabilityForm):
    """Allow availability edits scoped to a BIA via component selection."""

    component_id = SelectField(
        _l("bia.context_form.component_fields.name.label"),
        coerce=int,
        validators=[DataRequired()],
    )


class BIAConsequenceManagerForm(ConsequenceForm):
    """Manage CIA consequences for any component within a BIA."""

    component_id = SelectField(
        _l("bia.context_form.component_fields.name.label"),
        coerce=int,
        validators=[DataRequired()],
    )
    consequence_id = HiddenField()


class ComponentAIForm(FlaskForm):
    """Capture AI classification details for a component within a BIA."""

    component_id = SelectField(
        _l("bia.context_form.component_fields.name.label"),
        coerce=int,
        validators=[DataRequired()],
    )
    category = SelectField(
        _l("bia.context_detail.ai_risks.category"),
        choices=_AI_CATEGORY_CHOICES,
        validators=[DataRequired()],
    )
    motivatie = TextAreaField(
        _l("bia.context_detail.ai_risks.motivation"),
        validators=[Optional()],
    )
    submit = SubmitField(_l("bia.components.modal.buttons.save"))


class SummaryForm(FlaskForm):
    """Capture executive summary details."""

    content = TextAreaField("Summary", validators=[DataRequired()])
    submit = SubmitField("Save summary")


class ImportCSVForm(FlaskForm):
    """Upload CSV files for bulk import."""

    bia = FileField("BIA CSV", validators=[FileAllowed(["csv"], "CSV files only")])
    components = FileField("Components CSV", validators=[FileAllowed(["csv"], "CSV files only")])
    consequences = FileField("Consequences CSV", validators=[FileAllowed(["csv"], "CSV files only")])
    availability_requirements = FileField(
        "Availability requirements CSV",
        validators=[FileAllowed(["csv"], "CSV files only")],
    )
    ai_identification = FileField("AI identification CSV", validators=[FileAllowed(["csv"], "CSV files only")])
    summary = FileField("Summary CSV", validators=[FileAllowed(["csv"], "CSV files only")])
    submit = SubmitField("Import CSV")


class ChangePasswordForm(FlaskForm):
    """Allow the current user to update their password."""

    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), EqualTo("confirm_password", message="Passwords must match")])
    confirm_password = PasswordField("Confirm new password", validators=[DataRequired()])
    submit = SubmitField("Change password")


class ImportSQLForm(FlaskForm):
    """Upload a SQL export to import a full BIA."""

    sql_file = FileField(
        "SQL file",
        validators=[FileRequired(message="Select a SQL file."), FileAllowed(["sql"], "SQL files only")],
    )
    submit = SubmitField("Import SQL")
