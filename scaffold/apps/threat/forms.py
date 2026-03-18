"""Flask-WTF forms for the threat modeling module."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)

from wtforms.validators import DataRequired, Length, NumberRange, Optional

from scaffold.core.i18n import lazy_gettext as _l

from .models import AssetType, ScenarioStatus, StrideCategory, TreatmentOption


BIA_CHOICES_PLACEHOLDER: list = []  # populated at runtime in routes

LIKELIHOOD_CHOICES = [
    ("1", "1 – Rare"),
    ("2", "2 – Unlikely"),
    ("3", "3 – Possible"),
    ("4", "4 – Likely"),
    ("5", "5 – Almost certain"),
]

IMPACT_CHOICES = [
    ("1", "1 – Negligible"),
    ("2", "2 – Minor"),
    ("3", "3 – Moderate"),
    ("4", "4 – Significant"),
    ("5", "5 – Critical"),
]

ASSET_TYPE_CHOICES = [(t.value, t.value.replace("_", " ").title()) for t in AssetType]
STRIDE_CHOICES = [
    ("spoofing", "Spoofing (S)"),
    ("tampering", "Tampering (T)"),
    ("repudiation", "Repudiation (R)"),
    ("information_disclosure", "Information Disclosure (I)"),
    ("denial_of_service", "Denial of Service (D)"),
    ("elevation_of_privilege", "Elevation of Privilege (E)"),
    ("lateral_movement", "Lateral Movement (LM)"),
]
TREATMENT_CHOICES = [(t.value, t.value.title()) for t in TreatmentOption]
STATUS_CHOICES = [(s.value, s.value.replace("_", " ").title()) for s in ScenarioStatus]
RESIDUAL_LIKELIHOOD_CHOICES = [("" , "— not set —")] + LIKELIHOOD_CHOICES
RESIDUAL_IMPACT_CHOICES = [("" , "— not set —")] + IMPACT_CHOICES


class ThreatModelForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Description", validators=[Optional()], render_kw={"rows": 3})
    scope = TextAreaField("Scope", validators=[Optional()], render_kw={"rows": 4})
    bia_id = SelectField(
        "Import components from BIA",
        validators=[Optional()],
        choices=[],
        coerce=str,
    )
    submit = SubmitField("Save")


class ThreatModelAssetForm(FlaskForm):
    name = StringField(
        "Name",
        validators=[DataRequired(), Length(max=255)],
        description=_l("threat.asset_form.help.name"),
    )
    asset_type = SelectField(
        "Asset type",
        validators=[DataRequired()],
        choices=ASSET_TYPE_CHOICES,
        description=_l("threat.asset_form.help.asset_type"),
    )
    description = TextAreaField(
        "Description",
        validators=[Optional()],
        render_kw={"rows": 3},
        description=_l("threat.asset_form.help.description"),
    )
    order = IntegerField(
        "Order",
        validators=[Optional(), NumberRange(min=0)],
        default=0,
        description=_l("threat.asset_form.help.order"),
    )
    submit = SubmitField("Save")


class ThreatScenarioForm(FlaskForm):
    stride_category = SelectField(
        "STRIDE-LM category",
        validators=[DataRequired()],
        choices=STRIDE_CHOICES,
        description=_l("threat.scenario_form.help.stride_category"),
    )
    asset_id = SelectField(
        "Threatened asset",
        validators=[Optional()],
        choices=[],
        coerce=str,
        description=_l("threat.scenario_form.help.asset_id"),
    )
    title = StringField(
        "Scenario title",
        validators=[DataRequired(), Length(max=255)],
        description=_l("threat.scenario_form.help.title"),
    )
    description = TextAreaField(
        "Description",
        validators=[Optional()],
        render_kw={"rows": 4},
        description=_l("threat.scenario_form.help.description"),
    )
    threat_actor = StringField(
        "Threat actor",
        validators=[Optional(), Length(max=255)],
        description=_l("threat.scenario_form.help.threat_actor"),
    )
    attack_vector = TextAreaField(
        "Attack vector",
        validators=[Optional()],
        render_kw={"rows": 3},
        description=_l("threat.scenario_form.help.attack_vector"),
    )
    preconditions = TextAreaField(
        "Preconditions",
        validators=[Optional()],
        render_kw={"rows": 3},
        description=_l("threat.scenario_form.help.preconditions"),
    )
    impact_description = TextAreaField(
        "Impact description",
        validators=[Optional()],
        render_kw={"rows": 3},
        description=_l("threat.scenario_form.help.impact_description"),
    )
    cia_c = BooleanField("Confidentiality")
    cia_i = BooleanField("Integrity")
    cia_a = BooleanField("Availability")
    likelihood = SelectField(
        "Likelihood",
        validators=[DataRequired()],
        choices=LIKELIHOOD_CHOICES,
        default="3",
        description=_l("threat.scenario_form.help.likelihood"),
    )
    impact_score = SelectField(
        "Impact",
        validators=[DataRequired()],
        choices=IMPACT_CHOICES,
        default="3",
        description=_l("threat.scenario_form.help.impact_score"),
    )
    residual_likelihood = SelectField(
        "Residual likelihood",
        validators=[Optional()],
        choices=RESIDUAL_LIKELIHOOD_CHOICES,
        description=_l("threat.scenario_form.help.residual_likelihood"),
    )
    residual_impact = SelectField(
        "Residual impact",
        validators=[Optional()],
        choices=RESIDUAL_IMPACT_CHOICES,
        description=_l("threat.scenario_form.help.residual_impact"),
    )
    treatment = SelectField(
        "Treatment",
        validators=[Optional()],
        choices=[("" , "— select —")] + TREATMENT_CHOICES,
        description=_l("threat.scenario_form.help.treatment"),
    )
    status = SelectField(
        "Status",
        validators=[DataRequired()],
        choices=STATUS_CHOICES,
        description=_l("threat.scenario_form.help.status"),
    )
    owner_id = SelectField(
        "Owner",
        validators=[Optional()],
        choices=[],
        description=_l("threat.scenario_form.help.owner_id"),
    )
    csa_control_ids = SelectMultipleField(
        "Controls selected",
        validators=[Optional()],
        choices=[],
        render_kw={"size": 6},
        description=_l("threat.scenario_form.help.csa_control_ids"),
    )
    submit = SubmitField("Save scenario")
