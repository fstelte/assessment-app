"""Routes for the threat modeling module."""

from __future__ import annotations

from datetime import UTC, datetime

import sqlalchemy as sa
from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
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
from .forms import (
    ThreatLibraryEntryForm,
    ThreatMitigationActionForm,
    ThreatModelAssetForm,
    ThreatModelForm,
    ThreatProductForm,
    ThreatScenarioForm,
)
from .models import (
    AssetType,
    MitigationStatus,
    RiskLevel,
    ScenarioStatus,
    StrideCategory,
    ThreatFramework,
    ThreatLibraryEntry,
    ThreatMitigationAction,
    ThreatModel,
    ThreatModelAsset,
    ThreatProduct,
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
    # Aggregated cross-model stats
    stats = {
        "total": db.session.query(sa.func.count(ThreatScenario.id))
            .filter(ThreatScenario.is_archived == False)  # noqa: E712
            .scalar() or 0,
        "by_level": db.session.query(ThreatScenario.risk_level, sa.func.count(ThreatScenario.id))
            .filter(ThreatScenario.is_archived == False)  # noqa: E712
            .group_by(ThreatScenario.risk_level)
            .all(),
        "by_status": db.session.query(ThreatScenario.status, sa.func.count(ThreatScenario.id))
            .filter(ThreatScenario.is_archived == False)  # noqa: E712
            .group_by(ThreatScenario.status)
            .all(),
        "open_critical": db.session.query(sa.func.count(ThreatScenario.id))
            .filter(
                ThreatScenario.is_archived == False,  # noqa: E712
                ThreatScenario.risk_level == RiskLevel.CRITICAL,
                ThreatScenario.status != ScenarioStatus.CLOSED,
            )
            .scalar() or 0,
    }
    all_scenarios = (
        ThreatScenario.query
        .filter(ThreatScenario.is_archived == False)  # noqa: E712
        .options(
            sa.orm.joinedload(ThreatScenario.threat_model),
            sa.orm.joinedload(ThreatScenario.asset),
        )
        .order_by(ThreatScenario.risk_score.desc())
        .limit(100)
        .all()
    )
    return render_template(
        "threat/dashboard.html",
        models=models,
        stats=stats,
        all_scenarios=all_scenarios,
        RiskLevel=RiskLevel,
        ScenarioStatus=ScenarioStatus,
    )


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
        stride_cat_value = form.stride_category.data or "spoofing"
        scenario = ThreatScenario(
            threat_model_id=model.id,
            asset_id=int(form.asset_id.data) if form.asset_id.data else None,
            stride_category=StrideCategory(stride_cat_value),
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
            library_entry_id=int(form.library_entry_id.data) if form.library_entry_id.data else None,
            methodology=form.methodology.data or "STRIDE",
            pasta_stage=form.pasta_stage.data or None,
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
        form.library_entry_id.data = str(scenario.library_entry_id) if scenario.library_entry_id else ""
        form.methodology.data = scenario.methodology or "STRIDE"
        form.pasta_stage.data = scenario.pasta_stage or ""
        cia = scenario.affected_cia or ""
        form.cia_c.data = "C" in cia
        form.cia_i.data = "I" in cia
        form.cia_a.data = "A" in cia
    if form.validate_on_submit():
        cia = _build_cia(form)
        stride_cat_value = form.stride_category.data or "spoofing"
        scenario.stride_category = StrideCategory(stride_cat_value)
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
        scenario.library_entry_id = int(form.library_entry_id.data) if form.library_entry_id.data else None
        scenario.methodology = form.methodology.data or "STRIDE"
        scenario.pasta_stage = form.pasta_stage.data or None
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
    log_event(
        action="threat_model.exported",
        entity_type="threat_model",
        entity_id=model.id,
        details={"format": "csv", "title": model.title},
    )
    db.session.commit()
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
    log_event(
        action="threat_model.exported",
        entity_type="threat_model",
        entity_id=model.id,
        details={"format": "html", "title": model.title},
    )
    db.session.commit()
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
    log_event(
        action="threat_model.exported",
        entity_type="threat_model",
        entity_id=model.id,
        details={"format": "pdf", "title": model.title},
    )
    db.session.commit()
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


# ---------------------------------------------------------------------------
# New-from-library scenario shortcut
# ---------------------------------------------------------------------------


@bp.route("/<int:model_id>/scenarios/new-from-library/<int:entry_id>", methods=["GET"])
@login_required
def scenario_new_from_library(model_id: int, entry_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    entry = ThreatLibraryEntry.query.get_or_404(entry_id)
    form = ThreatScenarioForm()
    _configure_scenario_form(form, model)
    # Pre-fill from library entry
    form.title.data = entry.name
    form.description.data = entry.description or ""
    form.mitigation.data = entry.suggested_mitigation or ""
    form.library_entry_id.data = str(entry.id)
    if entry.stride_hint:
        form.stride_category.data = entry.stride_hint
    if entry.framework and entry.framework.name == "PASTA":
        form.methodology.data = "PASTA"
        form.pasta_stage.data = entry.category or ""
    elif entry.framework and "LINDDUN" in entry.framework.name:
        form.methodology.data = "LINDDUN"
    elif entry.framework and "OWASP" in entry.framework.name:
        form.methodology.data = "OWASP"
    return render_template("threat/scenario_form.html", form=form, model=model, scenario=None)


# ---------------------------------------------------------------------------
# Threat Library
# ---------------------------------------------------------------------------


@bp.route("/library/")
@login_required
def library_index():
    _require_access()
    frameworks = ThreatFramework.query.order_by(ThreatFramework.name).all()
    return render_template("threat/library/index.html", frameworks=frameworks)


@bp.route("/library/<int:fw_id>/")
@login_required
def library_entries(fw_id: int):
    _require_access()
    framework = ThreatFramework.query.get_or_404(fw_id)
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", "").strip()
    query = ThreatLibraryEntry.query.filter_by(framework_id=fw_id)
    if q:
        query = query.filter(
            ThreatLibraryEntry.name.ilike(f"%{q}%") | ThreatLibraryEntry.description.ilike(f"%{q}%")
        )
    if cat:
        query = query.filter_by(category=cat)
    entries = query.order_by(ThreatLibraryEntry.category, ThreatLibraryEntry.name).all()
    categories = (
        db.session.query(ThreatLibraryEntry.category)
        .filter_by(framework_id=fw_id)
        .distinct()
        .order_by(ThreatLibraryEntry.category)
        .all()
    )
    categories = [c[0] for c in categories if c[0]]
    return render_template(
        "threat/library/entries.html",
        framework=framework,
        entries=entries,
        categories=categories,
        q=q,
        selected_cat=cat,
    )


@bp.route("/library/<int:fw_id>/new", methods=["GET", "POST"])
@login_required
def library_entry_new(fw_id: int):
    _require_access()
    framework = ThreatFramework.query.get_or_404(fw_id)
    form = ThreatLibraryEntryForm()
    if form.validate_on_submit():
        entry = ThreatLibraryEntry(
            framework_id=fw_id,
            name=(form.name.data or "").strip(),
            category=(form.category.data or "").strip() or None,
            description=form.description.data,
            suggested_mitigation=form.suggested_mitigation.data,
            is_custom=True,
            created_by_id=current_user.id,
        )
        db.session.add(entry)
        db.session.flush()
        log_event(
            action="threat_library_entry_created",
            entity_type="threat_library_entry",
            entity_id=entry.id,
            details={"name": entry.name, "framework": framework.name},
        )
        db.session.commit()
        flash(_("threat.library.flash.entry_created"), "success")
        return redirect(url_for("threat.library_entries", fw_id=fw_id))
    return render_template("threat/library/entry_form.html", form=form, framework=framework, entry=None)


@bp.route("/library/entries/<int:eid>/edit", methods=["GET", "POST"])
@login_required
def library_entry_edit(eid: int):
    _require_access()
    entry = ThreatLibraryEntry.query.get_or_404(eid)
    if not entry.is_custom:
        abort(403)
    if entry.created_by_id != current_user.id and not current_user.has_role(ROLE_ADMIN):
        abort(403)
    form = ThreatLibraryEntryForm(obj=entry)
    if form.validate_on_submit():
        entry.name = (form.name.data or "").strip()
        entry.category = (form.category.data or "").strip() or None
        entry.description = form.description.data
        entry.suggested_mitigation = form.suggested_mitigation.data
        log_event(
            action="threat_library_entry_updated",
            entity_type="threat_library_entry",
            entity_id=entry.id,
            details={"name": entry.name},
        )
        db.session.commit()
        flash(_("threat.library.flash.entry_updated"), "success")
        return redirect(url_for("threat.library_entries", fw_id=entry.framework_id))
    return render_template("threat/library/entry_form.html", form=form, framework=entry.framework, entry=entry)


@bp.route("/library/entries/<int:eid>/delete", methods=["POST"])
@login_required
def library_entry_delete(eid: int):
    _require_access()
    entry = ThreatLibraryEntry.query.get_or_404(eid)
    if not entry.is_custom:
        abort(403)
    if entry.created_by_id != current_user.id and not current_user.has_role(ROLE_ADMIN):
        abort(403)
    fw_id = entry.framework_id
    db.session.delete(entry)
    log_event(
        action="threat_library_entry_deleted",
        entity_type="threat_library_entry",
        entity_id=eid,
        details={"name": entry.name},
    )
    db.session.commit()
    flash(_("threat.library.flash.entry_deleted"), "info")
    return redirect(url_for("threat.library_entries", fw_id=fw_id))


@bp.route("/library/entries/<int:eid>/json")
@login_required
def library_entry_json(eid: int):
    _require_access()
    entry = ThreatLibraryEntry.query.get_or_404(eid)
    return jsonify({
        "id": entry.id,
        "name": entry.name,
        "description": entry.description or "",
        "category": entry.category or "",
        "suggested_mitigation": entry.suggested_mitigation or "",
        "stride_hint": entry.stride_hint or "",
        "framework_name": entry.framework.name if entry.framework else "",
    })


# ---------------------------------------------------------------------------
# Threat Products
# ---------------------------------------------------------------------------


@bp.route("/products/")
@login_required
def product_list():
    _require_access()
    products = (
        ThreatProduct.query
        .options(sa.orm.selectinload(ThreatProduct.models))
        .order_by(ThreatProduct.name)
        .all()
    )
    return render_template("threat/products/index.html", products=products)


@bp.route("/products/new", methods=["GET", "POST"])
@login_required
def product_new():
    _require_access()
    form = ThreatProductForm()
    form.owner_id.choices = user_choices()
    if form.validate_on_submit():
        product = ThreatProduct(
            name=(form.name.data or "").strip(),
            description=form.description.data,
            owner_id=int(form.owner_id.data) if form.owner_id.data else None,
        )
        db.session.add(product)
        db.session.flush()
        log_event(
            action="threat_product_created",
            entity_type="threat_product",
            entity_id=product.id,
            details={"name": product.name},
        )
        db.session.commit()
        flash(_("threat.product.flash.created"), "success")
        return redirect(url_for("threat.product_detail", product_id=product.id))
    return render_template("threat/products/form.html", form=form, product=None)


@bp.route("/products/<int:product_id>/")
@login_required
def product_detail(product_id: int):
    _require_access()
    product = ThreatProduct.query.get_or_404(product_id)
    models = (
        ThreatModel.query
        .filter_by(product_id=product_id, is_archived=False)
        .options(sa.orm.selectinload(ThreatModel.scenarios))
        .order_by(ThreatModel.created_at.desc())
        .all()
    )
    unlinked_models = (
        ThreatModel.query
        .filter_by(product_id=None, is_archived=False)
        .order_by(ThreatModel.title)
        .all()
    )
    return render_template(
        "threat/products/detail.html",
        product=product,
        models=models,
        unlinked_models=unlinked_models,
        RiskLevel=RiskLevel,
    )


@bp.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def product_edit(product_id: int):
    _require_access()
    product = ThreatProduct.query.get_or_404(product_id)
    form = ThreatProductForm(obj=product)
    form.owner_id.choices = user_choices()
    if request.method == "GET":
        form.owner_id.data = str(product.owner_id) if product.owner_id else ""
    if form.validate_on_submit():
        product.name = (form.name.data or "").strip()
        product.description = form.description.data
        product.owner_id = int(form.owner_id.data) if form.owner_id.data else None
        log_event(
            action="threat_product_updated",
            entity_type="threat_product",
            entity_id=product.id,
            details={"name": product.name},
        )
        db.session.commit()
        flash(_("threat.product.flash.updated"), "success")
        return redirect(url_for("threat.product_detail", product_id=product.id))
    return render_template("threat/products/form.html", form=form, product=product)


@bp.route("/products/<int:product_id>/archive", methods=["POST"])
@login_required
def product_archive(product_id: int):
    _require_access()
    product = ThreatProduct.query.get_or_404(product_id)
    product.is_archived = not product.is_archived
    log_event(
        action="threat_product_archived" if product.is_archived else "threat_product_unarchived",
        entity_type="threat_product",
        entity_id=product.id,
        details={"name": product.name},
    )
    db.session.commit()
    flash(_("threat.product.flash.archived") if product.is_archived else _("threat.product.flash.unarchived"), "info")
    return redirect(url_for("threat.product_list"))


@bp.route("/products/<int:product_id>/add-model/<int:model_id>", methods=["POST"])
@login_required
def product_add_model(product_id: int, model_id: int):
    _require_access()
    ThreatProduct.query.get_or_404(product_id)
    model = ThreatModel.query.get_or_404(model_id)
    model.product_id = product_id
    db.session.commit()
    flash(_("threat.product.flash.model_added"), "success")
    return redirect(url_for("threat.product_detail", product_id=product_id))


# ---------------------------------------------------------------------------
# Mitigation Actions
# ---------------------------------------------------------------------------


@bp.route("/<int:model_id>/scenarios/<int:scenario_id>/mitigations/new", methods=["GET", "POST"])
@login_required
def mitigation_new(model_id: int, scenario_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    scenario = ThreatScenario.query.get_or_404(scenario_id)
    if scenario.threat_model_id != model.id:
        abort(404)
    form = ThreatMitigationActionForm()
    form.assigned_to_id.choices = user_choices()
    if form.validate_on_submit():
        action = ThreatMitigationAction(
            scenario_id=scenario.id,
            title=(form.title.data or "").strip(),
            description=form.description.data,
            status=MitigationStatus(form.status.data),
            assigned_to_id=int(form.assigned_to_id.data) if form.assigned_to_id.data else None,
            due_date=form.due_date.data,
            notes=form.notes.data,
        )
        db.session.add(action)
        db.session.flush()
        log_event(
            action="threat_mitigation_created",
            entity_type="threat_mitigation_action",
            entity_id=action.id,
            details={"title": action.title, "scenario_id": scenario.id},
        )
        db.session.commit()
        flash(_("threat.mitigation.flash.created"), "success")
        return redirect(url_for("threat.scenario_detail", model_id=model.id, scenario_id=scenario.id))
    return render_template(
        "threat/mitigation_form.html",
        form=form,
        model=model,
        scenario=scenario,
        action=None,
    )


@bp.route("/<int:model_id>/scenarios/<int:scenario_id>/mitigations/<int:action_id>/edit", methods=["GET", "POST"])
@login_required
def mitigation_edit(model_id: int, scenario_id: int, action_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    scenario = ThreatScenario.query.get_or_404(scenario_id)
    if scenario.threat_model_id != model.id:
        abort(404)
    action = ThreatMitigationAction.query.get_or_404(action_id)
    if action.scenario_id != scenario.id:
        abort(404)
    form = ThreatMitigationActionForm(obj=action)
    form.assigned_to_id.choices = user_choices()
    if request.method == "GET":
        form.status.data = action.status.value
        form.assigned_to_id.data = str(action.assigned_to_id) if action.assigned_to_id else ""
    if form.validate_on_submit():
        action.title = (form.title.data or "").strip()
        action.description = form.description.data
        action.status = MitigationStatus(form.status.data)
        action.assigned_to_id = int(form.assigned_to_id.data) if form.assigned_to_id.data else None
        action.due_date = form.due_date.data
        action.notes = form.notes.data
        log_event(
            action="threat_mitigation_updated",
            entity_type="threat_mitigation_action",
            entity_id=action.id,
            details={"title": action.title},
        )
        db.session.commit()
        flash(_("threat.mitigation.flash.updated"), "success")
        return redirect(url_for("threat.scenario_detail", model_id=model.id, scenario_id=scenario.id))
    return render_template(
        "threat/mitigation_form.html",
        form=form,
        model=model,
        scenario=scenario,
        action=action,
    )


@bp.route("/<int:model_id>/scenarios/<int:scenario_id>/mitigations/<int:action_id>/delete", methods=["POST"])
@login_required
def mitigation_delete(model_id: int, scenario_id: int, action_id: int):
    _require_access()
    model = _get_model_or_404(model_id)
    scenario = ThreatScenario.query.get_or_404(scenario_id)
    if scenario.threat_model_id != model.id:
        abort(404)
    action = ThreatMitigationAction.query.get_or_404(action_id)
    if action.scenario_id != scenario.id:
        abort(404)
    db.session.delete(action)
    log_event(
        action="threat_mitigation_deleted",
        entity_type="threat_mitigation_action",
        entity_id=action_id,
        details={"title": action.title, "scenario_id": scenario.id},
    )
    db.session.commit()
    flash(_("threat.mitigation.flash.deleted"), "info")
    return redirect(url_for("threat.scenario_detail", model_id=model.id, scenario_id=scenario.id))
