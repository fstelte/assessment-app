"""Forms for the System Security Plan module."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from scaffold.core.i18n import lazy_gettext as _l


class SSPEditForm(FlaskForm):
    """Edit SSP-specific metadata fields."""

    laws_regulations = TextAreaField(
        _l("ssp.forms.laws_regulations"),
        validators=[Optional()],
        render_kw={"rows": 6},
    )
    authorization_boundary = TextAreaField(
        _l("ssp.forms.authorization_boundary"),
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
        _l("ssp.forms.plan_completion_date"),
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    plan_approval_date = DateField(
        _l("ssp.forms.plan_approval_date"),
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    monitoring_kpis_kris = TextAreaField(
        _l("ssp.forms.monitoring_kpis_kris"),
        validators=[Optional()],
        render_kw={"rows": 4, "placeholder": "List the key performance and risk indicators that apply to this system."},
    )
    monitoring_what = TextAreaField(
        _l("ssp.forms.monitoring_what"),
        validators=[Optional()],
        render_kw={"rows": 4, "placeholder": "Describe the controls, metrics, events, and logs that are subject to monitoring."},
    )
    monitoring_who = TextAreaField(
        _l("ssp.forms.monitoring_who"),
        validators=[Optional()],
        render_kw={"rows": 3, "placeholder": "Roles or teams responsible for carrying out monitoring activities."},
    )
    monitoring_tools = TextAreaField(
        _l("ssp.forms.monitoring_tools"),
        validators=[Optional()],
        render_kw={"rows": 3, "placeholder": "List the tooling, platforms, or services used for monitoring."},
    )
    monitoring_frequency = StringField(
        _l("ssp.forms.monitoring_frequency"),
        validators=[Optional(), Length(max=100)],
        render_kw={"placeholder": "e.g. Monthly, Quarterly, Annually"},
    )
    submit = SubmitField(_l("ssp.forms.save"))


class SSPInterconnectionForm(FlaskForm):
    """Add or edit a system interconnection entry."""

    system_name = StringField(
        _l("ssp.forms.system_name"),
        validators=[DataRequired(), Length(max=255)],
    )
    owning_organization = StringField(
        _l("ssp.forms.owning_organization"),
        validators=[Optional(), Length(max=255)],
    )
    agreement_type = SelectField(
        _l("ssp.forms.agreement_type"),
        choices=[
            ("none", "None"),
            ("mou", "MOU"),
            ("isa", "ISA"),
            ("contract", "Contract"),
            ("informal", "Informal"),
        ],
    )
    data_direction = SelectField(
        _l("ssp.forms.data_direction"),
        choices=[
            ("bidirectional", "Bidirectional"),
            ("incoming", "Incoming"),
            ("outgoing", "Outgoing"),
        ],
    )
    security_contact = StringField(
        _l("ssp.forms.security_contact"),
        validators=[Optional(), Length(max=255)],
    )
    notes = TextAreaField(
        _l("ssp.forms.notes"),
        validators=[Optional()],
        render_kw={"rows": 3},
    )
    submit = SubmitField(_l("ssp.forms.save"))


class SSPControlEntryForm(FlaskForm):
    """Annotate a control implementation entry."""

    implementation_status = SelectField(
        _l("ssp.forms.implementation_status"),
        choices=[
            ("planned", "Planned"),
            ("partially_implemented", "Partially Implemented"),
            ("implemented", "Implemented"),
            ("not_applicable", "Not Applicable"),
        ],
    )
    responsible_entity = StringField(
        _l("ssp.forms.responsible_entity"),
        validators=[Optional(), Length(max=255)],
    )
    implementation_statement = TextAreaField(
        _l("ssp.forms.implementation_statement"),
        validators=[Optional()],
        render_kw={"rows": 4},
    )
    submit = SubmitField(_l("ssp.forms.save"))


class POAMItemForm(FlaskForm):
    """Create or edit a POA&M item."""

    weakness_description = TextAreaField(
        _l("ssp.forms.weakness_description"),
        validators=[DataRequired()],
        render_kw={"rows": 4},
    )
    resources_required = TextAreaField(
        _l("ssp.forms.resources_required"),
        validators=[Optional()],
        render_kw={"rows": 3},
    )
    point_of_contact = StringField(
        _l("ssp.forms.point_of_contact"),
        validators=[Optional(), Length(max=255)],
    )
    scheduled_completion = DateField(
        _l("ssp.forms.scheduled_completion"),
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    estimated_cost = StringField(
        _l("ssp.forms.estimated_cost"),
        validators=[Optional(), Length(max=100)],
    )
    status = SelectField(
        _l("ssp.forms.status"),
        choices=[
            ("open", "Open"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("delayed", "Delayed"),
            ("cancelled", "Cancelled"),
        ],
    )
    submit = SubmitField(_l("ssp.forms.save"))


class POAMMilestoneForm(FlaskForm):
    """Add a milestone to a POA&M item."""

    description = TextAreaField(
        _l("ssp.forms.milestone_description"),
        validators=[DataRequired()],
        render_kw={"rows": 2},
    )
    scheduled_date = DateField(
        _l("ssp.forms.scheduled_date"),
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    completed_date = DateField(
        _l("ssp.forms.completed_date"),
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    submit = SubmitField(_l("ssp.forms.add_milestone_btn"))
