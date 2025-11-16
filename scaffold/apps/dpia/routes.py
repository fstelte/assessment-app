"""Blueprint wiring for DPIA / FRIA workflows."""

from __future__ import annotations

import math

import sqlalchemy as sa
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

from ...core.i18n import gettext as _
from ...extensions import db
from ..bia.models import Component, ContextScope
from ..bia.utils import get_impact_color
from ..identity.models import ROLE_ADMIN, ROLE_ASSESSMENT_MANAGER
from .forms import AnswerQuestionForm, AssessmentDetailsForm, MeasureForm, RiskForm, StartDPIAForm
from .models import DPIAAssessment, DPIAAnswer, DPIAMeasure, DPIAQuestion, DPIARisk, DPIAAssessmentStatus
from .services.creation import bootstrap_assessment
from .services.questions import ensure_default_questions

blueprint = Blueprint(
    "dpia",
    __name__,
    url_prefix="/dpia",
    template_folder="templates",
    static_folder="static",
)

_RISK_LEVEL_LABELS = {
    1: "dpia.assessment.risks.level.very_low",
    2: "dpia.assessment.risks.level.low",
    3: "dpia.assessment.risks.level.medium",
    4: "dpia.assessment.risks.level.high",
    5: "dpia.assessment.risks.level.very_high",
}


_DPIA_STATUS_BADGES = {
    DPIAAssessmentStatus.IN_PROGRESS.value: "bg-primary",
    DPIAAssessmentStatus.IN_REVIEW.value: "bg-warning text-dark",
    DPIAAssessmentStatus.FINISHED.value: "bg-success",
    DPIAAssessmentStatus.ABANDONED.value: "bg-black",
}


def _risk_severity_payload(likelihood: int, impact: int) -> dict[str, object]:
    """Return severity metadata (level, label, badge class) for risk badges."""

    like = max(1, min(5, likelihood or 1))
    imp = max(1, min(5, impact or 1))
    severity_raw = max(1, like * imp)
    level = max(1, min(5, math.ceil(severity_raw / 5)))
    label_key = _RISK_LEVEL_LABELS.get(level, _RISK_LEVEL_LABELS[1])
    return {
        "level": level,
        "score": severity_raw,
        "label": _(label_key),
        "badge_class": f"badge badge-impact {get_impact_color(level)}",
    }


@blueprint.get("/")
@login_required
def dashboard():
    """List BIA components so users can start a DPIA directly from this module."""

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = current_app.config.get("BIA_COMPONENTS_PER_PAGE", 25)
    search_query = (request.args.get("q") or "").strip()
    selected_scope = (request.args.get("scope") or "all").strip()

    component_query = Component.query.options(
        joinedload(Component.dpia_assessments),
        joinedload(Component.context_scope),
        joinedload(Component.authentication_method),
    )
    component_query = component_query.join(ContextScope)
    if search_query:
        like = f"%{search_query}%"
        component_query = component_query.filter(Component.name.ilike(like))
    if selected_scope and selected_scope.lower() != "all":
        component_query = component_query.filter(ContextScope.name == selected_scope)

    pagination = component_query.order_by(Component.name.asc()).paginate(page=page, per_page=per_page, error_out=False)
    contexts = ContextScope.query.order_by(ContextScope.name.asc()).all()

    if pagination.total:
        page_start = (pagination.page - 1) * pagination.per_page + 1
        page_end = min(pagination.total, pagination.page * pagination.per_page)
    else:
        page_start = 0
        page_end = 0

    return render_template(
        "dpia/dashboard.html",
        components=pagination.items,
        pagination=pagination,
        contexts=contexts,
        search_query=search_query,
        selected_scope=selected_scope,
        page_start=page_start,
        page_end=page_end,
        per_page=per_page,
        dpia_status_badges=_DPIA_STATUS_BADGES,
    )


@blueprint.route("/components/<int:component_id>/start", methods=["GET", "POST"])
@login_required
def start_from_component(component_id: int):
    """Start a DPIA from a BIA component, pre-filling known fields."""

    component = Component.query.get_or_404(component_id)
    if component.context_scope and component.context_scope.author not in {None, current_user}:
        can_manage_owner = current_user.has_role(ROLE_ADMIN) or current_user.has_role(ROLE_ASSESSMENT_MANAGER)
        if not can_manage_owner:
            abort(403)

    existing_assessment = (
        DPIAAssessment.query.filter_by(component_id=component.id)
        .order_by(DPIAAssessment.updated_at.desc(), DPIAAssessment.id.desc())
        .first()
    )
    if existing_assessment:
        flash(_("dpia.flash.assessment_exists"), "info")
        return redirect(url_for("dpia.view_assessment", assessment_id=existing_assessment.id))

    form = StartDPIAForm()
    if not form.is_submitted():
        form.title.data = component.name
        form.project_lead.data = component.context_scope.project_leader if component.context_scope else None
        form.responsible_name.data = component.context_scope.responsible or component.info_owner

    if form.validate_on_submit():
        assessment = bootstrap_assessment(
            component=component,
            creator=current_user,
            title=form.title.data,
            project_lead=form.project_lead.data,
            responsible=form.responsible_name.data,
        )
        db.session.add(assessment)
        db.session.commit()
        flash(_("dpia.flash.assessment_created"), "success")
        return redirect(url_for("dpia.view_assessment", assessment_id=assessment.id))

    return render_template("dpia/start_from_component.html", component=component, form=form)


@blueprint.route("/assessments/<int:assessment_id>", methods=["GET", "POST"])
@login_required
def view_assessment(assessment_id: int):
    """Guided DPIA workflow with question answers, risks, and measures."""

    assessment = (
        DPIAAssessment.query.options(
            joinedload(DPIAAssessment.component).joinedload(Component.context_scope),
            joinedload(DPIAAssessment.answers).joinedload(DPIAAnswer.question),
            joinedload(DPIAAssessment.risks).joinedload(DPIARisk.measures),
            joinedload(DPIAAssessment.measures).joinedload(DPIAMeasure.risk),
        )
        .filter_by(id=assessment_id)
        .first_or_404()
    )
    component = assessment.component
    if component and component.context_scope and component.context_scope.author not in {None, current_user}:
        can_manage_owner = current_user.has_role(ROLE_ADMIN) or current_user.has_role(ROLE_ASSESSMENT_MANAGER)
        if not can_manage_owner and component.context_scope.author != current_user:
            abort(403)

    ensure_default_questions()

    questions = (
        DPIAQuestion.query.order_by(sa.nulls_last(DPIAQuestion.sort_order), DPIAQuestion.id.asc()).all()
    )
    def _localize(key: str | None, fallback: str | None) -> str | None:
        if not key:
            return fallback
        translated = _(key)
        return translated if translated != key else fallback

    for question in questions:
        question.localized_text = _localize(question.text_key, question.text) or question.text
        question.localized_help = _localize(question.help_key, question.help_text)
    answer_lookup = {answer.question_id: answer for answer in assessment.answers}

    def _truncate(label: str) -> str:
        return (label[:80] + "…") if len(label) > 80 else label

    question_choices = [(q.id, _truncate(q.localized_text)) for q in questions]
    likelihood_choices = [(i, str(i)) for i in range(1, 6)]
    effect_choices = [(i, f"{i:+d}") for i in range(-3, 4)]
    risk_type_choices = RiskForm().risk_type.choices
    status_choices = [(status.value, _("dpia.status." + status.value)) for status in DPIAAssessmentStatus]
    risk_choices = [(0, _("dpia.assessment.measures.no_risk_option"))] + [
        (risk.id, (risk.description[:60] + "…") if len(risk.description) > 60 else risk.description)
        for risk in assessment.risks
    ]

    details_form = AssessmentDetailsForm(obj=assessment)
    details_form.status.choices = status_choices
    if not details_form.status.data:
        details_form.status.data = assessment.status.value
    answer_form = AnswerQuestionForm()
    answer_form.question_id.choices = question_choices
    risk_form = RiskForm()
    risk_form.likelihood.choices = likelihood_choices
    risk_form.impact.choices = likelihood_choices
    measure_form = MeasureForm()
    measure_form.effect_likelihood.choices = effect_choices
    measure_form.effect_impact.choices = effect_choices
    measure_form.risk_id.choices = risk_choices
    if measure_form.risk_id.data is None:
        measure_form.risk_id.data = 0

    redirect_url = url_for("dpia.view_assessment", assessment_id=assessment.id)
    active_form = request.form.get("form_name")
    if request.method == "POST":
        if active_form == "details":
            details_form = AssessmentDetailsForm(formdata=request.form)
            details_form.status.choices = status_choices
            if details_form.validate():
                assessment.title = details_form.title.data.strip()
                assessment.project_lead = (details_form.project_lead.data or "").strip() or None
                assessment.responsible_name = (details_form.responsible_name.data or "").strip() or None
                assessment.status = DPIAAssessmentStatus(details_form.status.data)
                db.session.commit()
                flash(_("dpia.flash.details_saved"), "success")
                return redirect(redirect_url)
        elif active_form == "answer":
            answer_form = AnswerQuestionForm(formdata=request.form)
            answer_form.question_id.choices = question_choices
            if answer_form.validate():
                question_id = answer_form.question_id.data
                text = answer_form.answer_text.data.strip()
                answer = answer_lookup.get(question_id)
                if answer is None:
                    answer = DPIAAnswer(assessment=assessment, question_id=question_id)
                answer.answer_text = text
                db.session.add(answer)
                db.session.commit()
                flash(_("dpia.flash.answer_saved"), "success")
                return redirect(redirect_url)
        elif active_form == "risk":
            risk_form = RiskForm(formdata=request.form)
            risk_form.likelihood.choices = likelihood_choices
            risk_form.impact.choices = likelihood_choices
            if risk_form.validate():
                risk = DPIARisk(
                    assessment=assessment,
                    risk_type=risk_form.risk_type.data,
                    description=risk_form.description.data.strip(),
                    likelihood=risk_form.likelihood.data,
                    impact=risk_form.impact.data,
                )
                db.session.add(risk)
                db.session.commit()
                flash(_("dpia.flash.risk_added"), "success")
                return redirect(redirect_url)
        elif active_form == "risk_update":
            target_id = request.form.get("risk_id", type=int)
            target_risk = next((risk for risk in assessment.risks if risk.id == target_id), None)
            if target_risk is None:
                flash(_("dpia.flash.risk_not_found"), "warning")
            else:
                update_form = RiskForm(formdata=request.form)
                update_form.likelihood.choices = likelihood_choices
                update_form.impact.choices = likelihood_choices
                if update_form.validate():
                    target_risk.risk_type = update_form.risk_type.data
                    target_risk.description = update_form.description.data.strip()
                    target_risk.likelihood = update_form.likelihood.data
                    target_risk.impact = update_form.impact.data
                    db.session.commit()
                    flash(_("dpia.flash.risk_updated"), "success")
                    return redirect(redirect_url)
                flash(_("dpia.flash.risk_update_failed"), "danger")
        elif active_form == "risk_delete":
            target_id = request.form.get("risk_id", type=int)
            target_risk = next((risk for risk in assessment.risks if risk.id == target_id), None)
            if target_risk is None:
                flash(_("dpia.flash.risk_not_found"), "warning")
            else:
                db.session.delete(target_risk)
                db.session.commit()
                flash(_("dpia.flash.risk_deleted"), "success")
                return redirect(redirect_url)
        elif active_form == "measure":
            measure_form = MeasureForm(formdata=request.form)
            measure_form.effect_likelihood.choices = effect_choices
            measure_form.effect_impact.choices = effect_choices
            measure_form.risk_id.choices = risk_choices
            if measure_form.validate():
                linked_risk_id = measure_form.risk_id.data or 0
                linked_risk = next((risk for risk in assessment.risks if risk.id == linked_risk_id), None)
                measure = DPIAMeasure(
                    assessment=assessment,
                    description=measure_form.description.data.strip(),
                    effect_likelihood=measure_form.effect_likelihood.data,
                    effect_impact=measure_form.effect_impact.data,
                    risk=linked_risk,
                )
                db.session.add(measure)
                db.session.commit()
                flash(_("dpia.flash.measure_added"), "success")
                return redirect(redirect_url)
        elif active_form == "measure_update":
            target_id = request.form.get("measure_id", type=int)
            target_measure = next((measure for measure in assessment.measures if measure.id == target_id), None)
            if target_measure is None:
                flash(_("dpia.flash.measure_not_found"), "warning")
            else:
                update_form = MeasureForm(formdata=request.form)
                update_form.effect_likelihood.choices = effect_choices
                update_form.effect_impact.choices = effect_choices
                update_form.risk_id.choices = risk_choices
                if update_form.validate():
                    target_measure.description = update_form.description.data.strip()
                    target_measure.effect_likelihood = update_form.effect_likelihood.data
                    target_measure.effect_impact = update_form.effect_impact.data
                    linked_risk_id = update_form.risk_id.data or 0
                    linked_risk = next((risk for risk in assessment.risks if risk.id == linked_risk_id), None)
                    target_measure.risk = linked_risk
                    db.session.commit()
                    flash(_("dpia.flash.measure_updated"), "success")
                    return redirect(redirect_url)
                flash(_("dpia.flash.measure_update_failed"), "danger")
        elif active_form == "measure_delete":
            target_id = request.form.get("measure_id", type=int)
            target_measure = next((measure for measure in assessment.measures if measure.id == target_id), None)
            if target_measure is None:
                flash(_("dpia.flash.measure_not_found"), "warning")
            else:
                db.session.delete(target_measure)
                db.session.commit()
                flash(_("dpia.flash.measure_deleted"), "success")
                return redirect(redirect_url)

    for risk in assessment.risks:
        risk.initial_severity = _risk_severity_payload(risk.likelihood, risk.impact)
        risk.residual_severity = _risk_severity_payload(risk.residual_likelihood, risk.residual_impact)

    total_questions = len(questions)
    answered_questions = len(answer_lookup)

    return render_template(
        "dpia/assessment_detail.html",
        assessment=assessment,
        component=component,
        questions=questions,
        answers=answer_lookup,
        details_form=details_form,
        answer_form=answer_form,
        risk_form=risk_form,
        measure_form=measure_form,
        likelihood_choices=likelihood_choices,
        risk_type_choices=risk_type_choices,
        effect_choices=effect_choices,
        measure_risk_choices=risk_choices,
        dpia_status_badges=_DPIA_STATUS_BADGES,
        answered_questions=answered_questions,
        total_questions=total_questions,
    )


@blueprint.post("/assessments/<int:assessment_id>/delete")
@login_required
def delete_assessment(assessment_id: int):
    """Remove a DPIA assessment and its related data."""

    assessment = (
        DPIAAssessment.query.options(
            joinedload(DPIAAssessment.component).joinedload(Component.context_scope),
        )
        .filter_by(id=assessment_id)
        .first_or_404()
    )
    component = assessment.component
    if component and component.context_scope and component.context_scope.author not in {None, current_user}:
        can_manage_owner = current_user.has_role(ROLE_ADMIN) or current_user.has_role(ROLE_ASSESSMENT_MANAGER)
        if not can_manage_owner and component.context_scope.author != current_user:
            abort(403)

    db.session.delete(assessment)
    db.session.commit()
    flash(_("dpia.flash.assessment_deleted"), "success")
    return redirect(url_for("dpia.dashboard"))
