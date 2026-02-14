"""Forms for the Business Impact Analysis workflow."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, DateField, FieldList, FormField, HiddenField, IntegerField, PasswordField, SelectField, SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms.form import Form
from wtforms.validators import DataRequired, EqualTo, Length, Optional
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
    tier = SelectField(_l("bia.context_form.fields.tier.label"), validators=[Optional()], coerce=_optional_int)
    responsible = StringField("End responsible", validators=[Optional(), Length(max=255)])
    coordinator = StringField("Coordinator", validators=[Optional(), Length(max=255)])
    start_date = DateField("Start date", format="%Y-%m-%d", validators=[Optional()])
    end_date = DateField("End date", format="%Y-%m-%d", validators=[Optional()])
    service_description = TextAreaField("Service description", validators=[Optional()])
    knowledge = TextAreaField("Knowledge within the organisation", validators=[Optional()])
    interfaces = TextAreaField("Interfaces with systems", validators=[Optional()])
    mission_critical = TextAreaField("Mission critical dependencies", validators=[Optional()])
    support_contracts = TextAreaField("Support contracts", validators=[Optional()])
    security_supplier = TextAreaField("Security supplier", validators=[Optional()])
    user_amount = IntegerField("Number of users", validators=[Optional()])
    scope_description = TextAreaField("Scope description", validators=[Optional()])
    risk_assessment_human = BooleanField("Requires people risk assessment")
    risk_assessment_process = BooleanField("Requires process risk assessment")
    risk_assessment_technological = BooleanField("Requires technology risk assessment")
    ai_model = BooleanField("Uses AI components")
    project_leader = StringField("Project leader", validators=[Optional(), Length(max=255)])
    risk_owner = StringField("Risk owner", validators=[Optional(), Length(max=255)])
    product_owner = StringField("Product owner", validators=[Optional(), Length(max=255)])
    technical_administrator = StringField("Technical administrator", validators=[Optional(), Length(max=255)])
    security_manager = StringField("Security manager", validators=[Optional(), Length(max=255)])
    incident_contact = StringField("Incident contact", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Save context")

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

    name = StringField("Component name", validators=[DataRequired(), Length(max=255)])
    info_type = StringField("Information type", validators=[Optional(), Length(max=255)])
    info_owner = StringField("Information owner", validators=[Optional(), Length(max=255)])
    user_type = StringField(_l("bia.components.labels.user_type"), validators=[Optional(), Length(max=255)])
    dependencies_it_systems_applications = TextAreaField(
        _l("bia.components.labels.dependencies_it_systems_applications"), validators=[Optional()]
    )
    dependencies_equipment = TextAreaField(
        _l("bia.components.labels.dependencies_equipment"), validators=[Optional()]
    )
    dependencies_suppliers = TextAreaField(
        _l("bia.components.labels.dependencies_suppliers"), validators=[Optional()]
    )
    dependencies_people = TextAreaField(_l("bia.components.labels.dependencies_people"), validators=[Optional()])
    dependencies_facilities = TextAreaField(
        _l("bia.components.labels.dependencies_facilities"), validators=[Optional()]
    )
    dependencies_others = TextAreaField(_l("bia.components.labels.dependencies_others"), validators=[Optional()])
    description = TextAreaField(_l("bia.components.labels.description"), validators=[Optional()])
    environments = FieldList(
        FormField(ComponentEnvironmentForm),
        min_entries=len(_COMPONENT_ENVIRONMENT_TYPES),
        max_entries=len(_COMPONENT_ENVIRONMENT_TYPES),
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
