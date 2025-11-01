"""Forms used by the admin blueprint."""

from __future__ import annotations

from typing import cast

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import HiddenField, SelectField, SubmitField
from wtforms.validators import DataRequired

from ..i18n import gettext as _, lazy_gettext as _l


def _label(key: str) -> str:
    return _l(key)


class ControlImportForm(FlaskForm):
    data_file = FileField(
        _label("admin.import.fields.data_file"),
        validators=[
            FileRequired(message=_("admin.import.errors.file_required")),
            FileAllowed(["json"], message=_("admin.import.errors.file_allowed")),
        ],
    )
    submit = SubmitField(_label("admin.import.actions.submit"))


class UserRoleAssignForm(FlaskForm):
    role = SelectField(
        _label("admin.roles.fields.role"),
        validators=[DataRequired(message=_("admin.roles.errors.role_required"))],
    )
    submit = SubmitField(_label("admin.roles.actions.assign"))


class UserRoleRemoveForm(FlaskForm):
    role = HiddenField(validators=[DataRequired(message=_("admin.roles.errors.role_missing"))])
    submit = SubmitField(_label("admin.roles.actions.remove"))
