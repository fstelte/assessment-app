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
        description=_l("ssp.forms.help.laws_regulations"),
        render_kw={"rows": 6},
    )
    authorization_boundary = TextAreaField(
        _l("ssp.forms.authorization_boundary"),
        validators=[Optional()],
        description=_l("ssp.forms.help.authorization_boundary"),
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
        description=_l("ssp.forms.help.plan_completion_date"),
        format="%Y-%m-%d",
    )
    plan_approval_date = DateField(
        _l("ssp.forms.plan_approval_date"),
        validators=[Optional()],
        description=_l("ssp.forms.help.plan_approval_date"),
        format="%Y-%m-%d",
    )
    monitoring_kpis_kris = TextAreaField(
        _l("ssp.forms.monitoring_kpis_kris"),
        validators=[Optional()],
        description=_l("ssp.forms.help.monitoring_kpis_kris"),
        render_kw={"rows": 4},
    )
    monitoring_what = TextAreaField(
        _l("ssp.forms.monitoring_what"),
        validators=[Optional()],
        description=_l("ssp.forms.help.monitoring_what"),
        render_kw={"rows": 4},
    )
    monitoring_who = TextAreaField(
        _l("ssp.forms.monitoring_who"),
        validators=[Optional()],
        description=_l("ssp.forms.help.monitoring_who"),
        render_kw={"rows": 3},
    )
    monitoring_tools = TextAreaField(
        _l("ssp.forms.monitoring_tools"),
        validators=[Optional()],
        description=_l("ssp.forms.help.monitoring_tools"),
        render_kw={"rows": 3},
    )
    monitoring_frequency = StringField(
        _l("ssp.forms.monitoring_frequency"),
        validators=[Optional(), Length(max=100)],
        description=_l("ssp.forms.help.monitoring_frequency"),
        render_kw={"placeholder": "e.g. Monthly, Quarterly, Annually"},
    )
    submit = SubmitField(_l("ssp.forms.save"))


class SSPInterconnectionForm(FlaskForm):
    """Add or edit a system interconnection entry."""

    system_name = StringField(
        _l("ssp.forms.system_name"),
        validators=[DataRequired(), Length(max=255)],
        description=_l("ssp.forms.help.system_name"),
    )
    owning_organization = StringField(
        _l("ssp.forms.owning_organization"),
        validators=[Optional(), Length(max=255)],
        description=_l("ssp.forms.help.owning_organization"),
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
        description=_l("ssp.forms.help.agreement_type"),
    )
    data_direction = SelectField(
        _l("ssp.forms.data_direction"),
        choices=[
            ("bidirectional", "Bidirectional"),
            ("incoming", "Incoming"),
            ("outgoing", "Outgoing"),
        ],
        description=_l("ssp.forms.help.data_direction"),
    )
    security_contact = StringField(
        _l("ssp.forms.security_contact"),
        validators=[Optional(), Length(max=255)],
        description=_l("ssp.forms.help.security_contact"),
    )
    notes = TextAreaField(
        _l("ssp.forms.notes"),
        validators=[Optional()],
        description=_l("ssp.forms.help.notes"),
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
        description=_l("ssp.forms.help.implementation_status"),
    )
    responsible_entity = StringField(
        _l("ssp.forms.responsible_entity"),
        validators=[Optional(), Length(max=255)],
        description=_l("ssp.forms.help.responsible_entity"),
    )
    implementation_statement = TextAreaField(
        _l("ssp.forms.implementation_statement"),
        validators=[Optional()],
        description=_l("ssp.forms.help.implementation_statement"),
        render_kw={"rows": 4},
    )
    submit = SubmitField(_l("ssp.forms.save"))


class POAMItemForm(FlaskForm):
    """Create or edit a POA&M item."""

    weakness_description = TextAreaField(
        _l("ssp.forms.weakness_description"),
        validators=[DataRequired()],
        description=_l("ssp.forms.help.weakness_description"),
        render_kw={"rows": 4},
    )
    resources_required = TextAreaField(
        _l("ssp.forms.resources_required"),
        validators=[Optional()],
        description=_l("ssp.forms.help.resources_required"),
        render_kw={"rows": 3},
    )
    point_of_contact = StringField(
        _l("ssp.forms.point_of_contact"),
        validators=[Optional(), Length(max=255)],
        description=_l("ssp.forms.help.point_of_contact"),
    )
    scheduled_completion = DateField(
        _l("ssp.forms.scheduled_completion"),
        validators=[Optional()],
        description=_l("ssp.forms.help.scheduled_completion"),
        format="%Y-%m-%d",
    )
    estimated_cost = StringField(
        _l("ssp.forms.estimated_cost"),
        validators=[Optional(), Length(max=100)],
        description=_l("ssp.forms.help.estimated_cost"),
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
        description=_l("ssp.forms.help.status"),
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
