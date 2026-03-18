"""Routes for the threat modeling module."""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from flask import (
    Blueprint,
    abort,
    flash,
    make_response,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from ...core.audit import log_event
from ...core.i18n import gettext as _
from ...extensions import db
from ..bia.models import Component as BiaComponent, ContextScope
from ..csa.models import Control
from ..identity.models import ROLE_ADMIN, ROLE_ASSESSMENT_MANAGER
from .forms import ThreatModelAssetForm, ThreatModelForm, ThreatScenarioForm
from .models import (
    AssetType,
    RiskLevel,
    ScenarioStatus,
    StrideCategory,
    ThreatModel,
    ThreatModelAsset,
    ThreatScenario,
    TreatmentOption,
)
from .services import apply_residual_risk_score, apply_risk_score, export_scenarios_csv, user_choices

bp = Blueprint(
    "threat",
    __name__,
    url_prefix="/threat",
    template_folder="templates",
)


def _require_access() -> None:
    if not current_user.is_authenticated:
        abort(403)
    if not (current_user.has_role(ROLE_ADMIN) or current_user.has_role(ROLE_ASSESSMENT_MANAGER)):
        abort(403)


def _get_model_or_404(model_id: int) -> ThreatModel:
    return ThreatModel.query.get_or_404(model_id)


def _configure_scenario_form(form: ThreatScenarioForm, threat_model: ThreatModel) -> None:
    asset_choices = [("", "— none —")] + [
        (str(a.id), a.name) for a in threat_model.assets
    ]
    form.asset_id.choices = asset_choices
    form.owner_id.choices = user_choices()
    control_choices = [
        (str(c.id), f"{c.domain}")
        for c in Control.query.order_by(Control.domain).all()
    ]
    form.csa_control_ids.choices = control_choices


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


@bp.route("/")
@login_required
def dashboard():
    _require_access()
    models = (
        ThreatModel.query.filter_by(is_archived=False)
        .options(sa.orm.selectinload(ThreatModel.scenarios))
        .order_by(ThreatModel.created_at.desc())
        .all()
    )
    return render_template("threat/dashboard.html", models=models)


# ---------------------------------------------------------------------------
# ThreatModel CRUD
# ---------------------------------------------------------------------------


def _bia_choices() -> list[tuple[str, str]]:
    """Return (id, name) choices for active BIAs, prefixed with a blank option."""
    scopes = (
        ContextScope.query.filter_by(is_archived=False)
        .order_by(ContextScope.name)
        .all()
    )
    return [("" , "— standalone (no BIA) —")] + [(str(s.id), s.name) for s in scopes]


@bp.route("/new", methods=["GET", "POST"])
@login_required
def model_new():
    _require_access()
    form = ThreatModelForm()
    form.bia_id.choices = _bia_choices()
    if form.validate_on_submit():
        model = ThreatModel(
            title=(form.title.data or "").strip(),
            description=form.description.data,
            scope=form.scope.data,
            owner_id=current_user.id,
        )
        db.session.add(model)
        db.session.flush()
        # ------------------------------------------------------------------
        # If a BIA was selected, pre-populate assets from its components.
        # ------------------------------------------------------------------
        bia_id = form.bia_id.data
        if bia_id:
            components = (
                BiaComponent.query
                .filter_by(context_scope_id=int(bia_id))
                .order_by(BiaComponent.name)
                .all()
            )
            for idx, comp in enumerate(components):
                asset = ThreatModelAsset(
                    threat_model_id=model.id,
                    name=comp.name,
                    asset_type=AssetType.COMPONENT,
                    description=comp.description or "",
                    order=idx,
                )
                db.session.add(asset)
        log_event(
            action="threat_model_created",
            entity_type="threat_model",
            entity_id=model.id,
            details={"title": model.title, "bia_id": bia_id or None},
        )
        db.session.commit()
        flash(_("threat.flash.created"), "success")
        return redirect(url_for("threat.model_detail", model_id=model.id))
    return render_template("threat/model_form.html", form=form, model=None)


@bp.route("/<int:model_id>")
@login_required
def model_detail(model_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    scenarios_by_category: dict[str, list[ThreatScenario]] = {}
    for cat in StrideCategory:
        scenarios_by_category[cat.value] = [
            s for s in model.scenarios if s.stride_category == cat
        ]
    return render_template(
        "threat/model_detail.html",
        model=model,
        scenarios_by_category=scenarios_by_category,
        StrideCategory=StrideCategory,
        RiskLevel=RiskLevel,
        ScenarioStatus=ScenarioStatus,
    )


@bp.route("/<int:model_id>/edit", methods=["GET", "POST"])
@login_required
def model_edit(model_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    form = ThreatModelForm(obj=model)
    if form.validate_on_submit():
        model.title = (form.title.data or "").strip()
        model.description = form.description.data
        model.scope = form.scope.data
        log_event(
            action="threat_model_updated",
            entity_type="threat_model",
            entity_id=model.id,
            details={"title": model.title},
        )
        db.session.commit()
        flash(_("threat.flash.updated"), "success")
        return redirect(url_for("threat.model_detail", model_id=model.id))
    return render_template("threat/model_form.html", form=form, model=model)


@bp.route("/<int:model_id>/archive", methods=["POST"])
@login_required
def model_archive(model_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    model.is_archived = not model.is_archived
    model.archived_at = datetime.now(UTC) if model.is_archived else None
    log_event(
        action="threat_model_archived" if model.is_archived else "threat_model_unarchived",
        entity_type="threat_model",
        entity_id=model.id,
        details={"title": model.title},
    )
    db.session.commit()
    flash(_("threat.flash.archived") if model.is_archived else _("threat.flash.unarchived"), "info")
    return redirect(url_for("threat.dashboard"))


# ---------------------------------------------------------------------------
# Asset CRUD
# ---------------------------------------------------------------------------


@bp.route("/<int:model_id>/assets/new", methods=["GET", "POST"])
@login_required
def asset_new(model_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    form = ThreatModelAssetForm()
    if form.validate_on_submit():
        asset = ThreatModelAsset(
            threat_model_id=model.id,
            name=(form.name.data or "").strip(),
            asset_type=AssetType(form.asset_type.data),
            description=form.description.data,
            order=form.order.data or 0,
        )
        db.session.add(asset)
        db.session.flush()
        log_event(
            action="threat_asset_created",
            entity_type="threat_model_asset",
            entity_id=asset.id,
            details={"name": asset.name, "model_id": model.id},
        )
        db.session.commit()
        flash(_("threat.flash.asset_created"), "success")
        return redirect(url_for("threat.model_detail", model_id=model.id))
    return render_template("threat/asset_form.html", form=form, model=model, asset=None)


@bp.route("/<int:model_id>/assets/<int:asset_id>/edit", methods=["GET", "POST"])
@login_required
def asset_edit(model_id: int, asset_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    asset = ThreatModelAsset.query.get_or_404(asset_id)
    if asset.threat_model_id != model.id:
        abort(404)
    form = ThreatModelAssetForm(obj=asset)
    if form.validate_on_submit():
        asset.name = (form.name.data or "").strip()
        asset.asset_type = AssetType(form.asset_type.data)
        asset.description = form.description.data
        asset.order = form.order.data or 0
        log_event(
            action="threat_asset_updated",
            entity_type="threat_model_asset",
            entity_id=asset.id,
            details={"name": asset.name},
        )
        db.session.commit()
        flash(_("threat.flash.asset_updated"), "success")
        return redirect(url_for("threat.model_detail", model_id=model.id))
    return render_template("threat/asset_form.html", form=form, model=model, asset=asset)


@bp.route("/<int:model_id>/assets/<int:asset_id>/delete", methods=["POST"])
@login_required
def asset_delete(model_id: int, asset_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    asset = ThreatModelAsset.query.get_or_404(asset_id)
    if asset.threat_model_id != model.id:
        abort(404)
    db.session.delete(asset)
    log_event(
        action="threat_asset_deleted",
        entity_type="threat_model_asset",
        entity_id=asset_id,
        details={"name": asset.name, "model_id": model.id},
    )
    db.session.commit()
    flash(_("threat.flash.asset_deleted"), "info")
    return redirect(url_for("threat.model_detail", model_id=model.id))


# ---------------------------------------------------------------------------
# Scenario CRUD
# ---------------------------------------------------------------------------


@bp.route("/<int:model_id>/scenarios/new", methods=["GET", "POST"])
@login_required
def scenario_new(model_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    form = ThreatScenarioForm()
    _configure_scenario_form(form, model)
    if form.validate_on_submit():
        cia = _build_cia(form)
        scenario = ThreatScenario(
            threat_model_id=model.id,
            asset_id=int(form.asset_id.data) if form.asset_id.data else None,
            stride_category=StrideCategory(form.stride_category.data),
            title=(form.title.data or "").strip(),
            description=form.description.data,
            threat_actor=(form.threat_actor.data or "").strip() or None,
            attack_vector=form.attack_vector.data,
            preconditions=form.preconditions.data,
            impact_description=form.impact_description.data,
            affected_cia=cia or None,
            likelihood=int(form.likelihood.data),
            impact_score=int(form.impact_score.data),
            treatment=TreatmentOption(form.treatment.data) if form.treatment.data else None,
            residual_likelihood=int(form.residual_likelihood.data) if form.residual_likelihood.data else None,
            residual_impact=int(form.residual_impact.data) if form.residual_impact.data else None,
            status=ScenarioStatus(form.status.data),
            owner_id=int(form.owner_id.data) if form.owner_id.data else None,
        )
        apply_risk_score(scenario)
        apply_residual_risk_score(scenario)
        _attach_controls(scenario, form)
        db.session.add(scenario)
        db.session.flush()
        log_event(
            action="threat_scenario_created",
            entity_type="threat_scenario",
            entity_id=scenario.id,
            details={"title": scenario.title, "model_id": model.id},
        )
        db.session.commit()
        flash(_("threat.flash.scenario_created"), "success")
        return redirect(url_for("threat.model_detail", model_id=model.id))
    return render_template("threat/scenario_form.html", form=form, model=model, scenario=None)


@bp.route("/<int:model_id>/scenarios/<int:scenario_id>")
@login_required
def scenario_detail(model_id: int, scenario_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    scenario = ThreatScenario.query.get_or_404(scenario_id)
    if scenario.threat_model_id != model.id:
        abort(404)
    return render_template(
        "threat/scenario_detail.html",
        model=model,
        scenario=scenario,
        RiskLevel=RiskLevel,
        ScenarioStatus=ScenarioStatus,
    )


@bp.route("/<int:model_id>/scenarios/<int:scenario_id>/edit", methods=["GET", "POST"])
@login_required
def scenario_edit(model_id: int, scenario_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    scenario = ThreatScenario.query.get_or_404(scenario_id)
    if scenario.threat_model_id != model.id:
        abort(404)
    form = ThreatScenarioForm(obj=scenario)
    _configure_scenario_form(form, model)
    if request.method == "GET":
        # Pre-fill CIA checkboxes and enum fields
        form.stride_category.data = scenario.stride_category.value if scenario.stride_category else None
        form.treatment.data = scenario.treatment.value if scenario.treatment else ""
        form.status.data = scenario.status.value if scenario.status else None
        form.asset_id.data = str(scenario.asset_id) if scenario.asset_id else ""
        form.owner_id.data = str(scenario.owner_id) if scenario.owner_id else ""
        form.csa_control_ids.data = [str(c.id) for c in scenario.controls]
        form.residual_likelihood.data = str(scenario.residual_likelihood) if scenario.residual_likelihood else ""
        form.residual_impact.data = str(scenario.residual_impact) if scenario.residual_impact else ""
        cia = scenario.affected_cia or ""
        form.cia_c.data = "C" in cia
        form.cia_i.data = "I" in cia
        form.cia_a.data = "A" in cia
    if form.validate_on_submit():
        cia = _build_cia(form)
        scenario.stride_category = StrideCategory(form.stride_category.data)
        scenario.asset_id = int(form.asset_id.data) if form.asset_id.data else None
        scenario.title = (form.title.data or "").strip()
        scenario.description = form.description.data
        scenario.threat_actor = (form.threat_actor.data or "").strip() or None
        scenario.attack_vector = form.attack_vector.data
        scenario.preconditions = form.preconditions.data
        scenario.impact_description = form.impact_description.data
        scenario.affected_cia = cia or None
        scenario.likelihood = int(form.likelihood.data)
        scenario.impact_score = int(form.impact_score.data)
        scenario.treatment = TreatmentOption(form.treatment.data) if form.treatment.data else None
        scenario.residual_likelihood = int(form.residual_likelihood.data) if form.residual_likelihood.data else None
        scenario.residual_impact = int(form.residual_impact.data) if form.residual_impact.data else None
        scenario.status = ScenarioStatus(form.status.data)
        scenario.owner_id = int(form.owner_id.data) if form.owner_id.data else None
        apply_risk_score(scenario)
        apply_residual_risk_score(scenario)
        _attach_controls(scenario, form)
        log_event(
            action="threat_scenario_updated",
            entity_type="threat_scenario",
            entity_id=scenario.id,
            details={"title": scenario.title},
        )
        db.session.commit()
        flash(_("threat.flash.scenario_updated"), "success")
        return redirect(url_for("threat.scenario_detail", model_id=model.id, scenario_id=scenario.id))
    return render_template("threat/scenario_form.html", form=form, model=model, scenario=scenario)


@bp.route("/<int:model_id>/scenarios/<int:scenario_id>/delete", methods=["POST"])
@login_required
def scenario_delete(model_id: int, scenario_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    scenario = ThreatScenario.query.get_or_404(scenario_id)
    if scenario.threat_model_id != model.id:
        abort(404)
    db.session.delete(scenario)
    log_event(
        action="threat_scenario_deleted",
        entity_type="threat_scenario",
        entity_id=scenario_id,
        details={"title": scenario.title, "model_id": model.id},
    )
    db.session.commit()
    flash(_("threat.flash.scenario_deleted"), "info")
    return redirect(url_for("threat.model_detail", model_id=model.id))


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------


@bp.route("/<int:model_id>/export/csv")
@login_required
def export_csv(model_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    csv_data = export_scenarios_csv(model.scenarios)
    response = make_response(csv_data)
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    slug = model.title.lower().replace(" ", "_")[:40]
    response.headers["Content-Disposition"] = (
        f'attachment; filename="threat_model_{model.id}_{slug}.csv"'
    )
    return response


@bp.route("/<int:model_id>/export/html")
@login_required
def export_html(model_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    theme = "dark" if not (current_user.is_authenticated and current_user.theme_preference == "light") else "light"
    html = render_template(
        "threat/export_report.html",
        model=model,
        export_mode=True,
        theme=theme,
        StrideCategory=StrideCategory,
        RiskLevel=RiskLevel,
        ScenarioStatus=ScenarioStatus,
    )
    response = make_response(html)
    response.headers["Content-Type"] = "text/html; charset=utf-8"
    slug = model.title.lower().replace(" ", "_")[:40]
    response.headers["Content-Disposition"] = (
        f'attachment; filename="threat_model_{model.id}_{slug}.html"'
    )
    return response


@bp.route("/<int:model_id>/export/pdf")
@login_required
def export_pdf(model_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    theme = "dark" if not (current_user.is_authenticated and current_user.theme_preference == "light") else "light"
    html = render_template(
        "threat/export_report.html",
        model=model,
        export_mode=True,
        theme=theme,
        StrideCategory=StrideCategory,
        RiskLevel=RiskLevel,
        ScenarioStatus=ScenarioStatus,
    )
    from ...core.pdf_export import html_to_pdf_bytes

    pdf_bytes = html_to_pdf_bytes(html)
    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    slug = model.title.lower().replace(" ", "_")[:40]
    response.headers["Content-Disposition"] = (
        f'attachment; filename="threat_model_{model.id}_{slug}.pdf"'
    )
    return response


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_cia(form: ThreatScenarioForm) -> str:
    cia = ""
    if form.cia_c.data:
        cia += "C"
    if form.cia_i.data:
        cia += "I"
    if form.cia_a.data:
        cia += "A"
    return cia


def _attach_controls(scenario: ThreatScenario, form: ThreatScenarioForm) -> None:
    selected_ids = [int(v) for v in (form.csa_control_ids.data or []) if v]
    if selected_ids:
        controls = Control.query.filter(Control.id.in_(selected_ids)).all()
    else:
        controls = []
    scenario.controls = controls
