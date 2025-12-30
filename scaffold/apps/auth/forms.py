"""Forms for unified authentication flows."""

from __future__ import annotations

from typing import Any, cast

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, ValidationError
from scaffold.core.i18n import lazy_gettext as _l, gettext as _


def _label(key: str):
    """Return a lazy translation for WTForms labels."""
    return cast(Any, _l(key))

from ...extensions import db
from ..identity.models import User


class RegistrationForm(FlaskForm):
    """Registration form supporting BIA and CSA fields."""

    email = StringField(
        _label("auth.register.fields.email"),
        validators=[DataRequired(), Email(), Length(max=255)],
        description=_label("auth.register.help.email"),
    )
    username = StringField(_label("auth.register.fields.username"), validators=[Optional(), Length(min=3, max=64)])
    first_name = StringField(_label("auth.register.fields.first_name"), validators=[Optional(), Length(max=120)])
    last_name = StringField(_label("auth.register.fields.last_name"), validators=[Optional(), Length(max=120)])
    password = PasswordField(
        _label("auth.register.fields.password"),
        validators=[
            DataRequired(),
            Length(min=8, max=255, message=_("auth.register.errors.password_length")),
        ],
        description=_label("auth.register.help.password"),
    )
    confirm_password = PasswordField(
        _label("auth.register.fields.confirm_password"),
        validators=[
            DataRequired(),
            EqualTo("password", message=_("auth.register.errors.password_mismatch")),
        ],
    )
    submit = SubmitField(_label("auth.register.actions.submit"))

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
    email = StringField(_label("auth.login.fields.email"), validators=[DataRequired(), Email()])
    password = PasswordField(_label("auth.login.fields.password"), validators=[DataRequired()])
    remember_me = BooleanField(_label("auth.login.fields.remember_me"))
    submit = SubmitField(_label("auth.login.actions.submit"))


class MFAEnrollForm(FlaskForm):
    otp_token = StringField(
        _label("auth.mfa.fields.otp"),
        validators=[DataRequired(), Length(min=6, max=6)],
        render_kw={"autocomplete": "one-time-code"},
    )
    submit = SubmitField(_label("auth.mfa.enroll.submit"))


class MFAVerifyForm(FlaskForm):
    otp_token = StringField(
        _label("auth.mfa.fields.otp"),
        validators=[DataRequired(), Length(min=6, max=6)],
        render_kw={"autocomplete": "one-time-code"},
    )
    remember_device = BooleanField(_label("auth.mfa.verify.remember_device"))
    submit = SubmitField(_label("auth.mfa.verify.submit"))


class ProfileForm(FlaskForm):
    first_name = StringField(_label("profile.fields.first_name"), validators=[Optional(), Length(max=120)])
    last_name = StringField(_label("profile.fields.last_name"), validators=[Optional(), Length(max=120)])
    theme = SelectField(
        _label("profile.fields.theme"),
        choices=[("dark", _label("profile.theme.dark")), ("light", _label("profile.theme.light"))],
        validators=[Optional()],
        default="dark",
    )
    locale = SelectField(_label("profile.fields.language"), choices=[], validators=[Optional()], default="en")
    current_password = PasswordField(_label("profile.fields.current_password"), validators=[Optional()])
    new_password = PasswordField(_label("profile.fields.new_password"), validators=[Optional(), Length(min=8, max=255)])
    submit = SubmitField(_label("profile.actions.submit"))

    def validate(self, extra_validators=None):  # noqa: D401
        if not super().validate(extra_validators=extra_validators):
            return False

        if self.new_password.data and not self.current_password.data:
            errors = cast(list[str], self.current_password.errors)
            errors.append("Enter your current password to change it.")
            return False

        return True
