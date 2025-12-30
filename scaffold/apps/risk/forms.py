"""WTForms definitions supporting risk management flows."""

from __future__ import annotations

from datetime import date

from flask_wtf import FlaskForm
from wtforms import DateField, HiddenField, IntegerField, SelectField, SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, URL, ValidationError

from .models import RiskTreatmentOption
from ...core.i18n import gettext as _, lazy_gettext as _l


class RiskForm(FlaskForm):
    """Create or edit a risk entry."""

    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Description", validators=[DataRequired()], render_kw={"rows": 4})
    discovered_on = DateField("Discovered on", default=date.today, validators=[Optional()])
    ticket_url = StringField(
        "Ticket link",
        validators=[
            Optional(),
            URL(message=_("admin.risks.form.invalid_ticket_url")),
            Length(max=500),
        ],
    )
    impact = SelectField("Impact", validators=[DataRequired()], choices=[])
    chance = SelectField("Chance", validators=[DataRequired()], choices=[])
    impact_areas = SelectMultipleField(
        "Impact areas",
        validators=[DataRequired()],
        choices=[],
        render_kw={"size": 6},
        description=_l('risk.help.impact_areas'),
    )
    component_ids = SelectMultipleField(
        "Components",
        validators=[DataRequired()],
        choices=[],
        render_kw={"size": 8},
        description=_l('risk.help.component_ids'),
    )
    treatment = SelectField("Treatment", validators=[DataRequired()], choices=[])
    treatment_plan = TextAreaField("Treatment plan", validators=[Optional()], render_kw={"rows": 3})
    treatment_due_date = DateField("Treatment due date", validators=[Optional()])
    treatment_owner_id = SelectField("Owner", validators=[Optional()], choices=[])
    csa_control_ids = SelectMultipleField(
        "CSA Controls",
        validators=[Optional()],
        choices=[],
        render_kw={"size": 6},
    )
    submit = SubmitField("Save risk")

    def validate_component_ids(self, field: SelectMultipleField) -> None:  # type: ignore[override]
        if not field.data:
            raise ValidationError(_("admin.risks.errors.invalid_components"))

    def validate(self, extra_validators=None):  # type: ignore[override]
        valid = super().validate(extra_validators=extra_validators)
        if not valid:
            return False
        requires_control = self.treatment.data == RiskTreatmentOption.MITIGATE.value
        selected_controls: list[str] = []
        seen: set[str] = set()
        for value in self.csa_control_ids.data or []:
            if not value:
                continue
            if value in seen:
                continue
            seen.add(value)
            selected_controls.append(value)
        self.csa_control_ids.data = selected_controls

        if requires_control and not selected_controls:
            self.csa_control_ids.errors.append(_("admin.risks.form.csa_help"))
            return False
        return True


class RiskThresholdForm(FlaskForm):
    """Update severity threshold bounds."""

    severity = HiddenField(validators=[DataRequired()])
    min_score = IntegerField("Min score", validators=[DataRequired(), NumberRange(min=0)])
    max_score = IntegerField("Max score", validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField("Save threshold")

    def validate_max_score(self, field: IntegerField) -> None:  # type: ignore[override]
        if self.min_score.data is None or field.data is None:
            return
        if field.data < self.min_score.data:
            raise ValidationError(_("admin.risks.thresholds.errors.invalid_range"))


class RiskActionForm(FlaskForm):
    """Lightweight form used for close/delete buttons."""

    submit = SubmitField("Confirm")
