"""Authentication and MFA related forms."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length


class RegistrationForm(FlaskForm):
    email = StringField("E-mailadres", validators=[DataRequired(), Email(), Length(max=255)])
    first_name = StringField("Voornaam", validators=[Length(max=120)])
    last_name = StringField("Achternaam", validators=[Length(max=120)])
    password = PasswordField(
        "Wachtwoord",
        validators=[
            DataRequired(message="Wachtwoord is verplicht."),
            Length(min=8, max=255, message="Wachtwoord moet minimaal 8 tekens lang zijn."),
        ],
    )
    confirm_password = PasswordField(
        "Bevestig wachtwoord",
        validators=[
            DataRequired(message="Bevestiging is verplicht."),
            EqualTo("password", message="Wachtwoorden komen niet overeen."),
        ],
    )
    submit = SubmitField("Registreren")


class LoginForm(FlaskForm):
    email = StringField("E-mailadres", validators=[DataRequired(), Email()])
    password = PasswordField("Wachtwoord", validators=[DataRequired()])
    remember_me = BooleanField("Onthoud mij")
    submit = SubmitField("Inloggen")


class MFAEnrollForm(FlaskForm):
    otp_token = StringField(
        "6-cijferige code",
        validators=[DataRequired(), Length(min=6, max=6)],
        render_kw={"autocomplete": "one-time-code"},
    )
    submit = SubmitField("MFA activeren")


class MFAVerifyForm(FlaskForm):
    otp_token = StringField(
        "6-cijferige code",
        validators=[DataRequired(), Length(min=6, max=6)],
        render_kw={"autocomplete": "one-time-code"},
    )
    remember_device = BooleanField("Vertrouw dit apparaat")
    submit = SubmitField("Verifiëren")
