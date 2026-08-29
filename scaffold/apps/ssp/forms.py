"""Forms for the System Security Plan module."""

from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired, FileSize
from PIL import Image, UnidentifiedImageError
from wtforms import DateField, HiddenField, SelectField, SelectMultipleField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError

from scaffold.core.i18n import lazy_gettext as _l

MAX_ARCHITECTURE_OVERVIEW_BYTES = 5 * 1024 * 1024
MAX_ARCHITECTURE_OVERVIEW_DIMENSION_PX = 8000


def _validate_architecture_overview_image(form, field):
    """Decode the upload to confirm it's a genuine PNG/JPEG within size limits.

    FileAllowed only checks the filename extension; this reopens the actual
    bytes with Pillow so a renamed non-image file is rejected too.
    """
    file_storage = field.data
    if not file_storage:
        return

    file_storage.stream.seek(0)
    try:
        image = Image.open(file_storage.stream)
        image.verify()
        file_storage.stream.seek(0)
        image = Image.open(file_storage.stream)
        if image.format not in {"PNG", "JPEG"}:
            raise ValidationError(_l("ssp.architecture_overview.upload.errors.invalid_image"))
        if image.width > MAX_ARCHITECTURE_OVERVIEW_DIMENSION_PX or image.height > MAX_ARCHITECTURE_OVERVIEW_DIMENSION_PX:
            raise ValidationError(_l("ssp.architecture_overview.upload.errors.dimensions_too_large"))
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ValidationError(_l("ssp.architecture_overview.upload.errors.invalid_image"))
    finally:
        file_storage.stream.seek(0)


class SSPEditForm(FlaskForm):
    """Edit SSP-specific metadata fields."""

    laws_regulations = TextAreaField(
        _l("ssp.forms.laws_regulations"),
        validators=[Optional()],
        description=_l("ssp.forms.help.laws_regulations"),
        render_kw={"rows": 6},
    )
    authorization_boundary = TextAreaField(
        _l("ssp.forms.authorization_boundary"),
        validators=[Optional()],
        description=_l("ssp.forms.help.authorization_boundary"),
        render_kw={"rows": 4},
    )
    fips_confidentiality = SelectField(
        "Confidentiality Override",
        choices=[
            ("not_set", "Use derived (auto)"),
            ("low", "Low"),
            ("moderate", "Moderate"),
            ("high", "High"),
        ],
    )
    fips_integrity = SelectField(
        "Integrity Override",
        choices=[
            ("not_set", "Use derived (auto)"),
            ("low", "Low"),
            ("moderate", "Moderate"),
            ("high", "High"),
        ],
    )
    fips_availability = SelectField(
        "Availability Override",
        choices=[
            ("not_set", "Use derived (auto)"),
            ("low", "Low"),
            ("moderate", "Moderate"),
            ("high", "High"),
        ],
    )
    plan_completion_date = DateField(
        _l("ssp.forms.plan_completion_date"),
        validators=[Optional()],
        description=_l("ssp.forms.help.plan_completion_date"),
        format="%Y-%m-%d",
    )
    plan_approval_date = DateField(
        _l("ssp.forms.plan_approval_date"),
        validators=[Optional()],
        description=_l("ssp.forms.help.plan_approval_date"),
        format="%Y-%m-%d",
    )
    monitoring_kpis_kris = TextAreaField(
        _l("ssp.forms.monitoring_kpis_kris"),
        validators=[Optional()],
        description=_l("ssp.forms.help.monitoring_kpis_kris"),
        render_kw={"rows": 4},
    )
    monitoring_what = TextAreaField(
        _l("ssp.forms.monitoring_what"),
        validators=[Optional()],
        description=_l("ssp.forms.help.monitoring_what"),
        render_kw={"rows": 4},
    )
    monitoring_who = TextAreaField(
        _l("ssp.forms.monitoring_who"),
        validators=[Optional()],
        description=_l("ssp.forms.help.monitoring_who"),
        render_kw={"rows": 3},
    )
    monitoring_tools = TextAreaField(
        _l("ssp.forms.monitoring_tools"),
        validators=[Optional()],
        description=_l("ssp.forms.help.monitoring_tools"),
        render_kw={"rows": 3},
    )
    monitoring_frequency = StringField(
        _l("ssp.forms.monitoring_frequency"),
        validators=[Optional(), Length(max=100)],
        description=_l("ssp.forms.help.monitoring_frequency"),
        render_kw={"placeholder": "e.g. Monthly, Quarterly, Annually"},
    )
    submit = SubmitField(_l("ssp.forms.save"))


class SSPInterconnectionForm(FlaskForm):
    """Add or edit a system interconnection entry."""

    system_name = StringField(
        _l("ssp.forms.system_name"),
        validators=[DataRequired(), Length(max=255)],
        description=_l("ssp.forms.help.system_name"),
    )
    owning_organization = StringField(
        _l("ssp.forms.owning_organization"),
        validators=[Optional(), Length(max=255)],
        description=_l("ssp.forms.help.owning_organization"),
    )
    agreement_type = SelectField(
        _l("ssp.forms.agreement_type"),
        choices=[
            ("none", "None"),
            ("mou", "MOU"),
            ("isa", "ISA"),
            ("contract", "Contract"),
            ("informal", "Informal"),
        ],
        description=_l("ssp.forms.help.agreement_type"),
    )
    data_direction = SelectField(
        _l("ssp.forms.data_direction"),
        choices=[
            ("bidirectional", "Bidirectional"),
            ("incoming", "Incoming"),
            ("outgoing", "Outgoing"),
        ],
        description=_l("ssp.forms.help.data_direction"),
    )
    security_contact = StringField(
        _l("ssp.forms.security_contact"),
        validators=[Optional(), Length(max=255)],
        description=_l("ssp.forms.help.security_contact"),
    )
    notes = TextAreaField(
        _l("ssp.forms.notes"),
        validators=[Optional()],
        description=_l("ssp.forms.help.notes"),
        render_kw={"rows": 3},
    )
    submit = SubmitField(_l("ssp.forms.save"))


class SSPControlEntryForm(FlaskForm):
    """Annotate a control implementation entry."""

    implementation_status = SelectField(
        _l("ssp.forms.implementation_status"),
        choices=[
            ("planned", "Planned"),
            ("partially_implemented", "Partially Implemented"),
            ("implemented", "Implemented"),
            ("not_applicable", "Not Applicable"),
        ],
        description=_l("ssp.forms.help.implementation_status"),
    )
    responsible_entity = StringField(
        _l("ssp.forms.responsible_entity"),
        validators=[Optional(), Length(max=255)],
        description=_l("ssp.forms.help.responsible_entity"),
    )
    implementation_statement = TextAreaField(
        _l("ssp.forms.implementation_statement"),
        validators=[Optional()],
        description=_l("ssp.forms.help.implementation_statement"),
        render_kw={"rows": 4},
    )
    submit = SubmitField(_l("ssp.forms.save"))


class POAMItemForm(FlaskForm):
    """Create or edit a POA&M item."""

    weakness_description = TextAreaField(
        _l("ssp.forms.weakness_description"),
        validators=[DataRequired()],
        description=_l("ssp.forms.help.weakness_description"),
        render_kw={"rows": 4},
    )
    resources_required = TextAreaField(
        _l("ssp.forms.resources_required"),
        validators=[Optional()],
        description=_l("ssp.forms.help.resources_required"),
        render_kw={"rows": 3},
    )
    point_of_contact = StringField(
        _l("ssp.forms.point_of_contact"),
        validators=[Optional(), Length(max=255)],
        description=_l("ssp.forms.help.point_of_contact"),
    )
    scheduled_completion = DateField(
        _l("ssp.forms.scheduled_completion"),
        validators=[Optional()],
        description=_l("ssp.forms.help.scheduled_completion"),
        format="%Y-%m-%d",
    )
    estimated_cost = StringField(
        _l("ssp.forms.estimated_cost"),
        validators=[Optional(), Length(max=100)],
        description=_l("ssp.forms.help.estimated_cost"),
    )
    status = SelectField(
        _l("ssp.forms.status"),
        choices=[
            ("open", "Open"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("delayed", "Delayed"),
            ("cancelled", "Cancelled"),
        ],
        description=_l("ssp.forms.help.status"),
    )
    submit = SubmitField(_l("ssp.forms.save"))


# Status choices intentionally exclude "superseded": that state is reachable
# only via the supersede action on another ADR (FR-008), never a direct edit.
_ADR_STATUS_CHOICES = [
    ("proposed", "Proposed"),
    ("accepted", "Accepted"),
    ("rejected", "Rejected"),
    ("deprecated", "Deprecated"),
]


class ADRCreateForm(FlaskForm):
    """Create an Architecture Decision Record (adr.github.io) on an SSP."""

    title = StringField(_l("ssp.adr.forms.title"), validators=[DataRequired(), Length(max=255)])
    primary_principle_id = SelectField(
        _l("ssp.adr.forms.primary_principle"),
        validators=[DataRequired()],
        choices=[],
        coerce=int,
        description=_l("ssp.adr.forms.help.primary_principle"),
    )
    secondary_principle_ids = SelectMultipleField(
        _l("ssp.adr.forms.secondary_principles"),
        validators=[Optional()],
        choices=[],
        coerce=int,
        render_kw={"size": 6},
        description=_l("ssp.adr.forms.help.secondary_principles"),
    )
    status = SelectField(
        _l("ssp.adr.forms.status"),
        choices=_ADR_STATUS_CHOICES,
        description=_l("ssp.adr.forms.help.status"),
    )
    context = TextAreaField(_l("ssp.adr.forms.context"), validators=[DataRequired()], render_kw={"rows": 4})
    decision = TextAreaField(_l("ssp.adr.forms.decision"), validators=[DataRequired()], render_kw={"rows": 4})
    consequences = TextAreaField(_l("ssp.adr.forms.consequences"), validators=[Optional()], render_kw={"rows": 3})
    supersedes_id = SelectField(
        _l("ssp.adr.forms.supersedes"),
        validators=[Optional()],
        choices=[],
        coerce=int,
        description=_l("ssp.adr.forms.help.supersedes"),
    )
    submit = SubmitField(_l("ssp.adr.forms.submit"))


class ADRUpdateForm(FlaskForm):
    """Update an existing ADR. No primary_principle_id or supersedes_id field:

    the primary principle is immutable after creation (FR-004), and supersession
    is a create-time declaration (FR-008), not a generic update.
    """

    adr_id = HiddenField(validators=[DataRequired()])
    title = StringField(_l("ssp.adr.forms.title"), validators=[DataRequired(), Length(max=255)])
    secondary_principle_ids = SelectMultipleField(
        _l("ssp.adr.forms.secondary_principles"),
        validators=[Optional()],
        choices=[],
        coerce=int,
        render_kw={"size": 6},
        description=_l("ssp.adr.forms.help.secondary_principles"),
    )
    status = SelectField(
        _l("ssp.adr.forms.status"),
        choices=_ADR_STATUS_CHOICES,
        description=_l("ssp.adr.forms.help.status"),
    )
    context = TextAreaField(_l("ssp.adr.forms.context"), validators=[DataRequired()], render_kw={"rows": 4})
    decision = TextAreaField(_l("ssp.adr.forms.decision"), validators=[DataRequired()], render_kw={"rows": 4})
    consequences = TextAreaField(_l("ssp.adr.forms.consequences"), validators=[Optional()], render_kw={"rows": 3})
    submit = SubmitField(_l("ssp.adr.forms.update_submit"))


class POAMMilestoneForm(FlaskForm):
    """Add a milestone to a POA&M item."""

    description = TextAreaField(
        _l("ssp.forms.milestone_description"),
        validators=[DataRequired()],
        render_kw={"rows": 2},
    )
    scheduled_date = DateField(
        _l("ssp.forms.scheduled_date"),
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    completed_date = DateField(
        _l("ssp.forms.completed_date"),
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    submit = SubmitField(_l("ssp.forms.add_milestone_btn"))


class SSPArchitectureOverviewUploadForm(FlaskForm):
    """Upload a new architecture overview image version for an SSP."""

    image = FileField(
        _l("ssp.architecture_overview.upload.field.label"),
        validators=[
            FileRequired(message=_l("ssp.architecture_overview.upload.errors.required")),
            FileAllowed(["png", "jpg", "jpeg"], message=_l("ssp.architecture_overview.upload.errors.invalid_image")),
            FileSize(
                max_size=MAX_ARCHITECTURE_OVERVIEW_BYTES,
                message=_l("ssp.architecture_overview.upload.errors.too_large"),
            ),
            _validate_architecture_overview_image,
        ],
    )
    submit = SubmitField(_l("ssp.architecture_overview.upload.submit"))
