"""Forms used within the CSA administration features."""

from __future__ import annotations

from typing import cast

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import HiddenField, SelectField, SubmitField
from wtforms.validators import DataRequired

from scaffold.core.i18n import lazy_gettext as _l


def _label(key: str) -> str:
    """Return a lazy translation coerced to str for WTForms labels."""

    # Return the lazy translation object so evaluation occurs at render/request time
    # instead of at module import time. Casting to str here forces evaluation
    # using the fallback translator and prevents dynamic locale switching.
    return _l(key)


def _message(key: str) -> str:
    """Return a lazy translation coerced to str for validation messages."""

    return _l(key)


class ControlImportForm(FlaskForm):
    """Upload a JSON payload containing control metadata."""

    data_file = FileField(
        _label("csa.admin.import.fields.data_file.label"),
        validators=[
            FileRequired(message=_message("csa.admin.import.fields.data_file.required")),
            FileAllowed(["json"], message=_message("csa.admin.import.fields.data_file.allowed")),
        ],
    )
    submit = SubmitField(_label("csa.admin.import.submit"))


class UserRoleAssignForm(FlaskForm):
    """Assign an application role to a user."""

    role = SelectField(
        _label("csa.roles.assign.role"),
        validators=[DataRequired(message=_message("csa.roles.assign.required"))],
    )
    submit = SubmitField(_label("csa.roles.assign.submit"))


class UserRoleRemoveForm(FlaskForm):
    """Remove an existing application role from a user."""

    role = HiddenField(validators=[DataRequired(message=_message("csa.roles.remove.required"))])
    submit = SubmitField(_label("csa.roles.remove.submit"))
