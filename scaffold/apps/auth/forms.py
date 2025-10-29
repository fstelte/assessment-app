"""Forms for unified authentication flows."""

from __future__ import annotations

from typing import cast

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError

from ...extensions import db
from ..identity.models import User


class RegistrationForm(FlaskForm):
    """Registration form supporting BIA and CSA fields."""

    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    username = StringField("Username", validators=[Optional(), Length(min=3, max=64)])
    first_name = StringField("First name", validators=[Optional(), Length(max=120)])
    last_name = StringField("Last name", validators=[Optional(), Length(max=120)])
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=255, message="Password must be between 8 and 255 characters."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm password",
        validators=[
            DataRequired(),
            EqualTo("password", message="Passwords must match."),
        ],
    )
    submit = SubmitField("Register")

    def validate_email(self, field: StringField) -> None:  # noqa: D401
        if field.data and User.find_by_email(field.data):
            raise ValidationError("This email address is already in use.")

    def validate_username(self, field: StringField) -> None:  # noqa: D401
        if not field.data:
            return
        existing = User.query.filter(db.func.lower(User.username) == field.data.lower()).first()
        if existing:
            raise ValidationError("This username is already in use.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Sign in")


class MFAEnrollForm(FlaskForm):
    otp_token = StringField(
        "6-digit code",
        validators=[DataRequired(), Length(min=6, max=6)],
        render_kw={"autocomplete": "one-time-code"},
    )
    submit = SubmitField("Enable MFA")


class MFAVerifyForm(FlaskForm):
    otp_token = StringField(
        "6-digit code",
        validators=[DataRequired(), Length(min=6, max=6)],
        render_kw={"autocomplete": "one-time-code"},
    )
    remember_device = BooleanField("Trust this device")
    submit = SubmitField("Verify")


class ProfileForm(FlaskForm):
    first_name = StringField("First name", validators=[Optional(), Length(max=120)])
    last_name = StringField("Last name", validators=[Optional(), Length(max=120)])
    theme = SelectField(
        "Theme",
        choices=[("dark", "Dark"), ("light", "Light")],
        validators=[Optional()],
        default="dark",
    )
    locale = SelectField("Language", choices=[], validators=[Optional()], default="en")
    current_password = PasswordField("Current password", validators=[Optional()])
    new_password = PasswordField("New password", validators=[Optional(), Length(min=8, max=255)])
    submit = SubmitField("Save changes")

    def validate(self, extra_validators=None):  # noqa: D401
        if not super().validate(extra_validators=extra_validators):
            return False

        if self.new_password.data and not self.current_password.data:
            errors = cast(list[str], self.current_password.errors)
            errors.append("Enter your current password to change it.")
            return False

        return True
