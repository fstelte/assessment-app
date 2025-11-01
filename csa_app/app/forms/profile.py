"""Forms for user profile management."""

from __future__ import annotations

from typing import cast

from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length, Optional

from ..i18n import gettext as _, lazy_gettext as _l


def _label(key: str) -> str:
    return _l(key)


class ProfileForm(FlaskForm):
    theme = SelectField(
        _label("profile.fields.theme"),
        choices=[("dark", _label("profile.theme.dark")), ("light", _label("profile.theme.light"))],
        validators=[DataRequired(message=_("form.errors.required"))],
    )
    current_password = PasswordField(_label("profile.fields.current_password"), validators=[Optional()])
    new_password = PasswordField(
        _label("profile.fields.new_password"),
        validators=[Optional(), Length(min=8, message=_("profile.errors.password_length"))],
    )
    confirm_password = PasswordField(
        _label("profile.fields.confirm_password"),
        validators=[Optional(), EqualTo("new_password", message=_("profile.errors.password_mismatch"))],
    )
    submit = SubmitField(_label("profile.actions.submit"))
