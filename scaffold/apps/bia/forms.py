"""Forms for the Business Impact Analysis workflow."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import BooleanField, DateField, IntegerField, PasswordField, SelectField, SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length, Optional


def _optional_int(value: object) -> int | None:
    if value in (None, "", "None"):
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError("Not a valid integer value") from exc


class ContextScopeForm(FlaskForm):
    """Capture or update the core attributes of a BIA context."""

    name = StringField("Service or product name", validators=[DataRequired(), Length(max=255)])
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


class ComponentForm(FlaskForm):
    """Create or update a component linked to a BIA context."""

    name = StringField("Component name", validators=[DataRequired(), Length(max=255)])
    info_type = StringField("Information type", validators=[Optional(), Length(max=255)])
    info_owner = StringField("Information owner", validators=[Optional(), Length(max=255)])
    user_type = StringField("User type", validators=[Optional(), Length(max=255)])
    process_dependencies = TextAreaField("Process dependencies", validators=[Optional()])
    description = TextAreaField("Description", validators=[Optional()])
    authentication_method = SelectField(
        "Authentication type",
        validators=[Optional()],
        choices=[],
        coerce=_optional_int,
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
