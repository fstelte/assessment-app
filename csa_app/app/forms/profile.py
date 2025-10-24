"""Forms for user profile management."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Optional


class ProfileForm(FlaskForm):
    theme = SelectField(
        "Thema",
        choices=[("dark", "Donker"), ("light", "Licht")],
        validators=[DataRequired()],
    )
    current_password = PasswordField("Huidig wachtwoord", validators=[Optional()])
    new_password = PasswordField(
        "Nieuw wachtwoord",
        validators=[Optional(), Length(min=8, message="Minimaal 8 tekens")],
    )
    confirm_password = PasswordField(
        "Bevestig nieuw wachtwoord",
        validators=[Optional(), EqualTo("new_password", message="Wachtwoorden komen niet overeen")],
    )
    submit = SubmitField("Wijzigingen opslaan")
