"""Forms used within the CSA administration features."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import HiddenField, SelectField, SubmitField
from wtforms.validators import DataRequired


class ControlImportForm(FlaskForm):
    """Upload a JSON payload containing control metadata."""

    data_file = FileField(
        "JSON file",
        validators=[
            FileRequired(message="Select a JSON file."),
            FileAllowed(["json"], message="Only JSON files are accepted."),
        ],
    )
    submit = SubmitField("Import controls")


class UserRoleAssignForm(FlaskForm):
    """Assign an application role to a user."""

    role = SelectField("Role", validators=[DataRequired(message="Select a role.")])
    submit = SubmitField("Add role")


class UserRoleRemoveForm(FlaskForm):
    """Remove an existing application role from a user."""

    role = HiddenField(validators=[DataRequired(message="Missing role identifier.")])
    submit = SubmitField("Remove")
