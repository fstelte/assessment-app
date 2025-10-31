"""Authentication and MFA related forms."""

from __future__ import annotations

from typing import cast

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

from ..i18n import gettext as _, lazy_gettext as _l


def _label(key: str) -> str:
    """Return a typed string label for WTForms from a lazy translation."""

    return cast(str, _l(key))


class RegistrationForm(FlaskForm):
    email = StringField(
        _label("auth.register.fields.email"),
        validators=[
            DataRequired(message=_("form.errors.required")),
            Email(message=_("form.errors.email")),
            Length(max=255, message=_("form.errors.max_length", max=255)),
        ],
    )
    first_name = StringField(_label("auth.register.fields.first_name"), validators=[Length(max=120, message=_("form.errors.max_length", max=120))])
    last_name = StringField(_label("auth.register.fields.last_name"), validators=[Length(max=120, message=_("form.errors.max_length", max=120))])
    password = PasswordField(
    _label("auth.register.fields.password"),
        validators=[
            DataRequired(message=_("auth.register.errors.password_required")),
            Length(min=8, max=255, message=_("auth.register.errors.password_length")),
        ],
    )
    confirm_password = PasswordField(
    _label("auth.register.fields.confirm_password"),
        validators=[
            DataRequired(message=_("auth.register.errors.confirm_required")),
            EqualTo("password", message=_("auth.register.errors.password_mismatch")),
        ],
    )
    submit = SubmitField(_label("auth.register.actions.submit"))


class LoginForm(FlaskForm):
    email = StringField(
    _label("auth.login.fields.email"),
        validators=[
            DataRequired(message=_("form.errors.required")),
            Email(message=_("form.errors.email")),
        ],
    )
    password = PasswordField(
    _label("auth.login.fields.password"),
        validators=[DataRequired(message=_("form.errors.required"))],
    )
    remember_me = BooleanField(_label("auth.login.fields.remember_me"))
    submit = SubmitField(_label("auth.login.actions.submit"))


class MFAEnrollForm(FlaskForm):
    otp_token = StringField(
    _label("auth.mfa.fields.otp"),
        validators=[
            DataRequired(message=_("form.errors.required")),
            Length(min=6, max=6, message=_("auth.mfa.errors.otp_length")),
        ],
        render_kw={"autocomplete": "one-time-code"},
    )
    submit = SubmitField(_label("auth.mfa.enroll.submit"))


class MFAVerifyForm(FlaskForm):
    otp_token = StringField(
    _label("auth.mfa.fields.otp"),
        validators=[
            DataRequired(message=_("form.errors.required")),
            Length(min=6, max=6, message=_("auth.mfa.errors.otp_length")),
        ],
        render_kw={"autocomplete": "one-time-code"},
    )
    remember_device = BooleanField(_label("auth.mfa.verify.remember_device"))
    submit = SubmitField(_label("auth.mfa.verify.submit"))
