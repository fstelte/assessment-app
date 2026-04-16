"""Forms used by the administration interface."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import HiddenField, IntegerField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp

from scaffold.core.i18n import lazy_gettext as _l


def _label(key: str) -> str:
    return _l(key)


def _message(key: str) -> str:
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


class ControlCreateForm(FlaskForm):
    """Manually create a control entry from the admin UI."""

    code = StringField(
        _label("admin.controls.manual.code_label"),
        validators=[Length(max=120)],
        render_kw={"placeholder": _l("admin.controls.manual.code_placeholder")},
        description=_l("admin.controls.manual.help.code"),
    )
    name = StringField(
        _label("admin.controls.manual.name_label"),
        validators=[DataRequired(), Length(max=255)],
        render_kw={"placeholder": _l("admin.controls.manual.name_placeholder")},
        description=_l("admin.controls.manual.help.name"),
    )
    description = TextAreaField(
        _label("admin.controls.manual.description_label"),
        validators=[Optional(), Length(max=5000)],
        render_kw={
            "placeholder": _l("admin.controls.manual.description_placeholder"),
            "rows": 4,
        },
    )
    submit = SubmitField(_label("admin.controls.manual.submit"))


class ControlUpdateForm(ControlCreateForm):
    """Update an existing control's metadata."""

    control_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField(_label("admin.controls.manual.update_submit"))


class ControlDeleteForm(FlaskForm):
    """Delete an existing control entry."""

    control_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField(_label("admin.controls.manual.delete_submit"))


class AuthenticationMethodForm(FlaskForm):
    """Create or update an authentication method option."""

    slug = StringField(
        "Slug",
        validators=[DataRequired(), Length(max=64), Regexp(r"^[a-z0-9-]+$", message="Use lowercase letters, digits, or hyphens.")],
    )
    submit = SubmitField("Save method")


class AuthenticationMethodToggleForm(FlaskForm):
    """Toggle the active state of an authentication method."""

    method_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField("Toggle active state")


class AuthenticationMethodDeleteForm(FlaskForm):
    """Remove or deactivate an authentication method."""

    method_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField("Delete method")


class BiaTierForm(FlaskForm):
    """Update a BIA tier's name."""

    submit = SubmitField(_label("actions.save"))


class InformationLabelForm(FlaskForm):
    """Create or update a sensitivity / information classification label."""

    label_en = StringField(
        _label("admin.information_labels.form.label_en"),
        validators=[DataRequired(), Length(max=255)],
    )
    label_nl = StringField(
        _label("admin.information_labels.form.label_nl"),
        validators=[DataRequired(), Length(max=255)],
    )
    severity = IntegerField(
        _label("admin.information_labels.form.severity"),
        validators=[NumberRange(min=0)],
        default=0,
    )
    submit = SubmitField(_label("admin.information_labels.form.submit"))


class InformationLabelToggleForm(FlaskForm):
    """Toggle the active state of an information label."""

    label_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField("Toggle")


class InformationLabelDeleteForm(FlaskForm):
    """Remove an information label."""

    label_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField("Delete")


class BackupCreateForm(FlaskForm):
    """Trigger an admin-initiated encrypted backup."""

    custom_key = StringField(
        _label("admin.backup.create.custom_key_label"),
        validators=[Optional(), Length(max=512)],
        render_kw={"placeholder": _l("admin.backup.create.custom_key_placeholder"), "autocomplete": "off"},
    )
    submit = SubmitField(_label("admin.backup.create.submit"))


class BackupRestoreForm(FlaskForm):
    """Upload a backup file for restore, with optional encryption key."""

    backup_file = FileField(
        _label("admin.backup.restore.file_label"),
        validators=[
            FileRequired(message=_message("admin.backup.restore.file_required")),
            FileAllowed(
                ["gz", "enc", "db", "sql", "dump"],
                message=_message("admin.backup.restore.file_type"),
            ),
        ],
    )
    encryption_key = PasswordField(
        _label("admin.backup.restore.key_label"),
        validators=[Optional(), Length(max=128)],
        description=_l("admin.backup.restore.key_help"),
    )
    submit = SubmitField(_label("admin.backup.restore.submit"))
