"""Routes for the System Security Plan module."""

from __future__ import annotations

import re
import unicodedata
from datetime import date

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...core.audit import log_event
from ...extensions import db
from ..bia.models import ContextScope
from . import bp
from .forms import POAMItemForm, POAMMilestoneForm, SSPControlEntryForm, SSPEditForm, SSPInterconnectionForm
from .models import FipsRating, POAMItem, POAMMilestone, POAMStatus, SSPControlEntry, SSPInterconnection, SSPlan
from ..bia.utils import get_cia_impact
from ..bia.routes import _load_export_css, _send_export_response
from .services import build_environment_summary, seed_controls, seed_interconnections


def _safe_filename(name: str) -> str:
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    name = re.sub(r"[^\w\s-]", "", name).strip().lower()
    return re.sub(r"[-\s]+", "_", name)


def _get_ssp_or_404(ssp_id: int) -> SSPlan:
    ssp = SSPlan.query.get_or_404(ssp_id)
    return ssp


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------


@bp.route("/")
@login_required
def index():
    """List all SSPs."""
    ssps = (
        SSPlan.query
        .join(ContextScope)
        .filter(ContextScope.is_archived == False)  # noqa: E712
        .order_by(ContextScope.name)
        .all()
    )
    # Also list scopes that don't yet have an SSP
    scopes_without_ssp = (
        ContextScope.query
        .filter(ContextScope.is_archived == False, ContextScope.ssp == None)  # noqa: E711 E712
        .order_by(ContextScope.name)
        .all()
    )
    return render_template(
        "ssp/index.html",
        ssps=ssps,
        scopes_without_ssp=scopes_without_ssp,
    )


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


@bp.route("/create/<int:context_scope_id>", methods=["POST"])
@login_required
def create(context_scope_id: int):
    """Create an SSP for a ContextScope."""
    context = ContextScope.query.get_or_404(context_scope_id)

    if context.ssp is not None:
        flash("An SSP already exists for this system.", "warning")
        return redirect(url_for("ssp.view", ssp_id=context.ssp.id))

    ssp = SSPlan(
        context_scope_id=context.id,
        created_by_id=current_user.id,
    )
    db.session.add(ssp)
    db.session.flush()  # Get ssp.id before seeding

    seed_interconnections(ssp)
    seed_controls(ssp)

    log_event(
        action="ssp_created",
        entity_type="ssp_plan",
        entity_id=ssp.id,
        details={"context_scope_id": context.id, "context_scope_name": context.name},
    )
    db.session.commit()
    flash("System Security Plan created.", "success")
    return redirect(url_for("ssp.view", ssp_id=ssp.id))


# ---------------------------------------------------------------------------
# View
# ---------------------------------------------------------------------------


@bp.route("/<int:ssp_id>")
@login_required
def view(ssp_id: int):
    """Full NIST SP 800-18 SSP view."""
    ssp = _get_ssp_or_404(ssp_id)
    context = ssp.context_scope

    # Derive C/I/A impact ratings from BIA consequences
    all_consequences = []
    for component in context.components:
        all_consequences.extend(component.consequences)
    effective_cia = {
        prop: get_cia_impact(all_consequences, prop)
        for prop in ("confidentiality", "integrity", "availability")
    }

    env_summary = build_environment_summary(context)

    # Group control entries by control domain
    from itertools import groupby
    control_entries_sorted = sorted(
        ssp.control_entries,
        key=lambda e: (e.control.section or "", e.control.domain),
    )
    controls_by_domain: dict[str, list] = {}
    for entry in control_entries_sorted:
        domain = entry.control.section or "Other"
        controls_by_domain.setdefault(domain, []).append(entry)

    # Risk severity summary
    from ..risk.models import RiskSeverityThreshold
    thresholds = RiskSeverityThreshold.query.order_by(RiskSeverityThreshold.min_score).all()
    risk_summary: dict[str, int] = {}
    for component in context.components:
        for risk in component.risks:
            if risk.is_closed:
                continue
            sev = risk.determine_severity(thresholds)
            key = sev.value if sev else "unknown"
            risk_summary[key] = risk_summary.get(key, 0) + 1

    # DPIA check
    has_dpia = any(comp.dpia_assessments for comp in context.components)

    return render_template(
        "ssp/view.html",
        ssp=ssp,
        context=context,
        effective_cia=effective_cia,
        env_summary=env_summary,
        controls_by_domain=controls_by_domain,
        risk_summary=risk_summary,
        has_dpia=has_dpia,
    )


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------


@bp.route("/<int:ssp_id>/edit", methods=["GET", "POST"])
@login_required
def edit(ssp_id: int):
    """Edit SSP metadata."""
    ssp = _get_ssp_or_404(ssp_id)
    form = SSPEditForm(obj=ssp)

    if form.validate_on_submit():
        ssp.laws_regulations = form.laws_regulations.data
        ssp.authorization_boundary = form.authorization_boundary.data
        ssp.fips_confidentiality = FipsRating(form.fips_confidentiality.data)
        ssp.fips_integrity = FipsRating(form.fips_integrity.data)
        ssp.fips_availability = FipsRating(form.fips_availability.data)
        ssp.plan_completion_date = form.plan_completion_date.data
        ssp.plan_approval_date = form.plan_approval_date.data
        ssp.monitoring_kpis_kris = form.monitoring_kpis_kris.data or None
        ssp.monitoring_what = form.monitoring_what.data or None
        ssp.monitoring_who = form.monitoring_who.data or None
        ssp.monitoring_tools = form.monitoring_tools.data or None
        ssp.monitoring_frequency = form.monitoring_frequency.data or None

        log_event(
            action="ssp_updated",
            entity_type="ssp_plan",
            entity_id=ssp.id,
            details={"context_scope_id": ssp.context_scope_id},
        )
        db.session.commit()
        flash("SSP updated.", "success")
        return redirect(url_for("ssp.view", ssp_id=ssp.id))

    # Pre-fill enum select values
    if request.method == "GET":
        form.fips_confidentiality.data = ssp.fips_confidentiality.value if ssp.fips_confidentiality else "not_set"
        form.fips_integrity.data = ssp.fips_integrity.value if ssp.fips_integrity else "not_set"
        form.fips_availability.data = ssp.fips_availability.value if ssp.fips_availability else "not_set"

    return render_template("ssp/edit.html", ssp=ssp, form=form)


# ---------------------------------------------------------------------------
# Interconnections
# ---------------------------------------------------------------------------


@bp.route("/<int:ssp_id>/interconnections", methods=["GET", "POST"])
@login_required
def interconnections(ssp_id: int):
    """Manage system interconnection entries."""
    ssp = _get_ssp_or_404(ssp_id)
    form = SSPInterconnectionForm()

    if form.validate_on_submit():
        entry = SSPInterconnection(
            ssp_id=ssp.id,
            system_name=form.system_name.data,
            owning_organization=form.owning_organization.data,
            agreement_type=form.agreement_type.data,
            data_direction=form.data_direction.data,
            security_contact=form.security_contact.data,
            notes=form.notes.data,
            sort_order=len(ssp.interconnections),
        )
        db.session.add(entry)
        db.session.commit()
        flash("Interconnection added.", "success")
        return redirect(url_for("ssp.interconnections", ssp_id=ssp.id))

    return render_template("ssp/interconnections.html", ssp=ssp, form=form)


@bp.route("/<int:ssp_id>/interconnections/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit_interconnection(ssp_id: int, entry_id: int):
    """Edit a single interconnection entry."""
    ssp = _get_ssp_or_404(ssp_id)
    entry = SSPInterconnection.query.filter_by(id=entry_id, ssp_id=ssp.id).first_or_404()
    form = SSPInterconnectionForm(obj=entry)

    if form.validate_on_submit():
        entry.system_name = form.system_name.data
        entry.owning_organization = form.owning_organization.data
        entry.agreement_type = form.agreement_type.data
        entry.data_direction = form.data_direction.data
        entry.security_contact = form.security_contact.data
        entry.notes = form.notes.data
        db.session.commit()
        flash("Interconnection updated.", "success")
        return redirect(url_for("ssp.interconnections", ssp_id=ssp.id))

    if request.method == "GET":
        form.agreement_type.data = entry.agreement_type.value if entry.agreement_type else "none"
        form.data_direction.data = entry.data_direction.value if entry.data_direction else "bidirectional"

    return render_template("ssp/edit_interconnection.html", ssp=ssp, entry=entry, form=form)


@bp.route("/<int:ssp_id>/interconnections/<int:entry_id>/delete", methods=["POST"])
@login_required
def delete_interconnection(ssp_id: int, entry_id: int):
    """Delete a single interconnection entry."""
    ssp = _get_ssp_or_404(ssp_id)
    entry = SSPInterconnection.query.filter_by(id=entry_id, ssp_id=ssp.id).first_or_404()
    db.session.delete(entry)
    db.session.commit()
    flash("Interconnection removed.", "success")
    return redirect(url_for("ssp.interconnections", ssp_id=ssp.id))


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------


@bp.route("/<int:ssp_id>/controls")
@login_required
def controls(ssp_id: int):
    """Review Section 14 control entries."""
    ssp = _get_ssp_or_404(ssp_id)
    entries_sorted = sorted(
        ssp.control_entries,
        key=lambda e: (e.control.section or "", e.control.domain),
    )
    controls_by_domain: dict[str, list] = {}
    for entry in entries_sorted:
        domain = entry.control.section or "Other"
        controls_by_domain.setdefault(domain, []).append(entry)

    return render_template("ssp/controls.html", ssp=ssp, controls_by_domain=controls_by_domain)


@bp.route("/<int:ssp_id>/controls/<int:entry_id>/edit", methods=["GET", "POST"])
@login_required
def edit_control_entry(ssp_id: int, entry_id: int):
    """Edit a single control entry."""
    ssp = _get_ssp_or_404(ssp_id)
    entry = SSPControlEntry.query.filter_by(id=entry_id, ssp_id=ssp.id).first_or_404()
    form = SSPControlEntryForm(obj=entry)

    if form.validate_on_submit():
        entry.implementation_status = form.implementation_status.data
        entry.responsible_entity = form.responsible_entity.data
        entry.implementation_statement = form.implementation_statement.data
        db.session.commit()
        flash("Control entry updated.", "success")
        return redirect(url_for("ssp.controls", ssp_id=ssp.id))

    if request.method == "GET":
        form.implementation_status.data = entry.implementation_status.value if entry.implementation_status else "planned"

    return render_template("ssp/edit_control_entry.html", ssp=ssp, entry=entry, form=form)


@bp.route("/<int:ssp_id>/controls/add", methods=["GET", "POST"])
@login_required
def add_control_entry(ssp_id: int):
    """Manually add a control to the SSP."""
    from ..csa.models import Control

    ssp = _get_ssp_or_404(ssp_id)
    existing_ids = {e.control_id for e in ssp.control_entries}
    if existing_ids:
        available_controls = Control.query.filter(
            ~Control.id.in_(existing_ids)
        ).order_by(Control.section, Control.domain).all()
    else:
        available_controls = Control.query.order_by(Control.section, Control.domain).all()

    if request.method == "POST":
        control_id = request.form.get("control_id", type=int)
        if not control_id:
            abort(400)
        control = Control.query.get_or_404(control_id)
        entry = SSPControlEntry(
            ssp_id=ssp.id,
            control_id=control.id,
            source="manual",
        )
        db.session.add(entry)
        db.session.commit()
        flash(f"Control '{control.domain}' added.", "success")
        return redirect(url_for("ssp.controls", ssp_id=ssp.id))

    return render_template("ssp/add_control.html", ssp=ssp, available_controls=available_controls)


# ---------------------------------------------------------------------------
# PDF Export
# ---------------------------------------------------------------------------


@bp.route("/<int:ssp_id>/export/pdf")
@login_required
def export_pdf(ssp_id: int):
    """Stream SSP as a PDF download."""
    ssp = _get_ssp_or_404(ssp_id)
    context = ssp.context_scope

    all_consequences = []
    for component in context.components:
        all_consequences.extend(component.consequences)
    effective_cia = {
        prop: get_cia_impact(all_consequences, prop)
        for prop in ("confidentiality", "integrity", "availability")
    }

    env_summary = build_environment_summary(context)

    control_entries_sorted = sorted(
        ssp.control_entries,
        key=lambda e: (e.control.section or "", e.control.domain),
    )
    controls_by_domain: dict[str, list] = {}
    for entry in control_entries_sorted:
        domain = entry.control.section or "Other"
        controls_by_domain.setdefault(domain, []).append(entry)

    from ..risk.models import RiskSeverityThreshold
    thresholds = RiskSeverityThreshold.query.order_by(RiskSeverityThreshold.min_score).all()
    risk_summary: dict[str, int] = {}
    for component in context.components:
        for risk in component.risks:
            if risk.is_closed:
                continue
            sev = risk.determine_severity(thresholds)
            key = sev.value if sev else "unknown"
            risk_summary[key] = risk_summary.get(key, 0) + 1

    has_dpia = any(comp.dpia_assessments for comp in context.components)

    html_content = render_template(
        "ssp/print.html",
        ssp=ssp,
        context=context,
        effective_cia=effective_cia,
        env_summary=env_summary,
        controls_by_domain=controls_by_domain,
        risk_summary=risk_summary,
        has_dpia=has_dpia,
        export_mode=True,
        export_css=_load_export_css(),
    )

    abbr = context.abbreviation or _safe_filename(context.name)
    filename = f"SSP_{abbr}_{date.today().isoformat()}.html"

    return _send_export_response(html_content, filename)


# ---------------------------------------------------------------------------
# Plan of Action & Milestones (POA&M)
# ---------------------------------------------------------------------------


@bp.route("/<int:ssp_id>/poam")
@login_required
def poam(ssp_id: int):
    """List all POA&M items for an SSP."""
    ssp = _get_ssp_or_404(ssp_id)
    return render_template("ssp/poam.html", ssp=ssp, context=ssp.context_scope)


@bp.route("/<int:ssp_id>/poam/add", methods=["GET", "POST"])
@login_required
def add_poam_item(ssp_id: int):
    """Create a new POA&M item."""
    ssp = _get_ssp_or_404(ssp_id)
    form = POAMItemForm()
    if form.validate_on_submit():
        item = POAMItem(
            ssp_id=ssp.id,
            weakness_description=form.weakness_description.data,
            resources_required=form.resources_required.data or None,
            point_of_contact=form.point_of_contact.data or None,
            scheduled_completion=form.scheduled_completion.data,
            estimated_cost=form.estimated_cost.data or None,
            status=POAMStatus(form.status.data),
        )
        db.session.add(item)
        db.session.commit()
        log_event("poam_item_created", resource_type="SSPlan", resource_id=ssp.id)
        flash("POA&M item added.", "success")
        return redirect(url_for("ssp.poam", ssp_id=ssp.id))
    return render_template("ssp/poam_item_form.html", ssp=ssp, context=ssp.context_scope, form=form, item=None)


@bp.route("/<int:ssp_id>/poam/<int:item_id>/edit", methods=["GET", "POST"])
@login_required
def edit_poam_item(ssp_id: int, item_id: int):
    """Edit a POA&M item and manage its milestones."""
    ssp = _get_ssp_or_404(ssp_id)
    item = POAMItem.query.filter_by(id=item_id, ssp_id=ssp.id).first_or_404()
    form = POAMItemForm(obj=item)
    milestone_form = POAMMilestoneForm(prefix="ms")
    if request.method == "GET":
        form.status.data = item.status.value if item.status else "open"
    if form.validate_on_submit() and "save_item" in request.form:
        item.weakness_description = form.weakness_description.data
        item.resources_required = form.resources_required.data or None
        item.point_of_contact = form.point_of_contact.data or None
        item.scheduled_completion = form.scheduled_completion.data
        item.estimated_cost = form.estimated_cost.data or None
        item.status = POAMStatus(form.status.data)
        db.session.commit()
        log_event("poam_item_updated", resource_type="SSPlan", resource_id=ssp.id)
        flash("POA&M item updated.", "success")
        return redirect(url_for("ssp.edit_poam_item", ssp_id=ssp.id, item_id=item.id))
    if milestone_form.validate_on_submit() and "add_milestone" in request.form:
        ms = POAMMilestone(
            item_id=item.id,
            description=milestone_form.description.data,
            scheduled_date=milestone_form.scheduled_date.data,
            completed_date=milestone_form.completed_date.data,
        )
        db.session.add(ms)
        db.session.commit()
        flash("Milestone added.", "success")
        return redirect(url_for("ssp.edit_poam_item", ssp_id=ssp.id, item_id=item.id))
    return render_template(
        "ssp/poam_item_form.html",
        ssp=ssp,
        context=ssp.context_scope,
        form=form,
        item=item,
        milestone_form=milestone_form,
    )


@bp.route("/<int:ssp_id>/poam/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_poam_item(ssp_id: int, item_id: int):
    """Delete a POA&M item."""
    ssp = _get_ssp_or_404(ssp_id)
    item = POAMItem.query.filter_by(id=item_id, ssp_id=ssp.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    log_event("poam_item_deleted", resource_type="SSPlan", resource_id=ssp.id)
    flash("POA&M item deleted.", "success")
    return redirect(url_for("ssp.poam", ssp_id=ssp.id))


@bp.route("/<int:ssp_id>/delete", methods=["POST"])
@login_required
def delete(ssp_id: int):
    """Delete an SSP entirely, returning the system to 'no SSP' state."""
    ssp = _get_ssp_or_404(ssp_id)
    context_name = ssp.context_scope.name
    db.session.delete(ssp)
    db.session.commit()
    log_event("ssp.deleted", entity_type="SSPlan", entity_id=ssp_id, details={"name": context_name})
    flash(f"SSP '{context_name}' has been deleted.", "success")
    return redirect(url_for("ssp.index"))


@bp.route("/<int:ssp_id>/poam/<int:item_id>/milestones/<int:ms_id>/delete", methods=["POST"])
@login_required
def delete_poam_milestone(ssp_id: int, item_id: int, ms_id: int):
    """Delete a single milestone from a POA&M item."""
    ssp = _get_ssp_or_404(ssp_id)
    item = POAMItem.query.filter_by(id=item_id, ssp_id=ssp.id).first_or_404()
    ms = POAMMilestone.query.filter_by(id=ms_id, item_id=item.id).first_or_404()
    db.session.delete(ms)
    db.session.commit()
    flash("Milestone removed.", "success")
    return redirect(url_for("ssp.edit_poam_item", ssp_id=ssp.id, item_id=item.id))
