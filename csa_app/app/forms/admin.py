"""Forms used by the admin blueprint."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import HiddenField, SelectField, SubmitField
from wtforms.validators import DataRequired


class ControlImportForm(FlaskForm):
    data_file = FileField(
        "JSON-bestand",
        validators=[
            FileRequired(message="Selecteer een JSON-bestand."),
            FileAllowed(["json"], message="Alleen JSON-bestanden zijn toegestaan."),
        ],
    )
    submit = SubmitField("Importeren")


class UserRoleAssignForm(FlaskForm):
    role = SelectField("Rol", validators=[DataRequired(message="Kies een rol.")])
    submit = SubmitField("Rol toevoegen")


class UserRoleRemoveForm(FlaskForm):
    role = HiddenField(validators=[DataRequired(message="Rol ontbreekt.")])
    submit = SubmitField("Verwijderen")
