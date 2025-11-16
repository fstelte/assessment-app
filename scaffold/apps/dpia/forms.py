"""WTForms definitions for DPIA creation and risk capture.

The actual form fields will be ported from the standalone dpia-fria-app
once the domain models are available inside the unified database layer.
"""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length


class StartDPIAForm(FlaskForm):
    """Minimal form to start a DPIA from a BIA component."""

    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    project_lead = StringField("Project lead", validators=[Length(max=255)])
    responsible_name = StringField("Responsible", validators=[Length(max=255)])
    submit = SubmitField("Create DPIA")


class AssessmentDetailsForm(FlaskForm):
    """Edit high-level information for a DPIA assessment."""

    title = StringField("Title", validators=[DataRequired(), Length(max=255)])
    project_lead = StringField("Project lead", validators=[Length(max=255)])
    responsible_name = StringField("Responsible", validators=[Length(max=255)])
    status = SelectField("Status", validators=[DataRequired()], coerce=str)
    submit = SubmitField("Save changes")


class AnswerQuestionForm(FlaskForm):
    """Capture textual answers for canonical DPIA questions."""

    question_id = SelectField("Question", coerce=int, validators=[DataRequired()])
    answer_text = TextAreaField("Answer", validators=[DataRequired(), Length(min=3)])
    submit = SubmitField("Save answer")


class RiskForm(FlaskForm):
    """Register risks discovered during a DPIA."""

    risk_type = SelectField("Risk type", choices=[("DPIA", "DPIA"), ("FRIA", "FRIA")], validators=[DataRequired()])
    description = TextAreaField("Description", validators=[DataRequired(), Length(min=3)])
    likelihood = SelectField("Likelihood", coerce=int, validators=[DataRequired()])
    impact = SelectField("Impact", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Add risk")


class MeasureForm(FlaskForm):
    """Capture mitigating measures linked to risks or the overall assessment."""

    description = TextAreaField("Description", validators=[DataRequired(), Length(min=3)])
    effect_likelihood = SelectField("Effect on likelihood", coerce=int, validators=[DataRequired()])
    effect_impact = SelectField("Effect on impact", coerce=int, validators=[DataRequired()])
    risk_id = SelectField("Related risk", coerce=int)
    submit = SubmitField("Add measure")
