"""Frontend routes powering the risk workspace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Sequence

import sqlalchemy as sa
from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...core.audit import log_event
from ...core.i18n import gettext as _
from ...extensions import db
from ..bia.models import Component
from ..csa.models import Control
from ..identity.models import ROLE_ADMIN, ROLE_ASSESSMENT_MANAGER
from .forms import RiskForm, RiskActionForm
from .models import (
    CHANCE_WEIGHTS,
    IMPACT_WEIGHTS,
    Risk,
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
    if not (current_user.has_role(ROLE_ADMIN) or current_user.has_role(ROLE_ASSESSMENT_MANAGER)):
        abort(403)


def _risk_query():
    return Risk.query.options(
        sa.orm.selectinload(Risk.components).selectinload(Component.context_scope),
        sa.orm.selectinload(Risk.impact_area_links),
        sa.orm.selectinload(Risk.controls),
        sa.orm.selectinload(Risk.treatment_owner),
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


@bp.route("/")
@login_required
def dashboard():
    """Show a human-friendly overview of every registered risk."""

    _require_risk_access()
    thresholds = load_thresholds()
    risks = _risk_query().order_by(Risk.created_at.desc()).all()
    cards = _build_dashboard_cards(risks, thresholds)
    metrics = _dashboard_metrics(cards)
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
    )


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
            set_impact_areas(risk, form.impact_areas.data or [])
            db.session.add(risk)
            db.session.flush()
            log_event(
                action="risk_created",
                entity_type="risk",
                entity_id=risk.id,
                details={
                    "title": risk.title,
                    "impact": risk.impact.value,
                    "chance": risk.chance.value,
                    "treatment": risk.treatment.value,
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

    form = RiskForm(obj=risk)
    configure_risk_form(form, extra_components=list(risk.components))
    form.submit.label.text = _("Save changes")
    component_choices_available = bool(form.component_ids.choices)

    if request.method == "GET":
        form.component_ids.data = [str(component.id) for component in risk.components]
        form.impact_areas.data = [link.area.value for link in risk.impact_area_links]
        form.treatment_owner_id.data = "" if risk.treatment_owner_id is None else str(risk.treatment_owner_id)
        form.csa_control_ids.data = [str(control.id) for control in risk.controls]
        form.impact.data = risk.impact.value
        form.chance.data = risk.chance.value
        form.treatment.data = risk.treatment.value
        form.ticket_url.data = risk.ticket_url or ""

    if form.validate_on_submit():
        components = _resolve_components(form)
        controls = _resolve_controls(form)
        if components and controls is not None:
            risk.title = (form.title.data or "").strip()
            risk.description = form.description.data
            risk.discovered_on = form.discovered_on.data or risk.discovered_on
            risk.impact = RiskImpact(form.impact.data)
            risk.chance = RiskChance(form.chance.data)
            risk.treatment = RiskTreatmentOption(form.treatment.data)
            risk.treatment_plan = form.treatment_plan.data
            risk.treatment_due_date = form.treatment_due_date.data
            risk.treatment_owner_id = optional_int(form.treatment_owner_id.data)
            risk.ticket_url = (form.ticket_url.data or "").strip() or None
            risk.components = components
            risk.controls = controls or []
            set_impact_areas(risk, form.impact_areas.data or [])
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
                },
            )
            db.session.commit()
            flash(_("Risk \"{title}\" updated.").format(title=risk.title), "success")
            return redirect(url_for("risk.edit", risk_id=risk.id))

    if request.method == "POST":
        _flash_form_errors(form)

    thresholds = load_thresholds()
    score = risk.score()
    severity = determine_severity(score, thresholds)

    return render_template(
        "risk/form.html",
        form=form,
        risk=risk,
        component_choices_available=component_choices_available,
        form_mode="edit",
        score=score,
        severity=severity,
        RiskTreatmentOption=RiskTreatmentOption,
    )


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
    for risk in risks:
        score = risk.score()
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
                "impact": risk.impact,
                "impact_weight": IMPACT_WEIGHTS[risk.impact],
                "chance": risk.chance,
                "chance_weight": CHANCE_WEIGHTS[risk.chance],
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
            }
        )
    return cards


def _component_snapshot(component: Component) -> dict[str, object]:
    return {
        "id": component.id,
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


def _dashboard_metrics(cards: list[dict[str, object]]) -> dict[str, object]:
    component_ids = {
        component["id"]
        for card in cards
        for component in card["components"]
        if component.get("id") is not None
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
        cell = lookup[(risk.chance, risk.impact)]
        severity = determine_severity(risk.score(), thresholds)
        cell.risks.append(
            MatrixRisk(
                id=risk.id,
                title=risk.title,
                severity=severity,
                score=risk.score(),
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
