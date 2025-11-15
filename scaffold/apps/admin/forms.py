"""Forms used by the administration interface."""

from __future__ import annotations

from flask_wtf import FlaskForm
from wtforms import HiddenField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp


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
