"""Forms for Incident Response Plans."""

from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length

class ScenarioForm(FlaskForm):
    """Form to create or edit an Incident Scenario."""
    name = StringField("Scenario Name", validators=[DataRequired(), Length(max=255)])
    description = TextAreaField("Description")
    submit = SubmitField("Save Scenario")

class IncidentStepForm(FlaskForm):
    """Form to define the response steps for a scenario."""
    actions_first_hour = TextAreaField("Actions First Hour")
    alternatives = TextAreaField("Alternatives / Fallback")
    rto = StringField("RTO (Target)", description="Snapshot from BIA")
    rpo = StringField("RPO (Target)", description="Snapshot from BIA")
    contact_list = TextAreaField("Contact List")
    manual_procedures = TextAreaField("Manual Procedures / Offline Possibilities")
    submit = SubmitField("Save Steps")
