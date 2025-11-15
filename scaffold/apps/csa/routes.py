"""CSA routes for scaffold integration."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.orm import selectinload

from ...extensions import db
from ...core.i18n import gettext as _
from ..identity.models import (
    ROLE_ADMIN,
    ROLE_ASSESSMENT_MANAGER,
    User,
    UserStatus,
)
from .forms import (
    AssessmentAssignForm,
    AssessmentReviewForm,
    AssessmentStartForm,
    ControlImportForm,
    build_assessment_response_form,
    localise_question_set,
)
from .models import (
    Assessment,
    AssessmentAssignment,
    AssessmentDimension,
    AssessmentResponse,
    AssessmentStatus,
    AssessmentTemplate,
    Control,
)
from .services import import_controls_from_file, import_controls_from_mapping


MONTH_LABEL_KEYS = {
    1: "csa.months.january",
    2: "csa.months.february",
    3: "csa.months.march",
    4: "csa.months.april",
    5: "csa.months.may",
    6: "csa.months.june",
    7: "csa.months.july",
    8: "csa.months.august",
    9: "csa.months.september",
    10: "csa.months.october",
    11: "csa.months.november",
    12: "csa.months.december",
}


STATUS_LABEL_KEYS = {
    AssessmentStatus.ASSIGNED: "csa.status.assigned",
    AssessmentStatus.IN_PROGRESS: "csa.status.in_progress",
    AssessmentStatus.SUBMITTED: "csa.status.submitted",
    AssessmentStatus.REVIEWED: "csa.status.reviewed",
}


STATUS_BADGE_CLASSES = {
    AssessmentStatus.ASSIGNED: "secondary",
    AssessmentStatus.IN_PROGRESS: "info",
    AssessmentStatus.SUBMITTED: "warning",
    AssessmentStatus.REVIEWED: "success",
}


def _status_labels() -> dict[AssessmentStatus, str]:
    return {status: _(key) for status, key in STATUS_LABEL_KEYS.items()}


def _month_label(month: int) -> str:
    key = MONTH_LABEL_KEYS.get(month)
    return _(key) if key else str(month)


bp = Blueprint("csa", __name__, url_prefix="/csa", template_folder="templates")


@bp.app_context_processor
def inject_status_helpers() -> dict[str, object]:
    return {
        "csa_status_labels": _status_labels(),
        "csa_status_badges": STATUS_BADGE_CLASSES,
    }


def _has_assessment_management_role() -> bool:
    return current_user.has_role(ROLE_ADMIN) or current_user.has_role(ROLE_ASSESSMENT_MANAGER)


def _slugify_filename(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii", "ignore")
    ascii_only = ascii_only.replace("/", "-").replace("\\", "-").replace(":", "-")
    sanitized = re.sub(r"[^A-Za-z0-9 ._-]+", "", ascii_only)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized or "assessment"


def _require_assignment_permission() -> None:
    if not _has_assessment_management_role():
        abort(403)


def _user_can_access(assessment: Assessment) -> bool:
    return assessment.created_by_id == current_user.id or any(
        assignment.assignee_id == current_user.id for assignment in assessment.assignments
    )


def _ordered_templates() -> list[AssessmentTemplate]:
    templates = (
        AssessmentTemplate.query.filter_by(is_active=True)
        .options(selectinload(AssessmentTemplate.control))
        .all()
    )

    def _template_sort_key(template: AssessmentTemplate) -> tuple[int, list[int], str]:
        section_value = (template.control.section if template.control else "") or ""
        numeric_segments: list[int] = []
        root_order = 0
        if section_value:
            parts = [part for part in section_value.split() if part]
            if parts:
                first_part = parts[0]
                try:
                    root_order = int(first_part.split(".")[0])
                except ValueError:
                    root_order = 99
                for segment in first_part.split("."):
                    try:
                        numeric_segments.append(int(segment))
                    except ValueError:
                        numeric_segments.append(0)
        return (root_order, numeric_segments, template.name.lower())

    templates.sort(key=_template_sort_key)
    return templates


def _group_assessments_by_period(records: Iterable[Assessment]) -> list[dict[str, object]]:
    grouped: dict[int, dict[int, list[Assessment]]] = defaultdict(lambda: defaultdict(list))

    for assessment in records:
        reference = assessment.updated_at or assessment.created_at or assessment.started_at
        if reference is None:
            reference = datetime.now(UTC)
        if reference.tzinfo is None:
            reference = reference.replace(tzinfo=UTC)
        reference = reference.astimezone(UTC)
        grouped[reference.year][reference.month].append(assessment)

    year_buckets: list[dict[str, object]] = []
    for year in sorted(grouped.keys(), reverse=True):
        month_entries = []
        for month in sorted(grouped[year].keys(), reverse=True):
            def _sort_key(item: Assessment) -> datetime:
                candidate = item.updated_at or item.created_at or item.started_at
                if candidate is None:
                    return datetime.min.replace(tzinfo=UTC)
                if candidate.tzinfo is None:
                    candidate = candidate.replace(tzinfo=UTC)
                return candidate

            items = sorted(grouped[year][month], key=_sort_key, reverse=True)
            month_entries.append(
                {
                    "month": month,
                    "label": _month_label(month),
                    "assessments": items,
                }
            )
        year_buckets.append({"year": year, "months": month_entries})

    return year_buckets


@bp.get("/")
@login_required
def dashboard():
    assessment_count = db.session.query(func.count(Assessment.id)).scalar() or 0
    control_count = db.session.query(func.count(Control.id)).scalar() or 0

    status_totals = {status: 0 for status in AssessmentStatus}
    for status, total in (
        db.session.query(Assessment.status, func.count(Assessment.id))
        .group_by(Assessment.status)
        .all()
    ):
        status_totals[status] = total

    latest_assessments = (
        Assessment.query.options(
            selectinload(Assessment.template).selectinload(AssessmentTemplate.control),
            selectinload(Assessment.assignments).selectinload(AssessmentAssignment.assignee),
        )
        .order_by(Assessment.updated_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "csa/dashboard.html",
        assessment_count=assessment_count,
        control_count=control_count,
        status_totals=status_totals,
        latest_assessments=latest_assessments,
    )


@bp.route("/assessments/start", methods=["GET", "POST"])
@login_required
def start_assessment():
    form = AssessmentStartForm()
    templates = _ordered_templates()
    form.template_id.choices = [
        (
            template.id,
            " ".join(part for part in ((template.control.section if template.control else ""), template.name) if part).strip()
            or template.name,
        )
        for template in templates
    ]

    if not templates:
        if current_user.has_role(ROLE_ADMIN):
            flash(_("csa.flash.no_templates_import_first"), "warning")
            return redirect(url_for("csa.import_controls"))
        flash(_("csa.flash.no_templates_contact_admin"), "warning")
        return redirect(url_for("template.index"))

    if form.validate_on_submit():
        template = next((item for item in templates if item.id == form.template_id.data), None)
        if template is None:
            flash(_("csa.flash.invalid_template"), "danger")
        else:
            assessment = Assessment()
            assessment.template = template
            assessment.created_by = current_user
            assessment.mark_started()

            assignment = AssessmentAssignment()
            assignment.assessment = assessment
            assignment.assignee = current_user
            assignment.assigned_by = current_user
            assignment.is_primary = True

            db.session.add_all([assessment, assignment])
            db.session.commit()
            flash(_("csa.flash.assessment_started"), "success")
            return redirect(url_for("csa.view_assessment", assessment_id=assessment.id))

    return render_template("csa/assessments/start.html", form=form, templates=templates)


@bp.route("/assessments/assign", methods=["GET", "POST"])
@login_required
def assign_assessment():
    _require_assignment_permission()

    form = AssessmentAssignForm()
    templates = _ordered_templates()
    active_users = (
        User.query.filter(User.status == UserStatus.ACTIVE)
        .order_by(User.last_name.asc(), User.first_name.asc(), User.email.asc())
        .all()
    )

    form.template_id.choices = [
        (
            template.id,
            " ".join(part for part in ((template.control.section if template.control else ""), template.name) if part).strip()
            or template.name,
        )
        for template in templates
    ]
    form.assignee_id.choices = [(user.id, user.full_name) for user in active_users]

    if not templates:
        if current_user.has_role(ROLE_ADMIN):
            flash(_("csa.flash.no_templates_import_first"), "warning")
            return redirect(url_for("csa.import_controls"))
        flash(_("csa.flash.no_templates_contact_admin"), "warning")
        return redirect(url_for("template.index"))

    if not active_users:
        if current_user.has_role(ROLE_ADMIN):
            flash(_("csa.flash.no_active_users"), "warning")
            return redirect(url_for("admin.list_users"))
        flash(_("csa.flash.no_active_users"), "warning")
        return redirect(url_for("template.index"))

    if form.validate_on_submit():
        template = next((item for item in templates if item.id == form.template_id.data), None)
        assignee = next((item for item in active_users if item.id == form.assignee_id.data), None)

        if template is None or assignee is None:
            flash(_("csa.flash.invalid_selection"), "danger")
        else:
            assessment = Assessment()
            assessment.template = template
            assessment.created_by = current_user
            assessment.due_date = form.due_date.data

            assignment = AssessmentAssignment()
            assignment.assessment = assessment
            assignment.assignee = assignee
            assignment.assigned_by = current_user
            assignment.is_primary = True

            db.session.add_all([assessment, assignment])
            db.session.commit()
            flash(
                _(
                    "csa.flash.assessment_assigned",
                    template=template.name,
                    assignee=assignee.full_name,
                ),
                "success",
            )
            return redirect(url_for("csa.view_assessment", assessment_id=assessment.id))

    return render_template(
        "csa/assessments/assign.html",
        form=form,
        templates=templates,
        users=active_users,
    )


@bp.get("/assessments/overview")
@login_required
def overview_assessments():
    _require_assignment_permission()

    records = (
        Assessment.query.options(
            selectinload(Assessment.template).selectinload(AssessmentTemplate.control),
            selectinload(Assessment.assignments).selectinload(AssessmentAssignment.assignee),
            selectinload(Assessment.created_by),
        )
        .order_by(Assessment.updated_at.desc())
        .all()
    )

    timeline = _group_assessments_by_period(records)

    return render_template(
        "csa/assessments/overview.html",
        year_groups=timeline,
        status_labels=_status_labels(),
        badge_classes=STATUS_BADGE_CLASSES,
    )


@bp.route("/assessments/<int:assessment_id>", methods=["GET", "POST"])
@login_required
def view_assessment(assessment_id: int):
    assessment = Assessment.query.get_or_404(assessment_id)
    if not _user_can_access(assessment) and not _has_assessment_management_role():
        abort(403)

    question_set = assessment.template.question_set or {}
    form_class, layout = build_assessment_response_form(question_set)
    response_form = form_class()

    review_allowed = _has_assessment_management_role()
    review_form = None
    if review_allowed and assessment.status == AssessmentStatus.SUBMITTED:
        review_form = AssessmentReviewForm()
        if not review_form.is_submitted():
            review_form.comment.data = assessment.review_comment or ""

    has_questions = any(section["questions"] for section in layout)
    can_edit = assessment.status in {AssessmentStatus.ASSIGNED, AssessmentStatus.IN_PROGRESS}

    existing_responses = {
        (response.dimension.value, response.question_text): response
        for response in assessment.responses
    }

    if response_form.validate_on_submit() and "review_action" not in request.form:
        if not can_edit:
            flash(_("csa.flash.assessment_locked"), "info")
            return redirect(url_for("csa.view_assessment", assessment_id=assessment.id))

        submit_action = "review" if response_form.submit_for_review.data else "save"

        assessment.mark_started()
        for section in layout:
            for question in section["questions"]:
                field = getattr(response_form, question["field_name"])
                answer_text = (field.data or "").strip()
                key = (question["dimension"], question["question"])
                response = existing_responses.get(key)

                if response is None:
                    response = AssessmentResponse()
                    response.assessment = assessment
                    response.dimension = AssessmentDimension(question["dimension"])
                    response.question_text = question["question"]
                    db.session.add(response)
                    existing_responses[key] = response

                response.answer_text = answer_text or None
                response.responder = current_user
                response.responded_at = datetime.now(UTC)

        if submit_action == "review":
            assessment.mark_submitted()
            message = _("csa.flash.submitted_for_review")
        else:
            message = _("csa.flash.responses_saved")

        db.session.commit()
        flash(message, "success")
        return redirect(url_for("csa.view_assessment", assessment_id=assessment.id))

    if review_form and review_form.validate_on_submit() and "review_action" in request.form:
        action = request.form.get("review_action")
        review_comment = (review_form.comment.data or "").strip() or None

        if action == "approve":
            assessment.mark_reviewed()
            assessment.review_comment = review_comment
            db.session.commit()
            flash(_("csa.flash.review_approved"), "success")
        elif action == "return":
            if review_comment is None:
                flash(_("csa.flash.review_comment_required"), "warning")
                return redirect(url_for("csa.view_assessment", assessment_id=assessment.id))
            assessment.status = AssessmentStatus.IN_PROGRESS
            assessment.review_comment = review_comment
            assessment.reviewed_at = None
            db.session.commit()
            flash(_("csa.flash.review_returned"), "info")
        else:
            flash(_("csa.flash.unknown_review_action"), "danger")

        return redirect(url_for("csa.view_assessment", assessment_id=assessment.id))

    if not response_form.is_submitted():
        for section in layout:
            for question in section["questions"]:
                field = getattr(response_form, question["field_name"])
                existing = existing_responses.get((question["dimension"], question["question"]))
                if existing:
                    field.data = existing.answer_text or ""

    if not can_edit:
        for section in layout:
            for question in section["questions"]:
                field = getattr(response_form, question["field_name"])
                field.render_kw = {
                    **(field.render_kw or {}),
                    "readonly": True,
                    "disabled": True,
                }

    status_labels = _status_labels()
    status_label = status_labels.get(
        assessment.status, assessment.status.value.replace("_", " ").title()
    )

    return render_template(
        "csa/assessments/detail.html",
        assessment=assessment,
        layout=layout,
        form=response_form,
        review_form=review_form,
        has_questions=has_questions,
        can_edit=can_edit,
        review_allowed=review_allowed,
        status_label=status_label,
        badge_class=STATUS_BADGE_CLASSES.get(assessment.status, "secondary"),
    )


@bp.get("/assessments/<int:assessment_id>/export")
@login_required
def export_assessment(assessment_id: int):
    assessment = (
        Assessment.query.options(
            selectinload(Assessment.template).selectinload(AssessmentTemplate.control),
            selectinload(Assessment.assignments).selectinload(AssessmentAssignment.assignee),
            selectinload(Assessment.responses).selectinload(AssessmentResponse.responder),
            selectinload(Assessment.created_by),
        )
        .get_or_404(assessment_id)
    )

    if not _has_assessment_management_role() and not _user_can_access(assessment):
        abort(403)

    responses_lookup = {
        (resp.dimension.value, resp.question_text): resp for resp in assessment.responses
    }

    sections: list[dict[str, object]] = []
    question_set = assessment.template.question_set or {}
    localised_sections = localise_question_set(question_set)

    for section in localised_sections:
        questions = []
        for question in section["questions"]:
            canonical = question["question"]
            response = responses_lookup.get((section["dimension"], canonical))
            questions.append(
                {
                    "question": question["label"],
                    "answer": (response.answer_text if response else None) or "",
                    "comment": (response.comment if response else None) or "",
                    "responder": response.responder.full_name if response and response.responder else None,
                    "responded_at": response.responded_at if response else None,
                }
            )

        sections.append(
            {
                "dimension": section["dimension"],
                "label": section["label"],
                "questions": questions,
            }
        )

    generated_at = datetime.now(UTC)
    theme = "dark"
    if current_user.is_authenticated and getattr(current_user, "theme_preference", None) == "light":
        theme = "light"

    control_section = None
    control_description = None
    control_domain = None
    control_name = None
    control_code = None
    if assessment.template.control:
        control_section = (assessment.template.control.section or "").strip() or None
        control_description = assessment.template.control.description
        control_domain = (assessment.template.control.domain or "").strip() or None

    if control_section:
        control_code = control_section

    if control_domain:
        control_name = control_domain

    if not control_name:
        fallback_name = _("csa.assessments.export.default_name", id=assessment.id)
        control_name = control_section or assessment.template.name or fallback_name

    framework_code = control_code
    framework_reference = " ".join(part for part in (control_code, control_domain) if part).strip() or control_name

    status_labels = _status_labels()

    html = render_template(
        "csa/assessments/export.html",
        assessment=assessment,
        sections=sections,
        status_label=status_labels.get(
            assessment.status, assessment.status.value.replace("_", " ").title()
        ),
        generated_at=generated_at,
        theme=theme,
        control_name=control_name,
        control_code=control_code,
        control_section=control_section,
        framework_code=framework_code,
        framework_reference=framework_reference,
        control_description=control_description,
        badge_class=STATUS_BADGE_CLASSES.get(assessment.status, "secondary"),
    )

    if framework_code and control_name:
        filename_base = f"{framework_code} {control_name}"
    else:
        fallback_name = _("csa.assessments.export.default_name", id=assessment.id)
        filename_base = control_name or assessment.template.name or fallback_name

    safe_name = _slugify_filename(filename_base)
    date_suffix = generated_at.strftime("%Y%m%d")
    filename = f"{safe_name} - {date_suffix}.html"

    response = current_app.response_class(html, mimetype="text/html")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@bp.post("/assessments/<int:assessment_id>/delete")
@login_required
def delete_assessment(assessment_id: int):
    if not _has_assessment_management_role():
        abort(403)

    assessment = Assessment.query.get_or_404(assessment_id)
    db.session.delete(assessment)
    db.session.commit()
    flash(_("Assessment deleted."), "success")

    return redirect(url_for("csa.overview_assessments"))


@bp.route("/controls/import", methods=["GET", "POST"])
@login_required
def import_controls():
    if not current_user.has_role(ROLE_ADMIN):
        abort(403)

    form = ControlImportForm()

    if request.method == "POST" and request.form.get("action") == "import_builtin":
        builtin_path = Path(current_app.root_path).parent / "csa_app" / "iso_27002_controls.json"
        if not builtin_path.exists():
            flash(_("csa.flash.catalog_missing"), "danger")
        else:
            stats = import_controls_from_file(builtin_path)
            flash(
                _(
                    "csa.flash.import_result",
                    created=stats.created,
                    updated=stats.updated,
                ),
                "success" if not stats.errors else "warning",
            )
            for error in stats.errors:
                flash(error, "warning")
        return redirect(url_for("csa.import_controls"))

    if form.validate_on_submit():
        file_storage = form.data_file.data
        try:
            payload = json.load(file_storage)
        except json.JSONDecodeError as exc:
            flash(_("csa.flash.json_error", error=exc), "danger")
            file_storage.close()
            return redirect(url_for("csa.import_controls"))

        stats = import_controls_from_mapping(payload)
        flash(
            _(
                "csa.flash.import_result",
                created=stats.created,
                updated=stats.updated,
            ),
            "success" if not stats.errors else "warning",
        )
        for error in stats.errors:
            flash(error, "warning")
        return redirect(url_for("csa.import_controls"))

    return render_template("csa/admin/import_controls.html", form=form)
