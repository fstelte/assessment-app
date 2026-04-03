"""Forms for the System Security Plan module."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class SSPEditForm(FlaskForm):
    """Edit SSP-specific metadata fields."""

    laws_regulations = TextAreaField(
        "Laws, Regulations & Policies",
        validators=[Optional()],
        render_kw={"rows": 6},
    )
    authorization_boundary = TextAreaField(
        "Authorization Boundary",
        validators=[Optional()],
        render_kw={"rows": 4},
    )
    fips_confidentiality = SelectField(
        "Confidentiality Override",
        choices=[
            ("not_set", "Use derived (auto)"),
            ("low", "Low"),
            ("moderate", "Moderate"),
            ("high", "High"),
        ],
    )
    fips_integrity = SelectField(
        "Integrity Override",
        choices=[
            ("not_set", "Use derived (auto)"),
            ("low", "Low"),
            ("moderate", "Moderate"),
            ("high", "High"),
        ],
    )
    fips_availability = SelectField(
        "Availability Override",
        choices=[
            ("not_set", "Use derived (auto)"),
            ("low", "Low"),
            ("moderate", "Moderate"),
            ("high", "High"),
        ],
    )
    plan_completion_date = DateField(
        "Plan Completion Date",
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    plan_approval_date = DateField(
        "Plan Approval Date",
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    monitoring_kpis_kris = TextAreaField(
        "Relevant KPIs / KRIs",
        validators=[Optional()],
        render_kw={"rows": 4, "placeholder": "List the key performance and risk indicators that apply to this system."},
    )
    monitoring_what = TextAreaField(
        "What Will Be Monitored",
        validators=[Optional()],
        render_kw={"rows": 4, "placeholder": "Describe the controls, metrics, events, and logs that are subject to monitoring."},
    )
    monitoring_who = TextAreaField(
        "Monitored By",
        validators=[Optional()],
        render_kw={"rows": 3, "placeholder": "Roles or teams responsible for carrying out monitoring activities."},
    )
    monitoring_tools = TextAreaField(
        "Tools Used",
        validators=[Optional()],
        render_kw={"rows": 3, "placeholder": "List the tooling, platforms, or services used for monitoring."},
    )
    monitoring_frequency = StringField(
        "Review Frequency",
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "e.g. Monthly, Quarterly, Annually"},
    )
    submit = SubmitField("Save")


class SSPInterconnectionForm(FlaskForm):
    """Add or edit a system interconnection entry."""

    system_name = StringField(
        "System Name",
        validators=[DataRequired(), Length(max=255)],
    )
    owning_organization = StringField(
        "Owning Organization",
        validators=[Optional(), Length(max=255)],
    )
    agreement_type = SelectField(
        "Agreement Type",
        choices=[
            ("none", "None"),
            ("mou", "MOU"),
            ("isa", "ISA"),
            ("contract", "Contract"),
            ("informal", "Informal"),
        ],
    )
    data_direction = SelectField(
        "Data Direction",
        choices=[
            ("bidirectional", "Bidirectional"),
            ("incoming", "Incoming"),
            ("outgoing", "Outgoing"),
        ],
    )
    security_contact = StringField(
        "Security Contact",
        validators=[Optional(), Length(max=255)],
    )
    notes = TextAreaField(
        "Notes",
        validators=[Optional()],
        render_kw={"rows": 3},
    )
    submit = SubmitField("Save")


class SSPControlEntryForm(FlaskForm):
    """Annotate a control implementation entry."""

    implementation_status = SelectField(
        "Implementation Status",
        choices=[
            ("planned", "Planned"),
            ("partially_implemented", "Partially Implemented"),
            ("implemented", "Implemented"),
            ("not_applicable", "Not Applicable"),
        ],
    )
    responsible_entity = StringField(
        "Responsible Entity",
        validators=[Optional(), Length(max=255)],
    )
    implementation_statement = TextAreaField(
        "Implementation Statement",
        validators=[Optional()],
        render_kw={"rows": 4},
    )
    submit = SubmitField("Save")


class POAMItemForm(FlaskForm):
    """Create or edit a POA&M item."""

    weakness_description = TextAreaField(
        "Task / Weakness Description",
        validators=[DataRequired()],
        render_kw={"rows": 4},
    )
    resources_required = TextAreaField(
        "Resources Required",
        validators=[Optional()],
        render_kw={"rows": 3},
    )
    point_of_contact = StringField(
        "Point of Contact",
        validators=[Optional(), Length(max=255)],
    )
    scheduled_completion = DateField(
        "Scheduled Completion Date",
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    estimated_cost = StringField(
        "Estimated Cost / Effort",
        validators=[Optional(), Length(max=100)],
    )
    status = SelectField(
        "Status",
        choices=[
            ("open", "Open"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("delayed", "Delayed"),
            ("cancelled", "Cancelled"),
        ],
    )
    submit = SubmitField("Save")


class POAMMilestoneForm(FlaskForm):
    """Add a milestone to a POA&M item."""

    description = TextAreaField(
        "Milestone Description",
        validators=[DataRequired()],
        render_kw={"rows": 2},
    )
    scheduled_date = DateField(
        "Scheduled Date",
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    completed_date = DateField(
        "Completed Date",
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    submit = SubmitField("Add Milestone")
