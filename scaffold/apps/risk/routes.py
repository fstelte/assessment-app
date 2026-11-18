"""Frontend routes powering the risk workspace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Sequence

import sqlalchemy as sa
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...core.audit import log_event
from ...core.i18n import gettext as _
from ...extensions import db
from ..bia.models import Component, ContextScope
from ..csa.models import Control
from ..identity.models import ROLE_ADMIN, ROLE_ASSESSMENT_MANAGER
from .forms import RiskApprovalForm, RiskForm, RiskActionForm
from .models import (
    CHANCE_WEIGHTS,
    IMPACT_WEIGHTS,
    Risk,
    RiskApprovalStatus,
    RiskChance,
    RiskImpact,
    RiskSeverity,
    RiskSeverityThreshold,
    RiskTreatmentOption,
)
from .services import (
    configure_risk_form,
    determine_severity,
    load_thresholds,
    optional_int,
    set_impact_areas,
    set_ticket_links,
    validate_component_ids,
    validate_control_ids,
)

bp = Blueprint(
    "risk",
    __name__,
    url_prefix="/risk",
    template_folder="templates",
    static_folder="static",
)

_DEFAULT_PILL = "risk-pill risk-pill--muted"
_SEVERITY_BADGES = {
    RiskSeverity.CRITICAL: "risk-pill risk-pill--critical",
    RiskSeverity.HIGH: "risk-pill risk-pill--high",
    RiskSeverity.MODERATE: "risk-pill risk-pill--moderate",
    RiskSeverity.LOW: "risk-pill risk-pill--low",
}
_STATUS_BADGES = {
    "overdue": "risk-pill risk-pill--overdue",
    "scheduled": "risk-pill risk-pill--scheduled",
    "unscheduled": _DEFAULT_PILL,
    "archived": "risk-pill risk-pill--archived",
}


def register(app):
    """Register the blueprint with the Flask application."""

    app.register_blueprint(bp)
    app.logger.info("Risk UI blueprint registered.")


def _require_risk_access() -> None:
    if not current_user.is_authenticated:
        abort(403)


def _risk_query():
    return Risk.query.options(
        sa.orm.selectinload(Risk.components).selectinload(Component.context_scope),
        sa.orm.selectinload(Risk.impact_area_links),
        sa.orm.selectinload(Risk.controls),
        sa.orm.selectinload(Risk.treatment_owner),
        sa.orm.selectinload(Risk.ticket_links),
    )


def _flash_form_errors(form: RiskForm) -> None:
    for messages in form.errors.values():
        for message in messages:
            flash(message, "danger")


def _resolve_components(form: RiskForm) -> list[Component] | None:
    try:
        component_ids = [int(value) for value in form.component_ids.data]
    except (TypeError, ValueError):
        form.component_ids.errors.append(_("admin.risks.errors.invalid_components"))
        return None
    if not component_ids:
        form.component_ids.errors.append(_("admin.risks.errors.invalid_components"))
        return None
    try:
        return validate_component_ids(component_ids)
    except ValueError:
        form.component_ids.errors.append(_("admin.risks.errors.invalid_components"))
        return None


def _resolve_components_for_edit(form: RiskForm) -> list[Component] | None:
    """Like _resolve_components but also accepts ineligible components already in the form choices."""
    try:
        component_ids = [int(value) for value in form.component_ids.data]
    except (TypeError, ValueError):
        form.component_ids.errors.append(_("admin.risks.errors.invalid_components"))
        return None
    if not component_ids:
        form.component_ids.errors.append(_("admin.risks.errors.invalid_components"))
        return None
    # Accept any component id that appears in the rendered choices (eligible + ineligible extras)
    allowed_ids = {int(value) for value, _label in (form.component_ids.choices or [])}
    if not all(cid in allowed_ids for cid in component_ids):
        form.component_ids.errors.append(_("admin.risks.errors.invalid_components"))
        return None
    components = Component.query.filter(Component.id.in_(component_ids)).all()
    if not components:
        form.component_ids.errors.append(_("admin.risks.errors.invalid_components"))
        return None
    return components


def _resolve_controls(form: RiskForm) -> list[Control] | None:
    selected_ids = [value for value in (form.csa_control_ids.data or []) if value]
    if not selected_ids:
        return []
    try:
        control_ids = [int(value) for value in selected_ids]
    except (TypeError, ValueError):
        form.csa_control_ids.errors.append(_("admin.risks.errors.invalid_controls"))
        return None
    try:
        return validate_control_ids(control_ids)
    except ValueError:
        form.csa_control_ids.errors.append(_("admin.risks.errors.invalid_controls"))
        return None


def _apply_residual_fields(form: RiskForm, risk: Risk) -> None:
    """Copy the mitigated marker and residual assessment from the form (decision 20261118-0800)."""

    if form.mitigated.data:
        risk.mitigated_at = risk.mitigated_at or datetime.now(UTC)
    else:
        risk.mitigated_at = None
    risk.residual_impact = RiskImpact(form.residual_impact.data) if form.residual_impact.data else None
    risk.residual_chance = RiskChance(form.residual_chance.data) if form.residual_chance.data else None


def _residual_audit_details(risk: Risk) -> dict[str, object]:
    return {
        "mitigated": risk.is_mitigated,
        "residual_impact": risk.residual_impact.value if risk.residual_impact else None,
        "residual_chance": risk.residual_chance.value if risk.residual_chance else None,
    }


@bp.route("/sync-from-threats", methods=["POST"])
@login_required
def sync_from_threats():
    """Sync all eligible threat scenarios into the risk workspace (create or update)."""
    _require_risk_access()
    from ..threat.models import ThreatScenario, TreatmentOption
    from ..threat.services import _CLOSING_STATUSES, sync_scenario_to_risk

    scenarios = ThreatScenario.query.filter_by(is_archived=False).all()
    created = 0
    updated = 0
    for scenario in scenarios:
        if scenario.treatment is not TreatmentOption.MITIGATE:
            continue
        if scenario.status in _CLOSING_STATUSES:
            continue
        was_new = scenario.risk_id is None
        sync_scenario_to_risk(scenario)
        if was_new:
            created += 1
        else:
            updated += 1

    db.session.commit()
    if created or updated:
        flash(_("risk.flash.synced_from_threats").format(count=created + updated), "success")
    else:
        flash(_("risk.flash.synced_from_threats_none"), "info")
    return redirect(url_for("risk.dashboard"))


@bp.route("/")
@login_required
def dashboard():
    """Show a human-friendly overview of every registered risk."""

    _require_risk_access()
    thresholds = load_thresholds()
    # BIA filter (decision 20261118-0801): ?bia=<id>&bia=<id>; unknown ids are ignored.
    bia_options = (
        ContextScope.query.filter(ContextScope.components.any())
        .order_by(ContextScope.name)
        .all()
    )
    known_bia_ids = {scope.id for scope in bia_options}
    selected_bia_ids = sorted(
        {int(value) for value in request.args.getlist("bia") if value.isdigit()} & known_bia_ids
    )
    bia_filter = Risk.components.any(Component.context_scope_id.in_(selected_bia_ids)) if selected_bia_ids else sa.true()
    # Approval filter (decisions 20261118-1048, -1058): open risks only; unknown values are ignored.
    selected_approval = request.args.get("approval")
    if selected_approval not in _APPROVAL_FILTERS:
        selected_approval = None
    query = _risk_query().filter(bia_filter)
    if selected_approval:
        query = query.filter(Risk.closed_at.is_(None), _APPROVAL_FILTERS[selected_approval]())
    risks = query.order_by(Risk.created_at.desc()).all()
    mine_count = Risk.query.filter(bia_filter, Risk.closed_at.is_(None), _APPROVAL_FILTERS["mine"]()).count()
    cards = _build_dashboard_cards(risks, thresholds)
    metrics = _dashboard_metrics(cards, selected_bia_ids)
    matrix = _build_risk_matrix(risks, thresholds)
    severity_scale = _severity_scale(thresholds)
    action_form = RiskActionForm()
    return render_template(
        "risk/dashboard.html",
        risk_cards=cards,
        metrics=metrics,
        risk_matrix=matrix,
        severity_scale=severity_scale,
        api_endpoint_available="risk_api.get_risk" in current_app.view_functions,
        RiskTreatmentOption=RiskTreatmentOption,
        action_form=action_form,
        bia_options=bia_options,
        selected_bia_ids=selected_bia_ids,
        selected_approval=selected_approval,
        mine_count=mine_count,
    )


_APPROVAL_FILTERS = {
    "mine": lambda: sa.and_(
        Risk.treatment_owner_id == current_user.id,
        sa.or_(Risk.approval_status.is_(None), Risk.approval_status == RiskApprovalStatus.REJECTED),
    ),
    "awaiting": lambda: sa.and_(Risk.treatment_owner_id.isnot(None), Risk.approval_status.is_(None)),
    "rejected": lambda: Risk.approval_status == RiskApprovalStatus.REJECTED,
}


def _parse_ticket_links_from_form(form_data) -> list[dict]:
    """Extract ordered ticket link dicts from ticket_label_N / ticket_url_N form fields."""
    links = []
    i = 0
    while True:
        label = (form_data.get(f"ticket_label_{i}") or "").strip()
        url = (form_data.get(f"ticket_url_{i}") or "").strip()
        if not label and not url:
            break
        if label or url:
            links.append({"label": label, "url": url, "sort_order": i})
        i += 1
    return links


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    """Create a new risk entry via the shared form."""

    _require_risk_access()
    form = RiskForm()
    configure_risk_form(form)
    form.submit.label.text = _("Save risk")
    component_choices_available = bool(form.component_ids.choices)

    if form.validate_on_submit():
        components = _resolve_components(form)
        controls = _resolve_controls(form)
        if components and controls is not None:
            risk = Risk(
                title=(form.title.data or "").strip(),
                description=form.description.data,
                discovered_on=form.discovered_on.data or date.today(),
                impact=RiskImpact(form.impact.data),
                chance=RiskChance(form.chance.data),
                treatment=RiskTreatmentOption(form.treatment.data),
                treatment_plan=form.treatment_plan.data,
                treatment_due_date=form.treatment_due_date.data,
                treatment_owner_id=optional_int(form.treatment_owner_id.data),
                ticket_url=(form.ticket_url.data or "").strip() or None,
            )
            if risk.discovered_on is None:
                risk.discovered_on = date.today()
            risk.components = components
            risk.controls = controls or []
            _apply_residual_fields(form, risk)
            set_impact_areas(risk, form.impact_areas.data or [])
            db.session.add(risk)
            db.session.flush()
            # Persist plural ticket links (US4)
            links_data = _parse_ticket_links_from_form(request.form)
            if links_data:
                set_ticket_links(risk, links_data)
            elif risk.ticket_url:
                # Backfill legacy scalar ticket_url as a single link
                set_ticket_links(risk, [{"label": "Ticket", "url": risk.ticket_url, "sort_order": 0}])
            log_event(
                action="risk_created",
                entity_type="risk",
                entity_id=risk.id,
                details={
                    "title": risk.title,
                    "impact": risk.impact.value,
                    "chance": risk.chance.value,
                    "treatment": risk.treatment.value,
                    **_residual_audit_details(risk),
                },
            )
            db.session.commit()
            flash(_("Risk \"{title}\" created successfully.").format(title=risk.title), "success")
            return redirect(url_for("risk.dashboard"))

    if request.method == "POST":
        _flash_form_errors(form)

    return render_template(
        "risk/form.html",
        form=form,
        risk=None,
        component_choices_available=component_choices_available,
        form_mode="create",
        score=None,
        severity=None,
        RiskTreatmentOption=RiskTreatmentOption,
    )


@bp.route("/<int:risk_id>/edit", methods=["GET", "POST"])
@login_required
def edit(risk_id: int):
    """Edit an existing risk record."""

    _require_risk_access()
    risk = _risk_query().filter(Risk.id == risk_id).first()
    if risk is None:
        abort(404)

    # Threat-linked risks are a projection of their scenario: re-sync on every
    # visit and keep the sync-owned fields read-only (decision 20261118-0830).
    from ..threat.models import ThreatScenario
    from ..threat.services import sync_scenario_to_risk
    linked_scenario = ThreatScenario.query.filter_by(risk_id=risk_id).first()
    if linked_scenario:
        sync_scenario_to_risk(linked_scenario)
        db.session.commit()

    form = RiskForm(obj=risk)
    _threat_scope_id = linked_scenario.threat_model.context_scope_id if linked_scenario and linked_scenario.threat_model else None
    configure_risk_form(form, extra_components=list(risk.components), context_scope_id=_threat_scope_id)
    form.submit.label.text = _("Save changes")
    if linked_scenario:
        form.mark_managed_by_threat()
    component_choices_available = bool(form.component_ids.choices) or linked_scenario is not None

    if request.method == "GET":
        form.component_ids.data = [str(component.id) for component in risk.components]
        form.impact_areas.data = [link.area.value for link in risk.impact_area_links]
        form.treatment_owner_id.data = "" if risk.treatment_owner_id is None else str(risk.treatment_owner_id)
        form.csa_control_ids.data = [str(control.id) for control in risk.controls]
        form.impact.data = risk.impact.value
        form.chance.data = risk.chance.value
        form.treatment.data = risk.treatment.value
        form.mitigated.data = risk.is_mitigated
        form.residual_impact.data = risk.residual_impact.value if risk.residual_impact else ""
        form.residual_chance.data = risk.residual_chance.value if risk.residual_chance else ""
        form.ticket_url.data = risk.ticket_url or ""
        # Pre-fill template context variable for existing ticket links
        # (rendered by the Jinja template using risk.ticket_links)

    if form.validate_on_submit():
        if linked_scenario:
            # Sync-owned fields are ignored; the scenario stays the source of truth.
            components, controls = list(risk.components), list(risk.controls)
        else:
            components = _resolve_components_for_edit(form)
            controls = _resolve_controls(form)
        if components is not None and controls is not None:
            if not linked_scenario:
                risk.title = (form.title.data or "").strip()
                risk.description = form.description.data
                risk.impact = RiskImpact(form.impact.data)
                risk.chance = RiskChance(form.chance.data)
                risk.treatment = RiskTreatmentOption(form.treatment.data)
                risk.components = components
                risk.controls = controls or []
                _apply_residual_fields(form, risk)
            risk.discovered_on = form.discovered_on.data or risk.discovered_on
            risk.treatment_plan = form.treatment_plan.data
            risk.treatment_due_date = form.treatment_due_date.data
            risk.treatment_owner_id = optional_int(form.treatment_owner_id.data)
            risk.ticket_url = (form.ticket_url.data or "").strip() or None
            set_impact_areas(risk, form.impact_areas.data or [])
            # Persist plural ticket links (US4)
            links_data = _parse_ticket_links_from_form(request.form)
            if links_data:
                set_ticket_links(risk, links_data)
            elif not risk.ticket_links and risk.ticket_url:
                # Backfill legacy scalar when no plural links saved yet
                set_ticket_links(risk, [{"label": "Ticket", "url": risk.ticket_url, "sort_order": 0}])
            db.session.flush()
            log_event(
                action="risk_updated",
                entity_type="risk",
                entity_id=risk.id,
                details={
                    "title": risk.title,
                    "impact": risk.impact.value,
                    "chance": risk.chance.value,
                    "treatment": risk.treatment.value,
                    **_residual_audit_details(risk),
                },
            )
            db.session.commit()
            flash(_("Risk \"{title}\" updated.").format(title=risk.title), "success")
            return redirect(url_for("risk.edit", risk_id=risk.id))

    if request.method == "POST":
        _flash_form_errors(form)

    thresholds = load_thresholds()
    score = risk.actual_score()
    severity = determine_severity(score, thresholds)
    linked_scenario_url = (
        url_for(
            "threat.scenario_detail",
            model_id=linked_scenario.threat_model_id,
            scenario_id=linked_scenario.id,
        )
        if linked_scenario and "threat.scenario_detail" in current_app.view_functions
        else None
    )

    return render_template(
        "risk/form.html",
        form=form,
        risk=risk,
        component_choices_available=component_choices_available,
        form_mode="edit",
        score=score,
        severity=severity,
        linked_scenario=linked_scenario,
        linked_scenario_url=linked_scenario_url,
        RiskTreatmentOption=RiskTreatmentOption,
        approval=_approval_panel(risk),
    )


def _approval_panel(risk: Risk) -> dict:
    """Context for the approval panel on the edit page (decisions 20261118-1048, -1058)."""

    from ...models.audit import AuditLog

    is_owner = risk.treatment_owner_id is not None and risk.treatment_owner_id == current_user.id
    panel = {
        "state": risk.approval_state,
        "is_owner": is_owner,
        "decided_by": _display_name(risk.approval_decided_by) if risk.approval_status else None,
        "form": RiskApprovalForm(formdata=None, fingerprint=risk.approval_fingerprint()) if is_owner else None,
        "previous_rejection": None,
    }
    if risk.approval_status is None:
        entry = (
            AuditLog.query.filter_by(event_type="risk_rejected", target_type="risk", target_id=str(risk.id))
            .order_by(AuditLog.id.desc())
            .first()
        )
        if entry is not None:
            panel["previous_rejection"] = {
                "by": _display_name(entry.actor) if entry.actor else (entry.actor_name or _display_name(None)),
                "at": entry.created_at,
                "comment": (entry.payload or {}).get("comment"),
            }
    return panel


def _display_name(user) -> str:
    return user.full_name if user is not None else _("risk.approval.unknown_user")


@bp.route("/<int:risk_id>/close", methods=["POST"])
@login_required
def close(risk_id: int):
    """Archive a risk while keeping it on record."""

    _require_risk_access()
    form = RiskActionForm()
    if not form.validate_on_submit():
        flash(_("risk.flash.invalid_request"), "danger")
        return redirect(request.referrer or url_for("risk.dashboard"))

    risk = db.session.get(Risk, risk_id)
    if risk is None:
        abort(404)
    if risk.is_closed:
        flash(_("risk.flash.already_archived"), "info")
        return redirect(request.referrer or url_for("risk.dashboard"))

    risk.closed_at = datetime.utcnow()
    db.session.add(risk)
    db.session.flush()
    log_event(
        action="risk_closed",
        entity_type="risk",
        entity_id=risk.id,
        details={"title": risk.title},
    )
    db.session.commit()
    flash(_("risk.flash.archived").format(title=risk.title), "success")
    return redirect(request.referrer or url_for("risk.dashboard"))


@bp.route("/<int:risk_id>/reopen", methods=["POST"])
@login_required
def reopen(risk_id: int):
    """Reopen an archived risk."""

    _require_risk_access()
    form = RiskActionForm()
    if not form.validate_on_submit():
        flash(_("risk.flash.invalid_request"), "danger")
        return redirect(request.referrer or url_for("risk.dashboard"))

    risk = db.session.get(Risk, risk_id)
    if risk is None:
        abort(404)
    if not risk.is_closed:
        flash(_("risk.flash.already_open"), "info")
        return redirect(request.referrer or url_for("risk.dashboard"))

    risk.closed_at = None
    db.session.add(risk)
    db.session.flush()
    log_event(
        action="risk_reopened",
        entity_type="risk",
        entity_id=risk.id,
        details={"title": risk.title},
    )
    db.session.commit()
    flash(_("risk.flash.reopened").format(title=risk.title), "success")
    return redirect(request.referrer or url_for("risk.dashboard"))


@bp.route("/<int:risk_id>/approve", methods=["POST"])
@login_required
def approve(risk_id: int):
    """Record the owner's approval of the risk and its treatment."""

    return _decide(risk_id, RiskApprovalStatus.APPROVED)


@bp.route("/<int:risk_id>/reject", methods=["POST"])
@login_required
def reject(risk_id: int):
    """Record the owner's rejection; a comment is required."""

    return _decide(risk_id, RiskApprovalStatus.REJECTED)


def _decide(risk_id: int, status: RiskApprovalStatus):
    """Owner decision (decisions 20261118-1046, -1058).

    404 for an unknown risk, then 403 unless the current user is the risk's
    owner (admins are not exempt). Any state can be decided, so a decision can
    be flipped or repeated; each one is a new decision and audit event.
    """

    _require_risk_access()
    risk = db.session.get(Risk, risk_id)
    if risk is None:
        abort(404)
    if risk.treatment_owner_id is None or risk.treatment_owner_id != current_user.id:
        abort(403)

    edit_url = url_for("risk.edit", risk_id=risk.id)
    form = RiskApprovalForm()
    if not form.validate_on_submit():
        flash(_("risk.flash.invalid_request"), "danger")
        return redirect(edit_url)
    if form.fingerprint.data != risk.approval_fingerprint():
        flash(_("risk.flash.approval_stale"), "warning")
        return redirect(edit_url)
    comment = (form.comment.data or "").strip() or None
    if status is RiskApprovalStatus.REJECTED and comment is None:
        flash(_("risk.flash.approval_comment_required"), "danger")
        return redirect(edit_url)

    risk.approval_status = status
    risk.approval_decided_at = datetime.now(UTC)
    risk.approval_decided_by_id = current_user.id
    risk.approval_comment = comment
    severity = risk.determine_actual_severity()
    log_event(
        action=f"risk_{status.value}",
        entity_type="risk",
        entity_id=risk.id,
        details={
            "decision": status.value,
            "comment": comment,
            "chance": risk.chance.value,
            "impact": risk.impact.value,
            "treatment": risk.treatment.value,
            "residual_chance": risk.residual_chance.value if risk.residual_chance else None,
            "residual_impact": risk.residual_impact.value if risk.residual_impact else None,
            "mitigated": risk.is_mitigated,
            "actual_score": risk.actual_score(),
            "actual_severity": severity.value if severity else None,
            "fingerprint": risk.approval_fingerprint(),
        },
    )
    db.session.commit()
    message = _("risk.flash.approved") if status is RiskApprovalStatus.APPROVED else _("risk.flash.rejected")
    flash(message.format(title=risk.title), "success")
    return redirect(edit_url)


@bp.route("/<int:risk_id>/delete", methods=["POST"])
@login_required
def delete(risk_id: int):
    """Permanently remove a risk record."""

    _require_risk_access()
    form = RiskActionForm()
    if not form.validate_on_submit():
        flash(_("risk.flash.invalid_request"), "danger")
        return redirect(request.referrer or url_for("risk.dashboard"))

    risk = db.session.get(Risk, risk_id)
    if risk is None:
        abort(404)
    title = risk.title
    risk_id_value = risk.id
    db.session.delete(risk)
    db.session.flush()
    log_event(
        action="risk_deleted",
        entity_type="risk",
        entity_id=risk_id_value,
        details={"title": title},
    )
    db.session.commit()
    flash(_("risk.flash.deleted").format(title=title), "success")
    return redirect(url_for("risk.dashboard"))


def _build_dashboard_cards(risks: list[Risk], thresholds) -> list[dict[str, object]]:
    today = date.today()
    cards: list[dict[str, object]] = []

    # Build a lookup of Risk.id → PASTA source info (avoids N+1 queries)
    try:
        from ..threat.models import PastaRiskConclusion
        pasta_conclusions = PastaRiskConclusion.query.options(
            sa.orm.joinedload(PastaRiskConclusion.finding).joinedload("stage_record")
        ).filter(
            PastaRiskConclusion.published_risk_id.in_([r.id for r in risks])
        ).all()
        pasta_by_risk_id: dict[int, PastaRiskConclusion] = {
            c.published_risk_id: c for c in pasta_conclusions
        }
    except Exception:  # threat module may not be loaded in all configurations
        pasta_by_risk_id = {}

    for risk in risks:
        # Actual score: residual when mitigated, initial otherwise (decision 20261118-0802).
        score = risk.actual_score()
        severity = determine_severity(score, thresholds)
        due_date = risk.treatment_due_date
        status = _risk_status(risk, today)
        components = [
            _component_snapshot(component)
            for component in sorted(
                risk.components,
                key=lambda item: (
                    (item.context_scope.name if item.context_scope else ""),
                    (item.name or "").lower(),
                ),
            )
        ]
        impact_areas = sorted(link.area.value for link in risk.impact_area_links)
        controls = [
            {
                "id": control.id,
                "domain": control.domain,
                "section": control.section,
                "description": control.description,
            }
            for control in sorted(
                risk.controls,
                key=lambda entry: (
                    (entry.domain or ""),
                    (entry.section or ""),
                ),
            )
        ]
        cards.append(
            {
                "id": risk.id,
                "title": risk.title,
                "description": risk.description,
                "score": score,
                "severity": severity,
                "severity_class": _SEVERITY_BADGES.get(severity, _DEFAULT_PILL),
                "initial_score": risk.score(),
                "residual_score": risk.residual_score(),
                "is_mitigated": risk.is_mitigated,
                "approval_state": risk.approval_state,
                "impact": risk.actual_impact,
                "impact_weight": IMPACT_WEIGHTS[risk.actual_impact],
                "chance": risk.actual_chance,
                "chance_weight": CHANCE_WEIGHTS[risk.actual_chance],
                "treatment": risk.treatment,
                "treatment_plan": risk.treatment_plan,
                "treatment_due_date": due_date,
                "status": status,
                "status_class": _STATUS_BADGES.get(status, _DEFAULT_PILL),
                "is_overdue": status == "overdue",
                "is_closed": risk.is_closed,
                "closed_at": risk.closed_at,
                "owner": risk.treatment_owner,
                "components": components,
                "component_count": len(components),
                "impact_areas": impact_areas,
                "impact_area_count": len(impact_areas),
                "controls": controls,
                "control_count": len(controls),
                "primary_control": controls[0] if controls else None,
                "discovered_on": risk.discovered_on,
                "updated_at": risk.updated_at,
                "ticket_url": risk.ticket_url,
                "pasta_origin": pasta_by_risk_id.get(risk.id),
            }
        )
    return cards


def _component_snapshot(component: Component) -> dict[str, object]:
    return {
        "id": component.id,
        "context_scope_id": component.context_scope_id,
        "name": component.name or _("Untitled component"),
        "context": component.context_scope.name if component.context_scope else None,
    }


def _risk_status(risk: Risk, today: date) -> str:
    if risk.is_closed:
        return "archived"
    due_date = risk.treatment_due_date
    if due_date is None:
        return "unscheduled"
    if due_date < today:
        return "overdue"
    return "scheduled"


def _dashboard_metrics(
    cards: list[dict[str, object]],
    bia_ids: Sequence[int] = (),
) -> dict[str, object]:
    # Under a BIA filter, only components of the selected BIAs count as impacted.
    component_ids = {
        component["id"]
        for card in cards
        for component in card["components"]
        if component.get("id") is not None
        and (not bia_ids or component.get("context_scope_id") in bia_ids)
    }
    return {
        "total": len(cards),
        "high": sum(
            1
            for card in cards
            if card["severity"] in {RiskSeverity.HIGH, RiskSeverity.CRITICAL}
        ),
        "mitigate": sum(1 for card in cards if card["treatment"] == RiskTreatmentOption.MITIGATE),
        "overdue": sum(1 for card in cards if card["is_overdue"]),
        "components": len(component_ids),
        "recent_update": max(
            (card["updated_at"] for card in cards if card.get("updated_at")),
            default=None,
        ),
    }


_MATRIX_IMPACT_AXIS = [
    RiskImpact.INSIGNIFICANT,
    RiskImpact.MINOR,
    RiskImpact.MODERATE,
    RiskImpact.MAJOR,
    RiskImpact.CATASTROPHIC,
]

_MATRIX_CHANCE_AXIS = [
    RiskChance.ALMOST_CERTAIN,
    RiskChance.LIKELY,
    RiskChance.POSSIBLE,
    RiskChance.UNLIKELY,
    RiskChance.RARE,
]

_MATRIX_CELL_CLASSES = {
    RiskSeverity.CRITICAL: "risk-matrix-cell--critical",
    RiskSeverity.HIGH: "risk-matrix-cell--high",
    RiskSeverity.MODERATE: "risk-matrix-cell--moderate",
    RiskSeverity.LOW: "risk-matrix-cell--low",
}

_MATRIX_CHIP_CLASSES = {
    RiskSeverity.CRITICAL: "risk-matrix-chip--critical",
    RiskSeverity.HIGH: "risk-matrix-chip--high",
    RiskSeverity.MODERATE: "risk-matrix-chip--moderate",
    RiskSeverity.LOW: "risk-matrix-chip--low",
}

_MATRIX_PILL_CLASSES = {
    RiskSeverity.CRITICAL: "risk-matrix-pill--critical",
    RiskSeverity.HIGH: "risk-matrix-pill--high",
    RiskSeverity.MODERATE: "risk-matrix-pill--moderate",
    RiskSeverity.LOW: "risk-matrix-pill--low",
}

_DEFAULT_MATRIX_CELL_CLASS = "risk-matrix-cell--neutral"
_DEFAULT_MATRIX_CHIP_CLASS = "risk-matrix-chip--neutral"
_DEFAULT_MATRIX_PILL_CLASS = "risk-matrix-pill--neutral"


@dataclass
class MatrixRisk:
    id: int
    title: str
    severity: RiskSeverity | None
    score: int
    url: str


@dataclass
class MatrixCell:
    score: int
    severity: RiskSeverity | None
    risks: list[MatrixRisk]

_SEVERITY_ORDER = [
    RiskSeverity.LOW,
    RiskSeverity.MODERATE,
    RiskSeverity.HIGH,
    RiskSeverity.CRITICAL,
]


def _matrix_cell_class(severity: RiskSeverity | None) -> str:
    if severity is None:
        return _DEFAULT_MATRIX_CELL_CLASS
    return _MATRIX_CELL_CLASSES.get(severity, _DEFAULT_MATRIX_CELL_CLASS)


def _matrix_chip_class(severity: RiskSeverity | None) -> str:
    if severity is None:
        return _DEFAULT_MATRIX_CHIP_CLASS
    return _MATRIX_CHIP_CLASSES.get(severity, _DEFAULT_MATRIX_CHIP_CLASS)


def _matrix_pill_class(severity: RiskSeverity) -> str:
    return _MATRIX_PILL_CLASSES.get(severity, _DEFAULT_MATRIX_PILL_CLASS)


def _build_risk_matrix(
    risks: list[Risk],
    thresholds: Sequence[RiskSeverityThreshold],
) -> dict[str, object]:
    lookup: dict[tuple[RiskChance, RiskImpact], MatrixCell] = {}
    for chance in _MATRIX_CHANCE_AXIS:
        for impact in _MATRIX_IMPACT_AXIS:
            combo_score = IMPACT_WEIGHTS[impact] * CHANCE_WEIGHTS[chance]
            lookup[(chance, impact)] = MatrixCell(
                score=combo_score,
                severity=determine_severity(combo_score, thresholds),
                risks=[],
            )

    for risk in risks:
        cell = lookup[(risk.actual_chance, risk.actual_impact)]
        severity = determine_severity(risk.actual_score(), thresholds)
        cell.risks.append(
            MatrixRisk(
                id=risk.id,
                title=risk.title,
                severity=severity,
                score=risk.actual_score(),
                url=url_for("risk.edit", risk_id=risk.id),
            )
        )

    rows: list[dict[str, object]] = []
    for chance in _MATRIX_CHANCE_AXIS:
        cells: list[dict[str, object]] = []
        for impact in _MATRIX_IMPACT_AXIS:
            cell_data = lookup[(chance, impact)]
            risks_sorted = sorted(cell_data.risks, key=lambda entry: entry.score, reverse=True)
            cells.append(
                {
                    "impact": impact,
                    "score": cell_data.score,
                    "severity": cell_data.severity,
                    "severity_class": _matrix_cell_class(cell_data.severity),
                    "risks": [
                        {
                            "id": risk_entry.id,
                            "title": risk_entry.title,
                            "severity": risk_entry.severity,
                            "score": risk_entry.score,
                            "url": risk_entry.url,
                            "severity_class": _matrix_chip_class(risk_entry.severity),
                        }
                        for risk_entry in risks_sorted[:3]
                    ],
                    "extra_count": max(len(risks_sorted) - 3, 0),
                    "total": len(risks_sorted),
                }
            )
        rows.append({"chance": chance, "cells": cells})

    return {
        "impact_axis": _MATRIX_IMPACT_AXIS,
        "chance_axis": _MATRIX_CHANCE_AXIS,
        "rows": rows,
    }


def _severity_scale(thresholds: Sequence[RiskSeverityThreshold]) -> list[dict[str, object]]:
    ordered = sorted(
        thresholds,
        key=lambda entry: _SEVERITY_ORDER.index(entry.severity) if entry.severity in _SEVERITY_ORDER else len(_SEVERITY_ORDER),
    )
    return [
        {
            "severity": entry.severity,
            "label": _(f"risk.severity.{entry.severity.value}"),
            "min_score": entry.min_score,
            "max_score": entry.max_score,
            "class": _matrix_pill_class(entry.severity),
        }
        for entry in ordered
    ]
