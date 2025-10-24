"""Routes for assessment assignments and submissions."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
import re
import unicodedata

from flask import abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from ...extensions import db
from ...forms import (
    AssessmentAssignForm,
    AssessmentReviewForm,
    AssessmentStartForm,
    build_assessment_response_form,
)
from ...models import (
    Assessment,
    AssessmentAssignment,
    AssessmentStatus,
    AssessmentDimension,
    AssessmentResponse,
    AssessmentTemplate,
    User,
    UserStatus,
)
from . import bp


MONTH_LABELS = {
    1: "Januari",
    2: "Februari",
    3: "Maart",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Augustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "December",
}


STATUS_LABELS = {
    AssessmentStatus.ASSIGNED: "Toegewezen",
    AssessmentStatus.IN_PROGRESS: "In uitvoering",
    AssessmentStatus.SUBMITTED: "In review",
    AssessmentStatus.REVIEWED: "Beoordeeld",
}

STATUS_BADGE_CLASSES = {
    AssessmentStatus.ASSIGNED: "secondary",
    AssessmentStatus.IN_PROGRESS: "info",
    AssessmentStatus.SUBMITTED: "warning",
    AssessmentStatus.REVIEWED: "success",
}


def _slugify_filename(value: str) -> str:
    """Convert a string into a safe filename segment."""

    normalized = unicodedata.normalize("NFKD", value)
    ascii_only = normalized.encode("ascii", "ignore").decode("ascii", "ignore")
    ascii_only = ascii_only.replace("/", "-").replace("\\", "-").replace(":", "-")
    sanitized = re.sub(r"[^A-Za-z0-9 ._-]+", "", ascii_only)
    sanitized = re.sub(r"\s+", " ", sanitized).strip()
    return sanitized or "assessment"


def _format_template_choice(template: AssessmentTemplate) -> str:
    """Return a human readable label for a template selection."""

    if not template.control:
        return template.name

    code = (template.control.section or "").strip()
    label = (template.control.domain or "").strip()

    if code and label:
        return f"{code} · {label}"

    return label or code or template.name


def _user_can_access(assessment: Assessment) -> bool:
    """Return True when the current user may view the assessment."""

    return assessment.created_by_id == current_user.id or any(
        assignment.assignee_id == current_user.id for assignment in assessment.assignments
    )


def _group_assessments_by_period(records: list[Assessment]) -> list[dict[str, object]]:
    """Bucket assessments by year and month for timeline navigation."""

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
                    "label": MONTH_LABELS.get(month, str(month)),
                    "assessments": items,
                }
            )
        year_buckets.append({"year": year, "months": month_entries})

    return year_buckets

def _ordered_templates() -> list[AssessmentTemplate]:
    """Return active templates ordered by control section number when available."""

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


def _require_assignment_permission() -> None:
    if not (current_user.has_role("admin") or current_user.has_role("manager")):
        abort(403)


@bp.route("/start", methods=["GET", "POST"])
@login_required
def start():
    """Allow a user to start a new self assessment from an active template."""

    form = AssessmentStartForm()
    templates = _ordered_templates()
    form.template_id.choices = [
        (
            template.id,
            _format_template_choice(template),
        )
        for template in templates
    ]

    if not templates:
        if current_user.has_role("admin"):
            flash("Er zijn nog geen sjablonen. Importeer eerst controls.", "warning")
            return redirect(url_for("admin.import_controls"))
        flash("Er zijn geen actieve sjablonen beschikbaar. Neem contact op met uw administrator.", "warning")
        return redirect(url_for("public.index"))

    if form.validate_on_submit():
        template = next((item for item in templates if item.id == form.template_id.data), None)
        if template is None:
            flash("Ongeldig sjabloon geselecteerd.", "danger")
        else:
            assessment = Assessment(template=template, created_by=current_user)
            assessment.mark_started()
            assignment = AssessmentAssignment(
                assessment=assessment,
                assignee=current_user,
                assigned_by=current_user,
                is_primary=True,
            )
            db.session.add_all([assessment, assignment])
            db.session.commit()
            flash("Nieuwe self assessment is gestart.", "success")
            return redirect(url_for("assessments.detail", assessment_id=assessment.id))

    return render_template("assessments/start.html", form=form, templates=templates)


@bp.route("/assign", methods=["GET", "POST"])
@login_required
def assign():
    """Allow managers to assign self assessments to other users."""

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
            _format_template_choice(template),
        )
        for template in templates
    ]
    form.assignee_id.choices = [(user.id, user.full_name) for user in active_users]

    if not templates:
        if current_user.has_role("admin"):
            flash("Er zijn geen sjablonen beschikbaar om toe te wijzen. Importeer eerst controls.", "warning")
            return redirect(url_for("admin.import_controls"))
        flash("Er zijn geen sjablonen beschikbaar. Neem contact op met een administrator.", "warning")
        return redirect(url_for("public.index"))

    if not active_users:
        if current_user.has_role("admin"):
            flash("Er zijn geen actieve gebruikers om aan toe te wijzen.", "warning")
            return redirect(url_for("admin.users"))
        flash("Er zijn geen actieve gebruikers om aan toe te wijzen.", "warning")
        return redirect(url_for("public.index"))

    if form.validate_on_submit():
        template = next((item for item in templates if item.id == form.template_id.data), None)
        assignee = next((item for item in active_users if item.id == form.assignee_id.data), None)

        if template is None or assignee is None:
            flash("Ongeldige selectie, probeer het opnieuw.", "danger")
        else:
            assessment = Assessment(template=template, created_by=current_user, due_date=form.due_date.data)
            assignment = AssessmentAssignment(
                assessment=assessment,
                assignee=assignee,
                assigned_by=current_user,
                is_primary=True,
            )
            db.session.add_all([assessment, assignment])
            db.session.commit()
            flash(
                f"Assessment '{template.name}' is toegewezen aan {assignee.full_name}.",
                "success",
            )
            return redirect(url_for("assessments.detail", assessment_id=assessment.id))

    return render_template("assessments/assign.html", form=form, templates=templates, users=active_users)


@bp.route("/overview")
@login_required
def overview():
    """Provide an overview of all assessments for managers and administrators."""

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
        "assessments/overview.html",
        year_groups=timeline,
        status_labels=STATUS_LABELS,
        badge_classes=STATUS_BADGE_CLASSES,
    )


@bp.route("/<int:assessment_id>", methods=["GET", "POST"])
@login_required
def detail(assessment_id: int):
    """Display assessment details and capture answers from the assignee."""

    assessment = Assessment.query.get_or_404(assessment_id)
    if not _user_can_access(assessment):
        abort(403)

    question_set = assessment.template.question_set or {}
    form_class, layout = build_assessment_response_form(question_set)
    response_form = form_class()
    review_allowed = current_user.has_role("admin") or current_user.has_role("manager")
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
            flash("Deze assessment is al ingediend en kan niet meer worden gewijzigd.", "info")
            return redirect(url_for("assessments.detail", assessment_id=assessment.id))

        submit_action = "review" if response_form.submit_for_review.data else "save"

        assessment.mark_started()
        for section in layout:
            for question in section["questions"]:
                field = getattr(response_form, question["field_name"])
                answer_text = (field.data or "").strip()
                key = (question["dimension"], question["question"])
                response = existing_responses.get(key)

                if response is None:
                    response = AssessmentResponse(
                        assessment=assessment,
                        dimension=AssessmentDimension(question["dimension"]),
                        question_text=question["question"],
                    )
                    db.session.add(response)
                    existing_responses[key] = response

                response.answer_text = answer_text or None
                response.responder = current_user
                response.responded_at = datetime.now(UTC)

        if submit_action == "review":
            assessment.mark_submitted()
            message = "Assessment is ter beoordeling ingediend."
        else:
            message = "Antwoorden zijn opgeslagen."

        db.session.commit()
        flash(message, "success")
        return redirect(url_for("assessments.detail", assessment_id=assessment.id))

    elif review_form and review_form.validate_on_submit() and "review_action" in request.form:

        action = request.form.get("review_action")
        review_comment = (review_form.comment.data or "").strip() or None

        if action == "approve":
            assessment.mark_reviewed()
            assessment.review_comment = review_comment
            db.session.commit()
            flash("Assessment is goedgekeurd.", "success")
        elif action == "return":
            if review_comment is None:
                flash("Voeg een opmerking toe bij het terugsturen naar de indiener.", "warning")
                return redirect(url_for("assessments.detail", assessment_id=assessment.id))
            assessment.status = AssessmentStatus.IN_PROGRESS
            assessment.review_comment = review_comment
            assessment.reviewed_at = None
            flash("Assessment is teruggezet naar de indiener.", "info")
            db.session.commit()
        else:
            flash("Onbekende review-actie.", "danger")

        return redirect(url_for("assessments.detail", assessment_id=assessment.id))

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

    return render_template(
        "assessments/detail.html",
        assessment=assessment,
        layout=layout,
        form=response_form,
        review_form=review_form,
        has_questions=has_questions,
        can_edit=can_edit,
        review_allowed=review_allowed,
        status_label=STATUS_LABELS.get(
            assessment.status, assessment.status.value.replace("_", " ").title()
        ),
        badge_class=STATUS_BADGE_CLASSES.get(assessment.status, "secondary"),
    )


@bp.get("/<int:assessment_id>/export")
@login_required
def export(assessment_id: int):
    """Export a single assessment to JSON for audit evidence."""

    assessment = (
        Assessment.query.options(
            selectinload(Assessment.template).selectinload(AssessmentTemplate.control),
            selectinload(Assessment.assignments).selectinload(AssessmentAssignment.assignee),
            selectinload(Assessment.responses).selectinload(AssessmentResponse.responder),
            selectinload(Assessment.created_by),
        )
        .get_or_404(assessment_id)
    )

    if not (current_user.has_role("admin") or current_user.has_role("manager")) and not _user_can_access(assessment):
        abort(403)

    responses_lookup = {
        (resp.dimension.value, resp.question_text): resp for resp in assessment.responses
    }

    sections: list[dict[str, object]] = []
    question_set = assessment.template.question_set or {}
    for dimension_key, section in question_set.items():
        questions = []
        for question_text in section.get("questions", []) or []:
            response = responses_lookup.get((dimension_key, question_text))
            questions.append(
                {
                    "question": question_text,
                    "answer": (response.answer_text if response else None) or "",
                    "comment": (response.comment if response else None) or "",
                    "responder": response.responder.full_name if response and response.responder else None,
                    "responded_at": response.responded_at if response else None,
                }
            )
        sections.append(
            {
                "dimension": dimension_key,
                "label": section.get("label") or dimension_key.replace("_", " ").title(),
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
        control_name = control_section or assessment.template.name or f"Assessment {assessment.id}"

    framework_code = control_code
    framework_reference = " ".join(part for part in (control_code, control_domain) if part).strip() or control_name

    html = render_template(
        "assessments/export.html",
        assessment=assessment,
        sections=sections,
        status_label=STATUS_LABELS.get(
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
        filename_base = control_name or assessment.template.name or f"Assessment {assessment.id}"

    safe_name = _slugify_filename(filename_base)
    date_suffix = generated_at.strftime("%Y%m%d")
    filename = f"{safe_name} - {date_suffix}.html"

    response = current_app.response_class(html, mimetype="text/html")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
